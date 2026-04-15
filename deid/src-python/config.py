from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


NLP_ENTITY_MAPPING_DEFAULT = {
    "PER": "PERSON",
    "PERSON": "PERSON",
    "NORP": "NRP",
    "FAC": "FACILITY",
    "LOC": "LOCATION",
    "GPE": "LOCATION",
    "LOCATION": "LOCATION",
    "ORG": "ORGANIZATION",
    "ORGANIZATION": "ORGANIZATION",
    "DATE": "DATE_TIME",
    "TIME": "DATE_TIME",
    "MONEY": "MONEY",
}

CONFIG_DEFAULTS: dict[str, Any] = {
    "seed": "global_salt_v1",
    "likeliness": 1.0,
    "consistency": 0.1,
    "spacy_model": "en_core_web_lg",
    "analysis_language": "en",
    "score_threshold": 0.35,
    "low_confidence_score_multiplier": 0.4,
    "low_score_entity_names": ["ORG", "ORGANIZATION"],
    "labels_to_ignore": [],
    "custom_detectors": [],
    "chunk_size_chars": 2000,
    "max_workers": max(1, (os.cpu_count() or 2) - 1),
    "reload_nlp_on_run": False,
    "active_theme": "default",
    "email_domain_pool": ["example.com", "mail.test", "corp.local"],
    "preserve_phone_country_prefix": True,
    "phone_default_region": "US",
    "date_shift_days_min": -365,
    "date_shift_days_max": 365,
    "date_format_profiles": {
        "default": [
            "%m/%d/%Y",
            "%m-%d-%Y",
            "%Y-%m-%d",
            "%m/%d/%Y %H:%M",
            "%m/%d/%Y %I:%M %p",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%B %d, %Y",
        ]
    },
    "reversible_mapping_enabled": False,
    "ollama_endpoint": "http://127.0.0.1:11434",
    "ollama_model": "qwen3.5:9b",
    "ollama_enabled": True,
}

CONFIG_KEYS = tuple(CONFIG_DEFAULTS.keys())

FULL_REBUILD_CONFIG_KEYS = frozenset(
    {
        "spacy_model",
        "analysis_language",
        "score_threshold",
        "max_workers",
        "low_confidence_score_multiplier",
        "low_score_entity_names",
        "labels_to_ignore",
        "custom_detectors",
    }
)

PARTIAL_REBUILD_CONFIG_KEYS = frozenset(
    {
        "seed",
        "likeliness",
        "consistency",
        "active_theme",
        "email_domain_pool",
        "preserve_phone_country_prefix",
        "phone_default_region",
        "date_shift_days_min",
        "date_shift_days_max",
        "date_format_profiles",
        "reversible_mapping_enabled",
    }
)

NO_REBUILD_CONFIG_KEYS = frozenset(
    {
        "chunk_size_chars",
        "reload_nlp_on_run",
        "ollama_endpoint",
        "ollama_model",
        "ollama_enabled",
    }
)


def load_bootstrap_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError("config.yaml must contain an object at the root")
    return data


def resolve_db_path(root_dir: Path, bootstrap: dict[str, Any]) -> Path:
    raw_path = str(bootstrap.get("db_path", "deid.db"))
    db_path = Path(raw_path)
    if not db_path.is_absolute():
        db_path = root_dir / db_path
    return db_path


def build_initial_config_values(bootstrap: dict[str, Any]) -> dict[str, Any]:
    generator = bootstrap.get("generator", {})
    nlp = bootstrap.get("nlp", {})
    processing = bootstrap.get("processing", {})
    anonymization = bootstrap.get("anonymization", {})
    llm = bootstrap.get("llm", {})
    initial_pool = bootstrap.get("initial_name_pool", {})
    active_theme = "default"
    if isinstance(initial_pool, dict) and initial_pool:
        active_theme = next(iter(initial_pool.keys()))

    cpu_default = max(1, (os.cpu_count() or 2) - 1)
    max_workers = int(processing.get("max_workers", cpu_default))
    if max_workers < 1:
        max_workers = cpu_default

    merged_values: dict[str, Any] = dict(CONFIG_DEFAULTS)
    merged_values.update(
        {
            "seed": generator.get("seed", CONFIG_DEFAULTS["seed"]),
            "likeliness": generator.get("likeliness", CONFIG_DEFAULTS["likeliness"]),
            "consistency": generator.get("consistency", CONFIG_DEFAULTS["consistency"]),
            "spacy_model": nlp.get("spacy_model", CONFIG_DEFAULTS["spacy_model"]),
            "analysis_language": nlp.get("language", CONFIG_DEFAULTS["analysis_language"]),
            "score_threshold": nlp.get("score_threshold", CONFIG_DEFAULTS["score_threshold"]),
            "low_confidence_score_multiplier": nlp.get(
                "low_confidence_score_multiplier",
                CONFIG_DEFAULTS["low_confidence_score_multiplier"],
            ),
            "low_score_entity_names": nlp.get(
                "low_score_entity_names",
                CONFIG_DEFAULTS["low_score_entity_names"],
            ),
            "labels_to_ignore": nlp.get("labels_to_ignore", CONFIG_DEFAULTS["labels_to_ignore"]),
            "custom_detectors": nlp.get("custom_detectors", CONFIG_DEFAULTS["custom_detectors"]),
            "chunk_size_chars": processing.get(
                "chunk_size_chars", CONFIG_DEFAULTS["chunk_size_chars"]
            ),
            "max_workers": max_workers,
            "reload_nlp_on_run": processing.get(
                "reload_nlp_on_run", CONFIG_DEFAULTS["reload_nlp_on_run"]
            ),
            "active_theme": active_theme,
            "email_domain_pool": anonymization.get(
                "email_domain_pool", CONFIG_DEFAULTS["email_domain_pool"]
            ),
            "preserve_phone_country_prefix": anonymization.get(
                "preserve_phone_country_prefix",
                CONFIG_DEFAULTS["preserve_phone_country_prefix"],
            ),
            "phone_default_region": anonymization.get(
                "phone_default_region", CONFIG_DEFAULTS["phone_default_region"]
            ),
            "date_shift_days_min": anonymization.get(
                "date_shift_days_min", CONFIG_DEFAULTS["date_shift_days_min"]
            ),
            "date_shift_days_max": anonymization.get(
                "date_shift_days_max", CONFIG_DEFAULTS["date_shift_days_max"]
            ),
            "date_format_profiles": anonymization.get(
                "date_format_profiles", CONFIG_DEFAULTS["date_format_profiles"]
            ),
            "ollama_endpoint": llm.get("endpoint", CONFIG_DEFAULTS["ollama_endpoint"]),
            "ollama_model": llm.get("model", CONFIG_DEFAULTS["ollama_model"]),
            "ollama_enabled": llm.get("enabled", CONFIG_DEFAULTS["ollama_enabled"]),
        }
    )
    return normalize_config(merged_values)


def normalize_config(config: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key in CONFIG_KEYS:
        value = config.get(key, CONFIG_DEFAULTS[key])
        normalized[key] = coerce_config_value(key, value, normalized)
    return normalized


def coerce_config_value(
    key: str, value: Any, current_config: dict[str, Any] | None = None
) -> Any:
    if key not in CONFIG_DEFAULTS:
        raise ValueError(f"Unsupported config key: {key}")

    existing = current_config or {}
    if key in {"seed", "spacy_model", "analysis_language", "active_theme", "phone_default_region"}:
        text = str(value).strip()
        if not text:
            raise ValueError(f"{key} cannot be empty")
        if key == "phone_default_region":
            if len(text) != 2 or not text.isalpha():
                raise ValueError("phone_default_region must be a 2-letter ISO region code")
            return text.upper()
        return text
    if key in {"ollama_endpoint", "ollama_model"}:
        text = str(value).strip()
        if not text:
            raise ValueError(f"{key} cannot be empty")
        return text

    if key in {"likeliness", "score_threshold", "low_confidence_score_multiplier"}:
        numeric = float(value)
        if numeric < 0.0 or numeric > 1.0:
            raise ValueError(f"{key} must be between 0.0 and 1.0")
        return numeric

    if key == "consistency":
        numeric = float(value)
        if numeric < 0.0:
            raise ValueError("consistency must be >= 0.0")
        return numeric

    if key in {"chunk_size_chars", "max_workers", "date_shift_days_min", "date_shift_days_max"}:
        numeric = int(value)
        if key in {"chunk_size_chars", "max_workers"} and numeric < 1:
            raise ValueError(f"{key} must be >= 1")
        if key in {"date_shift_days_min", "date_shift_days_max"} and abs(numeric) > 3650:
            raise ValueError(f"{key} must be within [-3650, 3650]")
        min_days = (
            numeric
            if key == "date_shift_days_min"
            else int(existing.get("date_shift_days_min", CONFIG_DEFAULTS["date_shift_days_min"]))
        )
        max_days = (
            numeric
            if key == "date_shift_days_max"
            else int(existing.get("date_shift_days_max", CONFIG_DEFAULTS["date_shift_days_max"]))
        )
        if min_days > max_days:
            raise ValueError("date_shift_days_min must be <= date_shift_days_max")
        return numeric

    if key in {
        "preserve_phone_country_prefix",
        "reload_nlp_on_run",
        "ollama_enabled",
        "reversible_mapping_enabled",
    }:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"true", "1", "yes", "on"}:
                return True
            if lowered in {"false", "0", "no", "off"}:
                return False
        raise ValueError(f"{key} must be a boolean")

    if key in {"low_score_entity_names", "labels_to_ignore"}:
        values = _coerce_list_of_strings(value, key)
        if key == "low_score_entity_names" and not values:
            raise ValueError("low_score_entity_names must contain at least one value")
        return values

    if key == "custom_detectors":
        if not isinstance(value, list):
            raise ValueError("custom_detectors must be a list of detector objects")
        detectors: list[dict[str, Any]] = []
        for item in value:
            if not isinstance(item, dict):
                raise ValueError("custom_detectors entries must be objects")
            entity_type = str(item.get("entity_type", "")).strip()
            regex = str(item.get("regex", "")).strip()
            name = str(item.get("name", entity_type or "CustomDetector")).strip()
            score = float(item.get("score", 0.7))
            if not entity_type or not regex:
                raise ValueError("custom_detectors entries require entity_type and regex")
            if score < 0.0 or score > 1.0:
                raise ValueError("custom_detectors score must be between 0.0 and 1.0")
            detectors.append(
                {
                    "name": name,
                    "entity_type": entity_type,
                    "regex": regex,
                    "score": score,
                }
            )
        return detectors

    if key == "email_domain_pool":
        domains = _coerce_list_of_strings(value, key)
        if not domains:
            raise ValueError("email_domain_pool must contain at least one domain")
        return domains

    if key == "date_format_profiles":
        if not isinstance(value, dict):
            raise ValueError("date_format_profiles must be an object keyed by profile/theme")
        normalized_profiles: dict[str, list[str]] = {}
        for profile, formats in value.items():
            profile_key = str(profile).strip()
            if not profile_key:
                continue
            if isinstance(formats, str):
                fmt_list = [formats]
            elif isinstance(formats, list):
                fmt_list = [str(item).strip() for item in formats]
            else:
                raise ValueError("date_format_profiles values must be strings or lists of strings")
            cleaned = [fmt for fmt in fmt_list if fmt]
            if cleaned:
                normalized_profiles[profile_key] = list(dict.fromkeys(cleaned))
        if not normalized_profiles:
            raise ValueError("date_format_profiles must contain at least one profile with formats")
        return normalized_profiles

    raise ValueError(f"No coercion rule for config key: {key}")


def _coerce_list_of_strings(value: Any, key: str) -> list[str]:
    if isinstance(value, str):
        items = [part.strip() for part in value.split(",")]
    elif isinstance(value, list):
        items = [str(part).strip() for part in value]
    else:
        raise ValueError(f"{key} must be a list of strings")
    cleaned = [item for item in items if item]
    # Preserve order while removing duplicates.
    return list(dict.fromkeys(cleaned))


def validate_config_rebuild_partitions() -> None:
    known = set(CONFIG_KEYS)
    all_partitions = [
        ("FULL_REBUILD_CONFIG_KEYS", FULL_REBUILD_CONFIG_KEYS),
        ("PARTIAL_REBUILD_CONFIG_KEYS", PARTIAL_REBUILD_CONFIG_KEYS),
        ("NO_REBUILD_CONFIG_KEYS", NO_REBUILD_CONFIG_KEYS),
    ]
    for left_name, left_set in all_partitions:
        for right_name, right_set in all_partitions:
            if left_name >= right_name:
                continue
            overlap = left_set & right_set
            if overlap:
                raise ValueError(
                    f"Config rebuild key overlap detected between {left_name} and {right_name}: {sorted(overlap)}"
                )

    missing = known - (FULL_REBUILD_CONFIG_KEYS | PARTIAL_REBUILD_CONFIG_KEYS | NO_REBUILD_CONFIG_KEYS)
    if missing:
        raise ValueError(f"Config keys missing rebuild strategy: {sorted(missing)}")

    unknown = (
        FULL_REBUILD_CONFIG_KEYS | PARTIAL_REBUILD_CONFIG_KEYS | NO_REBUILD_CONFIG_KEYS
    ) - known
    if unknown:
        raise ValueError(f"Unknown rebuild strategy keys: {sorted(unknown)}")


validate_config_rebuild_partitions()
