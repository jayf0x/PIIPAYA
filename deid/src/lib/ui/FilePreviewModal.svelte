<script lang="ts">
  import type { EntityFilter, OutputSegment } from "$lib/types/ui";
  import { highlightClassForEntity } from "$lib/domain/entities/catalog";
  import TagThemeControls from "$lib/ui/components/TagThemeControls.svelte";
  import Button from "$lib/ui/shared/Button.svelte";

  let {
    visible,
    title,
    content,
    segments = [],
    highlightTags = true,
    kind = "text",
    canEdit = false,
    editBusy = false,
    editEntities = [],
    entityFilters = [],
    supportsThemes = false,
    themes = [],
    editTheme = "default",
    editStrength = 0.65,
    onToggleTags = () => {},
    onToggleEditEntity = (_entity: string) => {},
    onEditThemeChange = (_theme: string) => {},
    onEditStrengthChange = (_strength: number) => {},
    onReconvert = () => {},
    onDownload = () => {},
    onClose,
  }: {
    visible: boolean;
    title: string;
    content: string;
    segments?: OutputSegment[];
    highlightTags?: boolean;
    kind?: "text" | "image" | "unsupported";
    canEdit?: boolean;
    editBusy?: boolean;
    editEntities?: string[];
    entityFilters?: EntityFilter[];
    supportsThemes?: boolean;
    themes?: string[];
    editTheme?: string;
    editStrength?: number;
    onToggleTags?: () => void;
    onToggleEditEntity?: (entity: string) => void;
    onEditThemeChange?: (theme: string) => void;
    onEditStrengthChange?: (strength: number) => void;
    onReconvert?: () => void;
    onDownload?: () => void;
    onClose: () => void;
  } = $props();

  const editEntitySet = $derived(new Set(editEntities));

</script>

{#if visible}
  <div class="backdrop" role="presentation" onclick={onClose}></div>
  <div class="modal" role="dialog" aria-modal="true" aria-label="File preview">
    <header>
      <div class="title-wrap">
        <strong class="title-text">{title}</strong>
      </div>
      <div class="actions">
        {#if kind === "text" && segments.length > 0}
          <Button variant="ghost" size="sm" onclick={onToggleTags} ariaLabel="Toggle attachment tags">
            {highlightTags ? "Hide Tags" : "Show Tags"}
          </Button>
        {/if}
        <Button variant="ghost" size="sm" onclick={onDownload} ariaLabel="Download file">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          Download
        </Button>
        <Button variant="icon" size="sm" onclick={onClose} ariaLabel="Close">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </Button>
      </div>
    </header>

    <div class="body" class:with-sidebar={canEdit}>
      <div class="content-area">
        {#if kind === "image"}
          <div class="image-wrap">
            <img src={content} alt={title} />
          </div>
        {:else if kind === "text" && highlightTags && segments.length > 0}
          <div class="preview">
            {#each segments as segment}
              <span class:hl={segment.replaced} class={highlightClassForEntity(segment.entity_type)}>
                {segment.text}
              </span>
            {/each}
          </div>
        {:else}
          <pre>{content}</pre>
        {/if}
      </div>

      {#if canEdit}
        <aside class="edit-sidebar" aria-label="Per-file edit sidebar">
          <TagThemeControls
            entityFilters={entityFilters}
            activeEntityFilters={editEntitySet}
            {supportsThemes}
            {themes}
            activeTheme={editTheme}
            strength={editStrength}
            disabled={editBusy}
            onToggleEntity={onToggleEditEntity}
            onSetTheme={onEditThemeChange}
            onSetStrength={onEditStrengthChange}
          />

          <div class="actions-row">
            <Button variant="primary" size="md" onclick={onReconvert} disabled={editBusy}>
              {#if editBusy}
                <svg class="spinner" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg>
                Reconverting...
              {:else}
                Reconvert This File
              {/if}
            </Button>
          </div>
        </aside>
      {/if}
    </div>
  </div>
{/if}

<style>
  .backdrop {
    position: fixed;
    inset: 0;
    background: var(--surface-overlay);
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    z-index: 120;
    animation: fadeIn var(--duration-fast) var(--ease-out);
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  .modal {
    position: fixed;
    inset: 6vh 8vw;
    z-index: 121;
    border-radius: var(--radius-xl);
    background: var(--surface-solid);
    border: 1px solid var(--border-soft);
    display: grid;
    grid-template-rows: auto 1fr;
    overflow: hidden;
    box-shadow: var(--shadow-modal);
    animation: slideUp var(--duration-normal) var(--ease-out);
  }

  @keyframes slideUp {
    from { opacity: 0; transform: translateY(12px) scale(0.98); }
    to { opacity: 1; transform: translateY(0) scale(1); }
  }

  header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--space-md) var(--space-lg);
    border-bottom: 1px solid var(--border-soft);
    background: var(--surface-muted);
  }

  .title-wrap {
    display: flex;
    align-items: center;
    gap: var(--space-sm);
    min-width: 0;
  }

  .title-text {
    font-size: 14px;
    color: var(--text-primary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

.actions {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .body {
    display: grid;
    grid-template-columns: 1fr;
    min-height: 0;
  }

  .body.with-sidebar {
    grid-template-columns: 1fr 320px;
  }

  .content-area {
    min-height: 0;
    overflow: auto;
  }

  pre {
    margin: 0;
    padding: var(--space-lg);
    white-space: pre-wrap;
    word-break: break-word;
    font-family: var(--font-sans);
    font-size: 13px;
    line-height: 1.6;
    color: var(--text-primary);
    background: var(--surface-solid);
  }

  .preview {
    margin: 0;
    padding: var(--space-lg);
    white-space: pre-wrap;
    word-break: break-word;
    font-family: var(--font-sans);
    font-size: 13px;
    line-height: 1.6;
    color: var(--text-primary);
    background: var(--surface-solid);
  }

  .hl {
    padding: 1px 4px;
    border-radius: 4px;
    font-weight: 500;
    cursor: pointer;
    transition: opacity var(--duration-fast) var(--ease-out);
  }

  .hl:hover {
    opacity: 0.8;
  }

  .hl-person {
    background: var(--entity-person-bg);
    color: var(--entity-person-text);
  }

  .hl-loc {
    background: var(--entity-loc-bg);
    color: var(--entity-loc-text);
  }

  .hl-email {
    background: var(--entity-email-bg);
    color: var(--entity-email-text);
  }

  .hl-phone {
    background: var(--entity-phone-bg);
    color: var(--entity-phone-text);
  }

  .hl-org {
    background: var(--entity-org-bg);
    color: var(--entity-org-text);
  }

  .hl-date {
    background: var(--entity-date-bg);
    color: var(--entity-date-text);
  }

  .hl-money {
    background: var(--entity-money-bg);
    color: var(--entity-money-text);
  }

  .hl-url {
    background: var(--entity-url-bg);
    color: var(--entity-url-text);
  }

  .hl-ip {
    background: var(--entity-ip-bg);
    color: var(--entity-ip-text);
  }

  .hl-cc {
    background: var(--entity-cc-bg);
    color: var(--entity-cc-text);
  }

  .image-wrap {
    padding: var(--space-lg);
    overflow: auto;
    display: flex;
    align-items: flex-start;
    justify-content: center;
    background: var(--surface-solid);
    min-height: 100%;
  }

  .image-wrap img {
    max-width: 100%;
    max-height: 100%;
    border-radius: var(--radius-sm);
    border: 1px solid var(--border-soft);
  }

  .edit-sidebar {
    border-left: 1px solid var(--border-soft);
    background: var(--surface-muted);
    overflow: auto;
    padding-top: var(--space-lg);
  }

  .actions-row {
    padding: 0 var(--space-lg) var(--space-lg);
  }

  .actions-row :global(.btn) {
    width: 100%;
  }

  .spinner {
    animation: spin 800ms linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  @media (max-width: 980px) {
    .modal {
      inset: 2vh 2vw;
    }

    .body.with-sidebar {
      grid-template-columns: 1fr;
      grid-template-rows: 1fr auto;
    }

    .edit-sidebar {
      border-left: none;
      border-top: 1px solid var(--border-soft);
      max-height: 280px;
    }
  }
</style>
