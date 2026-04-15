from __future__ import annotations

import datetime as dt
import hashlib
import ipaddress
import math
import random
import re
import string
import unicodedata
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit
from dataclasses import dataclass
from typing import Any, Callable

from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer, RecognizerRegistry
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine

from config import NLP_ENTITY_MAPPING_DEFAULT

try:
    import phonenumbers
    from phonenumbers import PhoneNumberFormat
except Exception:  # pragma: no cover - optional runtime dependency
    phonenumbers = None
    PhoneNumberFormat = None


def create_analyzer_engine(
    spacy_model: str,
    language: str = "en",
    low_confidence_score_multiplier: float = 0.4,
    low_score_entity_names: list[str] | None = None,
    labels_to_ignore: list[str] | None = None,
    custom_detectors: list[dict[str, Any]] | None = None,
) -> AnalyzerEngine:
    entity_mapping = dict(NLP_ENTITY_MAPPING_DEFAULT)
    nlp_configuration = {
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": language, "model_name": spacy_model}],
        "ner_model_configuration": {
            "model_to_presidio_entity_mapping": entity_mapping,
            "low_confidence_score_multiplier": low_confidence_score_multiplier,
            "low_score_entity_names": low_score_entity_names or ["ORG", "ORGANIZATION"],
            "labels_to_ignore": labels_to_ignore or [],
        },
    }
    nlp_engine = NlpEngineProvider(nlp_configuration=nlp_configuration).create_engine()
    registry = RecognizerRegistry()
    registry.load_predefined_recognizers(nlp_engine=nlp_engine)
    # Ensure monetary values are detected even when upstream NER misses MONEY labels.
    # Covers symbol/code prefix or suffix and common decimal/thousand separators.
    money_pattern = Pattern(
        name="money_amount",
        # Four alternatives (case-insensitive, verbose):
        #   1. currency-code prefix:  EUR 1,000
        #   2. symbol prefix:         $1,000.00
        #   3. currency-code suffix:  1,000 EUR
        #   4. symbol suffix:         1,000$   (previously missing — caused "2000$" to pass through)
        regex=(
            r"(?ix)"
            r"\b(?:USD|EUR|GBP|JPY|CHF|CAD|AUD|NZD|SEK|NOK|DKK)\b\s?\d{1,3}(?:[.,\s]\d{3})*(?:[.,]\d{2})?"
            r"|[$€£¥]\s?\d{1,3}(?:[.,\s]\d{3})*(?:[.,]\d{2})?"
            r"|\d{1,3}(?:[.,\s]\d{3})*(?:[.,]\d{2})?\s?\b(?:USD|EUR|GBP|JPY|CHF|CAD|AUD|NZD|SEK|NOK|DKK)\b"
            r"|(?<!\d)\d{1,3}(?:[.,\s]\d{3})+(?:[.,]\d{2})?\s?[$€£¥]"
            r"|(?<!\d)\d+(?:[.,]\d+)?\s?[$€£¥]"
        ),
        score=0.6,
    )
    registry.add_recognizer(
        PatternRecognizer(
            supported_entity="MONEY",
            patterns=[money_pattern],
            name="money_pattern_recognizer",
        )
    )
    for detector in custom_detectors or []:
        try:
            pattern = Pattern(
                name=str(detector["name"]),
                regex=str(detector["regex"]),
                score=float(detector["score"]),
            )
            recognizer = PatternRecognizer(
                supported_entity=str(detector["entity_type"]),
                patterns=[pattern],
                name=str(detector["name"]),
            )
            registry.add_recognizer(recognizer)
        except Exception:
            continue
    return AnalyzerEngine(nlp_engine=nlp_engine, registry=registry)


def _stable_int(value: str) -> int:
    return int(hashlib.md5(value.encode("utf-8")).hexdigest(), 16)


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


@dataclass
class DeIDMapper:
    names: list[str]
    seed: str
    likeliness: float
    consistency: float

    def map_value(self, value: str) -> str:
        tokens = [token for token in value.split(" ") if token]
        if not tokens:
            return value

        mapped = " ".join(self._map_token(token) for token in tokens)
        return mapped

    def _map_token(self, token: str) -> str:
        if not self.names:
            return token

        normalized = _strip_accents(token).lower().replace(" ", "")
        if not normalized:
            return token

        n = len(self.names)
        if self.likeliness <= 0.0:
            index = _stable_int(f"{self.seed}:{normalized}") % n
        else:
            alpha = string.ascii_lowercase
            padded = (normalized + "aaa")[:3]
            weights = [alpha.find(ch) + 1 if ch in alpha else 0 for ch in padded]
            base_index = (weights[0] * 26 * 26 + weights[1] * 26 + weights[2]) % n
            seed_offset = _stable_int(f"{self.seed}:{normalized}") % n
            index = int((base_index + seed_offset * (1.0 - self.likeliness)) % n)

        base_name = self.names[index]
        drift_seed = _stable_int(normalized) % 100
        drift = math.sin(drift_seed * self.consistency) * 2
        if abs(drift) <= 1.4:
            return base_name

        mutation_suffixes = ["son", "ton", "ley", "er", "en"]
        suffix = mutation_suffixes[_stable_int(f"suffix:{normalized}") % len(mutation_suffixes)]
        return f"{base_name}{suffix}"


EntityHandler = Callable[[str], str]
KNOWN_COUNTRY_CODES = {
    "1",
    "7",
    "20",
    "27",
    "30",
    "31",
    "32",
    "33",
    "34",
    "39",
    "40",
    "41",
    "43",
    "44",
    "45",
    "46",
    "47",
    "48",
    "49",
    "51",
    "52",
    "53",
    "54",
    "55",
    "56",
    "57",
    "58",
    "60",
    "61",
    "62",
    "63",
    "64",
    "65",
    "66",
    "81",
    "82",
    "84",
    "86",
    "90",
    "91",
    "92",
    "93",
    "94",
    "95",
    "98",
    "211",
    "212",
    "213",
    "216",
    "218",
    "220",
    "221",
    "222",
    "223",
    "224",
    "225",
    "226",
    "227",
    "228",
    "229",
    "230",
    "231",
    "232",
    "233",
    "234",
    "235",
    "236",
    "237",
    "238",
    "239",
    "240",
    "241",
    "242",
    "243",
    "244",
    "245",
    "248",
    "249",
    "250",
    "251",
    "252",
    "253",
    "254",
    "255",
    "256",
    "257",
    "258",
    "260",
    "261",
    "262",
    "263",
    "264",
    "265",
    "266",
    "267",
    "268",
    "269",
    "290",
    "291",
    "297",
    "298",
    "299",
    "350",
    "351",
    "352",
    "353",
    "354",
    "355",
    "356",
    "357",
    "358",
    "359",
    "370",
    "371",
    "372",
    "373",
    "374",
    "375",
    "376",
    "377",
    "378",
    "380",
    "381",
    "382",
    "385",
    "386",
    "387",
    "389",
    "420",
    "421",
    "423",
    "500",
    "501",
    "502",
    "503",
    "504",
    "505",
    "506",
    "507",
    "508",
    "509",
    "590",
    "591",
    "592",
    "593",
    "594",
    "595",
    "596",
    "597",
    "598",
    "599",
    "670",
    "672",
    "673",
    "674",
    "675",
    "676",
    "677",
    "678",
    "679",
    "680",
    "681",
    "682",
    "683",
    "685",
    "686",
    "687",
    "688",
    "689",
    "690",
    "691",
    "692",
    "850",
    "852",
    "853",
    "855",
    "856",
    "880",
    "886",
    "960",
    "961",
    "962",
    "963",
    "964",
    "965",
    "966",
    "967",
    "968",
    "970",
    "971",
    "972",
    "973",
    "974",
    "975",
    "976",
    "977",
    "992",
    "993",
    "994",
    "995",
    "996",
    "998",
}
US_DEFAULT_DATE_FORMATS = [
    "%m/%d/%Y",
    "%m-%d-%Y",
    "%Y-%m-%d",
    "%m/%d/%Y %H:%M",
    "%m/%d/%Y %I:%M %p",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%d %H:%M:%S%z",
    "%b %d, %Y",
    "%B %d, %Y",
    "%B %d, %Y %I:%M %p",
]

MVP_ENTITY_TYPES = [
    "PERSON",
    "LOCATION",
    "ORGANIZATION",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "DATE_TIME",
    "MONEY",
    "NRP",
    "CREDIT_CARD",
    "IP_ADDRESS",
    "MAC_ADDRESS",
    "URL",
    "IBAN_CODE",
    "CRYPTO",
    "MEDICAL_LICENSE",
    "ID",
    "US_BANK_NUMBER",
    "US_DRIVER_LICENSE",
    "US_ITIN",
    "US_PASSPORT",
    "US_SSN",
]


class DeIDEngine:
    def __init__(
        self,
        mapper: DeIDMapper,
        entities_to_mask: list[str],
        global_seed: str,
        location_pool: list[str] | None = None,
        email_domain_pool: list[str] | None = None,
        preserve_phone_country_prefix: bool = True,
        phone_default_region: str = "US",
        date_shift_days_min: int = -365,
        date_shift_days_max: int = 365,
        date_formats: list[str] | None = None,
        handler_overrides: dict[str, EntityHandler] | None = None,
    ) -> None:
        self.mapper = mapper
        self.entities_to_mask = set(entities_to_mask)
        self.global_seed = global_seed
        self.main_analyzer: AnalyzerEngine | None = None
        self.anonymizer = AnonymizerEngine()
        self.session_cache: dict[tuple[str, str], str] = {}
        self.email_domain_pool = email_domain_pool or ["example.com", "mail.test", "corp.local"]
        self.preserve_phone_country_prefix = preserve_phone_country_prefix
        self.phone_default_region = phone_default_region
        self.date_shift_days_min = min(date_shift_days_min, date_shift_days_max)
        self.date_shift_days_max = max(date_shift_days_min, date_shift_days_max)
        self.date_formats = date_formats or list(US_DEFAULT_DATE_FORMATS)

        self.location_mapper: DeIDMapper | None = None
        if location_pool:
            self.location_mapper = DeIDMapper(
                names=location_pool,
                seed=self.mapper.seed,
                likeliness=self.mapper.likeliness,
                consistency=self.mapper.consistency,
            )
        self.handler_registry = self._build_handler_registry(handler_overrides or {})

    def warmup(
        self,
        spacy_model: str,
        language: str = "en",
        low_confidence_score_multiplier: float = 0.4,
        low_score_entity_names: list[str] | None = None,
        labels_to_ignore: list[str] | None = None,
        custom_detectors: list[dict[str, Any]] | None = None,
    ) -> None:
        self.main_analyzer = create_analyzer_engine(
            spacy_model=spacy_model,
            language=language,
            low_confidence_score_multiplier=low_confidence_score_multiplier,
            low_score_entity_names=low_score_entity_names,
            labels_to_ignore=labels_to_ignore,
            custom_detectors=custom_detectors,
        )

    def _build_handler_registry(
        self, overrides: dict[str, EntityHandler]
    ) -> dict[str, EntityHandler]:
        registry: dict[str, EntityHandler] = {
            "PERSON": self._handle_person,
            "LOCATION": self._handle_location,
            "ORGANIZATION": self.mapper.map_value,
            "EMAIL_ADDRESS": self._handle_email_address,
            "PHONE_NUMBER": self._handle_phone_number,
            "DATE_TIME": self._handle_date_time,
            "MONEY": self._handle_money,
            "NRP": self.mapper.map_value,
            "CREDIT_CARD": self._handle_credit_card,
            "IP_ADDRESS": self._handle_ip_address,
            "MAC_ADDRESS": self._handle_mac_address,
            "URL": self._handle_url,
            "IBAN_CODE": self._handle_iban,
            "CRYPTO": self._handle_crypto,
            "MEDICAL_LICENSE": self._handle_generic_id,
            "ID": self._handle_generic_id,
            "US_BANK_NUMBER": self._handle_generic_id,
            "US_DRIVER_LICENSE": self._handle_generic_id,
            "US_ITIN": self._handle_generic_id,
            "US_PASSPORT": self._handle_generic_id,
            "US_SSN": self._handle_generic_id,
        }
        for entity_type in MVP_ENTITY_TYPES:
            registry.setdefault(entity_type, self._placeholder_for(entity_type))
        registry.update(overrides)
        return registry

    def _placeholder_for(self, entity_type: str) -> EntityHandler:
        return lambda _value: f"[{entity_type}]"
    
    def _placeholder(self, entity_type: str):
        return f"[{entity_type}]"

    def _dispatch(self, entity_type: str, raw_value: str) -> str:
        cache_key = (entity_type, raw_value)
        cached = self.session_cache.get(cache_key)
        if cached is not None:
            return cached

        handler = self.handler_registry.get(entity_type)
        if handler is None:
            replacement = f"__{entity_type or 'UNKNOWN'}__"
        else:
            replacement = handler(raw_value)

        self.session_cache[cache_key] = replacement
        return replacement

    def _handle_location(self, value: str) -> str:
        if self.location_mapper is not None and self.location_mapper.names:
            return self.location_mapper.map_value(value)
        return self.mapper.map_value(value)

    def _handle_person(self, value: str) -> str:
        normalized = self._normalize_person_key(value)
        if normalized:
            normalized_key = ("PERSON::NORM", normalized)
            normalized_cached = self.session_cache.get(normalized_key)
            if normalized_cached is not None:
                return normalized_cached

        last_name = normalized.split(" ")[-1] if normalized else ""
        if last_name:
            last_name_key = ("PERSON::LAST", last_name)
            last_name_cached = self.session_cache.get(last_name_key)
            if last_name_cached is not None:
                if normalized:
                    self.session_cache[("PERSON::NORM", normalized)] = last_name_cached
                return last_name_cached

        mapped = self.mapper.map_value(value)
        if normalized:
            # Keep alias keys in the main session cache to avoid layered cache state.
            self.session_cache[("PERSON::NORM", normalized)] = mapped
            if last_name:
                self.session_cache[("PERSON::LAST", last_name)] = mapped
        return mapped

    def _normalize_person_key(self, value: str) -> str:
        lower = _strip_accents(value).lower()
        # Remove common honorifics/titles to reduce variant cache fragmentation.
        lower = re.sub(r"\b(mr|mrs|ms|miss|dr|prof|sir)\.?\b", "", lower)
        lower = re.sub(r"[^a-z0-9\s]", " ", lower)
        lower = re.sub(r"\s+", " ", lower).strip()
        return lower

    def _handle_email_address(self, value: str) -> str:
        local_part, _, original_domain = value.partition("@")
        if not local_part:
            local_part = "user"

        domain = self.email_domain_pool[
            _stable_int(f"{self.global_seed}:{value}:domain") % len(self.email_domain_pool)
        ]
        if "." in original_domain:
            tld = original_domain.rsplit(".", 1)[-1].lower()
            if 2 <= len(tld) <= 12 and tld.isalpha():
                if "." in domain:
                    domain = domain.rsplit(".", 1)[0] + "." + tld
                else:
                    domain = domain + "." + tld

        local_base, local_plus, local_alias = local_part.partition("+")
        pieces = re.split(r"([A-Za-z0-9]+)", local_base)
        mapped_local_parts: list[str] = []
        for piece in pieces:
            if not piece:
                continue
            if re.fullmatch(r"[A-Za-z0-9]+", piece):
                mapped_local_parts.append(self.mapper.map_value(piece).replace(" ", "."))
            else:
                mapped_local_parts.append(piece)
        mapped_local = "".join(mapped_local_parts).strip(".-_+")
        if not mapped_local:
            mapped_local = self.mapper.map_value("user").replace(" ", ".")
        mapped_local = re.sub(r"[._-]{2,}", ".", mapped_local)
        if local_plus and local_alias:
            alias_token = re.sub(r"[^A-Za-z0-9]", "", local_alias) or "alias"
            mapped_alias = self.mapper.map_value(alias_token).replace(" ", "").lower()
            mapped_local += f"+{mapped_alias}"
        return f"{mapped_local}@{domain}"

    def _handle_phone_number(self, value: str) -> str:
        formatted = self._handle_phone_number_with_library(value)
        if formatted is not None:
            return formatted

        rng = random.Random(_stable_int(f"{self.global_seed}:{value}:phone"))
        transformed_chars: list[str] = []
        country_prefix_match = (
            self._match_country_prefix(value) if self.preserve_phone_country_prefix else None
        )
        country_prefix_end = country_prefix_match.end() if country_prefix_match else 0

        for idx, char in enumerate(value):
            if char.isdigit():
                if country_prefix_end and idx < country_prefix_end:
                    transformed_chars.append(char)
                else:
                    transformed_chars.append(str(rng.randint(0, 9)))
            else:
                transformed_chars.append(char)
        return "".join(transformed_chars)

    def _handle_phone_number_with_library(self, value: str) -> str | None:
        if not self.preserve_phone_country_prefix:
            return None
        if phonenumbers is None or PhoneNumberFormat is None:
            return None
        region = None if value.strip().startswith("+") else self.phone_default_region
        try:
            parsed = phonenumbers.parse(value, region)
        except Exception:
            return None
        if not phonenumbers.is_possible_number(parsed):
            return None

        national = str(parsed.national_number)
        if not national:
            return None

        rng = random.Random(_stable_int(f"{self.global_seed}:{value}:phone-lib"))
        mapped_digits = [str(rng.randint(0, 9)) for _ in national]
        if mapped_digits and mapped_digits[0] == "0":
            mapped_digits[0] = str((int(mapped_digits[0]) + 1) % 9 + 1)

        generated = phonenumbers.PhoneNumber()
        generated.country_code = parsed.country_code
        generated.national_number = int("".join(mapped_digits))
        generated.extension = parsed.extension

        if value.strip().startswith("+"):
            return phonenumbers.format_number(generated, PhoneNumberFormat.INTERNATIONAL)
        if any(char in value for char in "()-."):
            return phonenumbers.format_number(generated, PhoneNumberFormat.NATIONAL)
        return phonenumbers.format_number(generated, PhoneNumberFormat.E164)

    def _match_country_prefix(self, value: str) -> re.Match[str] | None:
        match = re.match(r"^\+(\d{1,3})", value)
        if match is None:
            return None
        digits = match.group(1)
        for length in (3, 2, 1):
            if len(digits) >= length and digits[:length] in KNOWN_COUNTRY_CODES:
                return re.match(rf"^\+\d{{{length}}}", value)
        return match

    def _handle_date_time(self, value: str) -> str:
        range_size = max(1, (self.date_shift_days_max - self.date_shift_days_min) + 1)
        offset_days = (_stable_int(f"{self.global_seed}:{value}:date") % range_size) + self.date_shift_days_min

        known_formats = self.date_formats
        clean_value = re.sub(r"(\d+)(st|nd|rd|th)\b", r"\1", value, flags=re.IGNORECASE)

        for time_format in known_formats:
            try:
                parsed = dt.datetime.strptime(clean_value, time_format)
                shifted = parsed + dt.timedelta(days=offset_days)
                rendered = shifted.strftime(time_format)
                if "%z" in time_format and re.search(r"[+-]\d{2}:\d{2}$", clean_value):
                    rendered = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", rendered)
                return rendered
            except ValueError:
                continue

        try:
            parsed_iso = dt.datetime.fromisoformat(clean_value.replace("Z", "+00:00"))
            shifted_iso = parsed_iso + dt.timedelta(days=offset_days)
            if "T" in clean_value:
                has_seconds = clean_value.count(":") >= 2
                as_text = shifted_iso.strftime("%Y-%m-%dT%H:%M:%S" if has_seconds else "%Y-%m-%dT%H:%M")
            elif ":" in clean_value:
                has_seconds = clean_value.count(":") >= 2
                as_text = shifted_iso.strftime("%Y-%m-%d %H:%M:%S" if has_seconds else "%Y-%m-%d %H:%M")
            else:
                as_text = shifted_iso.strftime("%Y-%m-%d")
            if clean_value.endswith("Z"):
                return as_text + "Z"
            if re.search(r"[+-]\d{2}:\d{2}$", clean_value):
                offset = shifted_iso.strftime("%z")
                if offset:
                    return as_text + offset[:3] + ":" + offset[3:]
            return as_text
        except ValueError:
            pass

        # Bare 4-digit year (e.g. "2000" detected by NER as a year).
        # Day-shifting a year-only value rarely crosses a year boundary, so we
        # apply a deterministic year offset directly instead.
        year_only = re.fullmatch(r"\d{4}", clean_value.strip())
        if year_only:
            year = int(clean_value.strip())
            year_shift = (_stable_int(f"{self.global_seed}:{value}:year") % 10) + 1
            return str(year + year_shift)

        return self._placeholder("DATE_TIME")

    def _handle_credit_card(self, value: str) -> str:
        rng = random.Random(_stable_int(f"{self.global_seed}:{value}:credit-card"))
        digits = [char for char in value if char.isdigit()]
        if len(digits) >= 12:
            generated = [str(rng.randint(0, 9)) for _ in range(len(digits) - 1)]
            generated.append(str(self._luhn_check_digit(generated)))
            output: list[str] = []
            idx = 0
            for char in value:
                if char.isdigit():
                    output.append(generated[idx])
                    idx += 1
                else:
                    output.append(char)
            return "".join(output)

        output: list[str] = []
        for char in value:
            if char.isdigit():
                output.append(str(rng.randint(0, 9)))
            else:
                output.append(char)
        return "".join(output)

    def _luhn_check_digit(self, base_digits: list[str]) -> int:
        total = 0
        reversed_digits = [int(d) for d in reversed(base_digits)]
        for index, digit in enumerate(reversed_digits, start=1):
            value = digit
            if index % 2 == 1:
                value *= 2
                if value > 9:
                    value -= 9
            total += value
        return (10 - (total % 10)) % 10

    def _handle_ip_address(self, value: str) -> str:
        try:
            parsed = ipaddress.ip_address(value)
        except ValueError:
            return self._placeholder("IP_ADDRESS")

        rng = random.Random(_stable_int(f"{self.global_seed}:{value}:ip"))
        if isinstance(parsed, ipaddress.IPv4Address):
            # Stay in private RFC1918 ranges for safe, realistic samples.
            private_bases = [(10, rng.randint(0, 255), rng.randint(0, 255), rng.randint(1, 254))]
            base = private_bases[0]
            return ".".join(str(part) for part in base)

        random_bits = rng.getrandbits(128)
        fake_ipv6 = ipaddress.IPv6Address(random_bits)
        return fake_ipv6.compressed

    def _handle_mac_address(self, value: str) -> str:
        # Standard colon/hyphen separated: aa:bb:cc:dd:ee:ff or aa-bb-cc-dd-ee-ff
        for sep in (":", "-"):
            if sep in value:
                groups = value.split(sep)
                rng = random.Random(_stable_int(f"{self.global_seed}:{value}:mac"))
                mapped = [
                    "".join(rng.choice("0123456789ABCDEF") for _ in range(max(1, len(g))))
                    for g in groups
                ]
                return sep.join(mapped)

        # Cisco dot-notation: a1b2.c3d4.e5f6
        if "." in value:
            groups = value.split(".")
            rng = random.Random(_stable_int(f"{self.global_seed}:{value}:mac"))
            mapped = [
                "".join(rng.choice("0123456789abcdef") for _ in range(max(1, len(g))))
                for g in groups
            ]
            return ".".join(mapped)

        # Unseparated 12-char hex: a1b2c3d4e5f6
        clean = re.sub(r"[^0-9a-fA-F]", "", value)
        if len(clean) == 12:
            rng = random.Random(_stable_int(f"{self.global_seed}:{value}:mac"))
            return "".join(rng.choice("0123456789abcdef") for _ in range(12))

        return self._placeholder("MAC_ADDRESS")



    def _rand_url_token(self, seed_key: str, ref_len: int) -> str:
        """Stable seeded random lowercase alphanumeric token, length similar to input."""
        length = max(4, min(16, ref_len))
        rng = random.Random(_stable_int(f"{self.global_seed}:{seed_key}:urltoken"))
        return "".join(rng.choice(string.ascii_lowercase + string.digits) for _ in range(length))

    def _handle_url(self, value: str) -> str:
        try:
            working = value
            scheme_injected = False
            if not re.match(r"^[a-zA-Z][a-zA-Z0-9+\-.]*://", working):
                working = "https://" + working.lstrip("/")
                scheme_injected = True

            parsed = urlsplit(working)
            if not parsed.netloc:
                return self._placeholder('URL')

            mapped_host = self._map_url_host(parsed.hostname or "")
            if not mapped_host:
                return self._placeholder("URL")
            if parsed.port is not None:
                host = f"{mapped_host}:{parsed.port}"
            else:
                host = mapped_host

            path_segments = []
            for seg_idx, segment in enumerate(parsed.path.split("/")):
                if not segment:
                    continue
                mapped = self._rand_url_token(f"path:{seg_idx}:{segment}", len(segment))
                path_segments.append(quote(mapped, safe="-._~"))

            mapped_path = "/" + "/".join(path_segments) if path_segments else parsed.path

            query_pairs = parse_qsl(parsed.query, keep_blank_values=True)
            mapped_query_pairs = []
            for q_idx, (key, val) in enumerate(query_pairs):
                mapped_key = self._rand_url_token(f"qkey:{q_idx}:{key}", len(key))
                mapped_val = self._rand_url_token(f"qval:{q_idx}:{val}", len(val)) if val else ""
                mapped_query_pairs.append((mapped_key, mapped_val))
            mapped_query = urlencode(
                mapped_query_pairs,
                doseq=True,
                quote_via=quote,
                safe="-._~",
            )

            mapped_fragment = (
                quote(
                    self._rand_url_token(f"frag:{parsed.fragment}", len(parsed.fragment)),
                    safe="-._~",
                )
                if parsed.fragment
                else ""
            )

            scheme = "" if scheme_injected else parsed.scheme
            result = urlunsplit((scheme, host, mapped_path, mapped_query, mapped_fragment))
            # urlunsplit emits "//" prefix when scheme is empty — strip it.
            if scheme_injected and result.startswith("//"):
                result = result[2:]
            return result
        except Exception:
            return self._placeholder('URL')

    def _map_url_host(self, hostname: str) -> str:
        clean = hostname.strip().lower().strip(".")
        if not clean:
            return ""
        if re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", clean):
            return clean

        labels = [label for label in clean.split(".") if label]
        if len(labels) < 2:
            return clean

        suffix = labels[-1]
        mapped_labels: list[str] = []
        for label in labels[:-1]:
            token = re.sub(r"[^a-z0-9]", " ", label)
            token = re.sub(r"\s+", " ", token).strip()
            if not token:
                mapped_labels.append(label)
                continue
            mapped = self.mapper.map_value(token).replace(" ", "-").lower()
            mapped = re.sub(r"[^a-z0-9-]", "", mapped)
            mapped = re.sub(r"-{2,}", "-", mapped).strip("-")
            mapped_labels.append(mapped or "anon")
        return ".".join([*mapped_labels, suffix])


    def _handle_iban(self, value: str) -> str:
        rng = random.Random(_stable_int(f"{self.global_seed}:{value}:iban"))
        compact = re.sub(r"\s+", "", value).upper()
        if len(compact) < 5 or not compact[:2].isalpha():
            return self._placeholder('IBAN')

        country = compact[:2]
        bban_len = len(compact) - 4
        bban: list[str] = []
        for idx in range(bban_len):
            src = compact[idx + 4]
            if src.isdigit():
                bban.append(str(rng.randint(0, 9)))
            else:
                bban.append(rng.choice(string.ascii_uppercase))
        bban_text = "".join(bban)

        checksum = self._iban_checksum(country, bban_text)
        result = f"{country}{checksum:02d}{bban_text}"
        output: list[str] = []
        result_idx = 0
        for char in value:
            if char.isalnum():
                output.append(result[result_idx])
                result_idx += 1
            else:
                output.append(char)
        return "".join(output)

    def _iban_checksum(self, country: str, bban: str) -> int:
        rearranged = f"{bban}{country}00"
        numeric = "".join(str(ord(char) - 55) if char.isalpha() else char for char in rearranged)
        mod = int(numeric) % 97
        return 98 - mod

    def _handle_crypto(self, value: str) -> str:
        rng = random.Random(_stable_int(f"{self.global_seed}:{value}:crypto"))
        prefix = "0x" if value.lower().startswith("0x") else ""
        body = value[2:] if prefix else value
        mapped = []
        for char in body:
            if char.isalnum():
                mapped.append(rng.choice("0123456789abcdef"))
            else:
                mapped.append(char)
        return prefix + "".join(mapped)

    def _handle_generic_id(self, value: str) -> str:
        rng = random.Random(_stable_int(f"{self.global_seed}:{value}:id"))
        output: list[str] = []
        for char in value:
            if char.isdigit():
                output.append(str(rng.randint(0, 9)))
            elif char.isalpha():
                alphabet = string.ascii_uppercase if char.isupper() else string.ascii_lowercase
                output.append(rng.choice(alphabet))
            else:
                output.append(char)
        return "".join(output)

    # Currency keywords used to infer a symbol when only written-out text is present.
    _MONEY_TEXT_CURRENCY_MAP: dict[str, str] = {
        "dollar": "$",
        "dollars": "$",
        "euro": "€",
        "euros": "€",
        "pound": "£",
        "pounds": "£",
        "yen": "¥",
        "franc": "CHF",
        "francs": "CHF",
        "krona": "SEK",
        "kronor": "SEK",
        "usd": "USD",
        "eur": "EUR",
        "gbp": "GBP",
        "jpy": "JPY",
        "chf": "CHF",
    }

    def _handle_money(self, value: str) -> str:
        rng = random.Random(_stable_int(f"{self.global_seed}:{value}:money"))
        chars = list(value)
        digit_indices = [idx for idx, char in enumerate(chars) if char.isdigit()]
        if not digit_indices:
            # Text-based amount (e.g. "two thousand euros") — no digits to swap.
            # Detect the currency from keywords and emit a realistic fake numeric amount.
            lower_val = value.lower()
            symbol = "$"
            for keyword, sym in self._MONEY_TEXT_CURRENCY_MAP.items():
                if keyword in lower_val:
                    symbol = sym
                    break
            amount = rng.randint(1, 9_999)
            cents = rng.randint(0, 99)
            return f"{symbol}{amount:,}.{cents:02d}"

        # Generate a replacement number that is significantly different from the original.
        # Strategy: treat all digit characters as a single integer, generate a replacement
        # in the same magnitude range but cyclically shifted by 25-75% of the range so the
        # output is guaranteed to differ substantially from the input.
        digits_str = "".join(chars[i] for i in digit_indices)
        num_digits = len(digits_str)
        original_num = int(digits_str)
        min_val = 10 ** (num_digits - 1) if num_digits > 1 else 0
        max_val = (10 ** num_digits) - 1
        range_size = max_val - min_val + 1
        # Shift by 25–75% of range to guarantee meaningful difference
        shift_frac = rng.randint(range_size // 4, 3 * range_size // 4)
        fake_num = min_val + (original_num - min_val + shift_frac) % range_size
        fake_digits = str(fake_num).zfill(num_digits)
        for pos, char_idx in enumerate(digit_indices):
            chars[char_idx] = fake_digits[pos]
        return "".join(chars)

    def apply_mapping(
        self, chunk_text: str, detections: list[dict[str, Any]], score_threshold: float
    ) -> str:
        output, _ = self.apply_mapping_with_metadata(chunk_text, detections, score_threshold)
        return output

    def apply_mapping_with_metadata(
        self,
        chunk_text: str,
        detections: list[dict[str, Any]],
        score_threshold: float,
        entities_override: list[str] | None = None,
    ) -> tuple[str, list[dict[str, Any]]]:
        allowed_entities = (
            set(entity for entity in entities_override if entity)
            if entities_override
            else self.entities_to_mask
        )
        filtered = [
            d
            for d in detections
            if d.get("entity_type") in allowed_entities and float(d.get("score", 0.0)) >= score_threshold
        ]
        filtered.sort(key=lambda item: (int(item["start"]), -int(item["end"]) + int(item["start"])))

        non_overlapping: list[dict[str, Any]] = []
        last_end = -1
        for detection in filtered:
            start = int(detection["start"])
            end = int(detection["end"])
            if start < last_end:
                continue
            non_overlapping.append(
                {
                    "start": start,
                    "end": end,
                    "entity_type": str(detection.get("entity_type", "")),
                    "score": float(detection.get("score", 0.0)),
                }
            )
            last_end = end

        output_parts: list[str] = []
        cursor = 0
        output_cursor = 0
        mapped_entities: list[dict[str, Any]] = []
        for detection in non_overlapping:
            start = detection["start"]
            end = detection["end"]
            entity_type = str(detection.get("entity_type", ""))
            if cursor < start:
                unchanged = chunk_text[cursor:start]
                output_parts.append(unchanged)
                output_cursor += len(unchanged)
            raw_value = chunk_text[start:end]
            mapped_value = self._dispatch(entity_type, raw_value)
            mapped_start = output_cursor
            mapped_end = mapped_start + len(mapped_value)
            output_parts.append(mapped_value)
            mapped_entities.append(
                {
                    "start": start,
                    "end": end,
                    "entity_type": entity_type,
                    "score": float(detection.get("score", 0.0)),
                    "mapped_value": mapped_value,
                    "output_start": mapped_start,
                    "output_end": mapped_end,
                }
            )
            output_cursor = mapped_end
            cursor = end

        if cursor < len(chunk_text):
            output_parts.append(chunk_text[cursor:])
        output = "".join(output_parts)
        return output, mapped_entities
