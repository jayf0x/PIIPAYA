<script lang="ts">
  import type { EntityFilter } from "$lib/types/ui";
  import TagThemeControls from "$lib/ui/components/TagThemeControls.svelte";
  import ThemeToggle from "$lib/ui/shared/ThemeToggle.svelte";
  import Button from "$lib/ui/shared/Button.svelte";
  import CarbonSelect from "$lib/ui/shared/CarbonSelect.svelte";

  import logoImg from "$lib/assets/logo.png";

  let {
    ready,
    processing,
    browserMockMode,
    startupError,
    entityFilters,
    activeEntityFilters,
    supportsThemes,
    themes,
    activeTheme,
    strength,
    collapsed,
    profiles,
    activeProfileName,
    onToggleEntity,
    onSetTheme,
    onSetStrength,
    onOpenAdvanced,
    onToggleCollapsed,
    onSelectProfile,
  }: {
    ready: boolean;
    processing: boolean;
    browserMockMode: boolean;
    startupError: string | null;
    entityFilters: EntityFilter[];
    activeEntityFilters: Set<string>;
    supportsThemes: boolean;
    themes: string[];
    activeTheme: string;
    strength: number;
    collapsed: boolean;
    profiles: string[];
    activeProfileName: string;
    onToggleEntity: (entity: string) => void;
    onSetTheme: (theme: string) => void;
    onSetStrength: (value: number) => void;
    onOpenAdvanced: () => void;
    onToggleCollapsed: () => void;
    onSelectProfile: (name: string) => void;
  } = $props();
</script>

<aside class:collapsed>
  <!-- Top bar: logo + theme toggle + collapse -->
  <div class="sidebar-top">
    {#if !collapsed}
      <img class="logo" src={logoImg} alt="DeID" />
    {/if}
    <div class="sidebar-top-actions">
      {#if !collapsed}
        <ThemeToggle />
      {/if}
      <button
        class="icon-btn"
        title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        onclick={onToggleCollapsed}
        aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          {#if collapsed}
            <path d="M9 18l6-6-6-6" />
          {:else}
            <path d="M15 18l-6-6 6-6" />
          {/if}
        </svg>
      </button>
    </div>
  </div>
  {#if collapsed}
    <div class="collapsed-actions">
      <ThemeToggle />
    </div>
  {/if}

  {#if !collapsed}
    <div class="sidebar-content">
      <!-- Status banners -->
      {#if startupError}
        <div class="status-banner error">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
          <span>{startupError}</span>
        </div>
      {:else if !ready}
        <div class="status-banner loading">
          <svg class="spin" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg>
          <span>Initializing…</span>
        </div>
      {:else if browserMockMode}
        <div class="status-banner mock">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
          <span>Mock mode</span>
        </div>
      {/if}

      <!-- Profile selector -->
      <div class="sidebar-field">
        <CarbonSelect
          id="profile-select"
          labelText="Profile"
          selected={activeProfileName}
          items={profiles}
          disabled={!ready || processing}
          onchange={onSelectProfile}
        />
      </div>

      <!-- Tag + theme controls -->
      <TagThemeControls
        {entityFilters}
        {activeEntityFilters}
        {supportsThemes}
        {themes}
        {activeTheme}
        {strength}
        disabled={!ready || processing}
        {onToggleEntity}
        {onSetTheme}
        {onSetStrength}
      />

      <!-- Footer -->
      <div class="sidebar-foot">
        <Button variant="ghost" size="sm" onclick={onOpenAdvanced} disabled={!ready || processing}>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
          </svg>
          Settings
        </Button>
      </div>
    </div>
  {/if}
</aside>

<style>
  aside {
    width: 100%;
    height: 100%;
    box-sizing: border-box;
    background: var(--surface-sidebar);
    backdrop-filter: blur(30px);
    -webkit-backdrop-filter: blur(30px);
    border-right: 1px solid var(--border-soft);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    transition:
      width var(--duration-normal) ease,
      background-color var(--duration-normal) ease;
  }

  aside.collapsed {
    width: 48px;
    background: var(--surface-sidebar-collapsed);
  }

  /* ── Top bar ── */
  .sidebar-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 10px 10px 14px;
    flex-shrink: 0;
  }

  aside.collapsed .sidebar-top {
    justify-content: center;
    padding: 14px 0;
  }

  .collapsed-actions {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
    padding: 0 0 8px;
  }

  .logo {
    width: 46px;
    height: auto;
    opacity: 0.85;
  }

  .sidebar-top-actions {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .icon-btn {
    width: 34px;
    height: 34px;
    border: 1px solid var(--border-soft);
    background: var(--surface-hover);
    color: var(--text-secondary);
    border-radius: var(--radius-sm);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    transition:
      background var(--duration-fast) var(--ease-out),
      color var(--duration-fast) var(--ease-out),
      border-color var(--duration-fast) var(--ease-out);
  }

  .icon-btn:hover {
    background: var(--surface-hover-strong);
    color: var(--text-primary);
    border-color: var(--border-mid);
  }

  .icon-btn:focus-visible {
    outline: none;
    box-shadow: var(--focus-ring);
  }

  /* ── Scrollable content ── */
  .sidebar-content {
    display: flex;
    flex-direction: column;
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
    padding: 4px 0 0;
    min-width: 220px;
  }

  .sidebar-field {
    padding: 0 14px;
    margin-bottom: 18px;
  }

  /* ── Footer ── */
  .sidebar-foot {
    margin-top: auto;
    padding: 12px 14px 16px;
  }

  .sidebar-foot :global(.btn) {
    width: 100%;
    justify-content: flex-start;
    gap: 7px;
    color: var(--text-secondary);
    font-size: 12px;
    font-weight: 500;
    letter-spacing: 0;
    text-transform: none;
  }

  .sidebar-foot :global(.btn:hover:not(:disabled)) {
    color: var(--text-primary);
    background: var(--surface-hover);
  }

  /* ── Status banners ── */
  .status-banner {
    display: flex;
    align-items: flex-start;
    gap: 7px;
    margin: 0 14px 14px;
    padding: 8px 10px;
    border-radius: var(--radius-sm);
    font-size: 11px;
    font-weight: 500;
    line-height: 1.4;
  }

  .status-banner svg {
    flex-shrink: 0;
    margin-top: 1px;
  }

  .status-banner.error {
    background: var(--surface-danger-soft);
    border: 1px solid var(--border-danger);
    color: var(--text-danger);
  }

  .status-banner.mock {
    background: var(--surface-accent-soft);
    border: 1px solid var(--border-accent);
    color: var(--text-accent);
  }

  .status-banner.loading {
    background: var(--surface-hover);
    border: 1px solid var(--border-soft);
    color: var(--text-secondary);
  }

  .spin {
    animation: sidebar-spin 900ms linear infinite;
    flex-shrink: 0;
  }

  @keyframes sidebar-spin {
    to { transform: rotate(360deg); }
  }
</style>
