<script lang="ts">
  import type { AttachedInputFile } from "$lib/types/ui";
  import type { FileQueueItem } from "$lib/types/ui";
  import AttachmentPill from "$lib/ui/AttachmentPill.svelte";
  import FileQueueList from "$lib/ui/components/FileQueueList.svelte";
  import AskPopover from "$lib/ui/components/AskPopover.svelte";
  import Button from "$lib/ui/shared/Button.svelte";

  let {
    ready,
    processing,
    model,
    ask,
    actions,
  }: {
    ready: boolean;
    processing: boolean;
    model: {
      inputText: string;
      attachedFiles: AttachedInputFile[];
      fileQueue: FileQueueItem[];
    };
    ask: {
      enabled: boolean;
      instruction: string;
      response: string;
      busy: boolean;
      modelOptions: string[];
      selectedModel: string;
      modelContextTokens: number | null;
      estimatedTokens: number;
    };
    actions: {
      paste: () => void;
      run: () => void;
      attachClick: () => void;
      clearAttached: (id: string) => void;
      openAttached: (id: string) => void;
      downloadAttached: (id: string) => void;
      inputChange: (value: string) => void;
      askInstructionChange: (value: string) => void;
      ollamaModelChange: (value: string) => void;
      ask: () => void;
      applyAsk: () => void;
      clearAsk: () => void;
    };
  } = $props();

</script>

<section class="pane-shell" aria-label="Input pane">
  <header class="pane-header">
    <button class="pane-action-btn" title="Paste from clipboard" onclick={actions.paste} disabled={!ready || processing}>
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/></svg>
      Paste
    </button>
  </header>

  <textarea
    class="pane-textarea"
    value={model.inputText}
    placeholder="Drop or paste sensitive records..."
    disabled={!ready || processing}
    oninput={(event) => actions.inputChange((event.currentTarget as HTMLTextAreaElement).value)}
  ></textarea>

  <div class="pane-file-tray">
    {#each model.attachedFiles as file (file.id)}
      <AttachmentPill
        label={file.name}
        title={file.path ?? file.name}
        icon="file"
        onOpen={() => actions.openAttached(file.id)}
        onDownload={() => actions.downloadAttached(file.id)}
        onRemove={() => actions.clearAttached(file.id)}
      />
    {/each}
    <button class="file-add" onclick={actions.attachClick} disabled={!ready || processing}>
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
      Add
    </button>
  </div>

  <FileQueueList items={model.fileQueue} />

  <footer class="pane-footer">
    {#if ask.enabled}
      <AskPopover
        title="Input Assist"
        instruction={ask.instruction}
        response={ask.response}
        busy={ask.busy}
        disabled={!ready}
        modelOptions={ask.modelOptions}
        selectedModel={ask.selectedModel}
        modelContextTokens={ask.modelContextTokens}
        estimatedAskTokens={ask.estimatedTokens}
        inputPlaceholder="Switch David with Bruce"
        onInstructionChange={actions.askInstructionChange}
        onModelChange={actions.ollamaModelChange}
        onAsk={actions.ask}
        onApply={actions.applyAsk}
        onClear={actions.clearAsk}
      />
    {/if}
    <Button variant="primary" size="lg" onclick={actions.run} disabled={!ready || processing}>
      {#if processing}
        <svg class="spinner" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg>
        Processing...
      {:else}
        Run
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>
      {/if}
    </Button>
  </footer>
</section>

<style>
  @import "$lib/ui/shared/pane.css";

  .file-add {
    border: none;
    background: none;
    font-size: 11px;
    color: var(--action-primary);
    font-weight: 600;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 4px 8px;
    border-radius: var(--radius-xs);
    transition:
      background var(--duration-fast) var(--ease-out),
      color var(--duration-fast) var(--ease-out);
  }

  .file-add:hover:not(:disabled) {
    color: var(--action-primary-hover);
    background: var(--action-primary-soft);
  }

  .file-add:disabled {
    opacity: 0.5;
    cursor: default;
  }

  .spinner {
    animation: spin 800ms linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }
</style>
