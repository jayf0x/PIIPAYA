from __future__ import annotations

import unittest

from config import (
    CONFIG_KEYS,
    FULL_REBUILD_CONFIG_KEYS,
    NLP_ENTITY_MAPPING_DEFAULT,
    NO_REBUILD_CONFIG_KEYS,
    PARTIAL_REBUILD_CONFIG_KEYS,
    build_initial_config_values,
    coerce_config_value,
    normalize_config,
)


class ConfigTests(unittest.TestCase):
    def test_nlp_entity_mapping_includes_money(self) -> None:
        self.assertEqual(NLP_ENTITY_MAPPING_DEFAULT.get("MONEY"), "MONEY")

    def test_build_initial_config_values_includes_rich_settings(self) -> None:
        bootstrap = {
            "generator": {"seed": "abc", "likeliness": 0.8, "consistency": 0.25},
            "nlp": {
                "spacy_model": "en_core_web_lg",
                "language": "en",
                "score_threshold": 0.2,
                "low_confidence_score_multiplier": 0.5,
                "low_score_entity_names": ["ORG"],
                "labels_to_ignore": ["CARDINAL"],
            },
            "processing": {"chunk_size_chars": 1500, "max_workers": 3},
            "anonymization": {
                "email_domain_pool": ["example.org"],
                "preserve_phone_country_prefix": False,
                "date_shift_days_min": -14,
                "date_shift_days_max": 21,
            },
            "llm": {"endpoint": "http://localhost:11434", "model": "qwen2.5:7b"},
            "initial_name_pool": {"custom": ["Alice"]},
        }

        values = build_initial_config_values(bootstrap)
        self.assertEqual(values["seed"], "abc")
        self.assertEqual(values["analysis_language"], "en")
        self.assertEqual(values["low_score_entity_names"], ["ORG"])
        self.assertEqual(values["email_domain_pool"], ["example.org"])
        self.assertFalse(values["preserve_phone_country_prefix"])
        self.assertEqual(values["date_shift_days_min"], -14)
        self.assertEqual(values["date_shift_days_max"], 21)
        self.assertEqual(values["active_theme"], "custom")
        self.assertEqual(values["ollama_endpoint"], "http://localhost:11434")
        self.assertEqual(values["ollama_model"], "qwen2.5:7b")
        self.assertTrue(values["ollama_enabled"])
        self.assertFalse(values["reversible_mapping_enabled"])

    def test_coerce_config_value_rejects_invalid_date_bounds(self) -> None:
        with self.assertRaises(ValueError):
            coerce_config_value(
                "date_shift_days_min",
                10,
                {"date_shift_days_max": 5},
            )

    def test_coerce_config_value_normalizes_lists_and_booleans(self) -> None:
        labels = coerce_config_value("labels_to_ignore", "CARDINAL, DATE", {})
        self.assertEqual(labels, ["CARDINAL", "DATE"])

        phone_prefix = coerce_config_value("preserve_phone_country_prefix", "false", {})
        self.assertFalse(phone_prefix)
        self.assertTrue(coerce_config_value("ollama_enabled", "true", {}))
        self.assertTrue(coerce_config_value("reversible_mapping_enabled", "true", {}))

    def test_normalize_config_fills_defaults(self) -> None:
        normalized = normalize_config({"seed": "x", "spacy_model": "en_core_web_lg"})
        self.assertEqual(normalized["seed"], "x")
        self.assertEqual(normalized["spacy_model"], "en_core_web_lg")
        self.assertIn("email_domain_pool", normalized)
        self.assertIn("analysis_language", normalized)

    def test_custom_detectors_coercion(self) -> None:
        value = coerce_config_value(
            "custom_detectors",
            [
                {
                    "name": "AccountRegex",
                    "entity_type": "ACCOUNT_NUMBER",
                    "regex": r"ACC\d{4}",
                    "score": 0.8,
                }
            ],
            {},
        )
        self.assertEqual(value[0]["entity_type"], "ACCOUNT_NUMBER")
        self.assertEqual(value[0]["regex"], r"ACC\d{4}")

    def test_phone_default_region_coercion(self) -> None:
        region = coerce_config_value("phone_default_region", "be", {})
        self.assertEqual(region, "BE")

    def test_date_format_profiles_coercion(self) -> None:
        profiles = coerce_config_value(
            "date_format_profiles",
            {"default": ["%m/%d/%Y", "%Y-%m-%d"], "noir": "%B %d, %Y"},
            {},
        )
        self.assertEqual(profiles["default"], ["%m/%d/%Y", "%Y-%m-%d"])
        self.assertEqual(profiles["noir"], ["%B %d, %Y"])

    def test_rebuild_key_partitions_cover_all_config_keys(self) -> None:
        all_partitioned = (
            set(FULL_REBUILD_CONFIG_KEYS)
            | set(PARTIAL_REBUILD_CONFIG_KEYS)
            | set(NO_REBUILD_CONFIG_KEYS)
        )
        self.assertEqual(all_partitioned, set(CONFIG_KEYS))
        self.assertEqual(set(FULL_REBUILD_CONFIG_KEYS) & set(PARTIAL_REBUILD_CONFIG_KEYS), set())
        self.assertEqual(set(FULL_REBUILD_CONFIG_KEYS) & set(NO_REBUILD_CONFIG_KEYS), set())
        self.assertEqual(set(PARTIAL_REBUILD_CONFIG_KEYS) & set(NO_REBUILD_CONFIG_KEYS), set())


if __name__ == "__main__":
    unittest.main()
