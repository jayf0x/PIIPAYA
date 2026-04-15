<script lang="ts">
  import type { EntityFilter } from "$lib/types/ui";
  import CarbonSelect from "$lib/ui/shared/CarbonSelect.svelte";
  import CarbonSlider from "$lib/ui/shared/CarbonSlider.svelte";

  let {
    entityFilters,
    activeEntityFilters,
    supportsThemes,
    themes,
    activeTheme,
    strength,
    disabled = false,
    onToggleEntity,
    onSetTheme,
    onSetStrength,
  }: {
    entityFilters: EntityFilter[];
    activeEntityFilters: Set<string>;
    supportsThemes: boolean;
    themes: string[];
    activeTheme: string;
    strength: number;
    disabled?: boolean;
    onToggleEntity: (entity: string) => void;
    onSetTheme: (theme: string) => void;
    onSetStrength: (value: number) => void;
  } = $props();
</script>

<!-- Entity pills -->
<div class="tags-field" class:disabled>
  <div class="pills-row">
    {#each entityFilters as item}
      <button
        class="entity-pill"
        class:active={activeEntityFilters.has(item.entity)}
        style={`--pill-bg: ${item.color}; --pill-txt: ${item.textColor};`}
        onclick={() => onToggleEntity(item.entity)}
        {disabled}
      >
        {item.label}
      </button>
    {/each}
  </div>
</div>

<div class="sidebar-divider"></div>

<!-- Theme engine (only when supported and themes available) -->
{#if supportsThemes && themes.length > 0}
  <div class="sidebar-field">
    <CarbonSelect
      id="theme-engine"
      labelText="Theme"
      selected={activeTheme}
      items={themes}
      disabled={!supportsThemes || disabled}
      onchange={onSetTheme}
    />
  </div>
{/if}

<!-- Strength slider -->
<div class="sidebar-field">
  <CarbonSlider
    id="strength-slider"
    labelText="Strength"
    min={0}
    max={100}
    step={1}
    value={Math.round(strength * 100)}
    showPercent={true}
    {disabled}
    onchange={(value) => onSetStrength(value / 100)}
  />
</div>

<style>
  .sidebar-field {
    padding: 0 14px;
    margin-bottom: 18px;
  }

  /* Tags row */
  .tags-field {
    padding: 0 14px;
    margin-bottom: 18px;
  }

  .tags-field.disabled {
    opacity: 0.5;
    pointer-events: none;
  }

  .pills-row {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
  }

  .entity-pill {
    display: inline-flex;
    align-items: center;
    padding: 3px 9px;
    border-radius: var(--radius-full);
    font-size: 10px;
    font-weight: 600;
    cursor: pointer;
    white-space: nowrap;
    line-height: 1;
    background: transparent;
    border: 1.5px solid var(--pill-bg);
    color: var(--pill-txt);
    transition:
      background var(--duration-fast) var(--ease-out),
      transform 100ms var(--ease-out),
      box-shadow var(--duration-fast) var(--ease-out);
  }

  .entity-pill.active {
    background: var(--pill-bg);
    color: var(--pill-txt);
    box-shadow: var(--shadow-sm);
  }

  .entity-pill:hover:not(:disabled) {
    transform: translateY(-1px);
    box-shadow: var(--shadow-md);
  }

  .entity-pill:active:not(:disabled) {
    transform: scale(0.96);
  }

  .entity-pill:disabled {
    opacity: 0.5;
    cursor: default;
  }

  .sidebar-divider {
    height: 1px;
    background: var(--border-soft);
    margin: 4px 14px 18px;
  }
</style>
