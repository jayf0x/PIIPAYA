<script lang="ts">
  import { onMount } from "svelte";
  import {
    getTheme,
    toggleTheme,
    onThemeChange,
    type Theme,
  } from "$lib/stores/theme";

  let theme = $state<Theme>("light");

  onMount(() => {
    theme = getTheme();
    return onThemeChange((t) => (theme = t));
  });
</script>

<button
  class="theme-toggle"
  title={theme === "light" ? "Switch to dark mode" : "Switch to light mode"}
  aria-label={theme === "light" ? "Switch to dark mode" : "Switch to light mode"}
  onclick={() => {
    theme = toggleTheme();
  }}
>
  <span class="icon-wrapper" class:dark={theme === "dark"}>
    <!-- Sun -->
    <svg class="sun" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <circle cx="12" cy="12" r="5"/>
      <line x1="12" y1="1" x2="12" y2="3"/>
      <line x1="12" y1="21" x2="12" y2="23"/>
      <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
      <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
      <line x1="1" y1="12" x2="3" y2="12"/>
      <line x1="21" y1="12" x2="23" y2="12"/>
      <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
      <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
    </svg>
    <!-- Moon -->
    <svg class="moon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
    </svg>
  </span>
</button>

<style>
  .theme-toggle {
    width: 34px;
    height: 34px;
    border-radius: var(--radius-sm);
    border: 1px solid var(--border-soft);
    background: var(--surface-hover);
    color: var(--text-secondary);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition:
      background var(--duration-fast) var(--ease-out),
      color var(--duration-fast) var(--ease-out),
      border-color var(--duration-fast) var(--ease-out);
  }

  .theme-toggle:hover {
    background: var(--surface-hover-strong);
    color: var(--text-primary);
    border-color: var(--border-mid);
  }

  .theme-toggle:focus-visible {
    outline: none;
    box-shadow: var(--focus-ring);
  }

  .icon-wrapper {
    position: relative;
    width: 16px;
    height: 16px;
  }

  .sun,
  .moon {
    position: absolute;
    inset: 0;
    transition:
      opacity var(--duration-normal) var(--ease-out),
      transform var(--duration-normal) var(--ease-out);
  }

  .sun {
    opacity: 1;
    transform: rotate(0deg) scale(1);
  }

  .moon {
    opacity: 0;
    transform: rotate(90deg) scale(0.6);
  }

  .icon-wrapper.dark .sun {
    opacity: 0;
    transform: rotate(-90deg) scale(0.6);
  }

  .icon-wrapper.dark .moon {
    opacity: 1;
    transform: rotate(0deg) scale(1);
  }
</style>
