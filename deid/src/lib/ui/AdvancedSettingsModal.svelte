<script lang="ts">
  import type { SpacyModelInfo, OllamaModelInfo } from "$lib/types/ui";
  import type { RuntimeConfig } from "$lib/domain/backend/contract";
  import CarbonSlider from "$lib/ui/shared/CarbonSlider.svelte";
  import CarbonSelect from "$lib/ui/shared/CarbonSelect.svelte";
  import Button from "$lib/ui/shared/Button.svelte";
  import ToggleSwitch from "$lib/ui/shared/ToggleSwitch.svelte";

  let {
    visible,
    ready,
    processing,
    supportsThemePackImport,
    config,
    themes,
    spacyModels,
    fallbackSpacyModels,
    ollamaModels,
    themePackPath,
    purgeDays,
    supportsResetData,
    supportsPurgeData,
    storageEstimateLabel,
    profiles,
    activeProfileName,
    onClose,
    onSetTheme,
    onSetStrength,
    onConfig,
    onThemePackPath,
    onImportThemePack,
    onInstallSpacyModel,
    onSelectProfile,
    onSaveProfileAs,
    onSaveConfig,
    onDeleteProfile = () => {},
    onRenameProfile,
    onPurgeDays,
    onPurgeData,
    onResetData,
  }: {
    visible: boolean;
    ready: boolean;
    processing: boolean;
    supportsThemePackImport: boolean;
    config: RuntimeConfig;
    themes: string[];
    spacyModels: SpacyModelInfo[];
    fallbackSpacyModels: SpacyModelInfo[];
    ollamaModels: OllamaModelInfo[];
    themePackPath: string;
    purgeDays: number;
    supportsResetData: boolean;
    supportsPurgeData: boolean;
    storageEstimateLabel: string;
    profiles: string[];
    activeProfileName: string;
    onClose: () => void;
    onSetTheme: (theme: string) => void;
    onSetStrength: (value: number) => void;
    onConfig: <K extends keyof RuntimeConfig>(key: K, value: RuntimeConfig[K]) => void;
    onThemePackPath: (value: string) => void;
    onImportThemePack: () => void;
    onInstallSpacyModel: (model: string) => void;
    onSelectProfile: (name: string) => void;
    onSaveProfileAs: (name: string) => void;
    onSaveConfig: () => void;
    onDeleteProfile: () => void;
    onRenameProfile: (name: string) => void;
    onPurgeDays: (value: number) => void;
    onPurgeData: () => void;
    onResetData: () => void;
  } = $props();

  type Tab = "core" | "nlp" | "processing" | "agent" | "data";
  let activeTab = $state<Tab>("core");

  const tabs: { id: Tab; label: string; icon: string }[] = [
    { id: "core",       label: "Core",       icon: `<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>` },
    { id: "nlp",        label: "NLP",        icon: `<path d="M12 2a8 8 0 0 1 8 8v1a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3v-1a8 8 0 0 1 8-8z"/><path d="M9 21v-4a3 3 0 0 1 6 0v4"/><line x1="9" y1="21" x2="15" y2="21"/>` },
    { id: "processing", label: "Processing", icon: `<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>` },
    { id: "agent",      label: "Agent",      icon: `<rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/><path d="M12 7v4"/><line x1="8" y1="16" x2="8" y2="16"/><line x1="16" y1="16" x2="16" y2="16"/>` },
    { id: "data",       label: "Data",       icon: `<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>` },
  ];

  const isDisabled = $derived(!ready || processing);

  let initialConfigJson = $state("");
  let wasVisible = $state(false);
  $effect(() => {
    if (visible && !wasVisible) {
      initialConfigJson = JSON.stringify(config);
      wasVisible = true;
    } else if (!visible) {
      wasVisible = false;
    }
  });
  const configChanged = $derived(initialConfigJson !== "" && JSON.stringify(config) !== initialConfigJson);

  let confirmDelete = $state(false);
  let renamingProfile = $state(false);
  let renameValue = $state("");
  let addingProfile = $state(false);
  let newProfileName = $state("");

  function saveRename() {
    if (renameValue.trim() && renameValue.trim() !== activeProfileName) onRenameProfile(renameValue.trim());
    renamingProfile = false;
  }

  function saveNewProfile() {
    const name = newProfileName.trim();
    if (name) onSaveProfileAs(name);
    addingProfile = false;
    newProfileName = "";
  }


</script>

{#if visible}
  <div class="modal-backdrop" role="presentation" onclick={onClose}></div>
  <div class="modal" role="dialog" aria-modal="true" aria-label="Settings">
    <!-- Header -->
    <header class="modal-head">
      <div class="head-left">
        <h3>Settings</h3>
        <p class="head-subtitle">Profile: <strong>{activeProfileName}</strong></p>
      </div>
      <div class="head-actions">
        {#if confirmDelete}
          <span class="delete-confirm-text">Delete this profile?</span>
          <Button variant="danger" size="sm" onclick={onDeleteProfile} disabled={isDisabled}>Yes, Delete</Button>
          <Button variant="ghost" size="sm" onclick={() => (confirmDelete = false)}>Cancel</Button>
        {:else}
          <Button variant="ghost" size="sm" onclick={onSaveConfig} disabled={isDisabled || !configChanged}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
            Save
          </Button>
          <Button variant="ghost" size="sm" onclick={() => (confirmDelete = true)} disabled={isDisabled}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>
            Delete
          </Button>
        {/if}
        <Button variant="icon" size="sm" onclick={onClose} ariaLabel="Close">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </Button>
      </div>
    </header>

    <!-- Tab Navigation -->
    <nav class="tab-bar" role="tablist">
      {#each tabs as tab}
        <button
          role="tab"
          class="tab"
          class:active={activeTab === tab.id}
          aria-selected={activeTab === tab.id}
          onclick={() => (activeTab = tab.id)}
        >
          <svg class="tab-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{@html tab.icon}</svg>
          <span class="tab-label">{tab.label}</span>
        </button>
      {/each}
    </nav>

    <!-- Content -->
    <div class="modal-body">
      {#if activeTab === "core"}
        <div class="tab-content">
          <section class="card">
            <div class="card-head">
              <h4>Profile</h4>
            </div>
            <div class="card-body">
              <!-- Switch profile -->
              <div class="field">
                <CarbonSelect
                  labelText="Active Profile"
                  selected={activeProfileName}
                  items={profiles}
                  disabled={isDisabled}
                  onchange={onSelectProfile}
                />
              </div>
              <!-- Rename current profile -->
              <div class="rename-row">
                {#if renamingProfile}
                  <input
                    class="rename-input"
                    type="text"
                    bind:value={renameValue}
                    onkeydown={(e) => { if (e.key === "Enter") saveRename(); if (e.key === "Escape") renamingProfile = false; }}
                    placeholder="New profile name"
                    autofocus
                  />
                  <button class="rename-icon-btn" title="Save name" onclick={saveRename}>
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg>
                  </button>
                  <button class="rename-icon-btn" title="Cancel" onclick={() => (renamingProfile = false)}>
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                  </button>
                {:else}
                  <span class="rename-label">{activeProfileName}</span>
                  <button class="rename-icon-btn" title="Rename this profile" onclick={() => { renamingProfile = true; renameValue = activeProfileName; }} disabled={isDisabled}>
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                  </button>
                {/if}
              </div>
              <!-- Add new profile -->
              <div class="rename-row">
                {#if addingProfile}
                  <input
                    class="rename-input"
                    type="text"
                    bind:value={newProfileName}
                    onkeydown={(e) => { if (e.key === "Enter") saveNewProfile(); if (e.key === "Escape") { addingProfile = false; newProfileName = ""; } }}
                    placeholder="New profile name"
                    autofocus
                  />
                  <button class="rename-icon-btn" title="Create profile" onclick={saveNewProfile}>
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg>
                  </button>
                  <button class="rename-icon-btn" title="Cancel" onclick={() => { addingProfile = false; newProfileName = ""; }}>
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                  </button>
                {:else}
                  <span class="rename-label" style="color: var(--text-muted)">Add profile…</span>
                  <button class="rename-icon-btn" title="Add new profile" onclick={() => { addingProfile = true; newProfileName = ""; }} disabled={isDisabled}>
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                  </button>
                {/if}
              </div>
            </div>
          </section>

          <section class="card">
            <div class="card-head">
              <h4>Engine</h4>
            </div>
            <div class="card-body">
              <label class="field">
                <span class="field-label">Seed</span>
                <input
                  class="field-input"
                  type="text"
                  value={String(config.seed ?? "")}
                  oninput={(ev) => onConfig("seed", (ev.currentTarget as HTMLInputElement).value)}
                  disabled={isDisabled}
                  placeholder="Random seed value"
                />
              </label>
              <div class="field">
                <CarbonSelect
                  labelText="Active Theme"
                  selected={String(config.active_theme ?? "default")}
                  items={themes.length > 0 ? themes : ["default"]}
                  disabled={isDisabled}
                  onchange={onSetTheme}
                />
              </div>
              <div class="field">
                <CarbonSlider
                  id="consistency-slider"
                  labelText="Consistency"
                  min={0}
                  max={100}
                  step={1}
                  value={Math.round(Number(config.consistency ?? 0.1) * 100)}
                  showPercent={true}
                  disabled={isDisabled}
                  onchange={(value) => onConfig("consistency", value / 100)}
                />
              </div>
              <div class="field">
                <CarbonSlider
                  id="strength-slider-modal"
                  labelText="Strength"
                  min={0}
                  max={100}
                  step={1}
                  value={Math.round((1 - Number(config.score_threshold ?? 0.35)) * 100)}
                  showPercent={true}
                  disabled={isDisabled}
                  onchange={(value) => onSetStrength(value / 100)}
                />
              </div>
            </div>
          </section>

          <section class="card">
            <div class="card-head">
              <h4>Theme Packs</h4>
            </div>
            <div class="card-body">
              <label class="field">
                <span class="field-label">Absolute pack path</span>
                <input
                  class="field-input"
                  type="text"
                  value={themePackPath}
                  oninput={(ev) => onThemePackPath((ev.currentTarget as HTMLInputElement).value)}
                  disabled={isDisabled}
                  placeholder="/path/to/theme-pack.json"
                />
              </label>
              <Button variant="secondary" size="md" onclick={onImportThemePack} disabled={!supportsThemePackImport || isDisabled || !themePackPath.trim()}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                Import Theme Pack
              </Button>
            </div>
          </section>
        </div>
      {/if}

      {#if activeTab === "nlp"}
        <div class="tab-content">
          <section class="card">
            <div class="card-head">
              <h4>Model Configuration</h4>
            </div>
            <div class="card-body">
              <div class="field">
                <CarbonSelect
                  labelText="spaCy Model"
                  selected={String(config.spacy_model ?? "en_core_web_lg")}
                  items={(spacyModels.length > 0 ? spacyModels : fallbackSpacyModels).map((m) => ({
                    value: m.name,
                    text: `${m.name}${m.installed ? " (installed)" : ""}`,
                  }))}
                  disabled={isDisabled}
                  onchange={(v) => onConfig("spacy_model", v)}
                />
              </div>
              <label class="field">
                <span class="field-label">Analysis Language</span>
                <input
                  class="field-input"
                  type="text"
                  value={String(config.analysis_language ?? "en")}
                  oninput={(ev) => onConfig("analysis_language", (ev.currentTarget as HTMLInputElement).value)}
                  disabled={isDisabled}
                />
              </label>
            </div>
          </section>

          <section class="card">
            <div class="card-head">
              <h4>Behavior</h4>
            </div>
            <div class="card-body">
              <ToggleSwitch
                label="Reload NLP on Run"
                checked={Boolean(config.reload_nlp_on_run ?? false)}
                disabled={isDisabled}
                onchange={(v) => onConfig("reload_nlp_on_run", v)}
              />
              <ToggleSwitch
                label="Reversible Mapping"
                checked={Boolean(config.reversible_mapping_enabled ?? false)}
                disabled={isDisabled}
                onchange={(v) => onConfig("reversible_mapping_enabled", v)}
              />
            </div>
          </section>

          <section class="card">
            <div class="card-head">
              <h4>spaCy Installers</h4>
            </div>
            <div class="card-body">
              <div class="model-grid">
                {#each (spacyModels.length > 0 ? spacyModels : fallbackSpacyModels) as model}
                  <div class="model-item" class:installed={model.installed}>
                    <div class="model-info">
                      <span class="model-name">{model.name}</span>
                      <span class="model-status" class:active={model.installed}>
                        {model.installed ? "Installed" : "Not installed"}
                      </span>
                    </div>
                    <Button
                      variant={model.installed ? "ghost" : "primary"}
                      size="sm"
                      disabled={isDisabled || model.installed}
                      onclick={() => onInstallSpacyModel(model.name)}
                    >
                      {model.installed ? "✓" : "Install"}
                    </Button>
                  </div>
                {/each}
              </div>
            </div>
          </section>
        </div>
      {/if}

      {#if activeTab === "processing"}
        <div class="tab-content">
          <section class="card">
            <div class="card-head">
              <h4>Performance</h4>
            </div>
            <div class="card-body">
              <label class="field">
                <span class="field-label">Chunk Size (characters)</span>
                <input
                  class="field-input"
                  type="number"
                  value={Number(config.chunk_size_chars ?? 2000)}
                  oninput={(ev) => onConfig("chunk_size_chars", Number((ev.currentTarget as HTMLInputElement).value))}
                  disabled={isDisabled}
                />
                <span class="field-hint">Text is split into chunks of this size for processing.</span>
              </label>
              <label class="field">
                <span class="field-label">Max Workers</span>
                <input
                  class="field-input"
                  type="number"
                  value={Number(config.max_workers ?? 1)}
                  oninput={(ev) => onConfig("max_workers", Number((ev.currentTarget as HTMLInputElement).value))}
                  disabled={isDisabled}
                />
                <span class="field-hint">Parallel worker threads for batch processing.</span>
              </label>
            </div>
          </section>

        </div>
      {/if}

      {#if activeTab === "agent"}
        <div class="tab-content">
          <section class="card">
            <div class="card-head">
              <h4>Ollama Integration</h4>
              <ToggleSwitch
                checked={Boolean(config.ollama_enabled ?? false)}
                disabled={isDisabled}
                onchange={(v) => onConfig("ollama_enabled", v)}
              />
            </div>
            <div class="card-body">
              <label class="field">
                <span class="field-label">Endpoint</span>
                <input
                  class="field-input"
                  type="text"
                  value={String(config.ollama_endpoint ?? "http://127.0.0.1:11434")}
                  oninput={(ev) => onConfig("ollama_endpoint", (ev.currentTarget as HTMLInputElement).value)}
                  disabled={isDisabled}
                  placeholder="http://127.0.0.1:11434"
                />
              </label>
              <div class="field">
                <CarbonSelect
                  labelText="Model"
                  selected={String(config.ollama_model ?? "qwen3.5:9b")}
                  items={(ollamaModels.length > 0 ? ollamaModels : [{ name: "qwen3.5:9b", active: true }]).map(
                    (m) => ({ value: m.name, text: m.active ? `${m.name} (active)` : m.name }),
                  )}
                  disabled={isDisabled || !Boolean(config.ollama_enabled ?? false)}
                  onchange={(v) => onConfig("ollama_model", v)}
                />
              </div>
            </div>
          </section>
        </div>
      {/if}

      {#if activeTab === "data"}
        <div class="tab-content">
          <section class="card">
            <div class="card-head">
              <h4>Storage</h4>
            </div>
            <div class="card-body">
              <div class="storage-badge">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
                <span>Estimated stored data: <strong>{storageEstimateLabel}</strong></span>
              </div>
              <label class="field">
                <span class="field-label">Purge data older than (days)</span>
                <input
                  class="field-input"
                  type="number"
                  min="1"
                  max="3650"
                  value={purgeDays}
                  oninput={(ev) => onPurgeDays(Number((ev.currentTarget as HTMLInputElement).value))}
                  disabled={isDisabled}
                />
              </label>
              <div class="action-row">
                <Button variant="secondary" size="md" onclick={onPurgeData} disabled={isDisabled || !supportsPurgeData}>
                  Purge Old Data
                </Button>
                <Button variant="danger" size="md" onclick={onResetData} disabled={isDisabled || !supportsResetData}>
                  Reset App Data
                </Button>
              </div>
            </div>
          </section>
        </div>
      {/if}
    </div>

    <!-- Footer -->
    <footer class="modal-foot">
      <Button variant="primary" size="md" onclick={onClose}>Done</Button>
    </footer>
  </div>
{/if}

<style>
  /* ── Backdrop ────────────────────────────────── */
  .modal-backdrop {
    position: fixed;
    inset: 0;
    background: var(--surface-overlay);
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    z-index: 90;
    animation: fadeIn var(--duration-fast) var(--ease-out);
  }

  /* ── Modal ──────────────────────────────────── */
  .modal {
    position: fixed;
    inset: 4vh 6vw;
    z-index: 91;
    background: var(--surface-modal);
    border: 1px solid var(--border-soft);
    border-radius: var(--radius-xl);
    box-shadow: var(--shadow-modal);
    display: grid;
    grid-template-rows: auto auto 1fr auto;
    overflow: hidden;
    animation: slideUp var(--duration-normal) var(--ease-out);
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  @keyframes slideUp {
    from { opacity: 0; transform: translateY(12px) scale(0.98); }
    to { opacity: 1; transform: translateY(0) scale(1); }
  }

  /* ── Header ─────────────────────────────────── */
  .modal-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: var(--space-lg) var(--space-xl);
    border-bottom: 1px solid var(--border-soft);
    background: var(--surface-modal-head);
  }

  .head-left h3 {
    margin: 0;
    font-size: 17px;
    font-weight: 700;
    color: var(--text-primary);
    letter-spacing: -0.01em;
  }

  .head-subtitle {
    margin: 3px 0 0;
    font-size: 12px;
    color: var(--text-tertiary);
  }

  .head-actions {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .delete-confirm-text {
    font-size: 12px;
    color: var(--text-danger);
    margin-right: 4px;
  }

  /* ── Rename row ─────────────────────────────── */
  .rename-row {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 6px;
  }

  .rename-label {
    font-size: 12px;
    color: var(--text-secondary);
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .rename-input {
    flex: 1;
    font-size: 12px;
    padding: 4px 8px;
    border: 1px solid var(--border-mid);
    border-radius: var(--radius-sm);
    background: var(--surface-input);
    color: var(--text-primary);
    outline: none;
  }

  .rename-input:focus {
    border-color: var(--action-primary);
    box-shadow: var(--focus-ring);
  }

  .rename-icon-btn {
    width: 26px;
    height: 26px;
    border: 1px solid var(--border-soft);
    background: var(--surface-hover);
    color: var(--text-secondary);
    border-radius: var(--radius-sm);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    transition: background var(--duration-fast) var(--ease-out), color var(--duration-fast) var(--ease-out);
  }

  .rename-icon-btn:hover:not(:disabled) {
    background: var(--surface-hover-strong);
    color: var(--text-primary);
  }

  .rename-icon-btn:disabled {
    opacity: 0.4;
    cursor: default;
  }

  /* ── Tab Bar ────────────────────────────────── */
  .tab-bar {
    display: flex;
    gap: 2px;
    padding: 6px var(--space-xl);
    background: var(--surface-panel-strong);
    border-bottom: 1px solid var(--border-soft);
    overflow-x: auto;
  }

  .tab {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 14px;
    border: none;
    border-radius: var(--radius-sm);
    background: transparent;
    color: var(--text-secondary);
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    white-space: nowrap;
    transition:
      background var(--duration-fast) var(--ease-out),
      color var(--duration-fast) var(--ease-out);
  }

  .tab:hover {
    background: var(--surface-hover);
    color: var(--text-primary);
  }

  .tab.active {
    background: var(--action-primary-soft);
    color: var(--text-accent);
  }

  .tab-icon {
    flex-shrink: 0;
    display: block;
  }

  .tab-label {
    line-height: 1;
  }

  /* ── Body ───────────────────────────────────── */
  .modal-body {
    overflow: auto;
    padding: var(--space-xl);
  }

  .tab-content {
    display: flex;
    flex-direction: column;
    gap: var(--space-lg);
    max-width: 640px;
    animation: contentFadeIn var(--duration-fast) var(--ease-out);
  }

  @keyframes contentFadeIn {
    from { opacity: 0; transform: translateY(4px); }
    to { opacity: 1; transform: translateY(0); }
  }

  /* ── Card ───────────────────────────────────── */
  .card {
    border: 1px solid var(--border-soft);
    border-radius: var(--radius-lg);
    background: var(--surface-card);
    overflow: hidden;
    transition: border-color var(--duration-fast) var(--ease-out);
  }

  .card:hover {
    border-color: var(--border-mid);
  }

  .card-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: var(--space-md) var(--space-lg);
    border-bottom: 1px solid var(--border-soft);
    background: var(--surface-elevated);
  }

  .card-head h4 {
    margin: 0;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--text-primary);
  }

  .card-body {
    padding: var(--space-lg);
    display: flex;
    flex-direction: column;
    gap: var(--space-lg);
  }

  /* ── Fields ─────────────────────────────────── */
  .field {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .field-label {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--text-tertiary);
  }

  .field-input {
    width: 100%;
    border: 1px solid var(--border-input);
    border-radius: var(--radius-sm);
    padding: 9px 12px;
    font-size: 13px;
    background: var(--surface-input);
    color: var(--text-primary);
    box-sizing: border-box;
    transition:
      border-color var(--duration-fast) var(--ease-out),
      box-shadow var(--duration-fast) var(--ease-out);
  }

  .field-input:focus {
    outline: none;
    border-color: var(--border-input-focus);
    box-shadow: var(--focus-ring);
  }

  .field-input:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }

  .field-input::placeholder {
    color: var(--text-muted);
  }

  .field-textarea {
    resize: vertical;
    min-height: 120px;
    font-family: var(--font-mono);
    font-size: 12px;
    line-height: 1.6;
  }

  .field-hint {
    font-size: 11px;
    color: var(--text-muted);
    line-height: 1.4;
  }

  .field-row.inline {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: var(--space-sm);
    align-items: center;
  }

  /* ── Model Grid ─────────────────────────────── */
  .model-grid {
    display: flex;
    flex-direction: column;
    gap: var(--space-sm);
  }

  .model-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: var(--space-sm) var(--space-md);
    border-radius: var(--radius-sm);
    border: 1px solid var(--border-soft);
    background: var(--surface-input);
    transition: border-color var(--duration-fast) var(--ease-out);
  }

  .model-item:hover {
    border-color: var(--border-mid);
  }

  .model-item.installed {
    border-color: var(--border-accent);
    background: var(--surface-accent-soft);
  }

  .model-info {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .model-name {
    font-size: 13px;
    font-weight: 600;
    color: var(--text-primary);
    font-family: var(--font-mono);
  }

  .model-status {
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-muted);
  }

  .model-status.active {
    color: var(--status-done);
  }

  /* ── Storage Badge ──────────────────────────── */
  .storage-badge {
    display: flex;
    align-items: center;
    gap: var(--space-sm);
    padding: var(--space-md);
    border-radius: var(--radius-sm);
    background: var(--surface-accent-soft);
    border: 1px solid var(--border-accent);
    font-size: 13px;
    color: var(--text-accent);
  }

  .storage-badge strong {
    font-weight: 700;
  }

  /* ── Action Row ─────────────────────────────── */
  .action-row {
    display: flex;
    gap: var(--space-sm);
    flex-wrap: wrap;
  }

  /* ── Footer ─────────────────────────────────── */
  .modal-foot {
    border-top: 1px solid var(--border-soft);
    background: var(--surface-modal-foot);
    padding: var(--space-md) var(--space-xl);
    display: flex;
    justify-content: flex-end;
  }

  /* ── Responsive ─────────────────────────────── */
  @media (max-width: 980px) {
    .modal {
      inset: 2vh 2vw;
    }

    .modal-body {
      padding: var(--space-lg);
    }

    .tab-bar {
      padding: 6px var(--space-lg);
    }

    .tab-label {
      display: none;
    }

    .tab {
      padding: 8px 10px;
    }
  }
</style>
