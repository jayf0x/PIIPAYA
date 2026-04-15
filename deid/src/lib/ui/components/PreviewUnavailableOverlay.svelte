<script lang="ts">
  let {
    title = "No preview",
    subtitle = "File type is not supported.",
  }: {
    title?: string;
    subtitle?: string;
  } = $props();
</script>

<div class="overlay" role="status" aria-live="polite">
  <div class="icon-circle">
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
  </div>
  <h3>{title}</h3>
  <p>{subtitle}</p>
</div>

<style>
  .overlay {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    text-align: center;
    padding: var(--space-xl);
    background: var(--surface-solid);
    color: var(--text-primary);
    z-index: 2;
    gap: var(--space-sm);
  }

  .icon-circle {
    width: 56px;
    height: 56px;
    border-radius: var(--radius-full);
    background: var(--surface-hover);
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-muted);
    margin-bottom: var(--space-sm);
  }

  h3 {
    margin: 0;
    font-size: 18px;
    font-weight: 700;
  }

  p {
    margin: 0;
    font-size: 13px;
    color: var(--text-secondary);
  }
</style>
