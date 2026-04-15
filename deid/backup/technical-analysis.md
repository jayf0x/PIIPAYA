# DeID Technical Analysis (Current State)

Last updated: 2026-03-25

## Purpose
This is the handover document for any new agent joining the project. It captures the current architecture, shipped behavior, important implementation details, backlog reality, and product-direction constraints so work can continue immediately without re-discovery.

## Product Snapshot
DeID is a local-first anonymization workbench:
- Svelte 5 frontend (single-page app in Tauri webview)
- Rust/Tauri shell for lifecycle + IPC bridge
- Python sidecar for NLP anonymization, config, storage, and optional Ollama assist
- SQLite for config + theme name pools

Primary UX today:
- Input pane (text + attachments)
- Output pane (anonymized text + downloadable output + output attachments)
- Collapsible sidebar for quick settings/tags
- Advanced settings modal for full config/profile/data operations
- Popover-first AI Assist (Ask/Apply)

## Repo Map
- `src/routes/+page.svelte`: main app state, backend bridge, run flow, export flow, profiles, undo, mock mode
- `src/lib/ui/*.svelte`: pane/sidebar/modal/shared UI components
- `src-python/__main__.py`: sidecar command loop + handlers + CLI path
- `src-python/engine.py`: mapping handlers and anonymization behavior
- `src-python/processing.py`: chunking and worker-pool chunk analysis
- `src-python/config.py`: config defaults/coercion/rebuild partitioning
- `src-python/database.py`: SQLite schema/data access
- `src-python/protocol.py`: NDJSON event emission helpers
- `src-tauri/src/lib.rs`: sidecar lifecycle and event relay to frontend
- `backlog.md`: active planning + status tracking
- `technical-report-frontend.md`: frontend feature/style report (separate deliverable)

## Runtime Architecture

### Desktop startup
1. Tauri starts and spawns Python sidecar.
2. Sidecar initializes DB/config/runtime and emits `READY` with feature map.
3. Frontend listens to `backend:event` and queries `backend_status`.
4. Frontend gates controls from `feature_map` (`supports*` flags).

### Browser-only startup (`bun run dev:web`)
When Tauri bridge is missing, frontend falls back to mock mode:
- In-memory/mock command handling in `+page.svelte`
- Mock config persisted in localStorage
- Feature gating still simulated (including Ollama enablement)

## Sidecar Protocol
Transport: NDJSON lines.

Request shape:
- `{ id, command, payload }`

Event shape:
- `{ id, type, payload }`
- `type` in `READY | PROGRESS | CHUNK | DONE | ERROR`

## Implemented Sidecar Commands
In `src-python/__main__.py`:
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
- `PURGE_DATA` (MVP no-op retention contract)
- `GET_STORAGE_STATS`
- `SHUTDOWN`

### CLI mode
Also implemented in `__main__.py`:
- `--cli-text`
- `--cli-in`
- `--cli-out`
- `--cli-entities`

This provides one-shot non-daemon processing for command-line usage.

## Anonymization Engine Behavior
In `src-python/engine.py`:
- Deterministic mapping with seed + likeliness + consistency
- Session cache for within-session replacement stability
- Entity handlers include realistic transforms for:
  - `PERSON`
  - `LOCATION`
  - `EMAIL_ADDRESS`
  - `PHONE_NUMBER`
  - `DATE_TIME`
  - `URL`
  - `IP_ADDRESS`
  - `MAC_ADDRESS`
  - `CREDIT_CARD`
  - `IBAN_CODE`
  - `CRYPTO`
  - generic ID types (`US_SSN`, etc.)

Notable current detail:
- URL path slug tokenization was improved to anonymize person-like path segments (e.g. `/james-stuart`) while preserving separator structure.

## Chunking/Workers
In `src-python/processing.py` + `__main__.py`:
- Text split by paragraph/sentence fallback/hard chunking
- Worker analysis now uses `submit/as_completed` (not `map`) to reduce head-of-line blocking
- Chunk completion callback drives analysis progress events
- Ordered reassembly preserved for deterministic final text stream
- Chunk-specific error context added

## Sidecar Responsiveness
Improved recently:
- `INSTALL_SPACY_MODEL` now executes in a background thread so long installs do not block command loop
- `protocol.emit_message` now guarded by lock for thread-safe NDJSON writes

Still not fully solved:
- Some Ollama availability/check paths can still be synchronous

## Frontend Behavior (Current)

### Main run flow
In `src/routes/+page.svelte`:
- `Go` triggers `processSubmission()`
- Uses `PROCESS_FILES` when attachments exist and capability supports it
- Falls back to text processing when no attachments
- Active tags are sent as `entities` filter
- `Run` clears/refreshes output and logs safely with timeout watchdog

### Attachments flow
Current expected behavior is implemented:
- Input can contain main text + attached files
- Attachments are not injected into input text buffer
- Output includes:
  - main anonymized text (downloadable)
  - output attachments for processed files (same names, anonymized content)
- ZIP export now includes output text + attachment files (no metadata json)

### File preview behavior
Attachment click opens shared preview modal (`FilePreviewModal`) instead of mutating input/output text areas.

### Tags/highlighting
- Sidebar controls tag enable/disable
- Output toggle uses `Tags` label with eye open/eye-off icon logic
- Disabled tag types are ignored in backend call on subsequent runs (entity list filtered before submit)

### Ask (AI Assist)
- Popover-first Ask UI in both panes (`InputPane`, `OutputPane`)
- Ask/Apply/Clear actions
- Model select is in popover and synced to config (`ollama_model`)
- Context display now subtle text:
  - `X% used (~A/B tokens)`
- Rough token estimate uses `4 chars = 1 token`
- Supports model context fetch via `GET_OLLAMA_MODEL_INFO` (backed by `ollama show` parsing)

### Profiles
- Sidebar: profile load/select only
- Advanced modal: save profile, load config, save config
- Unsaved-change confirmation when switching profiles
- Profiles currently local-storage based on frontend snapshot

### Undo
- Global snapshot stack with `Cmd/Ctrl+Z`
- Captures major destructive actions (attach/remove, paste, apply ask, resets, run-related clears)
- Not yet universal for every single config mutation path

### Sidebar
- DOM-resident collapsible rail behavior retained
- Drag resize/resize line/cursor functionality intentionally removed
- Collapse/expand only

### Layout and scaling
- Main shell uses `100dvh`, box-sizing fixes, non-shrinking footer to reduce clipping
- Workbench remains two-column desktop / single-column small screens

## UI Components and Shared Primitives
- `SidebarPanel.svelte`: tags + profile + theme + strength + open advanced
- `InputPane.svelte`: input, attachments, ask popover, go button
- `OutputPane.svelte`: output render, tags toggle, export/save, ask popover
- `AdvancedSettingsModal.svelte`: full config, data controls, profile save/load actions
- `AttachmentPill.svelte`: segmented attachment chip controls
- `RangeField.svelte`: shared slider component
- `FilePreviewModal.svelte`: shared content preview modal

## Storage/Persistence
SQLite (`deid.db`):
- `config` table (JSON-encoded values by key)
- `name_pool` table (theme-based pseudonym pools)

App-level additional persistence:
- Frontend profiles saved in browser localStorage (current implementation)

## Testing Status

### Passing checks (current)
- `bun run check` (svelte-check)
- `bash ./scripts/test-python.sh` (Python unittests)

### E2E
- Existing specs were updated to current selectors
- Added capability-gating test for Ask visibility in mock mode
- Full desktop e2e lifecycle coverage still limited

## Known Gaps / Backlog Reality
See `backlog.md` for exact status; practical summary:
- Mostly `partial` items remain
- Remaining `open` items are low-priority quality/refactor work
- First-run `bun run dev` freeze item is explicitly deferred/ignored for now by product direction

Notable remaining technical work:
- Further modularization of large frontend files (`+page.svelte`, advanced modal)
- Deeper design-system deduplication and theme-tokenization
- More complete async/cancellable handling for long sidecar operations
- Broader undo coverage for all setting mutations

## Important Product/Collaboration Context for Next Agent
These patterns repeatedly matter for acceptance:
- User is very UI/UX strict and compares against design intent, not just functional parity.
- "Looks better" is not enough; interactions must also be correct (download, rerun, tags->backend behavior, profile flows, etc.).
- User wants backlog-driven execution: create/track tickets, close aggressively, keep statuses honest.
- User expects concrete progress over long discussions.
- When uncertain, ask only when the answer changes implementation direction.
- Current explicit direction: ignore the intermittent first-run dev freeze unless re-prioritized.

## Suggested Immediate Next Tasks (if continuing now)
1. Continue closing `partial` backlog items with highest UX impact first (profiles/data lifecycle + component extraction).
2. Consolidate repeated Input/Output pane styling/logic into shared primitives.
3. Expand e2e to cover advanced settings persistence and profile switch flows.
4. Introduce theme tokens/CSS vars to remove hardcoded colors and prepare dark theme.

## Quick Commands for New Agent
- Install deps: `bun install`
- Frontend check: `bun run check`
- Python tests: `bash ./scripts/test-python.sh`
- Web dev (mock): `bun run dev:web`
- Desktop dev: `bun run dev`
- E2E: `bash ./scripts/test-e2e.sh`
