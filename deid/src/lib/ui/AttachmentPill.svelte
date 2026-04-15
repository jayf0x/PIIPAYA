<script lang="ts">
  let {
    label,
    icon = "file",
    onOpen,
    onDownload,
    onEdit,
    onRemove,
    active = false,
    title,
  }: {
    label: string;
    icon?: "file" | "save";
    onOpen: () => void;
    onDownload: () => void;
    onEdit?: (() => void) | null;
    onRemove?: (() => void) | null;
    active?: boolean;
    title?: string;
  } = $props();
</script>

<div class="pill" class:active title={title ?? label}>
  <button class="seg name" onclick={onOpen}>
    <svg class="seg-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      {#if icon === "save"}
        <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/>
      {:else}
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>
      {/if}
    </svg>
    <span class="name-text">{label}</span>
  </button>
  <span class="divider"></span>
  <button class="seg action-seg" onclick={onDownload} aria-label="Download" title="Download">
    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
  </button>
  {#if onEdit}
    <span class="divider"></span>
    <button class="seg action-seg" onclick={onEdit} aria-label="Edit" title="Edit">
      <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
    </button>
  {/if}
  {#if onRemove}
    <span class="divider"></span>
    <button class="seg action-seg remove" onclick={onRemove} aria-label="Remove" title="Remove">
      <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
    </button>
  {/if}
</div>

<style>
  .pill {
    display: inline-flex;
    align-items: center;
    border: 1px solid var(--border-mid);
    border-radius: var(--radius-sm);
    background: var(--surface-solid);
    font-size: 11px;
    color: var(--text-secondary);
    overflow: hidden;
    transition:
      border-color var(--duration-fast) var(--ease-out),
      box-shadow var(--duration-fast) var(--ease-out);
  }

  .pill:hover {
    border-color: var(--border-strong);
    box-shadow: var(--shadow-sm);
  }

  .pill.active {
    border-color: var(--action-primary);
    box-shadow: 0 0 0 1px var(--action-primary-glow) inset;
    background: var(--surface-accent-soft);
  }

  .divider {
    width: 1px;
    align-self: stretch;
    background: var(--border-soft);
  }

  .seg {
    border: none;
    background: transparent;
    color: inherit;
    font: inherit;
    cursor: pointer;
    padding: 5px 8px;
    display: flex;
    align-items: center;
    gap: 5px;
    transition:
      background var(--duration-fast) var(--ease-out),
      color var(--duration-fast) var(--ease-out);
  }

  .seg:hover {
    background: var(--action-primary-soft);
    color: var(--action-primary);
  }

  .seg.name {
    max-width: 200px;
    overflow: hidden;
    text-align: left;
  }

  .seg-icon {
    flex-shrink: 0;
    opacity: 0.6;
  }

  .name-text {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .action-seg {
    width: 28px;
    padding: 5px 0;
    justify-content: center;
  }

  .action-seg.remove:hover {
    background: var(--surface-danger-soft);
    color: var(--text-danger);
  }
</style>
