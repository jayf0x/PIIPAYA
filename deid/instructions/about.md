# DeID Architecture Summary

Last updated: 2026-04-01

## Purpose
DeID is a local-first text anonymization workbench:
- Frontend: Svelte 5 single-page UI.
- Desktop shell: Tauri (Rust) for app lifecycle and frontend<->sidecar IPC.
- Sidecar: Python service for anonymization runtime, config/state management, and optional Ollama-assisted editing.
- Persistence: SQLite for runtime config and theme name pools.

Primary user flow:
1. Enter/paste text and/or attach files.
2. Run anonymization with selected entity filters.
3. Review highlighted output and per-file outputs.
4. Export output (text or zip), copy to clipboard, or iterate with Ask Assist.

## Runtime Architecture

### 1) Startup and readiness
- Tauri launches the Python sidecar.
- Sidecar initializes bootstrap config, DB, pools, NLP runtime, worker pool, and Ollama availability state.
- Sidecar emits `READY` with `feature_map`.
- Frontend listens on `backend:event`, then gates UI capabilities based on `feature_map`.

Browser dev fallback (`bun run dev:web`):
- If Tauri bridge is unavailable, frontend enters mock mode.
- Mock mode emulates command handling and local persistence for UI development.

### 2) Processing flow
- `Go` in the frontend resolves command strategy:
  - `PROCESS_TEXT` for text-only runs.
  - `PROCESS_FILE` for a single file-only run when supported.
  - `PROCESS_FILES` for mixed/multi-file runs.
- Sidecar splits text into chunks and analyzes chunks via worker pool.
- Mapping is applied with deterministic handlers and session cache.
- Sidecar emits progress + chunk events, then `DONE`.
- Frontend streams output, builds highlight segments, and captures run revision history.

### 3) Config/runtime updates
- Frontend pushes config changes via debounced `UPDATE_CONFIG`.
- Sidecar coerces/validates values and chooses:
  - full runtime rebuild,
  - partial rebuild,
  - or no rebuild.
- For `reload_nlp_on_run`, sidecar can defer full NLP rebuild until next processing command.

### 4) Ask Assist (Ollama)
- Ask is enabled only when feature map includes Ollama commands.
- Frontend sends `ASK_OLLAMA` with instruction, target, current/other text, optional history, and selected model.
- Sidecar streams token chunks and emits final response on `DONE`.
- Frontend supports Apply/Clear per input/output pane.

## Repo Map (Key Files)
- `src/routes/+page.svelte`
  - Main orchestrator: runtime state, command dispatch, progress handling, file flow, undo/history, profiles, exports, mock mode.
- `src/lib/ui/InputPane.svelte`
  - Input editor, file tray, run trigger, ask popover, drop handling entry point.
- `src/lib/ui/OutputPane.svelte`
  - Output rendering/highlights, output attachments, export controls, ask popover.
- `src/lib/ui/AdvancedSettingsModal.svelte`
  - Full config controls, profile actions, theme/model operations, data operations.
- `src-python/__main__.py`
  - Sidecar command loop, command handlers, feature map, runtime rebuild logic, CLI mode.
- `src-python/engine.py`
  - Core anonymization engine, entity handler registry, deterministic mapping behavior.
- `src-python/processing.py`
  - Chunking and parallel detection analysis.
- `src-python/config.py`
  - Config schema keys, coercion, defaults, rebuild partitioning.
- `src-python/database.py`
  - SQLite access for config + theme pools.
- `src-python/protocol.py`
  - Event emission utilities and NDJSON framing.
- `src-tauri/src/lib.rs`
  - Sidecar spawn/relay/shutdown bridge for desktop.

## Sidecar Protocol
Transport: NDJSON (one JSON object per line).

Request envelope:
```json
{ "id": "uuid", "command": "COMMAND_NAME", "payload": {} }
```

Event envelope:
```json
{ "id": "uuid-or-null", "type": "READY|PROGRESS|CHUNK|DONE|ERROR", "payload": {} }
```

Event semantics:
- `READY`: sidecar startup or capability refresh (`feature_map`, Ollama status).
- `PROGRESS`: user-visible progress logs with percentage.
- `CHUNK`: streamed output fragments (anonymized text chunks or Ollama token stream).
- `DONE`: terminal success payload for command.
- `ERROR`: terminal failure payload (`code`, `message`).

## Implemented Sidecar Commands
From `src-python/__main__.py`:
- `PROCESS_TEXT`
- `PROCESS_FILE`
- `PROCESS_FILES`
- `GET_CONFIG`
- `UPDATE_CONFIG`
- `LIST_THEMES`
- `SET_THEME`
- `IMPORT_THEME_PACK`
- `LIST_SPACY_MODELS`
- `INSTALL_SPACY_MODEL`
- `LIST_OLLAMA_MODELS`
- `GET_OLLAMA_MODEL_INFO`
- `ASK_OLLAMA`
- `RESET_DATA`
- `PURGE_DATA` (currently contract-only; no timestamped deletion yet)
- `GET_STORAGE_STATS`
- `SHUTDOWN`

CLI one-shot mode also exists:
- `--cli-text`
- `--cli-in`
- `--cli-out`
- `--cli-entities`

## Anonymization Engine Notes
- Entity detection: Presidio analyzer + spaCy.
- Replacement: deterministic mapping keyed by seed + likeliness + consistency.
- Cache: session-level cache for stable replacements during a run.
- Handler coverage includes: person/location/email/phone/date/url/ip/mac/credit card/IBAN/crypto and generic ID-like entities.
- URL mapping includes tokenized path/query/fragment anonymization while preserving URL structure.

## Implemented UX Capabilities (Current)
- File attachments process independently from manual text buffer.
- Output pane supports main output + output attachment artifacts.
- Attachment open actions use preview modal (no buffer overwrite).
- Zip export from frontend bundles main output + output attachments.
- Sidebar profile selection and advanced modal profile save/load config actions.
- Global undo (`Cmd/Ctrl+Z`) for major destructive actions.
- Ask Assist popover in both panes with model selection and context-token estimate display.
- Capability-gated Ask visibility is covered by e2e in mock mode.

## Known Gaps (from current backlog)

### Active feature/quality gaps
- Full drag-drop polish (visual drag-over state/accessibility).
- Per-file queueing/status/progress for multi-file workflows.
- Per-file details/progress channeling beyond combined stream output.
- DOCX/PDF ingestion and image OCR pipeline.
- Optional reversible mapping mode with secure persistence model.
- Profile-first simplification of configuration UX.
- Auto-copy/auto-paste clipboard automation toggles.
- YAML profile lifecycle operations (import/export/rename/delete/default).
- Real retention deletion logic for `PURGE_DATA`.
- Remaining synchronous long-running sidecar paths (Ollama checks/model info) and cancellation support.
- Broader e2e coverage for debounced config persistence + deterministic READY/config transitions.
- Undo coverage for settings-level mutations.
- Optional Ask dock/undock mode.
- Attachment metadata/details and accessibility polish.
- Final responsive verification for layout regressions.
- UI refinement work: sidebar collapse visuals, pulse feedback rollout, design-system extraction, large-file refactor, tokenized theming, pane deduplication.

### Release/post-launch gaps
- Rust-side IPC lifecycle tests.
- Plugin execution isolation/sandboxing.
- Deferred first-run `dev:web` freeze investigation.
- Tauri updater integration + release channel/signing decisions.
- First-run installer/setup flow for optional dependency installation.

## Quick Start for Future Agents
- Install deps: `bun install`
- Web dev (mock): `bun run dev:web`
- Desktop dev: `bun run dev`
- Frontend check: `bun run check`
- Python tests: `bash ./scripts/test-python.sh`
- E2E: `bash ./scripts/test-e2e.sh`

This document is intended to be sufficient context for starting feature work without re-reading the entire codebase.
