## [2026-03-24] Frontend: Support folder input for filePicker and drag and drop.
Type: feature
Priority: low
Status: open

Add support for folder in current Drag&Drop functionality. Tauri config needs to allow paths specifically (`"allowlist": {"fs": { "scope": ["$HOME/**"]...`). Then we can import `import { readDir } from '@tauri-apps/api/fs';` and list all files in that dir and pass this again to the regular file drop and file picker.


## [2026-03-24] Settings profile lifecycle hardening
Type: feature
Priority: high
Status: done

Rename + delete + save-as profile wired in AdvancedSettingsModal with inline UI (no window.prompt). YAML import/export and set-default deferred — out of scope for current release.

## [2026-03-24] Frontend e2e coverage for config/capability transitions
Type: test
Priority: high
Status: deferred

No e2e harness in place. Deferred until Playwright/Tauri test infra set up.


## [2026-03-24] Sidebar collapse visual polish
Type: feature
Priority: medium
Status: done

Collapsed-rail width unified to 48px across CSS layer, aside.collapsed, and sidebarDisplayWidth() JS. ThemeToggle + icon-btn alignment fixed. Transition timing consistent.

## [2026-03-24] Long-running sidecar operations still block in some paths
Type: limitation
Priority: medium
Status: deferred

Requires async rewrite of Python command loop. Deferred — no immediate user-facing breakage.

## [2026-03-24] Undo coverage for settings-level mutations
Type: feature
Priority: medium
Status: done

UndoSnapshot extended with config + activeProfileName. pushUndoSnapshot captures before modal open. restoreUndoSnapshot flushes full config via flushAllConfigValues() + restores activeProfileName. Cmd+Z reverts settings changes.

## [2026-03-24] Slider/dropdown design-system parity
Type: frontend
Priority: medium
Status: done

TagThemeControls uses CarbonSlider + CarbonSelect. AdvancedSettingsModal uses same primitives. Sidebar and modal controls share identical design-system components.


## [2026-03-25] Final-phase theming: replace hardcoded colors with tokens
Type: quality
Priority: low
Status: open

Replace hardcoded colors with centralized theme tokens/CSS variables across sidebar, panes, modal, highlights, and backgrounds, then wire token sets to support runtime theme switching (including dark theme readiness).



## Frontend: Extract logic into reusible functions
Type: quality
Priority: low
Status: open

Extract utility functions or functions that are used multiple times into a separate folder like utils or components.
Functions like `classForEntity` should be a util.


## Frontend: Reusible global typing
Type: quality
Priority: low
Status: open

Add a d.ts file with a global namespace T under which we add all our typing. Components or sections could have a custom name like `T.Ask.Target ("input" | "output")`.
Responsibilitis:iterating all components, resolving duplicates, making it future proof.

Goal: have almost no duplicate type declarations (only component based for props or similar).


---


## [2026-03-26] Add Tauri update system
Type: feature
Priority: low
Status: open

Integrate Tauri updater flow for production releases (check/apply update, close/relaunch) after finalizing update channels, signing, and distribution strategy.

## [2026-03-26] Post-feature installer/setup screen
Type: feature
Priority: low
Status: open

Add first-run installer/setup screen for optional dependencies (for example Ollama/model bundles/update hooks), with explicit progress states, failure recovery, and clear platform-specific permission/elevation handling.