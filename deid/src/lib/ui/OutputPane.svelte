<script lang="ts">
  import type { OutputAttachment, OutputSegment } from "$lib/types/ui";
  import { highlightClassForEntity } from "$lib/domain/entities/catalog";
  import AttachmentPill from "$lib/ui/AttachmentPill.svelte";
  import AskPopover from "$lib/ui/components/AskPopover.svelte";
  import PreviewUnavailableOverlay from "$lib/ui/components/PreviewUnavailableOverlay.svelte";
  import Button from "$lib/ui/shared/Button.svelte";

  let {
    model,
    features,
    ask,
    actions,
  }: {
    model: {
      outputText: string;
      outputSegments: OutputSegment[];
      previewText: string;
      previewSupported: boolean;
      previewDirty: boolean;
      previewSaving: boolean;
      activePreviewIsMain: boolean;
      droppedFilePath: string | null;
      outputAttachments: OutputAttachment[];
      activeOutputAttachmentId: string | null;
      outputSaveFormat: "txt" | "md";
      canHistoryPrev: boolean;
      canHistoryNext: boolean;
    };
    features: {
      supportsReverseText: boolean;
      reversibleMappingEnabled: boolean;
      supportsOllamaAsk: boolean;
    };
    ask: {
      instruction: string;
      response: string;
      busy: boolean;
      modelOptions: string[];
      selectedModel: string;
      modelContextTokens: number | null;
      estimatedTokens: number;
    };
    actions: {
      copy: () => void;
      reverse: () => void;
      previewInput: (value: string) => void;
      savePreview: () => void;
      history: (direction: "prev" | "next") => void;
      download: () => void;
      selectOutputAttachment: (id: string) => void;
      downloadOutputAttachment: (id: string) => void;
      editOutputAttachment: (id: string) => void;
      exportZip: () => void;
      saveFormatChange: (format: "txt" | "md") => void;
      askInstructionChange: (value: string) => void;
      ollamaModelChange: (value: string) => void;
      ask: () => void;
      applyAsk: () => void;
      clearAsk: () => void;
    };
  } = $props();

  function outputChipLabel() {
    if (!model.droppedFilePath) return "anonymized-output.txt";
    const parts = model.droppedFilePath.split(/[\\/]/);
    return parts[parts.length - 1] || model.droppedFilePath;
  }

  let showTags = $state(true);
  let editMode = $state(false);
  const hasSegments = $derived(model.outputSegments.length > 0 && model.outputSegments.some((s) => s.replaced));
  const highlightMode = $derived(hasSegments && showTags && !editMode);

</script>

<section class="pane-shell">
  <header class="pane-header">
    <div class="left-actions">
      <button class="pane-action-btn" title="Copy to clipboard" onclick={actions.copy} disabled={!model.outputText.trim()}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
        Copy
      </button>
      {#if features.supportsReverseText}
        <button
          class="pane-action-btn"
          title={features.reversibleMappingEnabled ? "Reverse anonymization mapping" : "Enable Reversible Mapping in Advanced Settings → NLP to use this"}
          onclick={actions.reverse}
          disabled={!model.outputText.trim() || !features.reversibleMappingEnabled}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/></svg>
          Reverse
        </button>
      {/if}
    </div>

    <div class="right-actions">
      {#if hasSegments}
        <button
          class="pane-action-btn"
          title={showTags ? "Hide anonymization highlights" : "Show anonymization highlights"}
          onclick={() => { showTags = !showTags; editMode = false; }}
        >
          {#if showTags}
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
            Hide Tags
          {:else}
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
            Show Tags
          {/if}
        </button>
        <button
          class="pane-action-btn"
          class:active-edit={editMode}
          title={editMode ? "Exit edit mode" : "Edit output text"}
          onclick={() => (editMode = !editMode)}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"/></svg>
          Edit
        </button>
      {/if}
      <div class="history-nav">
        <button class="nav-arrow" onclick={() => actions.history("prev")} disabled={!model.canHistoryPrev} title="Previous">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M15 18l-6-6 6-6"/></svg>
        </button>
        <button class="nav-arrow" onclick={() => actions.history("next")} disabled={!model.canHistoryNext} title="Next">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M9 18l6-6-6-6"/></svg>
        </button>
      </div>
    </div>
  </header>

  <div class="preview-shell">
    {#if hasSegments && highlightMode}
      <div class="segment-preview">
        {#each model.outputSegments as segment}
          <span class:hl={segment.replaced} class={highlightClassForEntity(segment.entity_type)}>
            {segment.text}
          </span>
        {/each}
      </div>
    {:else if model.previewSupported}
      <textarea
        class="pane-textarea preview-editor"
        value={model.previewText}
        oninput={(event) =>
          actions.previewInput((event.currentTarget as HTMLTextAreaElement).value)}
      ></textarea>
    {:else}
      <div class="preview preview-empty"></div>
      <PreviewUnavailableOverlay />
    {/if}

    <button
      class="save-floating"
      onclick={actions.savePreview}
      disabled={!model.previewSupported || model.previewSaving || !model.previewDirty}
      aria-label="Save preview changes"
    >
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/></svg>
      {model.previewSaving ? "Saving..." : "Save"}
    </button>
  </div>

  <div class="pane-file-tray">
    {#if model.outputText.trim()}
      <AttachmentPill
        label={outputChipLabel()}
        icon="save"
        onOpen={() => actions.selectOutputAttachment("main")}
        onDownload={actions.download}
        active={model.activePreviewIsMain}
      />
    {/if}
    {#if model.outputAttachments.length > 0}
      {#each model.outputAttachments as file (file.id)}
        <AttachmentPill
          label={file.name}
          icon="file"
          onOpen={() => actions.selectOutputAttachment(file.id)}
          onDownload={() => actions.downloadOutputAttachment(file.id)}
          onEdit={() => actions.editOutputAttachment(file.id)}
          active={model.activeOutputAttachmentId === file.id}
        />
      {/each}
    {/if}
  </div>

  <footer class="pane-footer">
    {#if features.supportsOllamaAsk}
      <AskPopover
        title="Output Assist"
        instruction={ask.instruction}
        response={ask.response}
        busy={ask.busy}
        disabled={false}
        modelOptions={ask.modelOptions}
        selectedModel={ask.selectedModel}
        modelContextTokens={ask.modelContextTokens}
        estimatedAskTokens={ask.estimatedTokens}
        inputPlaceholder="Shorten this paragraph by 30%"
        onInstructionChange={actions.askInstructionChange}
        onModelChange={actions.ollamaModelChange}
        onAsk={actions.ask}
        onApply={actions.applyAsk}
        onClear={actions.clearAsk}
      />
    {/if}
    <div class="footer-right">
      <Button variant="ghost" size="sm" onclick={actions.exportZip} disabled={!model.outputText.trim()}>
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
        Export .zip
      </Button>
      <div class="save-combo">
        <button class="save-combo-btn" onclick={actions.download} disabled={!model.outputText.trim()}>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          Save As
        </button>
        <select
          class="save-combo-format"
          value={model.outputSaveFormat}
          onchange={(event) => actions.saveFormatChange((event.currentTarget as HTMLSelectElement).value as "txt" | "md")}
        >
          <option value="txt">.txt</option>
          <option value="md">.md</option>
        </select>
      </div>
    </div>
  </footer>
</section>

<style>
  @import "$lib/ui/shared/pane.css";

  .left-actions,
  .right-actions {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .pane-action-btn.active-edit {
    background: var(--surface-accent-soft);
    color: var(--text-accent);
    border-color: var(--border-accent);
  }

  .right-actions {
    gap: 12px;
  }

  .history-nav {
    display: flex;
    align-items: center;
    gap: 2px;
    background: var(--surface-hover);
    padding: 2px;
    border-radius: var(--radius-md);
  }

  .nav-arrow {
    width: 28px;
    height: 28px;
    border: none;
    background: transparent;
    border-radius: var(--radius-sm);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition:
      background var(--duration-fast) var(--ease-out),
      color var(--duration-fast) var(--ease-out),
      box-shadow var(--duration-fast) var(--ease-out);
    color: var(--text-secondary);
  }

  .nav-arrow:hover:not(:disabled) {
    background: var(--surface-solid);
    color: var(--action-primary);
    box-shadow: var(--shadow-sm);
  }

  .nav-arrow:disabled {
    opacity: 0.25;
    cursor: default;
  }

  .preview-shell {
    position: relative;
    min-height: 0;
    overflow: hidden;
    background: transparent;
  }

  .segment-preview {
    padding: var(--space-xl);
    min-height: 320px;
    font-family: var(--font-sans);
    font-size: 14px;
    line-height: 1.7;
    color: var(--text-primary);
    white-space: pre-wrap;
    word-break: break-word;
    overflow-y: auto;
  }

  .segment-preview :global(.hl) {
    padding: 1px 4px;
    border-radius: 4px;
    font-weight: 500;
  }

  .segment-preview :global(.hl-person)  { background: var(--entity-person-bg);  color: var(--entity-person-text);  }
  .segment-preview :global(.hl-loc)     { background: var(--entity-loc-bg);     color: var(--entity-loc-text);     }
  .segment-preview :global(.hl-email)   { background: var(--entity-email-bg);   color: var(--entity-email-text);   }
  .segment-preview :global(.hl-phone)   { background: var(--entity-phone-bg);   color: var(--entity-phone-text);   }
  .segment-preview :global(.hl-org)     { background: var(--entity-org-bg);     color: var(--entity-org-text);     }
  .segment-preview :global(.hl-date)    { background: var(--entity-date-bg);    color: var(--entity-date-text);    }
  .segment-preview :global(.hl-money)   { background: var(--entity-money-bg);   color: var(--entity-money-text);   }
  .segment-preview :global(.hl-url)     { background: var(--entity-url-bg);     color: var(--entity-url-text);     }
  .segment-preview :global(.hl-default) { background: var(--entity-default-bg); color: var(--entity-default-text); }

  .preview-editor {
    width: 100%;
    height: 100%;
    min-height: 320px;
    border: none;
    outline: none;
    resize: none;
    padding: var(--space-xl);
    background: transparent;
    font-size: 14px;
    line-height: 1.7;
    color: var(--text-primary);
    white-space: pre-wrap;
  }

  .preview-empty {
    min-height: 320px;
  }

  .save-floating {
    position: absolute;
    right: var(--space-lg);
    bottom: var(--space-lg);
    z-index: 3;
    border: none;
    border-radius: var(--radius-md);
    background: var(--action-primary);
    color: var(--text-on-primary);
    font-size: 12px;
    font-weight: 600;
    padding: 9px 16px;
    cursor: pointer;
    box-shadow: var(--shadow-float);
    display: flex;
    align-items: center;
    gap: 6px;
    transition:
      background var(--duration-fast) var(--ease-out),
      box-shadow var(--duration-fast) var(--ease-out),
      transform 100ms var(--ease-out);
  }

  .save-floating:hover:not(:disabled) {
    background: var(--action-primary-hover);
    transform: translateY(-1px);
    box-shadow: var(--shadow-md);
  }

  .save-floating:active:not(:disabled) {
    transform: scale(0.97);
  }

  .save-floating:disabled {
    opacity: 0;
    pointer-events: none;
    box-shadow: none;
  }

  .footer-right {
    display: flex;
    gap: var(--space-sm);
    align-items: center;
  }

  .save-combo {
    display: flex;
    background: var(--surface-solid);
    border-radius: var(--radius-sm);
    border: 1px solid var(--border-soft);
    overflow: hidden;
    transition: border-color var(--duration-fast) var(--ease-out);
  }

  .save-combo:hover {
    border-color: var(--border-mid);
  }

  .save-combo-btn {
    border: none;
    background: transparent;
    padding: 8px 12px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    color: var(--text-primary);
    display: flex;
    align-items: center;
    gap: 6px;
    transition: background var(--duration-fast) var(--ease-out);
  }

  .save-combo-btn:hover:not(:disabled) {
    background: var(--surface-hover);
  }

  .save-combo-btn:disabled {
    opacity: 0.5;
    cursor: default;
  }

  .save-combo-format {
    border: none;
    border-left: 1px solid var(--border-soft);
    background: var(--surface-solid);
    color: var(--text-secondary);
    font-size: 11px;
    padding: 0 24px 0 8px;
    cursor: pointer;
    appearance: none;
    -webkit-appearance: none;
    background-image:
      url("data:image/svg+xml,%3Csvg width='8' height='5' viewBox='0 0 8 5' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M1 1L4 4L7 1' stroke='%235f6368' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
    background-position: right 8px center;
    background-repeat: no-repeat;
    transition: background-color var(--duration-fast) var(--ease-out);
  }

  .save-combo-format:hover {
    background-color: var(--surface-hover);
  }

  @media (max-width: 980px) {
    .pane-footer {
      flex-direction: column;
      align-items: flex-start;
      gap: var(--space-sm);
    }
  }
</style>
