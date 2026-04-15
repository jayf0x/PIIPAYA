from __future__ import annotations

import argparse
import importlib.util
import importlib
import json
import shutil
import signal
import subprocess
import sys
import threading
import time
import zipfile
from pathlib import Path
from typing import Any
import re
import yaml

from config import (
    CONFIG_KEYS,
    FULL_REBUILD_CONFIG_KEYS,
    NO_REBUILD_CONFIG_KEYS,
    PARTIAL_REBUILD_CONFIG_KEYS,
    coerce_config_value,
    build_initial_config_values,
    load_bootstrap_yaml,
    normalize_config,
    resolve_db_path,
)
from database import DatabaseManager
from engine import EntityHandler, MVP_ENTITY_TYPES, DeIDEngine, DeIDMapper
from ollama_client import OllamaClient
from processing import WorkerPool, chunk_text
from protocol import (
    EVENT_CHUNK,
    EVENT_DONE,
    EVENT_READY,
    LOG_TYPE_ENGINE,
    LOG_TYPE_SYSTEM,
    emit_error,
    emit_event,
    emit_progress,
)


COMMAND_PROCESS_TEXT = "PROCESS_TEXT"
COMMAND_PROCESS_FILE = "PROCESS_FILE"
COMMAND_PROCESS_FILES = "PROCESS_FILES"
COMMAND_PREVIEW_FILE = "PREVIEW_FILE"
COMMAND_REVERSE_TEXT = "REVERSE_TEXT"
COMMAND_GET_CONFIG = "GET_CONFIG"
COMMAND_UPDATE_CONFIG = "UPDATE_CONFIG"
COMMAND_LIST_THEMES = "LIST_THEMES"
COMMAND_SET_THEME = "SET_THEME"
COMMAND_IMPORT_THEME_PACK = "IMPORT_THEME_PACK"
COMMAND_LIST_SPACY_MODELS = "LIST_SPACY_MODELS"
COMMAND_INSTALL_SPACY_MODEL = "INSTALL_SPACY_MODEL"
COMMAND_LIST_OLLAMA_MODELS = "LIST_OLLAMA_MODELS"
COMMAND_GET_OLLAMA_MODEL_INFO = "GET_OLLAMA_MODEL_INFO"
COMMAND_ASK_OLLAMA = "ASK_OLLAMA"
COMMAND_CANCEL_REQUEST = "CANCEL_REQUEST"
COMMAND_RESET_DATA = "RESET_DATA"
COMMAND_PURGE_DATA = "PURGE_DATA"
COMMAND_GET_STORAGE_STATS = "GET_STORAGE_STATS"
COMMAND_SHUTDOWN = "SHUTDOWN"

COMMANDS = (
    COMMAND_PROCESS_TEXT,
    COMMAND_PROCESS_FILE,
    COMMAND_PROCESS_FILES,
    COMMAND_PREVIEW_FILE,
    COMMAND_REVERSE_TEXT,
    COMMAND_GET_CONFIG,
    COMMAND_UPDATE_CONFIG,
    COMMAND_LIST_THEMES,
    COMMAND_SET_THEME,
    COMMAND_IMPORT_THEME_PACK,
    COMMAND_LIST_SPACY_MODELS,
    COMMAND_INSTALL_SPACY_MODEL,
    COMMAND_LIST_OLLAMA_MODELS,
    COMMAND_GET_OLLAMA_MODEL_INFO,
    COMMAND_ASK_OLLAMA,
    COMMAND_CANCEL_REQUEST,
    COMMAND_RESET_DATA,
    COMMAND_PURGE_DATA,
    COMMAND_GET_STORAGE_STATS,
    COMMAND_SHUTDOWN,
)

SUPPORTED_SPACY_MODELS = ("en_core_web_sm", "en_core_web_md", "en_core_web_lg")
SUPPORTED_TEXT_FILE_EXTENSIONS = {
    "",
    ".txt",
    ".md",
    ".csv",
    ".json",
    ".log",
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".rb",
    ".go",
    ".rs",
    ".c",
    ".cc",
    ".cpp",
    ".h",
    ".hpp",
    ".sh",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".xml",
    ".html",
    ".css",
    ".sql",
    ".docx",
    ".pdf",
    ".pages",
}
SUPPORTED_IMAGE_FILE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".tif",
    ".tiff",
    ".bmp",
    ".gif",
    ".heic",
}
PREVIEW_BLOCKED_FILE_EXTENSIONS = {
    ".docx",
    ".pdf",
}


class SidecarService:
    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir
        self.db: DatabaseManager | None = None
        self.bootstrap: dict[str, Any] = {}
        self.config: dict[str, Any] = {}
        self.worker_pool: WorkerPool | None = None
        self.engine: DeIDEngine | None = None
        self.mapper: DeIDMapper | None = None
        self.location_pools: dict[str, list[str]] = {}
        self.base_entities_to_mask: list[str] = ["PERSON"]
        self.entities_to_mask: list[str] = ["PERSON"]
        self.running = True
        self.plugin_handlers: dict[str, EntityHandler] = {}
        self.runtime_dirty = False
        self.ollama_client: OllamaClient | None = None
        self.ollama_server_process: subprocess.Popen[bytes] | None = None
        self.ollama_installed = False
        self.ollama_running = False
        self.ollama_available = False
        self.background_tasks: set[threading.Thread] = set()
        self.background_tasks_lock = threading.Lock()
        self.cancelled_requests: set[str] = set()
        self.request_cancel_events: dict[str, threading.Event] = {}
        self.request_cancel_lock = threading.Lock()
        self.request_subprocesses: dict[str, set[subprocess.Popen[str]]] = {}

    def setup(self) -> None:
        config_path = self.root_dir / "config.yaml"
        self.bootstrap = load_bootstrap_yaml(config_path)
        db_path = resolve_db_path(self.root_dir, self.bootstrap)
        is_first_boot = not db_path.exists()
        self.db = DatabaseManager(db_path)

        if is_first_boot:
            initial_config = build_initial_config_values(self.bootstrap)
            initial_pool = self.bootstrap.get("initial_name_pool", {})
            if not isinstance(initial_pool, dict):
                raise ValueError("config.yaml initial_name_pool must be an object")
            self.db.seed_if_empty(initial_config, initial_pool)

        self.config = normalize_config(self.db.get_config())
        if not self.config:
            raise RuntimeError("No runtime config found in database")
        for key, value in self.config.items():
            self._db().update_config(key, value)

        bootstrap_pool = self.bootstrap.get("initial_name_pool", {})
        if isinstance(bootstrap_pool, dict):
            for theme, names in bootstrap_pool.items():
                if isinstance(names, list):
                    self._db().ensure_theme_pool(str(theme), [str(name) for name in names])

        self.base_entities_to_mask = self._load_entities_to_mask(self.bootstrap)
        self.plugin_handlers = self._load_plugin_handlers()
        self._refresh_entities_to_mask()
        self.location_pools = self._load_location_pools(self.bootstrap)
        self._refresh_ollama_state(boot_if_needed=True)
        self._rebuild_runtime(full_reload=True)

    def _setup_ollama_client(self) -> None:
        self.ollama_client = OllamaClient(
            endpoint=str(self.config["ollama_endpoint"]),
            model=str(self.config["ollama_model"]),
        )

    def _is_ollama_enabled(self) -> bool:
        return bool(self.config.get("ollama_enabled", False))

    def _enforce_ollama_enabled_policy(self) -> None:
        desired = bool(self.ollama_installed)
        current = bool(self.config.get("ollama_enabled", False))
        if current == desired:
            return
        self.config["ollama_enabled"] = desired
        if self.db is not None:
            self._db().update_config("ollama_enabled", desired)

    def _base_feature_map(self) -> list[str]:
        return [
            COMMAND_PROCESS_TEXT,
            COMMAND_PROCESS_FILE,
            COMMAND_PROCESS_FILES,
            COMMAND_PREVIEW_FILE,
            COMMAND_REVERSE_TEXT,
            COMMAND_GET_CONFIG,
            COMMAND_UPDATE_CONFIG,
            COMMAND_LIST_THEMES,
            COMMAND_SET_THEME,
            COMMAND_IMPORT_THEME_PACK,
            COMMAND_LIST_SPACY_MODELS,
            COMMAND_INSTALL_SPACY_MODEL,
            COMMAND_GET_STORAGE_STATS,
            COMMAND_RESET_DATA,
            COMMAND_PURGE_DATA,
            COMMAND_SHUTDOWN,
            COMMAND_CANCEL_REQUEST,
        ]

    def _feature_map(self) -> list[str]:
        features = self._base_feature_map()
        if self.ollama_installed:
            features.append(COMMAND_LIST_OLLAMA_MODELS)
            features.append(COMMAND_GET_OLLAMA_MODEL_INFO)
            features.append(COMMAND_ASK_OLLAMA)
        return features

    def _ready_payload(self) -> dict[str, Any]:
        return {
            "feature_map": self._feature_map(),
            "ollama": {
                "enabled": self._is_ollama_enabled(),
                "installed": self.ollama_installed,
                "running": self.ollama_running,
                "available": self.ollama_available,
                "model": str(self.config.get("ollama_model", "")),
            },
        }

    def _boot_ollama_server(self) -> bool:
        if not self.ollama_installed:
            return False
        if self.ollama_server_process is not None and self.ollama_server_process.poll() is None:
            return True
        try:
            self.ollama_server_process = subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
            )
        except Exception:
            self.ollama_server_process = None
            return False
        return True

    def _refresh_ollama_state(self, boot_if_needed: bool) -> None:
        self.ollama_installed = shutil.which("ollama") is not None
        self._enforce_ollama_enabled_policy()
        self.ollama_running = False
        self.ollama_available = False
        self._setup_ollama_client()

        if not self._is_ollama_enabled() or not self.ollama_installed:
            return

        if self.ollama_client is None:
            return

        self.ollama_running = self.ollama_client.is_server_running()
        if not self.ollama_running and boot_if_needed and self._boot_ollama_server():
            for _ in range(20):
                time.sleep(0.25)
                if self.ollama_client.is_server_running():
                    self.ollama_running = True
                    break

        self.ollama_available = self.ollama_running

    def _load_entities_to_mask(self, bootstrap: dict[str, Any]) -> list[str]:
        entities = bootstrap.get("entities_to_mask", MVP_ENTITY_TYPES)
        if not isinstance(entities, list) or not entities:
            return MVP_ENTITY_TYPES
        return [str(entity) for entity in entities]

    def _load_location_pools(self, bootstrap: dict[str, Any]) -> dict[str, list[str]]:
        raw_pool = bootstrap.get("location_name_pool", bootstrap.get("location_pool", []))
        if isinstance(raw_pool, list):
            return {"default": [str(item) for item in raw_pool if str(item).strip()]}
        if not isinstance(raw_pool, dict):
            return {}

        themed: dict[str, list[str]] = {}
        for theme, values in raw_pool.items():
            items = self._flatten_location_values(values)
            if items:
                themed[str(theme)] = items
        return themed

    def _flatten_location_values(self, values: Any) -> list[str]:
        if isinstance(values, str):
            stripped = values.strip()
            return [stripped] if stripped else []
        if isinstance(values, list):
            flattened: list[str] = []
            for item in values:
                flattened.extend(self._flatten_location_values(item))
            return flattened
        if isinstance(values, dict):
            flattened: list[str] = []
            for nested in values.values():
                flattened.extend(self._flatten_location_values(nested))
            return flattened
        return []

    def _active_location_pool(self, active_theme: str) -> list[str]:
        if active_theme in self.location_pools:
            return list(self.location_pools[active_theme])
        if "default" in self.location_pools:
            return list(self.location_pools["default"])
        for pool in self.location_pools.values():
            if pool:
                return list(pool)
        return []

    def _refresh_entities_to_mask(self) -> None:
        configured = list(self.base_entities_to_mask)
        custom = self.config.get("custom_detectors", [])
        if isinstance(custom, list):
            for detector in custom:
                if isinstance(detector, dict):
                    entity_type = str(detector.get("entity_type", "")).strip()
                    if entity_type:
                        configured.append(entity_type)
        configured.extend(self.plugin_handlers.keys())
        self.entities_to_mask = list(dict.fromkeys(configured))

    def _plugin_dir(self) -> Path:
        raw = str(
            self.bootstrap.get(
                "plugin_dir",
                "~/Library/Application Support/deid/plugins/",
            )
        )
        return Path(raw).expanduser()

    def _load_plugin_handlers(self) -> dict[str, EntityHandler]:
        plugin_dir = self._plugin_dir()
        if not plugin_dir.exists() or not plugin_dir.is_dir():
            return {}

        handlers: dict[str, EntityHandler] = {}
        for plugin_file in sorted(plugin_dir.glob("*.py")):
            module_name = f"deid_plugin_{plugin_file.stem}"
            try:
                spec = importlib.util.spec_from_file_location(module_name, plugin_file)
                if spec is None or spec.loader is None:
                    raise RuntimeError("Unable to create module spec")
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                register = getattr(module, "register_handlers", None)
                if not callable(register):
                    raise ValueError("register_handlers() not found")
                registered = register()
                if not isinstance(registered, dict):
                    raise ValueError("register_handlers() must return dict[str, callable]")
                for key, handler in registered.items():
                    entity_type = str(key).strip()
                    if not entity_type or not callable(handler):
                        continue
                    handlers[entity_type] = handler
                emit_progress(
                    f"Loaded plugin handlers from {plugin_file.name} ({len(registered)} entries).",
                    LOG_TYPE_SYSTEM,
                    pct=2,
                    message_id=None,
                )
            except Exception as exc:
                emit_progress(
                    f"Skipped plugin {plugin_file.name}: {exc}",
                    LOG_TYPE_SYSTEM,
                    pct=2,
                    message_id=None,
                )
        return handlers

    def _active_date_formats(self, active_theme: str) -> list[str]:
        profiles = self.config.get("date_format_profiles", {})
        if not isinstance(profiles, dict):
            return []
        raw_formats = profiles.get(active_theme, profiles.get("default", []))
        if isinstance(raw_formats, list):
            return [str(fmt).strip() for fmt in raw_formats if str(fmt).strip()]
        if isinstance(raw_formats, str) and raw_formats.strip():
            return [raw_formats.strip()]
        return []

    def _is_spacy_model_installed(self, model_name: str) -> bool:
        return importlib.util.find_spec(model_name) is not None

    def _list_spacy_models(self) -> list[dict[str, Any]]:
        active = str(self.config.get("spacy_model", ""))
        return [
            {
                "name": model_name,
                "installed": self._is_spacy_model_installed(model_name),
                "active": model_name == active,
            }
            for model_name in SUPPORTED_SPACY_MODELS
        ]

    def _ensure_runtime_ready_for_processing(self, message_id: str | None) -> bool:
        if not self.runtime_dirty:
            return True
        emit_progress(
            "Applying deferred NLP/runtime reload before processing.",
            LOG_TYPE_SYSTEM,
            pct=5,
            message_id=message_id,
        )
        try:
            self._rebuild_runtime(full_reload=True)
            self.runtime_dirty = False
            return True
        except Exception as exc:
            emit_error("RUNTIME_RELOAD_FAILED", str(exc), message_id)
            return False

    def _db(self) -> DatabaseManager:
        if self.db is None:
            raise RuntimeError("Database not initialized")
        return self.db

    def _spawn_background_task(self, target: Any) -> None:
        thread_ref: threading.Thread | None = None

        def _run() -> None:
            try:
                target()
            finally:
                if thread_ref is not None:
                    with self.background_tasks_lock:
                        self.background_tasks.discard(thread_ref)

        thread_ref = threading.Thread(target=_run, daemon=True)
        with self.background_tasks_lock:
            self.background_tasks.add(thread_ref)
        thread_ref.start()

    def _register_request_cancel_event(
        self, message_id: str | None
    ) -> threading.Event | None:
        if not message_id:
            return None
        event = threading.Event()
        with self.request_cancel_lock:
            self.request_cancel_events[message_id] = event
            self.cancelled_requests.discard(message_id)
        return event

    def _clear_request_tracking(self, message_id: str | None) -> None:
        if not message_id:
            return
        with self.request_cancel_lock:
            self.request_cancel_events.pop(message_id, None)
            self.cancelled_requests.discard(message_id)
            procs = self.request_subprocesses.pop(message_id, set())
        for proc in procs:
            if proc.poll() is None:
                try:
                    proc.terminate()
                except Exception:
                    pass

    def _is_request_cancelled(self, message_id: str | None) -> bool:
        if not message_id:
            return False
        with self.request_cancel_lock:
            return message_id in self.cancelled_requests

    def _cancel_request(self, request_id: str) -> None:
        with self.request_cancel_lock:
            self.cancelled_requests.add(request_id)
            event = self.request_cancel_events.get(request_id)
            procs = list(self.request_subprocesses.get(request_id, set()))
        if event is not None:
            event.set()
        for proc in procs:
            if proc.poll() is None:
                try:
                    proc.terminate()
                except Exception:
                    pass

    def _track_subprocess(
        self, message_id: str | None, proc: subprocess.Popen[str]
    ) -> None:
        if not message_id:
            return
        with self.request_cancel_lock:
            refs = self.request_subprocesses.setdefault(message_id, set())
            refs.add(proc)

    def _untrack_subprocess(
        self, message_id: str | None, proc: subprocess.Popen[str]
    ) -> None:
        if not message_id:
            return
        with self.request_cancel_lock:
            refs = self.request_subprocesses.get(message_id)
            if refs is None:
                return
            refs.discard(proc)
            if not refs:
                self.request_subprocesses.pop(message_id, None)

    def _worker(self) -> WorkerPool:
        if self.worker_pool is None:
            raise RuntimeError("Worker pool not initialized")
        return self.worker_pool

    def _runtime(self) -> DeIDEngine:
        if self.engine is None:
            raise RuntimeError("Engine not initialized")
        return self.engine

    def _rebuild_runtime(self, full_reload: bool) -> None:
        db = self._db()
        existing_analyzer = self.engine.main_analyzer if self.engine is not None else None
        active_theme = str(self.config.get("active_theme", "default"))
        if not db.theme_exists(active_theme):
            active_theme = "default"
            self.config["active_theme"] = active_theme
            db.update_config("active_theme", active_theme)

        names = db.get_name_pool(active_theme)
        self.mapper = DeIDMapper(
            names=names,
            seed=str(self.config["seed"]),
            likeliness=float(self.config["likeliness"]),
            consistency=float(self.config["consistency"]),
        )
        self.engine = DeIDEngine(
            mapper=self.mapper,
            entities_to_mask=self.entities_to_mask,
            global_seed=str(self.config["seed"]),
            location_pool=self._active_location_pool(active_theme),
            email_domain_pool=list(self.config["email_domain_pool"]),
            preserve_phone_country_prefix=bool(self.config["preserve_phone_country_prefix"]),
            phone_default_region=str(self.config["phone_default_region"]),
            date_shift_days_min=int(self.config["date_shift_days_min"]),
            date_shift_days_max=int(self.config["date_shift_days_max"]),
            date_formats=self._active_date_formats(active_theme),
            handler_overrides=self.plugin_handlers,
        )

        if full_reload or existing_analyzer is None:
            emit_progress(
                "Loading NLP model and recognizers...",
                LOG_TYPE_SYSTEM,
                pct=3,
                message_id=None,
            )
            self.engine.warmup(
                spacy_model=str(self.config["spacy_model"]),
                language=str(self.config["analysis_language"]),
                low_confidence_score_multiplier=float(self.config["low_confidence_score_multiplier"]),
                low_score_entity_names=list(self.config["low_score_entity_names"]),
                labels_to_ignore=list(self.config["labels_to_ignore"]),
                custom_detectors=list(self.config["custom_detectors"]),
            )
            emit_progress(
                "NLP warmup complete.",
                LOG_TYPE_SYSTEM,
                pct=7,
                message_id=None,
            )
        else:
            self.engine.main_analyzer = existing_analyzer
            emit_progress(
                "Reused warmed NLP analyzer for partial config update.",
                LOG_TYPE_SYSTEM,
                pct=7,
                message_id=None,
            )

        if full_reload:
            if self.worker_pool is not None:
                self.worker_pool.shutdown()
            self.worker_pool = WorkerPool(
                spacy_model=str(self.config["spacy_model"]),
                language=str(self.config["analysis_language"]),
                score_threshold=float(self.config["score_threshold"]),
                entities_to_mask=self.entities_to_mask,
                max_workers=max(1, int(self.config["max_workers"])),
                low_confidence_score_multiplier=float(
                    self.config["low_confidence_score_multiplier"]
                ),
                low_score_entity_names=list(self.config["low_score_entity_names"]),
                labels_to_ignore=list(self.config["labels_to_ignore"]),
                custom_detectors=list(self.config["custom_detectors"]),
            )
            emit_progress(
                "Worker pool initialized.",
                LOG_TYPE_SYSTEM,
                pct=9,
                message_id=None,
            )
            self.runtime_dirty = False

    def handle(self, message_id: str | None, command: str, payload: dict[str, Any]) -> None:
        if command not in COMMANDS:
            emit_error("UNKNOWN_COMMAND", f"Unsupported command: {command}", message_id)
            return

        if command == COMMAND_PROCESS_TEXT:
            self._handle_process_text(message_id, payload)
            return

        if command == COMMAND_PROCESS_FILE:
            self._handle_process_file(message_id, payload)
            return

        if command == COMMAND_PROCESS_FILES:
            self._handle_process_files(message_id, payload)
            return

        if command == COMMAND_PREVIEW_FILE:
            self._handle_preview_file(message_id, payload)
            return

        if command == COMMAND_REVERSE_TEXT:
            self._handle_reverse_text(message_id, payload)
            return

        if command == COMMAND_GET_CONFIG:
            emit_event(EVENT_DONE, {"config": self.config}, message_id=message_id)
            return

        if command == COMMAND_UPDATE_CONFIG:
            self._handle_update_config(message_id, payload)
            return

        if command == COMMAND_LIST_THEMES:
            themes = self._db().list_themes()
            emit_event(EVENT_DONE, {"themes": themes}, message_id=message_id)
            return

        if command == COMMAND_SET_THEME:
            self._handle_set_theme(message_id, payload)
            return

        if command == COMMAND_IMPORT_THEME_PACK:
            self._handle_import_theme_pack(message_id, payload)
            return

        if command == COMMAND_LIST_SPACY_MODELS:
            emit_event(EVENT_DONE, {"models": self._list_spacy_models()}, message_id=message_id)
            return

        if command == COMMAND_INSTALL_SPACY_MODEL:
            self._handle_install_spacy_model(message_id, payload)
            return

        if command == COMMAND_LIST_OLLAMA_MODELS:
            self._handle_list_ollama_models(message_id)
            return

        if command == COMMAND_GET_OLLAMA_MODEL_INFO:
            self._handle_get_ollama_model_info(message_id, payload)
            return

        if command == COMMAND_ASK_OLLAMA:
            self._handle_ask_ollama(message_id, payload)
            return

        if command == COMMAND_CANCEL_REQUEST:
            self._handle_cancel_request(message_id, payload)
            return

        if command == COMMAND_RESET_DATA:
            self._handle_reset_data(message_id)
            return

        if command == COMMAND_PURGE_DATA:
            self._handle_purge_data(message_id, payload)
            return

        if command == COMMAND_GET_STORAGE_STATS:
            self._handle_get_storage_stats(message_id)
            return

        if command == COMMAND_SHUTDOWN:
            emit_progress(
                "Shutdown requested.",
                LOG_TYPE_SYSTEM,
                pct=100,
                message_id=message_id,
            )
            emit_event(EVENT_DONE, {"shutdown": True}, message_id=message_id)
            self.running = False

    def _extract_entities_override(
        self, message_id: str | None, payload: dict[str, Any]
    ) -> list[str] | None:
        raw_entities = payload.get("entities")
        if raw_entities is None:
            return None
        if not isinstance(raw_entities, list):
            emit_error("INVALID_PAYLOAD", "entities must be a list of entity strings", message_id)
            return []
        selected = [str(item).strip() for item in raw_entities if str(item).strip()]
        if not selected:
            emit_error("INVALID_PAYLOAD", "entities list cannot be empty", message_id)
            return []
        return selected

    def _read_supported_text_file(self, file_path: Path) -> str:
        if file_path.suffix.lower() == ".zip":
            return self._read_zip_text(file_path)
        extension = file_path.suffix.lower()
        if extension in SUPPORTED_IMAGE_FILE_EXTENSIONS:
            return self._read_image_text(file_path)
        if extension == ".docx":
            return self._read_docx_text(file_path)
        if extension == ".pdf":
            return self._read_pdf_text(file_path)
        if extension == ".pages":
            return self._read_pages_text(file_path)
        if extension not in SUPPORTED_TEXT_FILE_EXTENSIONS:
            raise ValueError(
                f"Unsupported file type: {file_path.suffix or '[no extension]'} "
                "(supported: text/code formats, .zip, .docx, .pdf, .pages, image formats)"
            )
        return file_path.read_text(encoding="utf-8")

    def _handle_process_file(self, message_id: str | None, payload: dict[str, Any]) -> None:
        path = payload.get("path")
        if not isinstance(path, str) or not path:
            emit_error("INVALID_PAYLOAD", "PROCESS_FILE requires payload.path", message_id)
            return

        file_path = Path(path)
        if not file_path.is_absolute():
            emit_error("INVALID_PAYLOAD", "PROCESS_FILE path must be absolute", message_id)
            return
        if not file_path.exists():
            emit_error("NOT_FOUND", f"File not found: {path}", message_id)
            return

        entities_override = self._extract_entities_override(message_id, payload)
        if entities_override == []:
            return

        try:
            text = self._read_supported_text_file(file_path)
        except Exception as exc:
            emit_error("FILE_READ_FAILED", str(exc), message_id)
            return

        output_text, all_segments = self._anonymize_text(
            message_id=message_id,
            text=text,
            entities_override=entities_override,
            emit_chunks=True,
        )
        if output_text or text == "":
            emit_event(
                EVENT_DONE,
                {
                    "total_chars": len(output_text),
                    "output_text": output_text,
                    "segments": all_segments,
                    "source_text": text,
                    "source_name": file_path.name,
                },
                message_id=message_id,
            )

    def _handle_process_files(self, message_id: str | None, payload: dict[str, Any]) -> None:
        raw_paths = payload.get("paths", [])
        raw_inline_docs = payload.get("inline_docs", [])

        if not isinstance(raw_paths, list):
            emit_error("INVALID_PAYLOAD", "PROCESS_FILES payload.paths must be a list", message_id)
            return
        if not isinstance(raw_inline_docs, list):
            emit_error("INVALID_PAYLOAD", "PROCESS_FILES payload.inline_docs must be a list", message_id)
            return

        entities_override = self._extract_entities_override(message_id, payload)
        if entities_override == []:
            return

        docs: list[tuple[str, str]] = []
        for raw_path in raw_paths:
            if not isinstance(raw_path, str) or not raw_path:
                emit_error("INVALID_PAYLOAD", "PROCESS_FILES paths entries must be non-empty strings", message_id)
                return
            file_path = Path(raw_path)
            if not file_path.is_absolute():
                emit_error("INVALID_PAYLOAD", "PROCESS_FILES paths must be absolute", message_id)
                return
            if not file_path.exists():
                emit_error("NOT_FOUND", f"File not found: {raw_path}", message_id)
                return
            try:
                content = self._read_supported_text_file(file_path)
            except Exception as exc:
                emit_error("FILE_READ_FAILED", str(exc), message_id)
                return
            docs.append((file_path.name, content))

        for row in raw_inline_docs:
            if not isinstance(row, dict):
                emit_error("INVALID_PAYLOAD", "PROCESS_FILES inline_docs entries must be objects", message_id)
                return
            name = str(row.get("name", "inline.txt")).strip() or "inline.txt"
            text = row.get("text")
            if not isinstance(text, str):
                emit_error("INVALID_PAYLOAD", "PROCESS_FILES inline_docs.text must be a string", message_id)
                return
            docs.append((name, text))

        if not docs:
            emit_error("INVALID_PAYLOAD", "PROCESS_FILES requires at least one path or inline document", message_id)
            return

        emit_event(
            EVENT_CHUNK,
            {
                "stream": "file_progress",
                "phase": "queue",
                "files": [
                    {
                        "file_index": idx,
                        "file_total": len(docs),
                        "name": name,
                        "status": "queued",
                        "progress_pct": 0,
                        "detail": "Queued",
                    }
                    for idx, (name, _content) in enumerate(docs, start=1)
                ],
            },
            message_id=message_id,
        )

        output_files: list[dict[str, Any]] = []
        total_chars = 0
        for idx, (name, content) in enumerate(docs, start=1):
            emit_event(
                EVENT_CHUNK,
                {
                    "stream": "file_progress",
                    "phase": "processing",
                    "file_index": idx,
                    "file_total": len(docs),
                    "name": name,
                    "status": "processing",
                    "progress_pct": 5,
                    "detail": f"Processing {idx}/{len(docs)}",
                },
                message_id=message_id,
            )
            emit_progress(
                f"Processing file {idx}/{len(docs)}: {name}",
                LOG_TYPE_SYSTEM,
                pct=8,
                message_id=message_id,
            )
            try:
                mapped_text, mapped_segments = self._anonymize_text(
                    message_id=message_id,
                    text=content,
                    entities_override=entities_override,
                    emit_chunks=False,
                )
            except Exception as exc:
                emit_event(
                    EVENT_CHUNK,
                    {
                        "stream": "file_progress",
                        "phase": "failed",
                        "file_index": idx,
                        "file_total": len(docs),
                        "name": name,
                        "status": "failed",
                        "progress_pct": 0,
                        "detail": str(exc),
                    },
                    message_id=message_id,
                )
                emit_error("PROCESS_FILES_FAILED", f"{name}: {exc}", message_id)
                return
            total_chars += len(mapped_text)
            output_files.append(
                {
                    "name": name,
                    "text": mapped_text,
                    "segments": mapped_segments,
                    "source_text": content,
                }
            )
            emit_event(
                EVENT_CHUNK,
                {
                    "stream": "file_progress",
                    "phase": "done",
                    "file_index": idx,
                    "file_total": len(docs),
                    "name": name,
                    "status": "done",
                    "progress_pct": 100,
                    "detail": f"Done ({len(mapped_text)} chars)",
                },
                message_id=message_id,
            )
            emit_event(
                EVENT_CHUNK,
                {"text": f"\n\n--- {name} ---\n\n{mapped_text}", "segments": []},
                message_id=message_id,
            )

        emit_event(
            EVENT_DONE,
            {
                "total_chars": total_chars,
                "files": output_files,
                "output_text": "\n\n".join(
                    f"--- {row['name']} ---\n\n{row['text']}" for row in output_files
                ),
            },
            message_id=message_id,
        )

    def _handle_preview_file(self, message_id: str | None, payload: dict[str, Any]) -> None:
        path = payload.get("path")
        if not isinstance(path, str) or not path:
            emit_error("INVALID_PAYLOAD", "PREVIEW_FILE requires payload.path", message_id)
            return
        file_path = Path(path)
        if not file_path.is_absolute():
            emit_error("INVALID_PAYLOAD", "PREVIEW_FILE path must be absolute", message_id)
            return
        if not file_path.exists():
            emit_error("NOT_FOUND", f"File not found: {path}", message_id)
            return

        extension = file_path.suffix.lower()
        file_type = extension or "[no extension]"
        if extension in PREVIEW_BLOCKED_FILE_EXTENSIONS:
            emit_event(
                EVENT_DONE,
                {
                    "name": file_path.name,
                    "file_type": file_type,
                    "preview_supported": False,
                    "preview_text": "",
                    "message": "Preview not supported for this file type.",
                },
                message_id=message_id,
            )
            return
        try:
            preview_text = self._read_supported_text_file(file_path)
            emit_event(
                EVENT_DONE,
                {
                    "name": file_path.name,
                    "file_type": file_type,
                    "preview_supported": True,
                    "preview_text": preview_text[:60000],
                },
                message_id=message_id,
            )
        except Exception as exc:
            emit_event(
                EVENT_DONE,
                {
                    "name": file_path.name,
                    "file_type": file_type,
                    "preview_supported": False,
                    "preview_text": "",
                    "message": str(exc),
                },
                message_id=message_id,
            )

    def _read_zip_text(self, file_path: Path) -> str:
        supported_extensions = {".txt", ".md", ".csv", ".json", ".log"}
        docs: list[str] = []
        with zipfile.ZipFile(file_path, "r") as archive:
            for member in archive.infolist():
                if member.is_dir():
                    continue
                ext = Path(member.filename).suffix.lower()
                if ext and ext not in supported_extensions:
                    continue
                with archive.open(member, "r") as handle:
                    data = handle.read()
                try:
                    content = data.decode("utf-8")
                except UnicodeDecodeError:
                    content = data.decode("utf-8", errors="ignore")
                if content.strip():
                    docs.append(f"\n\n--- {member.filename} ---\n\n{content}")

        if not docs:
            raise ValueError("No supported text files found in ZIP archive")
        return "".join(docs).lstrip()

    def _read_docx_text(self, file_path: Path) -> str:
        try:
            docx_module = importlib.import_module("docx")
        except Exception as exc:
            raise ValueError("DOCX support requires 'python-docx' to be installed") from exc

        document = docx_module.Document(str(file_path))
        lines = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
        if not lines:
            raise ValueError("DOCX file contains no readable text")
        return "\n".join(lines)

    def _read_pdf_text(self, file_path: Path) -> str:
        try:
            pypdf_module = importlib.import_module("pypdf")
        except Exception as exc:
            raise ValueError("PDF support requires 'pypdf' to be installed") from exc

        reader = pypdf_module.PdfReader(str(file_path))
        lines: list[str] = []
        for page in reader.pages:
            text = page.extract_text() or ""
            clean = text.strip()
            if clean:
                lines.append(clean)
        if not lines:
            raise ValueError("PDF file contains no extractable text")
        return "\n\n".join(lines)

    def _read_pages_text(self, file_path: Path) -> str:
        try:
            with zipfile.ZipFile(file_path, "r") as archive:
                candidates = ("index.xml", "Index/Document.iwa", "preview-metadata.json")
                payload = None
                selected_name = ""
                for candidate in candidates:
                    if candidate in archive.namelist():
                        payload = archive.read(candidate)
                        selected_name = candidate
                        break
                if payload is None:
                    raise ValueError("Pages file does not contain a supported text container")
        except zipfile.BadZipFile as exc:
            raise ValueError("Invalid .pages file (not a valid zip archive)") from exc

        if selected_name.endswith(".json"):
            raw = payload.decode("utf-8", errors="ignore")
            match = re.findall(r'"(title|subject|comment|description)"\s*:\s*"([^"]+)"', raw, flags=re.IGNORECASE)
            values = [value.strip() for _key, value in match if value.strip()]
            if values:
                return "\n".join(values)
            raise ValueError("Pages metadata contains no readable text")

        if selected_name.endswith(".iwa"):
            raise ValueError("Pages file uses IWA container; text extraction is not supported for this version")

        xml_text = payload.decode("utf-8", errors="ignore")
        extracted = re.sub(r"<[^>]+>", " ", xml_text)
        extracted = re.sub(r"\s+", " ", extracted).strip()
        if not extracted:
            raise ValueError("Pages file contains no readable text")
        return extracted

    def _read_image_text(self, file_path: Path) -> str:
        if sys.platform != "darwin":
            raise ValueError("Image OCR is currently supported on macOS only")

        try:
            ocrmac_mod = importlib.import_module("ocrmac.ocrmac")
        except Exception as exc:
            raise ValueError("Image OCR requires 'ocrmac' to be installed (macOS only)") from exc
        raw_results = ocrmac_mod.OCR(str(file_path)).recognize()

        lines: list[str] = []
        if isinstance(raw_results, list):
            for row in raw_results:
                if isinstance(row, str):
                    text = row.strip()
                    if text:
                        lines.append(text)
                    continue
                if isinstance(row, dict):
                    text = str(row.get("text", "")).strip()
                    if text:
                        lines.append(text)
                    continue
                if isinstance(row, (tuple, list)) and row:
                    text = str(row[0]).strip()
                    if text:
                        lines.append(text)

        if not lines:
            raise ValueError("Image OCR returned no readable text")
        return "\n".join(lines)

    def _handle_process_text(self, message_id: str | None, payload: dict[str, Any]) -> None:
        text = payload.get("text")
        if not isinstance(text, str):
            emit_error("INVALID_PAYLOAD", "PROCESS_TEXT requires payload.text", message_id)
            return
        entities_override = self._extract_entities_override(message_id, payload)
        if entities_override == []:
            return
        theme_override_raw = payload.get("theme")
        theme_override = None
        if theme_override_raw is not None:
            if not isinstance(theme_override_raw, str) or not theme_override_raw.strip():
                emit_error("INVALID_PAYLOAD", "PROCESS_TEXT payload.theme must be a non-empty string", message_id)
                return
            theme_candidate = theme_override_raw.strip()
            if not self._db().theme_exists(theme_candidate):
                emit_error("INVALID_THEME", f"Theme not found: {theme_candidate}", message_id)
                return
            theme_override = theme_candidate

        score_override_raw = payload.get("score_threshold")
        score_override = None
        if score_override_raw is not None:
            if not isinstance(score_override_raw, (int, float)):
                emit_error("INVALID_PAYLOAD", "PROCESS_TEXT payload.score_threshold must be a number", message_id)
                return
            score_override = max(0.0, min(1.0, float(score_override_raw)))

        original_theme = str(self.config.get("active_theme", "default"))
        original_score = float(self.config.get("score_threshold", 0.35))
        theme_changed = bool(theme_override and theme_override != original_theme)
        score_changed = score_override is not None and score_override != original_score

        try:
            if theme_changed:
                self.config["active_theme"] = str(theme_override)
                self._rebuild_runtime(full_reload=False)
            if score_changed:
                self.config["score_threshold"] = float(score_override)
            self._process_text(message_id, text, entities_override=entities_override)
        finally:
            if score_changed:
                self.config["score_threshold"] = original_score
            if theme_changed:
                self.config["active_theme"] = original_theme
                self._rebuild_runtime(full_reload=False)

    def _anonymize_text(
        self,
        message_id: str | None,
        text: str,
        entities_override: list[str] | None = None,
        emit_chunks: bool = True,
        emit_events: bool = True,
    ) -> tuple[str, list[dict[str, Any]]]:
        if not self._ensure_runtime_ready_for_processing(message_id):
            return "", []
        score_threshold = float(self.config["score_threshold"])
        chunk_size = max(1, int(self.config["chunk_size_chars"]))
        chunks = chunk_text(text, chunk_size)

        if emit_events:
            emit_progress(
                f"Queued {len(chunks)} chunks.",
                LOG_TYPE_SYSTEM,
                pct=12,
                message_id=message_id,
            )

        try:
            analyzed_done = 0

            def _analysis_done(_idx: int, total: int) -> None:
                nonlocal analyzed_done
                analyzed_done += 1
                if not emit_events:
                    return
                pct = 12 + int((analyzed_done / max(1, total)) * 38)
                emit_progress(
                    f"Analyzed chunk {analyzed_done}/{total}",
                    LOG_TYPE_ENGINE,
                    pct=pct,
                    message_id=message_id,
                )

            analyzed_chunks = self._worker().analyze_chunks(
                chunks, entities_override=entities_override, on_chunk_done=_analysis_done
            )
        except Exception as exc:
            if emit_events:
                emit_error("ANALYZE_FAILED", str(exc), message_id)
            else:
                raise
            return "", []

        output_parts: list[str] = []
        all_segments: list[dict[str, Any]] = []
        reversible_rows: list[tuple[str, str, str]] = []
        for idx, (chunk, detections) in enumerate(zip(chunks, analyzed_chunks), start=1):
            mapped_text, mapped_entities = self._runtime().apply_mapping_with_metadata(
                chunk,
                detections,
                score_threshold,
                entities_override=entities_override,
            )
            if bool(self.config.get("reversible_mapping_enabled", False)):
                for entity in mapped_entities:
                    entity_type = str(entity.get("entity_type", "")).strip()
                    start = int(entity.get("start", 0))
                    end = int(entity.get("end", start))
                    mapped_value = str(entity.get("mapped_value", ""))
                    if not entity_type or not mapped_value:
                        continue
                    raw_value = chunk[start:end]
                    if not raw_value or raw_value == mapped_value:
                        continue
                    reversible_rows.append((entity_type, raw_value, mapped_value))
            segments = self._build_chunk_segments(mapped_text, mapped_entities)
            output_parts.append(mapped_text)
            all_segments.extend(segments)
            if emit_chunks and emit_events:
                emit_event(
                    EVENT_CHUNK,
                    {"text": mapped_text, "segments": segments},
                    message_id=message_id,
                )

            if emit_events:
                pct = 50 + int((idx / max(1, len(chunks))) * 48)
                emit_progress(
                    f"Mapped chunk {idx}/{len(chunks)}",
                    LOG_TYPE_ENGINE,
                    pct=pct,
                    message_id=message_id,
                )

        if reversible_rows:
            # Persist first-seen mappings by seed to allow future reverse transformations.
            self._db().upsert_reversible_mappings(str(self.config["seed"]), reversible_rows)

        return "".join(output_parts), all_segments

    def _handle_reverse_text(self, message_id: str | None, payload: dict[str, Any]) -> None:
        text = payload.get("text")
        if not isinstance(text, str):
            emit_error("INVALID_PAYLOAD", "REVERSE_TEXT requires payload.text", message_id)
            return
        if not bool(self.config.get("reversible_mapping_enabled", False)):
            emit_error(
                "REVERSIBLE_MAPPING_DISABLED",
                "Enable reversible_mapping_enabled before using REVERSE_TEXT",
                message_id,
            )
            return
        entities_override = self._extract_entities_override(message_id, payload)
        if entities_override == []:
            return

        mappings = self._db().list_reversible_mappings(
            seed=str(self.config["seed"]),
            entity_types=entities_override,
        )
        if not mappings:
            emit_event(
                EVENT_DONE,
                {
                    "total_chars": len(text),
                    "output_text": text,
                    "replaced_count": 0,
                    "mapping_count": 0,
                },
                message_id=message_id,
            )
            return

        reversed_text = text
        replaced_count = 0
        for row in mappings:
            mapped_value = row["mapped_value"]
            original_value = row["original_value"]
            if not mapped_value:
                continue
            occurrences = reversed_text.count(mapped_value)
            if occurrences <= 0:
                continue
            reversed_text = reversed_text.replace(mapped_value, original_value)
            replaced_count += occurrences

        emit_event(
            EVENT_DONE,
            {
                "total_chars": len(reversed_text),
                "output_text": reversed_text,
                "replaced_count": replaced_count,
                "mapping_count": len(mappings),
            },
            message_id=message_id,
        )

    def _process_text(
        self, message_id: str | None, text: str, entities_override: list[str] | None = None
    ) -> None:
        output_text, all_segments = self._anonymize_text(
            message_id=message_id,
            text=text,
            entities_override=entities_override,
            emit_chunks=True,
        )
        if output_text or text == "":
            emit_event(
                EVENT_DONE,
                {
                    "total_chars": len(output_text),
                    "output_text": output_text,
                    "segments": all_segments,
                },
                message_id=message_id,
            )

    def cli_process_text(
        self, text: str, entities_override: list[str] | None = None
    ) -> str:
        output_text, _ = self._anonymize_text(
            message_id=None,
            text=text,
            entities_override=entities_override,
            emit_chunks=False,
            emit_events=False,
        )
        return output_text

    def _build_chunk_segments(
        self, mapped_text: str, mapped_entities: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        if not mapped_entities:
            return [{"text": mapped_text, "entity_type": None, "replaced": False}]
        segments: list[dict[str, Any]] = []
        cursor = 0
        for entity in mapped_entities:
            start = int(entity.get("output_start", 0))
            end = int(entity.get("output_end", start))
            entity_type = str(entity.get("entity_type", ""))
            if cursor < start:
                segments.append(
                    {
                        "text": mapped_text[cursor:start],
                        "entity_type": None,
                        "replaced": False,
                    }
                )
            segments.append(
                {
                    "text": mapped_text[start:end],
                    "entity_type": entity_type or None,
                    "replaced": True,
                }
            )
            cursor = end
        if cursor < len(mapped_text):
            segments.append(
                {
                    "text": mapped_text[cursor:],
                    "entity_type": None,
                    "replaced": False,
                }
            )
        return segments

    def _handle_update_config(self, message_id: str | None, payload: dict[str, Any]) -> None:
        key = payload.get("key")
        value = payload.get("value")
        if not isinstance(key, str):
            emit_error("INVALID_PAYLOAD", "UPDATE_CONFIG requires payload.key", message_id)
            return
        if key not in CONFIG_KEYS:
            emit_error("INVALID_CONFIG_KEY", f"Unsupported config key: {key}", message_id)
            return

        try:
            coerced = coerce_config_value(key, value, self.config)
        except ValueError as exc:
            emit_error("INVALID_CONFIG_VALUE", str(exc), message_id)
            return

        if key == "active_theme" and not self._db().theme_exists(str(coerced)):
            emit_error("INVALID_THEME", "active_theme must be an existing theme", message_id)
            return

        self._db().update_config(key, coerced)
        self.config[key] = coerced

        if key in FULL_REBUILD_CONFIG_KEYS:
            if key == "custom_detectors":
                self._refresh_entities_to_mask()
            if bool(self.config.get("reload_nlp_on_run", False)):
                self.runtime_dirty = True
                emit_progress(
                    f"Deferred NLP/runtime reload for '{key}' until next Run.",
                    LOG_TYPE_SYSTEM,
                    pct=1,
                    message_id=message_id,
                )
            else:
                self._rebuild_runtime(full_reload=True)
                self.runtime_dirty = False
        elif key in PARTIAL_REBUILD_CONFIG_KEYS:
            self._rebuild_runtime(full_reload=False)
        elif key in NO_REBUILD_CONFIG_KEYS:
            if key == "reload_nlp_on_run" and not bool(coerced) and self.runtime_dirty:
                self._rebuild_runtime(full_reload=True)
                self.runtime_dirty = False
            if key in {"ollama_endpoint", "ollama_model", "ollama_enabled"}:
                self._refresh_ollama_state(boot_if_needed=True)
                coerced = self.config.get(key, coerced)
                emit_event(EVENT_READY, self._ready_payload(), message_id=None)

        emit_event(EVENT_DONE, {"key": key, "value": coerced}, message_id=message_id)

    def _handle_list_ollama_models(self, message_id: str | None) -> None:
        cancel_event = self._register_request_cancel_event(message_id)

        def _run() -> None:
            try:
                self._refresh_ollama_state(boot_if_needed=True)
                if self._is_request_cancelled(message_id) or (
                    cancel_event is not None and cancel_event.is_set()
                ):
                    emit_error("REQUEST_CANCELLED", "Request cancelled", message_id)
                    return
                if not self._is_ollama_enabled():
                    emit_error("OLLAMA_DISABLED", "ollama_enabled is false", message_id)
                    return
                if not self.ollama_installed:
                    emit_error("OLLAMA_NOT_INSTALLED", "Ollama executable not found", message_id)
                    return
                if not self.ollama_running or self.ollama_client is None:
                    emit_error("OLLAMA_NOT_RUNNING", "Ollama server is not running", message_id)
                    return
                names = self.ollama_client.list_models()
                if self._is_request_cancelled(message_id) or (
                    cancel_event is not None and cancel_event.is_set()
                ):
                    emit_error("REQUEST_CANCELLED", "Request cancelled", message_id)
                    return
                active = str(self.config.get("ollama_model", ""))
                models = [{"name": name, "active": name == active} for name in names]
                emit_event(
                    EVENT_DONE,
                    {
                        "models": models,
                        "available": self.ollama_available,
                    },
                    message_id=message_id,
                )
            except Exception as exc:
                emit_error("OLLAMA_REQUEST_FAILED", str(exc), message_id)
            finally:
                self._clear_request_tracking(message_id)

        self._spawn_background_task(_run)

    def _handle_ask_ollama(self, message_id: str | None, payload: dict[str, Any]) -> None:
        cancel_event = self._register_request_cancel_event(message_id)
        instruction = str(payload.get("instruction", "")).strip()
        target = str(payload.get("target", "")).strip().lower()
        current_text = str(payload.get("current_text", ""))
        other_text = str(payload.get("other_text", ""))
        raw_history = payload.get("history", [])
        requested_model = str(payload.get("model", "")).strip()
        raw_max_tokens = payload.get("max_tokens")

        if not instruction:
            emit_error("INVALID_PAYLOAD", "ASK_OLLAMA requires payload.instruction", message_id)
            return
        if target not in {"input", "output"}:
            emit_error("INVALID_PAYLOAD", "ASK_OLLAMA payload.target must be 'input' or 'output'", message_id)
            return
        if not isinstance(raw_history, list):
            emit_error("INVALID_PAYLOAD", "ASK_OLLAMA payload.history must be a list", message_id)
            return
        max_tokens: int | None = None
        if raw_max_tokens is not None:
            if not isinstance(raw_max_tokens, (int, float)):
                emit_error("INVALID_PAYLOAD", "ASK_OLLAMA payload.max_tokens must be a number", message_id)
                return
            max_tokens = max(64, min(8192, int(raw_max_tokens)))

        history: list[dict[str, str]] = []
        for row in raw_history:
            if not isinstance(row, dict):
                continue
            role = str(row.get("role", "")).strip()
            content = str(row.get("content", "")).strip()
            if role in {"user", "assistant"} and content:
                history.append({"role": role, "content": content})

        def _run() -> None:
            emit_progress(
                f"Ollama request started for {target}.",
                LOG_TYPE_SYSTEM,
                pct=4,
                message_id=message_id,
            )
            full_response = ""
            try:
                self._refresh_ollama_state(boot_if_needed=True)
                if self._is_request_cancelled(message_id) or (
                    cancel_event is not None and cancel_event.is_set()
                ):
                    emit_error("REQUEST_CANCELLED", "Request cancelled", message_id)
                    return
                if not self._is_ollama_enabled():
                    emit_error("OLLAMA_DISABLED", "ollama_enabled is false", message_id)
                    return
                if not self.ollama_installed:
                    emit_error("OLLAMA_NOT_INSTALLED", "Ollama executable not found", message_id)
                    return
                if not self.ollama_running:
                    emit_error("OLLAMA_NOT_RUNNING", "Ollama server is not running", message_id)
                    return
                if self.ollama_client is None:
                    self._setup_ollama_client()
                if self.ollama_client is None:
                    emit_error("OLLAMA_REQUEST_FAILED", "Ollama client unavailable", message_id)
                    return
                for token in self.ollama_client.stream_chat(
                    instruction=instruction,
                    target=target,
                    current_text=current_text,
                    other_text=other_text,
                    history=history,
                    model=requested_model or None,
                    max_tokens=max_tokens,
                ):
                    if self._is_request_cancelled(message_id) or (
                        cancel_event is not None and cancel_event.is_set()
                    ):
                        emit_error("REQUEST_CANCELLED", "Request cancelled", message_id)
                        return
                    full_response += token
                    emit_event(
                        EVENT_CHUNK,
                        {"stream": "ollama", "target": target, "text": token},
                        message_id=message_id,
                    )
            except Exception as exc:
                emit_error("OLLAMA_REQUEST_FAILED", str(exc), message_id)
                return
            finally:
                self._clear_request_tracking(message_id)

            emit_event(
                EVENT_DONE,
                {"target": target, "response": full_response},
                message_id=message_id,
            )

        self._spawn_background_task(_run)

    def _handle_get_ollama_model_info(self, message_id: str | None, payload: dict[str, Any]) -> None:
        cancel_event = self._register_request_cancel_event(message_id)
        model = str(payload.get("model", self.config.get("ollama_model", ""))).strip()
        if not model:
            emit_error("INVALID_PAYLOAD", "GET_OLLAMA_MODEL_INFO requires payload.model", message_id)
            return
        def _run_show(args: list[str]) -> tuple[int, str, str]:
            proc = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self._track_subprocess(message_id, proc)
            try:
                start = time.time()
                while proc.poll() is None:
                    if self._is_request_cancelled(message_id) or (
                        cancel_event is not None and cancel_event.is_set()
                    ):
                        proc.terminate()
                        break
                    if time.time() - start > 8:
                        proc.terminate()
                        break
                    time.sleep(0.05)
                stdout, stderr = proc.communicate(timeout=1)
                return proc.returncode or 0, stdout, stderr
            finally:
                self._untrack_subprocess(message_id, proc)

        def _run() -> None:
            try:
                self._refresh_ollama_state(boot_if_needed=True)
                if self._is_request_cancelled(message_id) or (
                    cancel_event is not None and cancel_event.is_set()
                ):
                    emit_error("REQUEST_CANCELLED", "Request cancelled", message_id)
                    return
                if not self.ollama_installed:
                    emit_error("OLLAMA_NOT_INSTALLED", "Ollama executable not found", message_id)
                    return

                context_tokens = 0
                _rc, stdout, stderr = _run_show(["ollama", "show", model])
                if self._is_request_cancelled(message_id) or (
                    cancel_event is not None and cancel_event.is_set()
                ):
                    emit_error("REQUEST_CANCELLED", "Request cancelled", message_id)
                    return
                combined = f"{stdout}\n{stderr}"
                match = re.search(r"(?i)context length\D+(\d+)", combined)
                if match:
                    context_tokens = int(match.group(1))
                if context_tokens <= 0:
                    _rc, modelfile_stdout, _modelfile_stderr = _run_show(
                        ["ollama", "show", model, "--modelfile"]
                    )
                    if self._is_request_cancelled(message_id) or (
                        cancel_event is not None and cancel_event.is_set()
                    ):
                        emit_error("REQUEST_CANCELLED", "Request cancelled", message_id)
                        return
                    match_modelfile = re.search(
                        r"(?i)\bnum_ctx\s+(\d+)", modelfile_stdout
                    )
                    if match_modelfile:
                        context_tokens = int(match_modelfile.group(1))

                emit_event(
                    EVENT_DONE,
                    {"model": model, "context_tokens": context_tokens},
                    message_id=message_id,
                )
            except Exception as exc:
                emit_error("OLLAMA_REQUEST_FAILED", str(exc), message_id)
            finally:
                self._clear_request_tracking(message_id)

        self._spawn_background_task(_run)

    def _handle_cancel_request(
        self, message_id: str | None, payload: dict[str, Any]
    ) -> None:
        request_id = str(payload.get("request_id", "")).strip()
        if not request_id:
            emit_error(
                "INVALID_PAYLOAD",
                "CANCEL_REQUEST requires payload.request_id",
                message_id,
            )
            return
        self._cancel_request(request_id)
        emit_event(
            EVENT_DONE,
            {"request_id": request_id, "cancelled": True},
            message_id=message_id,
        )

    def _handle_set_theme(self, message_id: str | None, payload: dict[str, Any]) -> None:
        theme = payload.get("theme")
        if not isinstance(theme, str) or not theme:
            emit_error("INVALID_PAYLOAD", "SET_THEME requires payload.theme", message_id)
            return
        if not self._db().theme_exists(theme):
            emit_error("INVALID_THEME", f"Theme not found: {theme}", message_id)
            return

        self._db().update_config("active_theme", theme)
        self.config["active_theme"] = theme
        self._rebuild_runtime(full_reload=False)
        emit_event(EVENT_DONE, {"active_theme": theme}, message_id=message_id)

    def _handle_reset_data(self, message_id: str | None) -> None:
        initial_config = build_initial_config_values(self.bootstrap)
        initial_pool = self.bootstrap.get("initial_name_pool", {})
        if not isinstance(initial_pool, dict):
            emit_error("INVALID_BOOTSTRAP", "initial_name_pool must be an object", message_id)
            return
        themed_pool: dict[str, list[str]] = {}
        for theme, names in initial_pool.items():
            if not isinstance(names, list):
                continue
            themed_pool[str(theme)] = [str(name) for name in names if str(name).strip()]
        if not themed_pool:
            emit_error("INVALID_BOOTSTRAP", "No valid initial name pool found", message_id)
            return

        self._db().replace_config_all(initial_config)
        self._db().replace_all_theme_pools(themed_pool)
        self._db().clear_reversible_mappings()
        self.config = normalize_config(self._db().get_config())
        self.base_entities_to_mask = self._load_entities_to_mask(self.bootstrap)
        self._refresh_entities_to_mask()
        self._refresh_ollama_state(boot_if_needed=True)
        self._rebuild_runtime(full_reload=True)
        emit_event(EVENT_READY, self._ready_payload(), message_id=None)
        emit_event(EVENT_DONE, {"reset": True}, message_id=message_id)

    def _handle_purge_data(self, message_id: str | None, payload: dict[str, Any]) -> None:
        days = payload.get("days", 30)
        if not isinstance(days, (int, float)) or int(days) < 1:
            emit_error("INVALID_PAYLOAD", "PURGE_DATA requires payload.days >= 1", message_id)
            return
        deleted_records = self._db().purge_reversible_mappings_older_than(int(days))
        emit_event(
            EVENT_DONE,
            {"purged": True, "days": int(days), "deleted_records": deleted_records},
            message_id=message_id,
        )

    def _handle_get_storage_stats(self, message_id: str | None) -> None:
        db_bytes = 0
        try:
            db_bytes = self._db().db_path.stat().st_size
        except Exception:
            db_bytes = 0
        config_count = len(self.config)
        theme_count = len(self._db().list_themes())
        mapping_count = len(
            self._db().list_reversible_mappings(seed=str(self.config.get("seed", "")))
        )
        emit_event(
            EVENT_DONE,
            {
                "db_bytes": db_bytes,
                "config_keys": config_count,
                "themes": theme_count,
                "reversible_mappings": mapping_count,
            },
            message_id=message_id,
        )

    def _handle_import_theme_pack(self, message_id: str | None, payload: dict[str, Any]) -> None:
        path = payload.get("path")
        if not isinstance(path, str) or not path:
            emit_error("INVALID_PAYLOAD", "IMPORT_THEME_PACK requires payload.path", message_id)
            return

        pack_path = Path(path)
        if not pack_path.is_absolute():
            emit_error("INVALID_PAYLOAD", "IMPORT_THEME_PACK path must be absolute", message_id)
            return
        if not pack_path.exists():
            emit_error("NOT_FOUND", f"Theme pack not found: {path}", message_id)
            return

        try:
            raw_data = pack_path.read_text(encoding="utf-8")
        except Exception as exc:
            emit_error("FILE_READ_FAILED", str(exc), message_id)
            return

        try:
            if pack_path.suffix.lower() == ".json":
                parsed = json.loads(raw_data)
            else:
                parsed = yaml.safe_load(raw_data)
        except Exception as exc:
            emit_error("INVALID_THEME_PACK", f"Failed to parse theme pack: {exc}", message_id)
            return

        try:
            themes = self._extract_theme_pack(parsed)
        except ValueError as exc:
            emit_error("INVALID_THEME_PACK", str(exc), message_id)
            return

        db = self._db()
        imported_themes: list[str] = []
        for theme, names in themes.items():
            db.replace_theme_pool(theme, names)
            imported_themes.append(theme)

        if not db.theme_exists(str(self.config.get("active_theme", "default"))) and imported_themes:
            self.config["active_theme"] = imported_themes[0]
            db.update_config("active_theme", imported_themes[0])
        self._rebuild_runtime(full_reload=False)
        emit_event(
            EVENT_DONE,
            {"imported_themes": sorted(imported_themes), "theme_count": len(imported_themes)},
            message_id=message_id,
        )

    def _extract_theme_pack(self, payload: Any) -> dict[str, list[str]]:
        if isinstance(payload, dict) and "theme" in payload and "names" in payload:
            theme = str(payload.get("theme", "")).strip()
            names = self._normalize_theme_names(payload.get("names"))
            if not theme or not names:
                raise ValueError("Single-theme pack requires non-empty theme and names")
            return {theme: names}

        if isinstance(payload, dict) and "themes" in payload:
            payload = payload["themes"]

        if not isinstance(payload, dict):
            raise ValueError("Theme pack must be an object keyed by theme name")

        extracted: dict[str, list[str]] = {}
        for theme, names in payload.items():
            theme_key = str(theme).strip()
            normalized_names = self._normalize_theme_names(names)
            if theme_key and normalized_names:
                extracted[theme_key] = normalized_names
        if not extracted:
            raise ValueError("Theme pack did not contain any valid themes")
        return extracted

    def _normalize_theme_names(self, raw: Any) -> list[str]:
        values: list[str] = []
        if isinstance(raw, list):
            for name in raw:
                text = str(name).strip()
                if text:
                    values.append(text)
        elif isinstance(raw, dict):
            for nested in raw.values():
                values.extend(self._normalize_theme_names(nested))
        else:
            text = str(raw).strip()
            if text:
                values.append(text)
        return list(dict.fromkeys(values))

    def _handle_install_spacy_model(self, message_id: str | None, payload: dict[str, Any]) -> None:
        model = str(payload.get("model", "")).strip()
        if model not in SUPPORTED_SPACY_MODELS:
            emit_error("INVALID_PAYLOAD", f"Unsupported spaCy model: {model}", message_id)
            return
        if self._is_spacy_model_installed(model):
            emit_event(
                EVENT_DONE,
                {"model": model, "installed": True, "already_installed": True},
                message_id=message_id,
            )
            return

        emit_progress(
            f"Installing spaCy model {model} in background...",
            LOG_TYPE_SYSTEM,
            pct=2,
            message_id=message_id,
        )

        def _install() -> None:
            try:
                process = subprocess.run(
                    [sys.executable, "-m", "spacy", "download", model],
                    capture_output=True,
                    text=True,
                    check=False,
                )
            except Exception as exc:
                emit_error("SPACY_INSTALL_FAILED", str(exc), message_id)
                return

            if process.returncode != 0:
                stderr = process.stderr.strip() or process.stdout.strip() or "Unknown install error"
                emit_error("SPACY_INSTALL_FAILED", stderr, message_id)
                return

            installed = self._is_spacy_model_installed(model)
            emit_event(
                EVENT_DONE,
                {"model": model, "installed": installed, "already_installed": False},
                message_id=message_id,
            )

        self._spawn_background_task(_install)

    def shutdown(self) -> None:
        if self.worker_pool is not None:
            self.worker_pool.shutdown()
            self.worker_pool = None
        with self.background_tasks_lock:
            tasks = list(self.background_tasks)
            self.background_tasks.clear()
        for task in tasks:
            if task.is_alive():
                task.join(timeout=0.1)
        if self.ollama_server_process is not None:
            if self.ollama_server_process.poll() is None:
                self.ollama_server_process.terminate()
            self.ollama_server_process = None
        if self.db is not None:
            self.db.close()
            self.db = None


def parse_command(line: str) -> tuple[str | None, str, dict[str, Any]]:
    try:
        message = json.loads(line)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc

    if not isinstance(message, dict):
        raise ValueError("Command must be an object")

    message_id = message.get("id")
    command = message.get("command")
    payload = message.get("payload", {})

    if message_id is not None and not isinstance(message_id, str):
        raise ValueError("id must be a string or null")
    if not isinstance(command, str):
        raise ValueError("command must be a string")
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")

    return message_id, command, payload


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--cli-text", type=str, default=None, help="One-shot CLI mode input text")
    parser.add_argument("--cli-in", type=str, default=None, help="One-shot CLI mode input file path")
    parser.add_argument("--cli-out", type=str, default=None, help="One-shot CLI mode output file path")
    parser.add_argument(
        "--cli-entities",
        type=str,
        default=None,
        help="Comma-separated entity types override",
    )
    return parser.parse_args(argv)


def main() -> int:
    args = _parse_args(sys.argv[1:])
    root_dir = Path(__file__).resolve().parent.parent
    service = SidecarService(root_dir)

    def _request_shutdown(_signum: int, _frame: Any) -> None:
        service.running = False

    signal.signal(signal.SIGINT, _request_shutdown)
    signal.signal(signal.SIGTERM, _request_shutdown)

    try:
        service.setup()
    except Exception as exc:
        emit_error("STARTUP_FAILED", str(exc), message_id=None)
        service.shutdown()
        return 1

    if args.cli_text is not None or args.cli_in is not None:
        try:
            if args.cli_in is not None:
                input_text = Path(args.cli_in).read_text(encoding="utf-8")
            else:
                input_text = args.cli_text or ""
            entities = None
            if args.cli_entities:
                parsed_entities = [item.strip() for item in args.cli_entities.split(",") if item.strip()]
                entities = parsed_entities or None
            output_text = service.cli_process_text(input_text, entities_override=entities)
            if args.cli_out:
                Path(args.cli_out).write_text(output_text, encoding="utf-8")
            else:
                sys.stdout.write(output_text)
                if not output_text.endswith("\n"):
                    sys.stdout.write("\n")
        except Exception as exc:
            sys.stderr.write(f"CLI_PROCESS_FAILED: {exc}\n")
            service.shutdown()
            return 1
        service.shutdown()
        return 0

    emit_event(EVENT_READY, service._ready_payload(), message_id=None)

    for raw_line in sys.stdin:
        if not service.running:
            break
        line = raw_line.strip()
        if not line:
            continue
        try:
            message_id, command, payload = parse_command(line)
        except ValueError as exc:
            emit_error("INVALID_MESSAGE", str(exc), message_id=None)
            continue

        try:
            service.handle(message_id, command, payload)
        except Exception as exc:
            emit_error("UNHANDLED_EXCEPTION", str(exc), message_id=message_id)
        if not service.running:
            break

    service.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
