# Frontend Target Structure

## Folder layout and responsibilities

```text
src/
  routes/
    +layout.ts
    +page.svelte                    # composition only

  lib/
    domain/
      backend/
        contract.ts                 # command names, capabilities, payload/response types
        client.ts                   # single transport facade (tauri + mock adapters behind it)

      workbench/
        store.ts                    # canonical run-session state and transitions
        files.ts                    # workbench-local file attach helpers (only if used by store)

      settings/
        store.ts                    # canonical settings + profiles state (backend-truth)

      entities/
        catalog.ts                  # canonical entity metadata + palette + mapping

      policies/
        fileCapabilities.ts         # canonical extension/capability policy

    ui/
      layout/
        SidebarPanel.svelte
      panes/
        InputPane.svelte
        OutputPane.svelte
      modals/
        AdvancedSettingsModal.svelte
        FilePreviewModal.svelte
      components/
        AttachmentPill.svelte
        AskPopover.svelte
        DropzoneWrapper.svelte
        FileQueueList.svelte
        PreviewUnavailableOverlay.svelte
        RangeField.svelte
        TagThemeControls.svelte
      shared/
        pane.css                    # only truly shared pane structure styles

    styles/
      tokens.css                    # semantic CSS variables
      base.css                      # reset/foundation only

    types/
      ui.ts                         # UI-only local types
```

## State management approach

- Use one canonical store per domain concept:
  - `workbench/store.ts` is the only owner of run/session workflow state.
  - `settings/store.ts` is the only owner of config and profiles state.
- Do not create component-scoped stores for shared concepts.
- Components consume derived state from these stores and emit actions back to them.
- Route layer wires stores to components and contains no domain state machine logic.
- Backend contract and lifecycle rules drive frontend state transitions; frontend stores mirror backend semantics.

## Backend source-of-truth rules

- Backend is authoritative for:
  - command names
  - protocol envelope/message shapes
  - capabilities/lifecycle events
  - profile persistence and active profile
  - runtime config truth
- Frontend must not introduce parallel authority for the same concept.
- Profiles are 100% backend-owned:
  - no frontend-local canonical profile persistence
  - frontend reads/writes profiles only through backend APIs/events
  - UI reflects backend profile state directly

## Styling strategy

- Keep styling layered and minimal:
  - `styles/tokens.css` defines semantic tokens.
  - `styles/base.css` defines foundational global styles only.
  - component styles stay local unless a pattern is reused across multiple components.
- Centralize only truly shared style primitives (for example pane shell layout used by both panes).
- Eliminate broad global interaction selectors (for example global button hover transforms).
- Entity colors come from entity tokens derived from `entities/catalog.ts`, not duplicated literals.

## Rules for code reuse

- Extract only when reused by multiple consumers or when needed to enforce single ownership.
- Keep single-use logic local to its owning domain module.
- Canonical shared modules:
  - backend contract/client
  - workbench store
  - settings store
  - entity catalog
  - file capability policy
- Components are thin:
  - render state
  - capture interaction
  - emit actions
- Components do not parse backend envelopes, define protocol constants, or own cross-feature state.

## Frontend behavior to preserve during refactor

The frontend is a local-first workbench for text and file anonymization. Refactoring must preserve behavior parity with current user workflows while improving structure.

### What the frontend needs to continue providing

- One clear end-to-end run flow: input/attachments -> backend processing -> streamed/assembled output -> save/copy/export.
- Strong backend alignment: feature availability and UI controls must remain capability-gated by backend feature map.
- Predictable state continuity: user input, output, selected entities, queue state, and active profile/settings must remain internally consistent.
- Safe editing loop: preview/edit/reconvert operations must not desynchronize output text, output segments, and output attachments.
- Cross-mode reliability: both Tauri backend mode and browser mock mode must keep the same command semantics and lifecycle behavior.

### Current behavior that must not be lost

- Processing modes:
  - text-only runs
  - single-file processing when supported
  - mixed/multi-file processing with queue/progress state
- Attachment handling:
  - dropzone + picker intake
  - dedupe behavior
  - unsupported file handling and queue status messaging
  - per-attachment preview/open/download actions
- Output workflow:
  - streamed output assembly
  - highlighted segment rendering
  - output attachment selection and per-file reconvert/edit flow
  - preview dirty detection and explicit save behavior
- Ask Assist workflow:
  - input and output ask targets
  - model selection
  - token estimate/context display
  - apply/clear actions and request cancellation behavior
- Settings workflow:
  - runtime config edits with backend sync/debounce
  - theme/model/spaCy options
  - storage estimate, purge/reset actions
  - backend-owned profile selection/save/load lifecycle
- Export and clipboard workflow:
  - copy output
  - save text output
  - attachment download
  - zip export
- History and recovery:
  - undo snapshots for destructive changes
  - run history previous/next navigation
- Capability-driven UI:
  - controls only enabled when backend reports support
  - graceful fallback behavior when capabilities are missing

### Refactor guardrails

- Do not change command names, payload shapes, or event semantics from backend contract.
- Do not move canonical domain state into components.
- Do not duplicate state ownership across multiple stores/modules for the same concept.
- Do not replace backend truth with frontend-local persistence for profiles or runtime config authority.
- Keep user-visible behavior unchanged unless explicitly listed as a backlog item.
