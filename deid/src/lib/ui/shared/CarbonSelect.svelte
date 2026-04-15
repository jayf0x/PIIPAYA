<script lang="ts">
  import { Select, SelectItem } from "carbon-components-svelte";

  type SelectOption = string | { value: string; text: string };

  let {
    id = "",
    labelText = "",
    selected = "",
    items = [] as SelectOption[],
    disabled = false,
    hideLabel = false,
    onchange,
  }: {
    id?: string;
    labelText?: string;
    selected: string;
    items: SelectOption[];
    disabled?: boolean;
    hideLabel?: boolean;
    onchange?: (value: string) => void;
  } = $props();

  function itemValue(item: SelectOption) {
    return typeof item === "string" ? item : item.value;
  }

  function itemText(item: SelectOption) {
    return typeof item === "string" ? item : item.text;
  }
</script>

<div class="cs-wrap">
  <Select
    {id}
    {labelText}
    {selected}
    {disabled}
    {hideLabel}
    on:update={(e) => onchange?.(e.detail)}
  >
    {#each items as item}
      <SelectItem value={itemValue(item)} text={itemText(item)} />
    {/each}
  </Select>
</div>

<style>
  .cs-wrap :global(.bx--form-item) {
    width: 100%;
    margin-bottom: 0;
  }

  .cs-wrap :global(.bx--select) {
    width: 100%;
  }

  .cs-wrap :global(.bx--label) {
    font-size: 11px;
    font-weight: 600;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 5px;
    line-height: 1.2;
  }

  .cs-wrap :global(.bx--select-input__wrapper) {
    width: 100%;
  }

  .cs-wrap :global(.bx--select-input) {
    background: var(--surface-input);
    color: var(--text-primary);
    font-family: var(--font-sans);
    font-size: 13px;
    font-weight: 500;
    border: 1px solid var(--border-soft);
    border-bottom: 1px solid var(--border-soft);
    border-radius: var(--radius-sm);
    height: 34px;
    padding: 0 36px 0 10px;
    width: 100%;
    cursor: pointer;
    box-shadow: none;
    transition:
      border-color var(--duration-fast) var(--ease-out),
      box-shadow var(--duration-fast) var(--ease-out);
  }

  .cs-wrap :global(.bx--select-input:focus) {
    outline: none;
    border-color: var(--action-primary);
    box-shadow: var(--focus-ring);
  }

  .cs-wrap :global(.bx--select--disabled .bx--select-input) {
    opacity: 0.55;
    cursor: not-allowed;
    background: var(--surface-muted);
  }

  .cs-wrap :global(.bx--select__arrow) {
    fill: var(--text-secondary) !important;
    top: 50%;
    transform: translateY(-50%);
    right: 10px;
  }

  .cs-wrap :global(.bx--select-input:focus ~ .bx--select__arrow) {
    fill: var(--action-primary) !important;
  }

  .cs-wrap :global(.bx--form__helper-text),
  .cs-wrap :global(.bx--form-requirement) {
    display: none;
  }
</style>
