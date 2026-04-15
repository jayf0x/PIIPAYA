<script lang="ts">
  let {
    id,
    label,
    min,
    max,
    step = 1,
    value,
    disabled = false,
    showPercent = false,
    onChange,
  }: {
    id: string;
    label: string;
    min: number;
    max: number;
    step?: number;
    value: number;
    disabled?: boolean;
    showPercent?: boolean;
    onChange: (value: number) => void;
  } = $props();

  const pct = $derived(Math.max(0, Math.min(100, ((value - min) / Math.max(1e-9, max - min)) * 100)));
</script>

<div class="range-field">
  <label for={id}>{label}</label>
  <div class="slider-container">
    <input
      {id}
      type="range"
      {min}
      {max}
      {step}
      {value}
      style={`--pct: ${pct}%`}
      {disabled}
      oninput={(event) => onChange(Number((event.currentTarget as HTMLInputElement).value))}
    />
    <span class="slider-value">{showPercent ? `${Math.round(value)}%` : Number(value).toFixed(2)}</span>
  </div>
</div>

<style>
  .range-field {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .range-field label {
    font-size: 11px;
    font-weight: 700;
    color: var(--text-tertiary);
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .slider-container {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .slider-container input[type="range"] {
    flex: 1;
    height: 4px;
    border-radius: var(--radius-full);
    background: linear-gradient(to right, var(--slider-fill) 0%, var(--slider-fill) var(--pct), var(--slider-track) var(--pct), var(--slider-track) 100%);
    appearance: none;
    -webkit-appearance: none;
    cursor: pointer;
    transition: opacity var(--duration-fast) var(--ease-out);
  }

  .slider-container input[type="range"]:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .slider-container input[type="range"]::-webkit-slider-runnable-track {
    height: 4px;
    border-radius: var(--radius-full);
    background: transparent;
  }

  .slider-container input[type="range"]::-moz-range-track {
    height: 4px;
    border-radius: var(--radius-full);
    background: transparent;
  }

  .slider-container input[type="range"]::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 16px;
    height: 16px;
    border-radius: var(--radius-full);
    background: var(--slider-thumb);
    border: 2px solid var(--slider-thumb-border);
    box-shadow: var(--slider-thumb-shadow);
    margin-top: -6px;
    transition:
      transform var(--duration-fast) var(--ease-spring),
      box-shadow var(--duration-fast) var(--ease-out);
  }

  .slider-container input[type="range"]::-webkit-slider-thumb:hover {
    transform: scale(1.15);
    box-shadow: var(--slider-thumb-shadow), var(--focus-ring);
  }

  .slider-container input[type="range"]::-moz-range-thumb {
    width: 16px;
    height: 16px;
    border-radius: var(--radius-full);
    background: var(--slider-thumb);
    border: 2px solid var(--slider-thumb-border);
    box-shadow: var(--slider-thumb-shadow);
  }

  .slider-value {
    font-size: 13px;
    font-weight: 600;
    color: var(--text-primary);
    min-width: 46px;
    text-align: right;
    font-variant-numeric: tabular-nums;
  }
</style>
