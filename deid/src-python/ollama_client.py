from __future__ import annotations

import json
from typing import Any, Callable, Iterable
from urllib import error, request


DEFAULT_OLLAMA_SYSTEM_PROMPT = """You are DeID Edit Assistant.
You receive:
1) A user instruction.
2) Current text context.
3) Optional prior turns (history).

Rules:
- Always ground your answer in the provided context and history.
- If instruction is an edit request, return ONLY the full rewritten target text.
- If instruction is a question or analysis request, return a concise answer grounded in context.
- Never invent context that is not present.
- Keep names/entities coherent when editing unless explicitly asked to change them.
- Do not wrap results in markdown fences.

Editing examples:
- Instruction: "Switch David with Bruce"
  Behavior: replace all occurrences of David with Bruce in the target text and return full updated text.
- Instruction: "delete the section where Johnes reveals his bank notes"
  Behavior: remove only the relevant section and return full updated text.
- Instruction: "shorten this paragraph by 30%"
  Behavior: preserve meaning, reduce length, return full updated text.

Question examples:
- Instruction: "What changed between input and output?"
  Behavior: give a short factual summary.
- Instruction: "Is this output still mentioning bank details?"
  Behavior: answer directly based on the provided text."""


class OllamaClient:
    def __init__(
        self,
        endpoint: str,
        model: str,
        *,
        timeout_seconds: int = 120,
        urlopen_fn: Callable[..., Any] | None = None,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self._urlopen = urlopen_fn or request.urlopen

    @staticmethod
    def build_user_content(
        instruction: str,
        target: str,
        current_text: str,
        other_text: str,
    ) -> str:
        return (
            f"TARGET: {target}\n"
            f"INSTRUCTION:\n{instruction.strip()}\n\n"
            f"CURRENT_TEXT:\n{current_text}\n\n"
            f"OTHER_TEXT:\n{other_text}\n"
        )

    def _build_messages(
        self,
        instruction: str,
        target: str,
        current_text: str,
        other_text: str,
        history: list[dict[str, str]] | None = None,
    ) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = [
            {"role": "system", "content": DEFAULT_OLLAMA_SYSTEM_PROMPT}
        ]
        if history:
            for item in history:
                role = str(item.get("role", "")).strip()
                content = str(item.get("content", "")).strip()
                if role in {"user", "assistant"} and content:
                    messages.append({"role": role, "content": content})
        messages.append(
            {
                "role": "user",
                "content": self.build_user_content(
                    instruction=instruction,
                    target=target,
                    current_text=current_text,
                    other_text=other_text,
                ),
            }
        )
        return messages

    def stream_chat(
        self,
        *,
        instruction: str,
        target: str,
        current_text: str,
        other_text: str,
        history: list[dict[str, str]] | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
    ) -> Iterable[str]:
        options: dict[str, Any] = {
            "temperature": 0.4,
            "top_p": 0.9,
            "seed": 420,
        }
        if isinstance(max_tokens, int) and max_tokens > 0:
            options["num_predict"] = max_tokens

        payload = {
            "model": (model or self.model),
            "messages": self._build_messages(
                instruction=instruction,
                target=target,
                current_text=current_text,
                other_text=other_text,
                history=history,
            ),
            "stream": True,
            "think": False,
            "options": options,
        }
        req = request.Request(
            f"{self.endpoint}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with self._urlopen(req, timeout=self.timeout_seconds) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8").strip()
                if not line:
                    continue
                data = json.loads(line)
                if not isinstance(data, dict):
                    continue
                message = data.get("message", {})
                if isinstance(message, dict):
                    token = str(message.get("content", ""))
                    if token:
                        yield token
                if bool(data.get("done", False)):
                    break

    def is_server_running(self) -> bool:
        try:
            req = request.Request(f"{self.endpoint}/api/tags", method="GET")
            with self._urlopen(req, timeout=max(2, min(self.timeout_seconds, 10))) as response:
                if hasattr(response, "status"):
                    return int(response.status) == 200
                return True
        except Exception:
            return False

    def list_models(self) -> list[str]:
        req = request.Request(f"{self.endpoint}/api/tags", method="GET")
        try:
            with self._urlopen(req, timeout=max(2, min(self.timeout_seconds, 15))) as response:
                body = response.read().decode("utf-8")
        except error.HTTPError as exc:
            raise RuntimeError(f"Ollama HTTP error: {exc.code}") from exc
        except Exception as exc:
            raise RuntimeError(f"Failed to query Ollama models: {exc}") from exc

        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Invalid JSON from Ollama /api/tags") from exc
        models = payload.get("models", [])
        if not isinstance(models, list):
            return []
        names: list[str] = []
        for item in models:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            if name:
                names.append(name)
        return list(dict.fromkeys(names))
