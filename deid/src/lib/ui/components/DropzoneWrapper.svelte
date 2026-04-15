<script lang="ts">
  import { getCurrentWebview } from "@tauri-apps/api/webview";
  import { onDestroy, onMount } from "svelte";

  export type DropzoneFile = {
    path?: string;
    file?: File;
  };

  let {
    tag = "section",
    className = "",
    ariaLabel = "",
    role = "region",
    disabled = false,
    onFiles = (_files: DropzoneFile[]) => {},
    children,
  } = $props<{
    tag?: string;
    className?: string;
    ariaLabel?: string;
    role?: string;
    disabled?: boolean;
    onFiles?: (files: DropzoneFile[]) => void;
    children?: import("svelte").Snippet;
  }>();

  let isVisible = $state(false);
  let dragDepth = $state(0);
  let unlisten: (() => void) | null = null;

  function hasTauriBridge() {
    return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
  }

  function setOverlayVisible(visible: boolean) {
    if (disabled) {
      isVisible = false;
      dragDepth = 0;
      return;
    }
    isVisible = visible;
  }

  function emitFiles(files: DropzoneFile[]) {
    if (disabled) return;
    const normalized = files.filter(
      (item) =>
        (typeof item.path === "string" && item.path.trim().length > 0) ||
        item.file instanceof File
    );
    if (normalized.length === 0) return;
    onFiles(normalized);
  }

  onMount(async () => {
    if (!hasTauriBridge()) return;
    const webview = getCurrentWebview();

    unlisten = await webview.onDragDropEvent((event) => {
      if (disabled) {
        isVisible = false;
        return;
      }

      const type = event.payload.type;
      if (type === "enter" || type === "over") {
        dragDepth = Math.max(1, dragDepth + 1);
        setOverlayVisible(true);
        return;
      }
      if (type === "drop") {
        dragDepth = 0;
        setOverlayVisible(false);
        const paths = Array.isArray(event.payload.paths)
          ? event.payload.paths.filter((row): row is string => typeof row === "string" && row.trim().length > 0)
          : [];
        emitFiles(paths.map((path) => ({ path })));
        return;
      }
      if (type === "leave" || type === "cancel") {
        dragDepth = 0;
        setOverlayVisible(false);
      }
    });
  });

  onDestroy(() => {
    unlisten?.();
  });

  function handleDragOver(event: DragEvent) {
    if (disabled) return;
    event.preventDefault();
    dragDepth += 1;
    setOverlayVisible(true);
  }

  function handleLeave(event: DragEvent) {
    if (disabled) return;
    event.preventDefault();
    dragDepth = Math.max(0, dragDepth - 1);
    if (dragDepth === 0) setOverlayVisible(false);
  }

  function handleDropDOM(event: DragEvent) {
    if (disabled) return;
    event.preventDefault();
    dragDepth = 0;
    setOverlayVisible(false);

    const files = Array.from(event.dataTransfer?.files ?? []);
    if (files.length === 0) return;
    const normalized = files.map((file) => {
      const maybePath = (file as File & { path?: string }).path;
      return typeof maybePath === "string" && maybePath.trim().length > 0
        ? { file, path: maybePath }
        : { file };
    });
    emitFiles(normalized);
  }

  $effect(() => {
    if (!disabled) return;
    dragDepth = 0;
    isVisible = false;
  });
</script>

<svelte:element
  this={tag}
  class={`dropzone-root ${className}`.trim()}
  {role}
  aria-label={ariaLabel}
  ondragover={handleDragOver}
  ondragleave={handleLeave}
  ondrop={handleDropDOM}
>
  {@render children?.()}

  {#if isVisible && !disabled}
    <div class="dropzone-overlay visible">
      <div class="dropzone-overlay-content">
        <div class="dz-icon">
          <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
        </div>
        <div class="dz-text">Drop files to attach</div>
      </div>
    </div>
  {/if}
</svelte:element>

<style>
  .dropzone-root {
    position: relative;
  }

  .dropzone-overlay {
    position: fixed;
    inset: 0;
    z-index: 9999;
    display: flex;
    align-items: center;
    justify-content: center;
    opacity: 1;
    pointer-events: none;
    backdrop-filter: blur(6px);
  }

  .dropzone-overlay-content {
    text-align: center;
    padding: 32px 40px;
    border-radius: var(--radius-xl);
    background: var(--surface-dropzone);
    border: 2px dashed rgba(255, 255, 255, 0.35);
    color: #fff;
    backdrop-filter: blur(4px);
    -webkit-backdrop-filter: blur(4px);
  }

  .dz-icon {
    display: flex;
    justify-content: center;
    margin-bottom: 12px;
    opacity: 0.9;
  }

  .dz-text {
    font-size: 15px;
    font-weight: 600;
    opacity: 0.9;
    letter-spacing: 0.01em;
  }
</style>
