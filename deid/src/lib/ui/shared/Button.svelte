<script lang="ts">
  import type { Snippet } from "svelte";

  let {
    variant = "secondary",
    size = "md",
    disabled = false,
    title = "",
    ariaLabel = "",
    type = "button",
    onclick,
    children,
  }: {
    variant?: "primary" | "secondary" | "danger" | "ghost" | "icon";
    size?: "sm" | "md" | "lg";
    disabled?: boolean;
    title?: string;
    ariaLabel?: string;
    type?: "button" | "submit" | "reset";
    onclick?: (event: MouseEvent) => void;
    children?: Snippet;
  } = $props();
</script>

<button
  class="btn btn-{variant} btn-size-{size}"
  {type}
  {disabled}
  {title}
  aria-label={ariaLabel || undefined}
  {onclick}
>
  {#if children}
    {@render children()}
  {/if}
</button>

<style>
  .btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: var(--space-xs);
    border: none;
    cursor: pointer;
    font-weight: 600;
    white-space: nowrap;
    transition:
      background var(--duration-fast) var(--ease-out),
      color var(--duration-fast) var(--ease-out),
      box-shadow var(--duration-fast) var(--ease-out),
      transform 100ms var(--ease-out),
      border-color var(--duration-fast) var(--ease-out),
      opacity var(--duration-fast) var(--ease-out);
    position: relative;
    isolation: isolate;
    line-height: 1;
  }

  .btn:active:not(:disabled) {
    transform: scale(0.97);
  }

  .btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .btn:focus-visible {
    outline: none;
    box-shadow: var(--focus-ring);
  }

  /* ── Sizes ─────────────────────────────────── */
  .btn-size-sm {
    height: 30px;
    padding: 0 10px;
    font-size: 11px;
    border-radius: var(--radius-sm);
  }

  .btn-size-md {
    height: 36px;
    padding: 0 14px;
    font-size: 12px;
    border-radius: var(--radius-md);
  }

  .btn-size-lg {
    height: 42px;
    padding: 0 20px;
    font-size: 13px;
    border-radius: var(--radius-md);
  }

  /* ── Primary ───────────────────────────────── */
  .btn-primary {
    background: var(--action-primary);
    color: var(--text-on-primary);
    border: 1px solid transparent;
    box-shadow: var(--shadow-sm);
  }

  .btn-primary:hover:not(:disabled) {
    background: var(--action-primary-hover);
    box-shadow: var(--shadow-md), 0 0 0 1px var(--action-primary-glow);
  }

  /* ── Secondary ─────────────────────────────── */
  .btn-secondary {
    background: var(--surface-solid);
    color: var(--text-primary);
    border: 1px solid var(--border-strong);
    box-shadow: var(--shadow-sm);
  }

  .btn-secondary:hover:not(:disabled) {
    background: var(--surface-hover);
    border-color: var(--border-mid);
  }

  /* ── Danger ────────────────────────────────── */
  .btn-danger {
    background: var(--surface-danger-soft);
    color: var(--text-danger);
    border: 1px solid var(--border-danger);
  }

  .btn-danger:hover:not(:disabled) {
    background: var(--action-danger);
    color: var(--text-on-primary);
    border-color: var(--action-danger);
  }

  /* ── Ghost ─────────────────────────────────── */
  .btn-ghost {
    background: transparent;
    color: var(--text-secondary);
    border: 1px solid transparent;
  }

  .btn-ghost:hover:not(:disabled) {
    background: var(--surface-hover);
    color: var(--text-primary);
  }

  /* ── Icon ──────────────────────────────────── */
  .btn-icon {
    background: transparent;
    color: var(--text-secondary);
    border: 1px solid transparent;
    padding: 0;
  }

  .btn-size-sm.btn-icon {
    width: 28px;
    height: 28px;
  }

  .btn-size-md.btn-icon {
    width: 34px;
    height: 34px;
  }

  .btn-size-lg.btn-icon {
    width: 40px;
    height: 40px;
  }

  .btn-icon:hover:not(:disabled) {
    background: var(--surface-hover);
    color: var(--action-primary);
  }
</style>
