
## FEATURE: add one shot with GLiNER
Add support in the UI to enable or use GLiNER.
user should be able to select to only use GLiNER as one-shot solution.


## [area: ui] Carbon component integration issues

- **ToggleSwitch remount on prop change** — uses `{#key checked}` to sync controlled state with Carbon Toggle's internal state. Causes a brief DOM remount when parent updates `checked`. Investigate `bind:toggled` once Svelte 5 / Carbon interop is stable.
- **Carbon white.css global resets** — overridden with `!important` in `base.css`. Long-term: import only per-component Carbon CSS instead of the full white theme.
- ~~CarbonSlider remount on value change~~ — FIXED: removed `{#key value}`, slider now works correctly during drag.
- ~~CarbonSelect `on:change`~~ — FIXED: now uses Carbon `on:update` (clean value from `createEventDispatcher`).
- ~~CarbonSlider track selector wrong~~ — FIXED: was targeting `.bx--slider` (container), now correctly targets `.bx--slider__track`.

## [area: ui] Sidebar gaps

- ~~**ThemeToggle disappears when collapsed**~~ — FIXED: ThemeToggle now rendered in a `.collapsed-actions` block below the expand button when sidebar is collapsed.
- ~~`browserMockMode` and `startupError` not rendered~~ — FIXED: status banners now shown in sidebar (error red / mock blue).

## [area: ui] AdvancedSettingsModal

- **Consistency slider precision loss** — value scaled ×100 for the 0–100 slider range. Sub-percent precision (e.g. 0.075 → 0.08) is lost. Consider 2-decimal display or a raw 0–1 range.
- ~~Tab icons use emoji~~ — FIXED: replaced with inline SVGs.
- ~~Profile/spaCy/Ollama selects still use raw `<select>`~~ — FIXED: all replaced with `CarbonSelect`.

## [area: ui] General

- ~~**No loading/startup state**~~ — FIXED: SidebarPanel now shows an animated "Initializing…" spinner banner when `ready=false` and no startupError is set.
- **AskPopover token bar has no label** — percentage or token count is not shown alongside the progress bar.
- ~~**FileQueueList fixed max-height**~~ — FIXED: changed to `clamp(120px, 30vh, 240px)`.

---

## [area: styling-system] [FRONTEND-018-complete-token-adoption]
type: feature
status: DONE

Problem: Shared design tokens were introduced, but many components still use hardcoded colors/gradients/shadows.
Why this is a problem: Theming changes (for example dark/black mode) still require widespread manual edits and risk inconsistent visuals.
Done looks like: Core UI components use semantic tokens for colors, borders, surfaces, and key shadows; only intentional decorative exceptions remain.
Resolution: All components migrated to CSS custom properties. Full dark theme added via `[data-theme="dark"]` overrides in `tokens.css`. Reusable `Button`, `ToggleSwitch`, `ThemeToggle` shared components created. `AdvancedSettingsModal` fully redesigned with 5-tab layout. Dark/light background images switch reactively. Anti-flash theme script in `app.html`.

## [area: route-architecture] [FRONTEND-019A-extract-settings-orchestration]
type: feature

Problem: Settings/profile/config lifecycle orchestration remains in `src/routes/+page.svelte`.
Why this is a problem: Settings changes remain tightly coupled to route rendering and are hard to test in isolation.
Done looks like: Settings/profile actions are moved to a dedicated domain action module with explicit dependencies and typed contracts.

## [area: route-architecture] [FRONTEND-019B-extract-run-and-queue-orchestration]
type: feature

Problem: Run submission, payload selection, queue updates, and completion/error handling remain route-owned.
Why this is a problem: Processing lifecycle behavior is difficult to evolve safely and review due to broad route coupling.
Done looks like: Run/queue lifecycle orchestration is extracted to a dedicated workbench action module consumed by the route.

## [area: route-architecture] [FRONTEND-019C-extract-preview-and-attachment-orchestration]
type: feature

Problem: Preview selection, attachment open/edit/reconvert, and preview save orchestration remain route-owned.
Why this is a problem: Attachment and preview logic has high complexity and is difficult to reason about when mixed with route composition.
Done looks like: Preview/attachment orchestration is extracted to a dedicated module with typed action APIs used by the route.

## BUG: visible overflow with a lot of attachment
When attaching +50 files, both the file tags element and the conversation status element (when expanded) give overflow.
Each should have a fixed max-height and a scrollable overflow.

## BUG: Tag IP ADDRESS has no color highlight
Expect each tag to have a unique color.

Optionally create a generic function that converts tag name to a modern color (not just raw unicode to hex, but something more refined).


## FEATURE: settings - move profile to separate tag
Move profile related setting to a separate settings tab

## FEATURE: remove responsive resizing
Currently resizing the UI gives unexpected layout.
We do not support resizable UI's and only need Desktop support.

There is currently an issue that with smaller screens the Ui flexes into vertical alignment, this should never happen. Sections should have a % of the total width, but not flex wrap.


## FEATURE: add general clear button in INPUT
INPUT needs a button to simply reset everything. Currently you have to manually delete all attachments and text.

Expected:
"Reset" button, before the "Run" button that clear all INPUT and attachments.