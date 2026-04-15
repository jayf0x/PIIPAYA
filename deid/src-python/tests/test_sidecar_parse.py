from __future__ import annotations

import importlib.util
import importlib
from pathlib import Path
import tempfile
import textwrap
import types
import unittest
import zipfile


def load_sidecar_main_module():
    module_path = Path(__file__).resolve().parents[1] / "__main__.py"
    spec = importlib.util.spec_from_file_location("deid_sidecar_main", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load sidecar __main__.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ParseCommandTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_sidecar_main_module()

    def test_parse_command_valid_envelope(self) -> None:
        message_id, command, payload = self.module.parse_command(
            '{"id":"1","command":"PROCESS_TEXT","payload":{"text":"hello"}}'
        )
        self.assertEqual(message_id, "1")
        self.assertEqual(command, "PROCESS_TEXT")
        self.assertEqual(payload, {"text": "hello"})

    def test_parse_command_rejects_invalid_payload_type(self) -> None:
        with self.assertRaises(ValueError):
            self.module.parse_command('{"id":"1","command":"PROCESS_TEXT","payload":[]}')

    def test_location_pool_loader_supports_themes_and_nested_groups(self) -> None:
        service = self.module.SidecarService(Path.cwd())
        pools = service._load_location_pools(
            {
                "location_name_pool": {
                    "default": ["Paris", "Berlin"],
                    "noir": {"cities": ["Chicago"], "countries": ["France"]},
                }
            }
        )
        self.assertEqual(pools["default"], ["Paris", "Berlin"])
        self.assertEqual(pools["noir"], ["Chicago", "France"])

    def test_read_zip_text_combines_supported_documents(self) -> None:
        service = self.module.SidecarService(Path.cwd())
        with tempfile.TemporaryDirectory() as tmp_dir:
            zip_path = Path(tmp_dir) / "bundle.zip"
            with zipfile.ZipFile(zip_path, "w") as archive:
                archive.writestr("a.txt", "hello")
                archive.writestr("nested/b.md", "world")
                archive.writestr("image.png", b"\x89PNG")

            content = service._read_zip_text(zip_path)
            self.assertIn("--- a.txt ---", content)
            self.assertIn("--- nested/b.md ---", content)
            self.assertIn("hello", content)
            self.assertIn("world", content)

    def test_read_pages_text_extracts_xml_payload(self) -> None:
        service = self.module.SidecarService(Path.cwd())
        with tempfile.TemporaryDirectory() as tmp_dir:
            pages_path = Path(tmp_dir) / "sample.pages"
            with zipfile.ZipFile(pages_path, "w") as archive:
                archive.writestr("index.xml", "<root><p>Hello</p><p>World</p></root>")
            content = service._read_supported_text_file(pages_path)
            self.assertIn("Hello", content)
            self.assertIn("World", content)

    def test_read_docx_requires_dependency_when_missing(self) -> None:
        service = self.module.SidecarService(Path.cwd())
        with tempfile.TemporaryDirectory() as tmp_dir:
            docx_path = Path(tmp_dir) / "sample.docx"
            docx_path.write_bytes(b"placeholder")

            original_import_module = importlib.import_module

            def fake_import(name: str):
                if name == "docx":
                    raise ImportError("missing docx")
                return original_import_module(name)

            importlib.import_module = fake_import  # type: ignore[assignment]
            try:
                with self.assertRaises(ValueError) as ctx:
                    service._read_supported_text_file(docx_path)
            finally:
                importlib.import_module = original_import_module  # type: ignore[assignment]

            self.assertIn("python-docx", str(ctx.exception))

    def test_read_pdf_requires_dependency_when_missing(self) -> None:
        service = self.module.SidecarService(Path.cwd())
        with tempfile.TemporaryDirectory() as tmp_dir:
            pdf_path = Path(tmp_dir) / "sample.pdf"
            pdf_path.write_bytes(b"placeholder")

            original_import_module = importlib.import_module

            def fake_import(name: str):
                if name == "pypdf":
                    raise ImportError("missing pypdf")
                return original_import_module(name)

            importlib.import_module = fake_import  # type: ignore[assignment]
            try:
                with self.assertRaises(ValueError) as ctx:
                    service._read_supported_text_file(pdf_path)
            finally:
                importlib.import_module = original_import_module  # type: ignore[assignment]

            self.assertIn("pypdf", str(ctx.exception))

    def test_read_image_requires_macos(self) -> None:
        service = self.module.SidecarService(Path.cwd())
        with tempfile.TemporaryDirectory() as tmp_dir:
            image_path = Path(tmp_dir) / "sample.png"
            image_path.write_bytes(b"fake")

            original_platform = self.module.sys.platform
            self.module.sys.platform = "linux"
            try:
                with self.assertRaises(ValueError) as ctx:
                    service._read_supported_text_file(image_path)
            finally:
                self.module.sys.platform = original_platform

            self.assertIn("macOS only", str(ctx.exception))

    def test_read_image_requires_ocrmac_dependency_when_missing(self) -> None:
        import sys
        from unittest.mock import patch

        service = self.module.SidecarService(Path.cwd())
        with tempfile.TemporaryDirectory() as tmp_dir:
            image_path = Path(tmp_dir) / "sample.png"
            image_path.write_bytes(b"fake")

            original_platform = self.module.sys.platform
            self.module.sys.platform = "darwin"
            try:
                # Blocking "ocrmac.ocrmac" in sys.modules causes ImportError on
                # importlib.import_module("ocrmac.ocrmac"), which _read_image_text
                # then wraps into a ValueError.
                with patch.dict(sys.modules, {"ocrmac.ocrmac": None}):
                    with self.assertRaises(ValueError) as ctx:
                        service._read_supported_text_file(image_path)
            finally:
                self.module.sys.platform = original_platform

            self.assertIn("ocrmac", str(ctx.exception))

    def test_read_image_extracts_text_from_ocrmac_results(self) -> None:
        import sys
        from unittest.mock import patch

        service = self.module.SidecarService(Path.cwd())
        with tempfile.TemporaryDirectory() as tmp_dir:
            image_path = Path(tmp_dir) / "sample.png"
            image_path.write_bytes(b"fake")

            class FakeOCR:
                def __init__(self, _path: str):
                    pass

                def recognize(self):
                    return [("Hello", 0.95, (0, 0, 10, 10)), {"text": "World"}]

            # Inject a fake "ocrmac.ocrmac" module so importlib.import_module
            # returns it without touching the real ocrmac/PIL stack.
            fake_ocrmac_mod = types.SimpleNamespace(OCR=FakeOCR)
            original_platform = self.module.sys.platform
            self.module.sys.platform = "darwin"
            try:
                with patch.dict(sys.modules, {"ocrmac.ocrmac": fake_ocrmac_mod}):
                    content = service._read_supported_text_file(image_path)
            finally:
                self.module.sys.platform = original_platform

            self.assertIn("Hello", content)
            self.assertIn("World", content)

    def test_extract_theme_pack_multiple_shapes(self) -> None:
        service = self.module.SidecarService(Path.cwd())
        one = service._extract_theme_pack({"theme": "lotr", "names": ["Frodo", "Sam"]})
        self.assertEqual(one, {"lotr": ["Frodo", "Sam"]})

        many = service._extract_theme_pack({"themes": {"dickens": ["Pip"], "trek": {"crew": ["Spock"]}}})
        self.assertEqual(many["dickens"], ["Pip"])
        self.assertEqual(many["trek"], ["Spock"])

    def test_active_date_formats_resolve_by_theme(self) -> None:
        service = self.module.SidecarService(Path.cwd())
        service.config = {
            "date_format_profiles": {
                "default": ["%m/%d/%Y"],
                "noir": ["%B %d, %Y"],
            }
        }
        self.assertEqual(service._active_date_formats("noir"), ["%B %d, %Y"])
        self.assertEqual(service._active_date_formats("unknown"), ["%m/%d/%Y"])

    def test_plugin_loader_reads_register_handlers(self) -> None:
        service = self.module.SidecarService(Path.cwd())
        with tempfile.TemporaryDirectory() as tmp_dir:
            plugin_dir = Path(tmp_dir)
            plugin_file = plugin_dir / "demo_plugin.py"
            plugin_file.write_text(
                textwrap.dedent(
                    """
                    def register_handlers():
                        return {
                            "ACME_ID": lambda value: "__ACME_ID__",
                        }
                    """
                ),
                encoding="utf-8",
            )
            service.bootstrap = {"plugin_dir": str(plugin_dir)}
            original_emit_progress = self.module.emit_progress
            self.module.emit_progress = lambda *args, **kwargs: None
            try:
                handlers = service._load_plugin_handlers()
            finally:
                self.module.emit_progress = original_emit_progress
            self.assertIn("ACME_ID", handlers)
            self.assertTrue(callable(handlers["ACME_ID"]))

    def test_build_chunk_segments_marks_replacements(self) -> None:
        service = self.module.SidecarService(Path.cwd())
        mapped_text = "Hello __PERSON__ from __LOCATION__."
        entities = [
            {"entity_type": "PERSON", "output_start": 6, "output_end": 16},
            {"entity_type": "LOCATION", "output_start": 22, "output_end": 34},
        ]
        segments = service._build_chunk_segments(mapped_text, entities)
        self.assertEqual(
            segments,
            [
                {"text": "Hello ", "entity_type": None, "replaced": False},
                {"text": "__PERSON__", "entity_type": "PERSON", "replaced": True},
                {"text": " from ", "entity_type": None, "replaced": False},
                {"text": "__LOCATION__", "entity_type": "LOCATION", "replaced": True},
                {"text": ".", "entity_type": None, "replaced": False},
            ],
        )

    def test_list_spacy_models_marks_installed_and_active(self) -> None:
        service = self.module.SidecarService(Path.cwd())
        service.config = {"spacy_model": "en_core_web_md"}

        original_probe = service._is_spacy_model_installed
        service._is_spacy_model_installed = lambda model: model in {
            "en_core_web_md",
            "en_core_web_sm",
        }
        try:
            models = service._list_spacy_models()
        finally:
            service._is_spacy_model_installed = original_probe

        by_name = {row["name"]: row for row in models}
        self.assertTrue(by_name["en_core_web_sm"]["installed"])
        self.assertTrue(by_name["en_core_web_md"]["active"])
        self.assertFalse(by_name["en_core_web_lg"]["installed"])

    def test_handle_ask_ollama_streams_chunks_and_done(self) -> None:
        service = self.module.SidecarService(Path.cwd())
        service.config = {
            "ollama_endpoint": "http://127.0.0.1:11434",
            "ollama_model": "llama3.1:8b",
            "ollama_enabled": True,
        }

        class _FakeOllama:
            def stream_chat(self, **_kwargs):
                return iter(["Hello ", "there"])

        service.ollama_client = _FakeOllama()
        service.ollama_installed = True
        service.ollama_running = True
        service.ollama_available = True
        service._refresh_ollama_state = lambda boot_if_needed: None

        events: list[tuple[str, dict, str | None]] = []
        original_emit_event = self.module.emit_event
        original_emit_progress = self.module.emit_progress
        original_emit_error = self.module.emit_error
        self.module.emit_event = lambda t, p, message_id=None: events.append((t, p, message_id))
        self.module.emit_progress = lambda *args, **kwargs: None
        self.module.emit_error = lambda *args, **kwargs: None
        try:
            service._handle_ask_ollama(
                "req-1",
                {
                    "target": "input",
                    "instruction": "Switch David with Bruce",
                    "current_text": "David works here.",
                    "other_text": "",
                    "history": [{"role": "user", "content": "old"}],
                },
            )
        finally:
            self.module.emit_event = original_emit_event
            self.module.emit_progress = original_emit_progress
            self.module.emit_error = original_emit_error

        chunk_events = [row for row in events if row[0] == "CHUNK"]
        done_events = [row for row in events if row[0] == "DONE"]
        self.assertEqual(len(chunk_events), 2)
        self.assertEqual(chunk_events[0][1]["stream"], "ollama")
        self.assertEqual(done_events[-1][1]["response"], "Hello there")

    def test_feature_map_excludes_ollama_when_not_installed(self) -> None:
        service = self.module.SidecarService(Path.cwd())
        service.config = {"ollama_enabled": True}
        service.ollama_installed = False
        features = service._feature_map()
        self.assertNotIn("ASK_OLLAMA", features)
        self.assertNotIn("LIST_OLLAMA_MODELS", features)

    def test_feature_map_includes_ollama_when_installed(self) -> None:
        service = self.module.SidecarService(Path.cwd())
        service.config = {"ollama_enabled": True}
        service.ollama_installed = True
        features = service._feature_map()
        self.assertIn("ASK_OLLAMA", features)
        self.assertIn("LIST_OLLAMA_MODELS", features)
        self.assertIn("CANCEL_REQUEST", features)

    def test_cancel_request_marks_target_and_emits_done(self) -> None:
        service = self.module.SidecarService(Path.cwd())
        events: list[tuple[str, dict, str | None]] = []
        original_emit_event = self.module.emit_event
        self.module.emit_event = lambda t, p, message_id=None: events.append((t, p, message_id))
        try:
            service._handle_cancel_request("cancel-1", {"request_id": "req-123"})
        finally:
            self.module.emit_event = original_emit_event

        self.assertTrue(service._is_request_cancelled("req-123"))
        self.assertEqual(events[-1][0], "DONE")
        self.assertEqual(events[-1][1]["request_id"], "req-123")
        self.assertTrue(events[-1][1]["cancelled"])

    def test_reverse_text_command_uses_seeded_reversible_mappings(self) -> None:
        service = self.module.SidecarService(Path.cwd())
        with tempfile.TemporaryDirectory() as tmp_dir:
            db = self.module.DatabaseManager(Path(tmp_dir) / "test.db")
            service.db = db
            service.config = {"seed": "seed-1", "reversible_mapping_enabled": True}
            db.upsert_reversible_mappings("seed-1", [("PERSON", "Alice", "Avery")])

            events: list[tuple[str, dict, str | None]] = []
            errors: list[tuple[str, str, str | None]] = []
            original_emit_event = self.module.emit_event
            original_emit_error = self.module.emit_error
            self.module.emit_event = lambda t, p, message_id=None: events.append((t, p, message_id))
            self.module.emit_error = lambda code, message, message_id=None: errors.append((code, message, message_id))
            try:
                service._handle_reverse_text(
                    "rev-1",
                    {"text": "Avery met Avery in London.", "entities": ["PERSON"]},
                )
            finally:
                self.module.emit_event = original_emit_event
                self.module.emit_error = original_emit_error
                db.close()

            self.assertEqual(errors, [])
            done_events = [row for row in events if row[0] == "DONE"]
            self.assertTrue(done_events)
            payload = done_events[-1][1]
            self.assertEqual(payload["output_text"], "Alice met Alice in London.")
            self.assertEqual(payload["replaced_count"], 2)

    def test_reverse_text_command_requires_feature_enabled(self) -> None:
        service = self.module.SidecarService(Path.cwd())
        service.config = {"seed": "seed-1", "reversible_mapping_enabled": False}

        errors: list[tuple[str, str, str | None]] = []
        original_emit_error = self.module.emit_error
        self.module.emit_error = lambda code, message, message_id=None: errors.append((code, message, message_id))
        try:
            service._handle_reverse_text("rev-2", {"text": "Avery"})
        finally:
            self.module.emit_error = original_emit_error

        self.assertTrue(errors)
        self.assertEqual(errors[-1][0], "REVERSIBLE_MAPPING_DISABLED")

    def test_refresh_ollama_state_enforces_enabled_policy_from_installation(self) -> None:
        service = self.module.SidecarService(Path.cwd())
        service.config = {"ollama_enabled": False, "ollama_endpoint": "http://127.0.0.1:11434", "ollama_model": "qwen3.5:9b"}
        service._setup_ollama_client = lambda: None

        original_which = self.module.shutil.which
        self.module.shutil.which = lambda _cmd: "/usr/local/bin/ollama"
        try:
            service._refresh_ollama_state(boot_if_needed=False)
        finally:
            self.module.shutil.which = original_which

        self.assertTrue(service.config["ollama_enabled"])

    def test_purge_data_deletes_old_reversible_mappings(self) -> None:
        service = self.module.SidecarService(Path.cwd())
        with tempfile.TemporaryDirectory() as tmp_dir:
            db = self.module.DatabaseManager(Path(tmp_dir) / "test.db")
            service.db = db
            service.config = {"seed": "seed-1"}
            db.upsert_reversible_mappings(
                "seed-1",
                [
                    ("PERSON", "Alice", "Avery"),
                    ("PERSON", "Bob", "Jordan"),
                ],
            )
            db.connection.execute(
                """
                UPDATE reversible_mapping
                SET created_at = datetime('now', '-90 days')
                WHERE mapped_value = 'Avery'
                """
            )
            db.connection.commit()

            events: list[tuple[str, dict, str | None]] = []
            original_emit_event = self.module.emit_event
            self.module.emit_event = lambda t, p, message_id=None: events.append((t, p, message_id))
            try:
                service._handle_purge_data("purge-1", {"days": 30})
            finally:
                self.module.emit_event = original_emit_event

            done_events = [row for row in events if row[0] == "DONE"]
            self.assertTrue(done_events)
            self.assertEqual(done_events[-1][1]["deleted_records"], 1)
            remaining = db.list_reversible_mappings("seed-1")
            self.assertEqual(len(remaining), 1)
            self.assertEqual(remaining[0]["mapped_value"], "Jordan")
            db.close()

    def test_preview_file_returns_unsupported_for_unknown_extension(self) -> None:
        service = self.module.SidecarService(Path.cwd())
        with tempfile.TemporaryDirectory() as tmp_dir:
            sample = Path(tmp_dir) / "blob.bin"
            sample.write_bytes(b"\x01\x02\x03")

            events: list[tuple[str, dict, str | None]] = []
            original_emit_event = self.module.emit_event
            self.module.emit_event = lambda t, p, message_id=None: events.append((t, p, message_id))
            try:
                service._handle_preview_file("preview-1", {"path": str(sample)})
            finally:
                self.module.emit_event = original_emit_event

            done_events = [row for row in events if row[0] == "DONE"]
            self.assertTrue(done_events)
            payload = done_events[-1][1]
            self.assertFalse(payload["preview_supported"])

    def test_preview_file_blocks_docx_and_pdf(self) -> None:
        service = self.module.SidecarService(Path.cwd())
        with tempfile.TemporaryDirectory() as tmp_dir:
            for filename in ("sample.docx", "sample.pdf"):
                sample = Path(tmp_dir) / filename
                sample.write_bytes(b"placeholder")

                events: list[tuple[str, dict, str | None]] = []
                original_emit_event = self.module.emit_event
                self.module.emit_event = (
                    lambda t, p, message_id=None: events.append((t, p, message_id))
                )
                try:
                    service._handle_preview_file("preview-2", {"path": str(sample)})
                finally:
                    self.module.emit_event = original_emit_event

                done_events = [row for row in events if row[0] == "DONE"]
                self.assertTrue(done_events)
                payload = done_events[-1][1]
                self.assertFalse(payload["preview_supported"])


if __name__ == "__main__":
    unittest.main()
