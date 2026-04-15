<script lang="ts">
  import type { FileQueueItem } from "$lib/types/ui";

  let {
    items,
  }: {
    items: FileQueueItem[];
  } = $props();
  let expanded = $state(false);

  function statusLabel(item: FileQueueItem) {
    if (item.status === "processing") return "Processing";
    if (item.status === "done") return "Done";
    if (item.status === "failed") return "Failed";
    if (item.status === "unsupported") return "Unsupported";
    return "Queued";
  }

  function convertedCount(items: FileQueueItem[]) {
    return items.filter((item) => item.status === "done").length;
  }

  function processedCount(items: FileQueueItem[]) {
    return items.filter(
      (item) =>
        item.status === "done" ||
        item.status === "failed" ||
        item.status === "unsupported",
    ).length;
  }

  function overallProgress(items: FileQueueItem[]) {
    if (items.length === 0) return 0;
    return Math.round((convertedCount(items) / items.length) * 100);
  }

  function summaryStatus(items: FileQueueItem[]) {
    const active = items.find((item) => item.status === "processing");
    if (active) return active.detail || `Processing ${active.name}`;
    const failed = items.find((item) => item.status === "failed");
    if (failed) return failed.detail || "File conversion failed";
    if (items.length > 0 && processedCount(items) === items.length) return "All files processed";
    return "Queued";
  }
</script>

{#if items.length > 0}
  <section class="queue" aria-label="File processing queue">
    <header class="summary">
      <div class="summary-progress" aria-hidden="true">
        <span class="summary-fill" style={`width: ${overallProgress(items)}%`}></span>
      </div>
      <small class="summary-count">{convertedCount(items)}/{items.length} converted</small>
      <small class="summary-status">{summaryStatus(items)}</small>
      <button
        type="button"
        class="toggle"
        aria-expanded={expanded}
        aria-label={expanded ? "Collapse queue" : "Expand queue"}
        onclick={() => (expanded = !expanded)}
      >
        <svg
          class:open={expanded}
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2.5"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <path d="m6 9 6 6 6-6"></path>
        </svg>
      </button>
    </header>
    {#if expanded}
      <div class="rows">
      {#each items as item (item.id)}
        <article
          class="row"
          class:failed={item.status === "failed"}
          class:unsupported={item.status === "unsupported"}
        >
          <div class="row-top">
            <span class="name" title={item.name}>{item.name}</span>
            <span class={`status ${item.status}`}>{statusLabel(item)}</span>
          </div>
          <div class="bar">
            <span class="bar-fill" style={`width: ${Math.max(0, Math.min(100, item.progressPct))}%`}></span>
          </div>
          <small class="detail">{item.detail}</small>
        </article>
      {/each}
      </div>
    {/if}
  </section>
{/if}

<style>
  .queue {
    margin: var(--space-sm) var(--space-lg) 0;
    display: grid;
    gap: var(--space-sm);
  }

  .summary {
    display: flex;
    align-items: center;
    gap: 10px;
    min-width: 0;
  }

  .summary-progress {
    flex: 1 1 220px;
    min-width: 120px;
    height: 6px;
    border-radius: var(--radius-full);
    background: var(--progress-track);
    overflow: hidden;
  }

  .summary-fill {
    display: block;
    height: 100%;
    background: var(--progress-fill);
    border-radius: var(--radius-full);
    transition: width var(--duration-normal) var(--ease-out);
  }

  .summary-count {
    font-size: 10px;
    color: var(--text-secondary);
    white-space: nowrap;
    font-weight: 600;
  }

  .summary-status {
    flex: 0 1 200px;
    min-width: 0;
    font-size: 10px;
    color: var(--text-primary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .toggle {
    border: none;
    background: transparent;
    padding: 2px;
    color: var(--text-secondary);
    cursor: pointer;
    border-radius: var(--radius-xs);
    line-height: 0;
    transition:
      background var(--duration-fast) var(--ease-out),
      color var(--duration-fast) var(--ease-out);
  }

  .toggle:hover {
    background: var(--surface-hover);
    color: var(--text-primary);
  }

  .toggle svg {
    transition: transform var(--duration-fast) var(--ease-out);
  }

  .toggle svg.open {
    transform: rotate(180deg);
  }

  .rows {
    display: grid;
    gap: 7px;
    max-height: clamp(120px, 30vh, 240px);
    overflow-y: auto;
    padding-right: 2px;
  }

  .row {
    display: grid;
    gap: 4px;
  }

  .row-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-sm);
  }

  .name {
    font-size: 11px;
    color: var(--text-primary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 240px;
    font-weight: 500;
  }

  .status {
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-secondary);
    font-weight: 600;
  }

  .status.processing { color: var(--status-processing); }
  .status.done { color: var(--status-done); }
  .status.failed { color: var(--status-failed); }
  .status.unsupported { color: var(--status-unsupported); }

  .bar {
    height: 4px;
    border-radius: var(--radius-full);
    background: var(--progress-track);
    overflow: hidden;
  }

  .bar-fill {
    display: block;
    height: 100%;
    background: var(--progress-fill);
    border-radius: var(--radius-full);
    transition: width var(--duration-normal) var(--ease-out);
  }

  .row.failed .bar-fill {
    background: var(--progress-fail);
  }

  .row.unsupported .bar-fill {
    background: var(--progress-warn);
  }

  .detail {
    font-size: 10px;
    color: var(--text-muted);
  }
</style>
