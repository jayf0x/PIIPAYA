<script lang="ts">
  import { Slider } from "carbon-components-svelte";

  let {
    id = "",
    labelText = "",
    value = 0,
    min = 0,
    max = 100,
    step = 1,
    disabled = false,
    showPercent = false,
    showValue = true,
    onchange,
  }: {
    id?: string;
    labelText?: string;
    value: number;
    min?: number;
    max?: number;
    step?: number;
    disabled?: boolean;
    showPercent?: boolean;
    showValue?: boolean;
    onchange?: (value: number) => void;
  } = $props();

  // $derived keeps the label in sync with the parent's controlled value.
  // on:input from Carbon fires immediately on drag, so the parent updates
  // and displayValue reflects the latest dragged position.
  let displayValue = $derived(value);

  function formatDisplay(v: number) {
    return showPercent ? `${Math.round(v)}%` : Number(v).toFixed(2);
  }
</script>

<div class="cslider-wrap">
  <div class="cslider-header">
    {#if labelText}
      <span class="cslider-label">{labelText}</span>
    {/if}
    {#if showValue}
      <span class="cslider-value">{formatDisplay(displayValue)}</span>
    {/if}
  </div>
  <Slider
    {id}
    {value}
    {min}
    {max}
    {step}
    {disabled}
    hideTextInput
    labelText=""
    minLabel=""
    maxLabel=""
    on:input={(e) => onchange?.(e.detail)}
  />
</div>

<style>
  .cslider-wrap {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .cslider-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .cslider-label {
    font-size: 11px;
    font-weight: 600;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }

  .cslider-value {
    font-size: 13px;
    font-weight: 600;
    color: var(--text-primary);
    font-variant-numeric: tabular-nums;
    min-width: 40px;
    text-align: right;
  }

  /* ── Carbon Slider overrides ─────────────────────
     Carbon positions the thumb via reactive style:left
     and fills the track via style:transform scaleX.
     Only touch colors, padding, and visibility.
     Never override height/transform/left/top on
     elements Carbon's JS touches. */

  /* Remove outer padding & hide min/max labels */
  .cslider-wrap :global(.bx--slider-container) {
    padding: 0;
    width: 100%;
  }

  .cslider-wrap :global(.bx--slider__range-label) {
    display: none;
  }

  /* Container: full width */
  .cslider-wrap :global(.bx--slider) {
    width: 100%;
    max-width: 100%;
  }

  /* Track background color — .bx--slider__track is the actual bar */
  .cslider-wrap :global(.bx--slider__track) {
    background: var(--slider-track);
  }

  /* Filled portion color */
  .cslider-wrap :global(.bx--slider__filled-track) {
    background: var(--slider-fill);
  }

  /* Thumb visuals only — Carbon owns position */
  .cslider-wrap :global(.bx--slider__thumb) {
    background: var(--slider-thumb);
    border: 2px solid var(--slider-thumb-border);
    box-shadow: var(--slider-thumb-shadow);
    transition: box-shadow var(--duration-fast) var(--ease-out);
  }

  .cslider-wrap :global(.bx--slider__thumb:hover) {
    box-shadow: var(--slider-thumb-shadow), var(--focus-ring);
  }

  .cslider-wrap :global(.bx--slider__thumb:focus) {
    outline: none;
    box-shadow: var(--slider-thumb-shadow), var(--focus-ring);
  }

  .cslider-wrap :global(.bx--slider--disabled) {
    opacity: 0.5;
    pointer-events: none;
  }

  .cslider-wrap :global(.bx--slider-text-input-wrapper) {
    display: none;
  }
</style>
