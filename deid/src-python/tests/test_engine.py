from __future__ import annotations

import datetime as dt
import unittest
from unittest.mock import patch
import urllib.parse

import engine as engine_module
from engine import DeIDEngine, DeIDMapper


class _ZeroRandom:
    def __init__(self, _seed: int) -> None:
        pass

    def randint(self, _a: int, _b: int) -> int:
        return 0

    def choice(self, values: str) -> str:
        return values[0]


class EngineHandlerTests(unittest.TestCase):
    def _engine(self, **kwargs: object) -> DeIDEngine:
        mapper = DeIDMapper(
            names=["Alice", "Bob", "Carol"],
            seed="seed-v1",
            likeliness=0.7,
            consistency=0.2,
        )
        return DeIDEngine(
            mapper=mapper,
            entities_to_mask=["PERSON", "PHONE_NUMBER", "DATE_TIME", "LOCATION", "EMAIL_ADDRESS"],
            global_seed="seed-v1",
            **kwargs,
        )

    def test_dispatch_cache_is_entity_type_aware(self) -> None:
        engine = self._engine(handler_overrides={"FOO": lambda _v: "X", "BAR": lambda _v: "Y"})
        self.assertEqual(engine._dispatch("FOO", "same"), "X")
        self.assertEqual(engine._dispatch("BAR", "same"), "Y")
        self.assertEqual(engine.session_cache[("FOO", "same")], "X")
        self.assertEqual(engine.session_cache[("BAR", "same")], "Y")

    def test_location_fallback_placeholder_without_pool(self) -> None:
        engine = self._engine(location_pool=None)
        mapped = engine._dispatch("LOCATION", "Paris")
        self.assertNotEqual(mapped, "__LOCATION__")
        self.assertNotEqual(mapped, "Paris")

    def test_email_uses_configured_domain_pool(self) -> None:
        engine = self._engine(email_domain_pool=["example.internal"])
        mapped = engine._dispatch("EMAIL_ADDRESS", "john@acme.org")
        self.assertTrue(mapped.endswith("@example.org"))

    def test_phone_country_prefix_behavior_is_configurable(self) -> None:
        with patch.object(engine_module.random, "Random", _ZeroRandom):
            keep_engine = self._engine(preserve_phone_country_prefix=True)
            change_engine = self._engine(preserve_phone_country_prefix=False)
            kept = keep_engine._dispatch("PHONE_NUMBER", "+44 20 555")
            self.assertTrue(kept.startswith("+44"))
            self.assertEqual(change_engine._dispatch("PHONE_NUMBER", "+44 20 555"), "+00 00 000")

    def test_phone_detects_one_digit_country_code(self) -> None:
        with patch.object(engine_module.random, "Random", _ZeroRandom):
            engine = self._engine(preserve_phone_country_prefix=True)
            mapped = engine._dispatch("PHONE_NUMBER", "+1 415 555 9999")
            self.assertTrue(mapped.startswith("+1"))
            self.assertNotIn("415", mapped)

    def test_date_shift_respects_configured_bounds(self) -> None:
        engine = self._engine(date_shift_days_min=10, date_shift_days_max=10)
        mapped = engine._dispatch("DATE_TIME", "2026-03-19")
        self.assertEqual(mapped, (dt.date(2026, 3, 19) + dt.timedelta(days=10)).isoformat())

    def test_date_shift_handles_ordinals_and_timezones(self) -> None:
        engine = self._engine(date_shift_days_min=1, date_shift_days_max=1)
        shifted = engine._dispatch("DATE_TIME", "March 1st, 2026 03:40 PM")
        self.assertEqual(shifted, "March 02, 2026 03:40 PM")

        shifted_tz = engine._dispatch("DATE_TIME", "2026-03-19T10:00:00+02:00")
        self.assertEqual(shifted_tz, "2026-03-20T10:00:00+02:00")

    def test_date_time_bare_year_is_shifted_not_placeholder(self) -> None:
        """Bare year strings (detected by NER as a year) must not produce [DATE_TIME]."""
        engine = self._engine()
        for year_str in ("2000", "1995", "2026", "1980"):
            with self.subTest(year=year_str):
                mapped = engine._dispatch("DATE_TIME", year_str)
                self.assertNotEqual(mapped, "[DATE_TIME]")
                self.assertNotEqual(mapped, year_str)
                self.assertRegex(mapped, r"^\d{4}$", "result should still be a 4-digit year")
                self.assertGreater(int(mapped), int(year_str), "year must be shifted forward")

    def test_date_time_natural_language_date_is_shifted(self) -> None:
        """'March 1, 2026' style dates (no ordinal) must shift correctly."""
        engine = self._engine(date_shift_days_min=1, date_shift_days_max=1)
        shifted = engine._dispatch("DATE_TIME", "March 1, 2026")
        self.assertNotEqual(shifted, "[DATE_TIME]")
        self.assertNotEqual(shifted, "March 1, 2026")
        self.assertEqual(shifted, "March 02, 2026")

    def test_date_time_various_formats_never_produce_placeholder(self) -> None:
        """Common real-world date formats must all resolve to a shifted value, never a tag."""
        engine = self._engine()
        inputs = [
            "2026-03-01",
            "03/01/2026",
            "March 1, 2026",
            "March 1st, 2026",
            "2026-03-01T10:30:00",
            "2026-03-01T10:30:00+02:00",
            "2000",
        ]
        for value in inputs:
            with self.subTest(value=value):
                mapped = engine._dispatch("DATE_TIME", value)
                self.assertNotEqual(mapped, "[DATE_TIME]", f"placeholder returned for {value!r}")
                self.assertNotEqual(mapped, value, f"value unchanged for {value!r}")

    def test_domain_specific_id_types_use_realistic_transformers(self) -> None:
        engine = self._engine()
        cc = engine._dispatch("CREDIT_CARD", "4111 1111 1111 1111")
        iban = engine._dispatch("IBAN_CODE", "BE68 5390 0754 7034")
        ssn = engine._dispatch("US_SSN", "123-45-6789")

        self.assertNotEqual(cc, "__CREDIT_CARD__")
        self.assertRegex(cc, r"^\d{4} \d{4} \d{4} \d{4}$")

        self.assertNotEqual(iban, "__IBAN_CODE__")
        self.assertRegex(iban, r"^[A-Z]{2}\d{2}(?: \w{4}){3}$")

        self.assertNotEqual(ssn, "__US_SSN__")
        self.assertRegex(ssn, r"^\d{3}-\d{2}-\d{4}$")

    def test_url_output_remains_parseable(self) -> None:
        engine = self._engine()
        mapped = engine._dispatch("URL", "https://example.org/path/alpha?token=abc#frag")
        parsed = urllib.parse.urlsplit(mapped)
        self.assertTrue(parsed.scheme in {"http", "https"})
        self.assertTrue(bool(parsed.netloc))
        self.assertTrue(mapped.startswith("https://"))

    def test_url_domain_labels_are_deterministic_and_seeded_like_names(self) -> None:
        engine = self._engine()
        original = "https://david.com/path"
        mapped_a = engine._dispatch("URL", original)
        mapped_b = engine._dispatch("URL", original)
        self.assertEqual(mapped_a, mapped_b)
        self.assertNotIn("david.com", mapped_a.lower())
        parsed = urllib.parse.urlsplit(mapped_a)
        self.assertTrue(parsed.netloc.lower().endswith(".com"))
        self.assertTrue(bool(parsed.path))

    def test_url_path_slug_tokens_are_anonymized(self) -> None:
        engine = self._engine()
        mapped = engine._dispatch("URL", "https://example.org/users/james-stuart/profile")
        parsed = urllib.parse.urlsplit(mapped)
        self.assertTrue(bool(parsed.path))
        self.assertEqual(len([part for part in parsed.path.split("/") if part]), 3)
        self.assertNotIn("james", parsed.path.lower())
        self.assertNotIn("stuart", parsed.path.lower())

    def test_core_ui_tags_have_non_placeholder_handlers(self) -> None:
        engine = self._engine()
        self.assertNotEqual(engine._dispatch("PERSON", "David"), "__PERSON__")
        self.assertNotEqual(engine._dispatch("LOCATION", "Brussels"), "__LOCATION__")
        self.assertNotEqual(engine._dispatch("ORGANIZATION", "OpenAI"), "__ORGANIZATION__")
        self.assertNotEqual(engine._dispatch("EMAIL_ADDRESS", "david@example.com"), "__EMAIL_ADDRESS__")
        self.assertNotEqual(engine._dispatch("PHONE_NUMBER", "+1 415 555 1212"), "__PHONE_NUMBER__")
        self.assertNotEqual(engine._dispatch("DATE_TIME", "2026-03-19"), "__DATE_TIME__")
        self.assertNotEqual(engine._dispatch("MONEY", "$123.45"), "__MONEY__")
        self.assertNotEqual(engine._dispatch("URL", "https://david.com"), "__URL__")
        self.assertNotEqual(engine._dispatch("IP_ADDRESS", "192.168.10.1"), "__IP_ADDRESS__")
        self.assertNotEqual(engine._dispatch("CREDIT_CARD", "4111 1111 1111 1111"), "__CREDIT_CARD__")

    def test_money_handler_transforms_digits_and_keeps_formatting(self) -> None:
        engine = self._engine()
        mapped = engine._dispatch("MONEY", "$4,500.75")
        self.assertNotEqual(mapped, "$4,500.75")
        self.assertRegex(mapped, r"^\$\d,\d{3}\.\d{2}$")

    def test_money_suffix_symbol_is_handled(self) -> None:
        """'2000$' (symbol suffix) must be transformed, not left as-is."""
        engine = self._engine()
        for value in ("2000$", "500€", "1234£"):
            with self.subTest(value=value):
                mapped = engine._dispatch("MONEY", value)
                self.assertNotEqual(mapped, "[MONEY]", f"placeholder returned for {value!r}")
                self.assertNotEqual(mapped, value, f"value unchanged for {value!r}")

    def test_money_text_amount_replaced_not_placeholder(self) -> None:
        """Written-out amounts (no digits) must produce a fake numeric value, never [MONEY]."""
        engine = self._engine()
        text_amounts = [
            "two thousand euros",
            "two thousand euro's",
            "five hundred dollars",
            "one million pounds",
            "fifty yen",
        ]
        for value in text_amounts:
            with self.subTest(value=value):
                mapped = engine._dispatch("MONEY", value)
                self.assertNotEqual(mapped, "[MONEY]", f"placeholder returned for {value!r}")
                self.assertNotEqual(mapped, value, f"value unchanged for {value!r}")
                # Must contain at least one digit (fake numeric amount)
                self.assertTrue(any(ch.isdigit() for ch in mapped), f"no digit in result for {value!r}")

    def test_money_text_amount_detects_currency_symbol(self) -> None:
        """Written-out euro amounts must use the € symbol in the replacement."""
        engine = self._engine()
        mapped = engine._dispatch("MONEY", "two thousand euros")
        self.assertIn("€", mapped)

    def test_money_various_formats_never_produce_placeholder(self) -> None:
        """All realistic MONEY detection inputs must resolve to a real value."""
        engine = self._engine()
        inputs = [
            "$4,500.75",
            "€1.200,00",
            "2000$",
            "1000 EUR",
            "USD 500",
            "two thousand euros",
            "500 dollars",
        ]
        for value in inputs:
            with self.subTest(value=value):
                mapped = engine._dispatch("MONEY", value)
                self.assertNotEqual(mapped, "[MONEY]", f"placeholder returned for {value!r}")
                self.assertNotEqual(mapped, value, f"value unchanged for {value!r}")

    def test_money_amount_differs_significantly_from_input(self) -> None:
        """Replacement amount must shift by at least 20% of same-magnitude range."""
        engine = self._engine()
        for value in ("2000$", "$5000", "1000 EUR", "EUR 9999"):
            with self.subTest(value=value):
                mapped = engine._dispatch("MONEY", value)
                # Extract digits from input and output
                in_digits = "".join(c for c in value if c.isdigit())
                out_digits = "".join(c for c in mapped if c.isdigit())
                if in_digits and out_digits and len(in_digits) == len(out_digits):
                    in_num = int(in_digits)
                    out_num = int(out_digits)
                    magnitude = 10 ** len(in_digits)
                    min_delta = magnitude // 5  # 20% of range
                    self.assertGreaterEqual(
                        abs(out_num - in_num), min_delta,
                        f"{value!r}: output {mapped!r} too close to input ({abs(out_num - in_num)} < {min_delta})"
                    )

    def test_money_suffix_4digit_detected_as_whole(self) -> None:
        """'2000$' must match from position 0 (whole token), not '000$' from position 1."""
        import re, sys
        # Replicate the money regex used in create_analyzer_engine
        pattern = re.compile(
            r"(?ix)"
            r"\b(?:USD|EUR|GBP|JPY|CHF|CAD|AUD|NZD|SEK|NOK|DKK)\b\s?\d{1,3}(?:[.,\s]\d{3})*(?:[.,]\d{2})?"
            r"|[$€£¥]\s?\d{1,3}(?:[.,\s]\d{3})*(?:[.,]\d{2})?"
            r"|\d{1,3}(?:[.,\s]\d{3})*(?:[.,]\d{2])?\s?\b(?:USD|EUR|GBP|JPY|CHF|CAD|AUD|NZD|SEK|NOK|DKK)\b"
            r"|(?<!\d)\d{1,3}(?:[.,\s]\d{3})+(?:[.,]\d{2])?\s?[$€£¥]"
            r"|(?<!\d)\d+(?:[.,]\d+)?\s?[$€£¥]"
        )
        m = pattern.search("2000$")
        self.assertIsNotNone(m, "No match found for '2000$'")
        self.assertEqual(m.start(), 0, f"Match started at {m.start()}, expected 0 (got '{m.group()}')")
        self.assertEqual(m.group(), "2000$")

    def test_apply_mapping_with_metadata(self) -> None:
        engine = self._engine()
        text = "Call me at +44 20 555."
        start = text.index("+44")
        end = start + len("+44 20 555")
        output, metadata = engine.apply_mapping_with_metadata(
            text,
            [{"start": start, "end": end, "entity_type": "PHONE_NUMBER", "score": 0.92}],
            score_threshold=0.0,
        )
        self.assertNotEqual(output, text)
        self.assertEqual(len(metadata), 1)
        self.assertEqual(metadata[0]["entity_type"], "PHONE_NUMBER")
        self.assertIn("mapped_value", metadata[0])

    def test_apply_mapping_with_metadata_respects_entities_override(self) -> None:
        engine = self._engine()
        engine.entities_to_mask = {"PERSON"}
        text = "Budget: $4,500.75"
        start = text.index("$")
        end = len(text)
        detections = [{"start": start, "end": end, "entity_type": "MONEY", "score": 0.92}]

        output_without_override, _ = engine.apply_mapping_with_metadata(
            text,
            detections,
            score_threshold=0.0,
        )
        self.assertEqual(output_without_override, text)

        output_with_override, metadata = engine.apply_mapping_with_metadata(
            text,
            detections,
            score_threshold=0.0,
            entities_override=["MONEY"],
        )
        self.assertNotEqual(output_with_override, text)
        self.assertEqual(len(metadata), 1)
        self.assertEqual(metadata[0]["entity_type"], "MONEY")


if __name__ == "__main__":
    unittest.main()
