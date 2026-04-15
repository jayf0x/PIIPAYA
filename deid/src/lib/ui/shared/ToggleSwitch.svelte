<script lang="ts">
  import { Toggle } from "carbon-components-svelte";

  let {
    checked = false,
    disabled = false,
    label = "",
    id = "",
    onchange,
  }: {
    checked?: boolean;
    disabled?: boolean;
    label?: string;
    id?: string;
    onchange?: (checked: boolean) => void;
  } = $props();
</script>

<div class="toggle-wrap" class:disabled>
  {#if label}
    <span class="toggle-label">{label}</span>
  {/if}
  {#key checked}
    <Toggle
      {id}
      toggled={checked}
      {disabled}
      size="sm"
      hideLabel
      labelText=""
      on:toggle={(e) => onchange?.(e.detail.toggled)}
    />
  {/key}
</div>

<style>
  .toggle-wrap {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-md);
  }

  .toggle-wrap.disabled {
    opacity: 0.5;
    pointer-events: none;
  }

  .toggle-label {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--text-tertiary);
    user-select: none;
  }

  /* Remove Carbon's form-item bottom margin */
  .toggle-wrap :global(.bx--form-item) {
    flex: 0 0 auto;
    margin-bottom: 0;
  }

  /* Hide Carbon's label wrapper text (we render our own) */
  .toggle-wrap :global(.bx--toggle__text--off),
  .toggle-wrap :global(.bx--toggle__text--on) {
    display: none;
  }

  /* ── Track (::before = pill background) ──────── */
  /* Carbon track: unchecked = gray, checked = green.
     Override both with our design tokens. */
  .toggle-wrap :global(.bx--toggle__switch::before) {
    background-color: var(--border-mid);
    border-radius: var(--radius-full);
    box-shadow: none !important;
  }

  /* Checked track */
  .toggle-wrap :global(.bx--toggle-input:checked + .bx--toggle-input__label .bx--toggle__switch::before) {
    background-color: var(--action-primary);
  }

  /* ── Thumb (::after = circle) ─────────────────
     Carbon controls position via transform: translateX.
     Only override color and shadow — never touch
     transform, top, left, or width/height. */
  .toggle-wrap :global(.bx--toggle__switch::after) {
    background-color: var(--surface-solid);
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
  }

  /* Focus ring */
  .toggle-wrap :global(.bx--toggle-input:focus-visible + .bx--toggle-input__label .bx--toggle__switch::before) {
    box-shadow: var(--focus-ring) !important;
  }
</style>
