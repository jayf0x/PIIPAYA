<script lang="ts">
  import Button from "$lib/ui/shared/Button.svelte";

  let {
    title,
    instruction,
    response,
    busy,
    disabled = false,
    modelOptions,
    selectedModel,
    modelContextTokens,
    estimatedAskTokens,
    inputPlaceholder,
    onInstructionChange,
    onModelChange,
    onAsk,
    onApply,
    onClear,
  }: {
    title: string;
    instruction: string;
    response: string;
    busy: boolean;
    disabled?: boolean;
    modelOptions: string[];
    selectedModel: string;
    modelContextTokens: number | null;
    estimatedAskTokens: number;
    inputPlaceholder: string;
    onInstructionChange: (value: string) => void;
    onModelChange: (value: string) => void;
    onAsk: () => void;
    onApply: () => void;
    onClear: () => void;
  } = $props();

  let open = $state(false);

  function close() {
    open = false;
  }
</script>

<svelte:window
  onkeydown={(event) => {
    if (!open) return;
    if (event.key === "Escape") {
      event.preventDefault();
      close();
    }
  }}
/>

<div class="ai-wrap">
  <button class="magic-ai" title="Ask" onclick={() => (open = !open)} disabled={disabled || busy}>
    <span class="spark">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2L14.5 9.5L22 12L14.5 14.5L12 22L9.5 14.5L2 12L9.5 9.5L12 2Z"/></svg>
    </span>
    <span>Ask</span>
  </button>
  {#if open}
    <div class="ai-popover">
      <div class="popover-head">
        <strong>{title}</strong>
        <Button variant="icon" size="sm" onclick={close} ariaLabel="Close">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </Button>
      </div>
      <div class="ask-row">
        <input
          type="text"
          class="ask-input"
          value={instruction}
          placeholder={inputPlaceholder}
          oninput={(event) => onInstructionChange((event.currentTarget as HTMLInputElement).value)}
          disabled={disabled || busy}
        />
        <div class="ask-config">
          <label class="config-label">
            <span>Model</span>
            <select
              class="config-select"
              value={selectedModel}
              onchange={(event) => onModelChange((event.currentTarget as HTMLSelectElement).value)}
              disabled={disabled || busy}
            >
              {#each modelOptions as model}
                <option value={model}>{model}</option>
              {/each}
            </select>
          </label>
          <div class="usage">
            {#if modelContextTokens && modelContextTokens > 0}
              {@const pct = Math.max(0, Math.min(100, Math.round((estimatedAskTokens / modelContextTokens) * 100)))}
              <div class="usage-bar">
                <span class="usage-fill" style={`width: ${pct}%`}></span>
              </div>
              <small class="usage-text">{pct}% (~{estimatedAskTokens.toLocaleString()}/{modelContextTokens.toLocaleString()} tokens)</small>
            {:else}
              <small class="usage-text">Context unavailable</small>
            {/if}
          </div>
        </div>
        <div class="ask-actions">
          <Button variant="icon" size="sm" onclick={onClear} disabled={disabled || busy} ariaLabel="Clear">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </Button>
          <Button variant="secondary" size="sm" onclick={onAsk} disabled={disabled || busy}>
            {busy ? "Asking..." : "Ask"}
          </Button>
          <Button variant="primary" size="sm" onclick={onApply} disabled={disabled || busy || !response.trim()}>
            Apply
          </Button>
        </div>
      </div>
      {#if response}
        <pre class="ask-result">{response}</pre>
      {/if}
    </div>
  {/if}
</div>

<style>
  .ai-wrap {
    position: relative;
    display: flex;
    align-items: center;
  }

  .magic-ai {
    height: 36px;
    border-radius: var(--radius-full);
    border: 1px solid var(--border-accent);
    background: var(--surface-accent-soft);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    padding: 0 14px;
    font-size: 12px;
    font-weight: 700;
    color: var(--text-accent);
    box-shadow: var(--shadow-sm);
    transition:
      background var(--duration-fast) var(--ease-out),
      border-color var(--duration-fast) var(--ease-out),
      box-shadow var(--duration-fast) var(--ease-out),
      transform 100ms var(--ease-out);
    position: relative;
    overflow: hidden;
  }

  .magic-ai::before {
    content: "";
    position: absolute;
    inset: 0;
    border-radius: inherit;
    background: linear-gradient(
      120deg,
      transparent 0%,
      hsla(200, 100%, 65%, 0.08) 25%,
      hsla(260, 100%, 65%, 0.08) 50%,
      hsla(320, 100%, 65%, 0.08) 75%,
      transparent 100%
    );
    background-size: 300% 300%;
    opacity: 0;
    transition: opacity var(--duration-fast) var(--ease-out);
    animation: shimmer 4s infinite linear;
  }

  .magic-ai:hover:not(:disabled)::before {
    opacity: 1;
  }

  @keyframes shimmer {
    0% { background-position: 0% 50%; }
    100% { background-position: 200% 50%; }
  }

  .spark {
    display: flex;
    align-items: center;
    line-height: 1;
  }

  .magic-ai:hover:not(:disabled) {
    border-color: var(--action-primary);
    background: var(--action-primary-soft);
    box-shadow: var(--shadow-md);
  }

  .magic-ai:active:not(:disabled) {
    transform: scale(0.97);
  }

  .magic-ai:disabled {
    opacity: 0.5;
    cursor: default;
  }

  .ai-popover {
    position: absolute;
    left: 0;
    bottom: calc(100% + 10px);
    width: min(540px, calc(100vw - 72px));
    border-radius: var(--radius-lg);
    border: 1px solid var(--border-mid);
    background: var(--surface-popover);
    box-shadow: var(--shadow-popover);
    overflow: hidden;
    z-index: 10;
    animation: popoverIn var(--duration-fast) var(--ease-out);
  }

  @keyframes popoverIn {
    from { opacity: 0; transform: translateY(4px); }
    to { opacity: 1; transform: translateY(0); }
  }

  .popover-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: var(--space-sm) var(--space-md);
    border-bottom: 1px solid var(--border-soft);
    background: var(--surface-popover-head);
    font-size: 12px;
    font-weight: 600;
    color: var(--text-primary);
  }

  .ask-row {
    display: flex;
    flex-direction: column;
    gap: var(--space-sm);
    padding: var(--space-md);
  }

  .ask-input {
    width: 100%;
    padding: 9px 12px;
    border-radius: var(--radius-sm);
    border: 1px solid var(--border-input);
    background: var(--surface-input);
    font-size: 13px;
    color: var(--text-primary);
    transition:
      border-color var(--duration-fast) var(--ease-out),
      box-shadow var(--duration-fast) var(--ease-out);
  }

  .ask-input:focus {
    outline: none;
    border-color: var(--border-input-focus);
    box-shadow: var(--focus-ring);
  }

  .ask-input::placeholder {
    color: var(--text-muted);
  }

  .ask-input:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }

  .ask-config {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--space-sm);
    align-items: end;
  }

  .config-label {
    display: grid;
    gap: 4px;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-tertiary);
    font-weight: 600;
  }

  .config-select {
    width: 100%;
    padding: 8px 10px;
    border-radius: var(--radius-sm);
    border: 1px solid var(--border-input);
    font-size: 12px;
    color: var(--text-primary);
    background: var(--surface-input);
    box-sizing: border-box;
    appearance: none;
    -webkit-appearance: none;
    background-image:
      url("data:image/svg+xml,%3Csvg width='10' height='6' viewBox='0 0 10 6' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M1 1L5 5L9 1' stroke='%235b6e87' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
    background-position: right 10px center;
    background-repeat: no-repeat;
    padding-right: 28px;
    transition:
      border-color var(--duration-fast) var(--ease-out),
      box-shadow var(--duration-fast) var(--ease-out);
  }

  .config-select:focus {
    outline: none;
    border-color: var(--border-input-focus);
    box-shadow: var(--focus-ring);
  }

  .config-select:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }

  .usage {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 2px 0;
  }

  .usage-bar {
    height: 3px;
    border-radius: var(--radius-full);
    background: var(--progress-track);
    overflow: hidden;
  }

  .usage-fill {
    display: block;
    height: 100%;
    background: var(--action-primary);
    border-radius: var(--radius-full);
    transition: width var(--duration-normal) var(--ease-out);
  }

  .usage-text {
    font-size: 10px;
    color: var(--text-muted);
    font-weight: 500;
  }

  .ask-actions {
    display: flex;
    gap: 6px;
    justify-content: flex-end;
    align-items: center;
  }

  .ask-result {
    margin: 0;
    border-top: 1px solid var(--border-soft);
    padding: var(--space-md);
    font-size: 12px;
    max-height: 120px;
    overflow: auto;
    white-space: pre-wrap;
    background: var(--surface-ask-result);
    color: var(--text-primary);
    font-family: var(--font-mono);
    line-height: 1.6;
  }

  @media (max-width: 980px) {
    .ask-config {
      grid-template-columns: 1fr;
    }
  }
</style>
