from __future__ import annotations

import re
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Any, Callable

from presidio_analyzer import AnalyzerEngine

from engine import create_analyzer_engine


_WORKER_ANALYZER: AnalyzerEngine | None = None
_WORKER_SCORE_THRESHOLD: float = 0.35
_WORKER_ENTITIES: tuple[str, ...] = ("PERSON",)
_WORKER_LANGUAGE: str = "en"


def init_worker(
    spacy_model: str,
    language: str,
    score_threshold: float,
    entities_to_mask: list[str],
    low_confidence_score_multiplier: float,
    low_score_entity_names: list[str],
    labels_to_ignore: list[str],
    custom_detectors: list[dict[str, Any]],
) -> None:
    global _WORKER_ANALYZER, _WORKER_SCORE_THRESHOLD, _WORKER_ENTITIES, _WORKER_LANGUAGE
    _WORKER_ANALYZER = create_analyzer_engine(
        spacy_model=spacy_model,
        language=language,
        low_confidence_score_multiplier=low_confidence_score_multiplier,
        low_score_entity_names=low_score_entity_names,
        labels_to_ignore=labels_to_ignore,
        custom_detectors=custom_detectors,
    )
    _WORKER_LANGUAGE = language
    _WORKER_SCORE_THRESHOLD = score_threshold
    supported = set(_WORKER_ANALYZER.get_supported_entities())
    filtered = [entity for entity in entities_to_mask if entity in supported]
    _WORKER_ENTITIES = tuple(filtered) if filtered else tuple(supported)


def analyze_chunk(
    chunk_text: str, entities_override: tuple[str, ...] | None = None
) -> list[dict[str, Any]]:
    if _WORKER_ANALYZER is None:
        raise RuntimeError("Worker analyzer not initialized")

    entities = list(_WORKER_ENTITIES)
    if entities_override:
        supported = set(_WORKER_ANALYZER.get_supported_entities())
        override_filtered = [entity for entity in entities_override if entity in supported]
        if override_filtered:
            entities = override_filtered

    results = _WORKER_ANALYZER.analyze(
        text=chunk_text,
        language=_WORKER_LANGUAGE,
        entities=entities,
        score_threshold=_WORKER_SCORE_THRESHOLD,
    )
    return [
        {
            "start": result.start,
            "end": result.end,
            "entity_type": result.entity_type,
            "score": result.score,
        }
        for result in results
    ]


def analyze_chunk_with_args(
    args: tuple[str, tuple[str, ...] | None]
) -> list[dict[str, Any]]:
    return analyze_chunk(args[0], args[1])


def chunk_text(text: str, chunk_size_chars: int) -> list[str]:
    if not text:
        return [""]

    # Keep paragraph separators so output reassembly remains faithful to input shape.
    pieces = re.split(r"(\n\n)", text)
    chunks: list[str] = []
    current = ""
    for piece in pieces:
        if not piece:
            continue
        if len(piece) > chunk_size_chars and piece != "\n\n":
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(_split_oversized_piece(piece, chunk_size_chars))
            continue
        if current and len(current) + len(piece) > chunk_size_chars:
            chunks.append(current)
            current = piece
            continue
        current += piece

    if current:
        chunks.append(current)
    return chunks or [text]


def _split_oversized_piece(piece: str, chunk_size_chars: int) -> list[str]:
    sentence_candidates = re.split(r"(?<=[.!?])\s+", piece)
    sentence_candidates = [sentence for sentence in sentence_candidates if sentence]
    if not sentence_candidates:
        sentence_candidates = [piece]

    results: list[str] = []
    current = ""
    for sentence in sentence_candidates:
        if len(sentence) > chunk_size_chars:
            if current:
                results.append(current)
                current = ""
            results.extend(
                sentence[idx : idx + chunk_size_chars]
                for idx in range(0, len(sentence), chunk_size_chars)
            )
            continue

        if current and len(current) + 1 + len(sentence) > chunk_size_chars:
            results.append(current)
            current = sentence
            continue

        if current:
            current += " " + sentence
        else:
            current = sentence

    if current:
        results.append(current)
    return results


class WorkerPool:
    def __init__(
        self,
        spacy_model: str,
        language: str,
        score_threshold: float,
        entities_to_mask: list[str],
        max_workers: int,
        low_confidence_score_multiplier: float,
        low_score_entity_names: list[str],
        labels_to_ignore: list[str],
        custom_detectors: list[dict[str, Any]],
    ) -> None:
        self.executor = ProcessPoolExecutor(
            max_workers=max_workers,
            initializer=init_worker,
            initargs=(
                spacy_model,
                language,
                score_threshold,
                entities_to_mask,
                low_confidence_score_multiplier,
                low_score_entity_names,
                labels_to_ignore,
                custom_detectors,
            ),
        )

    def analyze_chunks(
        self,
        chunks: list[str],
        entities_override: list[str] | None = None,
        on_chunk_done: Callable[[int, int], None] | None = None,
    ) -> list[list[dict[str, Any]]]:
        total = len(chunks)
        if total == 0:
            return []

        futures: dict[Any, int] = {}
        if entities_override:
            override = tuple(dict.fromkeys(entity for entity in entities_override if entity))
            for idx, chunk in enumerate(chunks):
                future = self.executor.submit(analyze_chunk_with_args, (chunk, override))
                futures[future] = idx
        else:
            for idx, chunk in enumerate(chunks):
                future = self.executor.submit(analyze_chunk, chunk)
                futures[future] = idx

        ordered: list[list[dict[str, Any]] | None] = [None] * total
        for future in as_completed(futures):
            idx = futures[future]
            try:
                ordered[idx] = future.result()
            except Exception as exc:
                raise RuntimeError(f"Chunk {idx + 1}/{total} analyze failed: {exc}") from exc
            if on_chunk_done is not None:
                on_chunk_done(idx, total)

        return [row or [] for row in ordered]

    def shutdown(self) -> None:
        self.executor.shutdown(wait=True, cancel_futures=True)
