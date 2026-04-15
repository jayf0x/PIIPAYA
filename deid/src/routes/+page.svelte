<script lang="ts">
  import { onMount } from "svelte";
  import { invoke } from "@tauri-apps/api/core";
  import { listen } from "@tauri-apps/api/event";
  import DropzoneWrapper from "$lib/ui/components/DropzoneWrapper.svelte";
  import SidebarPanel from "$lib/ui/SidebarPanel.svelte";
  import InputPane from "$lib/ui/InputPane.svelte";
  import OutputPane from "$lib/ui/OutputPane.svelte";
  import AdvancedSettingsModal from "$lib/ui/AdvancedSettingsModal.svelte";
  import FilePreviewModal from "$lib/ui/FilePreviewModal.svelte";
  import {
    BACKEND_CAPABILITIES,
    BACKEND_COMMANDS,
    BACKEND_EVENT,
    asObjectArray,
    hasAllCapabilities,
    hasCapability,
    isRecord,
    parseJsonObject,
    parseRuntimeConfig,
    parseOutputSegments,
    type BackendEnvelope,
    type BackendPayload,
    type BackendMessage,
    type BackendStatus,
    type RuntimeConfig,
  } from "$lib/domain/backend/contract";
  import { createBackendRequestLifecycle } from "$lib/domain/backend/client";
  import { createBrowserMockAdapter } from "$lib/domain/backend/mockAdapter";
  import {
    entityFiltersCatalog,
    entityTypesCatalog,
  } from "$lib/domain/entities/catalog";
  import {
    availableOllamaModels as buildAvailableOllamaModels,
    type AskTarget,
  } from "$lib/domain/workbench/askAssist";
  import {
    initializeFileQueueRows,
    markPendingQueueRowsAsFailed as markPendingQueueRowsAsFailedRows,
    mergeAttachedFiles,
    patchQueueRowByIndex,
    splitAttachmentsByCapability,
    type FileAttachInput,
  } from "$lib/domain/workbench/files";
  import {
    SUPPORTED_PATH_EXTENSIONS,
    extensionFromName,
  } from "$lib/domain/policies/fileCapabilities";

  // Build accept string for the file picker — all supported extensions except ""
  // (extensionless files cannot be expressed via the accept attribute).
  const FILE_PICKER_ACCEPT = [...SUPPORTED_PATH_EXTENSIONS]
    .filter((ext) => ext !== "")
    .sort()
    .join(",");
  import {
    createOutputPreviewDiffController,
    inferPreviewKind,
    resolveActiveOutputPreviewTarget as resolveOutputPreviewTarget,
  } from "$lib/domain/workbench/preview";
  import {
    captureRunRevision,
    createUndoSnapshot,
    createWorkbenchState,
    ensureOutputPreviewSelection as resolvePreviewSelection,
    navigateRunHistory,
    outputDownloadName as buildOutputDownloadName,
    restoreUndoSnapshot as restoreFromUndoSnapshot,
  } from "$lib/domain/workbench/store";
  import {
    buildExportZipBlob,
    outputAttachmentDownloadName,
    saveBlobWithPicker as saveBlobWithPickerHelper,
  } from "$lib/domain/workbench/io";
  import {
    createSettingsState,
    configSnapshot as makeConfigSnapshot,
    createProfileSnapshot,
    loadProfilesFromStorage,
    parseStringList,
    persistProfilesToStorage,
    profileNames as listProfileNames,
    queueActiveDateFormatsUpdate as buildDateFormatsUpdate,
    sameConfigValue,
    type SettingsProfile,
  } from "$lib/domain/settings/store";
  import type { LogEntry, LogType, OllamaTurn, OutputAttachment, FileQueueItem, SpacyModelInfo } from "$lib/types/ui";

  import "$lib/styles/global.css";
  import { initTheme, getTheme, onThemeChange } from "$lib/stores/theme";

  import backgroundUrlLight from "$lib/assets/bg-light.png";
  import backgroundUrlDark from "$lib/assets/bg-dark.png";

  type ApplyProfileOptions = {
    syncBackend?: boolean;
    deferBackendSync?: boolean;
  };
  type RuntimeConfigKey = keyof RuntimeConfig;

  const PROFILE_STORAGE_KEY = "deid:settings-profiles:v1";
  const ACTIVE_PROFILE_STORAGE_KEY = "deid:active-profile:v1";

  const entityFilters = entityFiltersCatalog();

  const defaultInput = `Adam went to see Eve in London on March 1, 2026. Contact Adam via adam@example.com or +321 882 46 98. Hash two thousand euro's or 2000 or 2000$.`;

  let ready = $state(false);
  let startupError = $state<string | null>(null);
  let browserMockMode = $state(false);
  let featureMap = $state<string[]>([]);
  let processing = $state(false);

  let workbenchState = $state(
    createWorkbenchState({
      defaultInput,
      entityTypes: entityTypesCatalog(),
    }),
  );
  let inputFilePicker: HTMLInputElement | null = null;
  let configImportPicker: HTMLInputElement | null = null;

  let logs = $state<LogEntry[]>([]);
  let settingsState = $state(createSettingsState());

  let showAdvanced = $state(false);
  let sidebarCollapsed = $state(false);
  let modelInfoRequestId = $state<string | null>(null);
  let mainBackgroundUrl = $state<string>('');

  let activeRunTimer: ReturnType<typeof setTimeout> | null = null;
  const configDebounceTimers = new Map<string, ReturnType<typeof setTimeout>>();
  let loadConfigAndThemesTask: Promise<void> | null = null;
  const outputPreviewDiffController = createOutputPreviewDiffController();

  const supportsProcessText = $derived(
    hasCapability(featureMap, BACKEND_CAPABILITIES.processText),
  );
  const supportsProcessFile = $derived(
    hasCapability(featureMap, BACKEND_CAPABILITIES.processFile),
  );
  const supportsProcessFiles = $derived(
    hasCapability(featureMap, BACKEND_CAPABILITIES.processFiles),
  );
  const supportsPreviewFile = $derived(
    hasCapability(featureMap, BACKEND_CAPABILITIES.previewFile),
  );
  const supportsReverseText = $derived(
    hasCapability(featureMap, BACKEND_CAPABILITIES.reverseText),
  );
  const supportsConfig = $derived(
    hasAllCapabilities(featureMap, [
      BACKEND_CAPABILITIES.getConfig,
      BACKEND_CAPABILITIES.updateConfig,
    ]),
  );
  const supportsThemes = $derived(
    hasAllCapabilities(featureMap, [
      BACKEND_CAPABILITIES.listThemes,
      BACKEND_CAPABILITIES.setTheme,
    ]),
  );
  const supportsThemePackImport = $derived(
    hasCapability(featureMap, BACKEND_CAPABILITIES.importThemePack),
  );
  const supportsSpacyModels = $derived(
    hasCapability(featureMap, BACKEND_CAPABILITIES.listSpacyModels),
  );
  const supportsOllamaAsk = $derived(
    hasCapability(featureMap, BACKEND_CAPABILITIES.askOllama),
  );
  const supportsOllamaModelList = $derived(
    hasCapability(featureMap, BACKEND_CAPABILITIES.listOllamaModels),
  );
  const supportsOllamaModelInfo = $derived(
    hasCapability(featureMap, BACKEND_CAPABILITIES.getOllamaModelInfo),
  );
  const supportsCancelRequest = $derived(
    hasCapability(featureMap, BACKEND_CAPABILITIES.cancelRequest),
  );
  const supportsResetData = $derived(
    hasCapability(featureMap, BACKEND_CAPABILITIES.resetData),
  );
  const supportsPurgeData = $derived(
    hasCapability(featureMap, BACKEND_CAPABILITIES.purgeData),
  );
  const supportsStorageStats = $derived(
    hasCapability(featureMap, BACKEND_CAPABILITIES.getStorageStats),
  );
  const hasHistoryPrev = $derived(workbenchState.runHistory.length > 1 && workbenchState.historyIndex > 0);
  const hasHistoryNext = $derived(
    workbenchState.runHistory.length > 1 && workbenchState.historyIndex < workbenchState.runHistory.length - 1,
  );

  function fallbackSpacyModels(): SpacyModelInfo[] {
    return [
      { name: "en_core_web_sm", installed: false, active: false },
      { name: "en_core_web_md", installed: false, active: false },
      { name: "en_core_web_lg", installed: true, active: true },
    ];
  }

  function sidebarDisplayWidth() {
    return sidebarCollapsed ? 48 : 260;
  }

  function makeId() {
    return crypto.randomUUID();
  }

  function hasTauriBridge() {
    return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
  }

  function afterFirstPaint() {
    return new Promise<void>((resolve) => {
      if (typeof window === "undefined") {
        resolve();
        return;
      }
      requestAnimationFrame(() => {
        setTimeout(resolve, 0);
      });
    });
  }

  function scheduleWhenIdle(task: () => void) {
    if (
      typeof window !== "undefined" &&
      typeof window.requestIdleCallback === "function"
    ) {
      window.requestIdleCallback(() => task(), { timeout: 1200 });
      return;
    }
    setTimeout(task, 0);
  }

  function configSnapshot() {
    return makeConfigSnapshot(settingsState.config);
  }

  function profileNames() {
    return listProfileNames(settingsState.settingsProfiles);
  }

  function persistProfiles(next: SettingsProfile[]) {
    settingsState.settingsProfiles = next;
    persistProfilesToStorage({
      profileStorageKey: PROFILE_STORAGE_KEY,
      activeProfileStorageKey: ACTIVE_PROFILE_STORAGE_KEY,
      settingsProfiles: next,
      activeProfileName: settingsState.activeProfileName,
    });
  }

  function syncActiveProfileSnapshot() {
    const snapshot = createProfileSnapshot({
      activeProfileName: settingsState.activeProfileName,
      config: settingsState.config,
      activeEntityFilters: workbenchState.activeEntityFilters,
    });
    const profileName = snapshot.name;
    if (!profileName) return;
    const others = settingsState.settingsProfiles.filter((row) => row.name !== profileName);
    persistProfiles(
      [...others, snapshot].sort((a, b) => a.name.localeCompare(b.name)),
    );
  }

  function loadProfiles() {
    const loaded = loadProfilesFromStorage({
      profileStorageKey: PROFILE_STORAGE_KEY,
      activeProfileStorageKey: ACTIVE_PROFILE_STORAGE_KEY,
    });
    if (!loaded) return;
    settingsState.settingsProfiles = loaded.settingsProfiles;
    settingsState.activeProfileName = loaded.activeProfileName;
  }

  function saveActiveProfileAs(name: string) {
    const profileName = name.trim();
    if (!profileName) return;
    if (settingsState.settingsProfiles.some((row) => row.name === profileName)) {
      pushLog("system", `Profile already exists: ${profileName}`);
      return;
    }
    const snapshot = createProfileSnapshot({
      activeProfileName: profileName,
      config: settingsState.config,
      activeEntityFilters: workbenchState.activeEntityFilters,
    });
    persistProfiles(
      [...settingsState.settingsProfiles, snapshot].sort((a, b) =>
        a.name.localeCompare(b.name),
      ),
    );
    settingsState.activeProfileName = profileName;
    void loadStorageEstimate();
    pushLog("system", `New profile created: ${profileName}`);
  }

  async function applyProfile(
    name: string,
    options: ApplyProfileOptions = {},
  ) {
    const selected = settingsState.settingsProfiles.find((row) => row.name === name);
    if (!selected) return;
    const syncBackend = options.syncBackend ?? true;
    const deferBackendSync = options.deferBackendSync ?? false;
    const baselineConfig = { ...settingsState.committedConfig };
    settingsState.activeProfileName = name;
    if (typeof localStorage !== "undefined") {
      localStorage.setItem(ACTIVE_PROFILE_STORAGE_KEY, name);
    }
    settingsState.config = { ...selected.config };
    workbenchState.activeEntityFilters = new Set(selected.activeEntities);
    if (!syncBackend) {
      settingsState.committedConfig = { ...selected.config };
      syncActiveProfileSnapshot();
      pushLog("system", `Profile loaded: ${name}`);
      return;
    }

    const updates = (Object.entries(selected.config) as Array<
      [RuntimeConfigKey, RuntimeConfig[RuntimeConfigKey]]
    >).filter(([key, value]) => !sameConfigValue(baselineConfig[key], value));
    const syncProfileToBackend = async () => {
      for (const [key, value] of updates) {
        await flushConfigValue(key, value, false);
      }
      syncActiveProfileSnapshot();
    };
    if (updates.length === 0) {
      settingsState.committedConfig = { ...selected.config };
    } else if (deferBackendSync) {
      scheduleWhenIdle(() => {
        void syncProfileToBackend();
      });
    } else {
      await syncProfileToBackend();
    }
    pushLog("system", `Profile loaded: ${name}`);
  }

  function pushLog(type: LogType, message: string, pct = 0) {
    logs = [
      ...logs,
      {
        type,
        message,
        pct,
        timestamp: new Date().toLocaleTimeString(),
      },
    ];
  }

  function pushUndoSnapshot() {
    const snapshot = createUndoSnapshot({
      inputText: workbenchState.inputText,
      outputText: workbenchState.outputText,
      outputSegments: workbenchState.outputSegments,
      outputAttachments: workbenchState.outputAttachments,
      attachedFiles: workbenchState.attachedFiles,
      activeEntityFilters: workbenchState.activeEntityFilters,
      droppedFilePath: workbenchState.droppedFilePath,
      fileQueue: workbenchState.fileQueue,
      config: settingsState.config,
      activeProfileName: settingsState.activeProfileName,
    });
    workbenchState.undoStack = [...workbenchState.undoStack, snapshot].slice(-60);
  }

  function restoreUndoSnapshot() {
    if (workbenchState.undoStack.length === 0) return;
    const snapshot = restoreFromUndoSnapshot(workbenchState.undoStack[workbenchState.undoStack.length - 1]);
    workbenchState.undoStack = workbenchState.undoStack.slice(0, -1);
    workbenchState.inputText = snapshot.inputText;
    workbenchState.outputText = snapshot.outputText;
    workbenchState.outputSegments = snapshot.outputSegments;
    workbenchState.outputAttachments = snapshot.outputAttachments;
    workbenchState.attachedFiles = snapshot.attachedFiles;
    workbenchState.activeEntityFilters = snapshot.activeEntityFilters;
    workbenchState.droppedFilePath = snapshot.droppedFilePath;
    workbenchState.fileQueue = snapshot.fileQueue;
    if (snapshot.config) {
      settingsState.config = snapshot.config;
      void flushAllConfigValues(snapshot.config);
    }
    if (snapshot.activeProfileName) {
      settingsState.activeProfileName = snapshot.activeProfileName;
    }
    pushLog("system", "Restored previous state.");
  }

  function resetFileQueue() {
    workbenchState.fileQueue = [];
  }

  function initializeFileQueue(items: { id: string; name: string }[]) {
    workbenchState.fileQueue = initializeFileQueueRows(items);
  }

  function updateQueueRowByIndex(
    index1Based: number,
    patch: Partial<FileQueueItem>,
  ) {
    workbenchState.fileQueue = patchQueueRowByIndex(workbenchState.fileQueue, index1Based, patch);
  }

  function markPendingQueueRowsAsFailed(detail: string) {
    workbenchState.fileQueue = markPendingQueueRowsAsFailedRows(workbenchState.fileQueue, detail);
  }

  function toggleEntityFilter(entityType: string) {
    const next = new Set(workbenchState.activeEntityFilters);
    if (next.has(entityType)) {
      next.delete(entityType);
    } else {
      next.add(entityType);
    }
    workbenchState.activeEntityFilters = next;
    syncActiveProfileSnapshot();
  }

  function strengthFromConfig() {
    const threshold = Math.max(
      0,
      Math.min(1, Number(settingsState.config.score_threshold ?? 0.35)),
    );
    return 1 - threshold;
  }

  function clearRunWatchdog() {
    if (!activeRunTimer) return;
    clearTimeout(activeRunTimer);
    activeRunTimer = null;
  }

  function armRunWatchdog(requestId: string) {
    clearRunWatchdog();
    activeRunTimer = setTimeout(() => {
      if (workbenchState.activeRequestId !== requestId) return;
      requestLifecycle.deletePending(requestId);
      workbenchState.activeRequestId = null;
      processing = false;
      activeRunTimer = null;
      pushLog(
        "system",
        "Run timed out waiting for backend completion. UI was unblocked.",
      );
    }, 120000);
  }

  const mockAdapter = createBrowserMockAdapter({
    onMessage: handleBackendMessage,
  });

  const requestLifecycle = createBackendRequestLifecycle({
    sendEnvelope: async (envelope) => {
      if (browserMockMode) {
        await mockAdapter.sendEnvelope(envelope);
        return;
      }
      await invoke("send_backend_command", { envelope });
    },
    makeId,
  });

  function enableBrowserMockMode(reason: string) {
    if (!browserMockMode) {
      mockAdapter.loadConfig();
      browserMockMode = true;
      pushLog("system", `Running in browser mock mode (${reason}).`);
    }
    ready = true;
    startupError = null;
    featureMap = mockAdapter.featureMap();
  }

  function resolveActiveOutputPreviewTarget() {
    return resolveOutputPreviewTarget({
      activeOutputAttachmentId: workbenchState.activeOutputAttachmentId,
      outputAttachments: workbenchState.outputAttachments,
      outputText: workbenchState.outputText,
    });
  }

  function clearOutputPreviewDebounce() {
    outputPreviewDiffController.clear();
  }

  function setOutputPreviewBaseline(
    text: string,
    options: { supported?: boolean; dirty?: boolean } = {},
  ) {
    clearOutputPreviewDebounce();
    workbenchState.outputPreviewText = text;
    workbenchState.outputPreviewSavedText = text;
    workbenchState.outputPreviewDirty = options.dirty ?? false;
    workbenchState.outputPreviewSupported = options.supported ?? true;
  }

  function queueOutputPreviewDiffCheck(nextText: string) {
    outputPreviewDiffController.queue({
      nextText,
      setText: (value) => {
        workbenchState.outputPreviewText = value;
      },
      getText: () => workbenchState.outputPreviewText,
      getSavedText: () => workbenchState.outputPreviewSavedText,
      setDirty: (dirty) => {
        workbenchState.outputPreviewDirty = dirty;
      },
    });
  }

  function ensureOutputPreviewSelection() {
    const selection = resolvePreviewSelection({
      activeOutputAttachmentId: workbenchState.activeOutputAttachmentId,
      outputAttachments: workbenchState.outputAttachments,
      outputText: workbenchState.outputText,
    });
    workbenchState.activeOutputAttachmentId = selection.activeOutputAttachmentId;
    const target = selection.target;
    if (!target) {
      setOutputPreviewBaseline("", { supported: true });
      return;
    }
    setOutputPreviewBaseline(target.text, { supported: target.supported });
  }

  async function sendEnvelope(
    envelope: BackendEnvelope,
    commandName: string,
    id: string,
  ): Promise<BackendPayload> {
    return requestLifecycle.sendEnvelope(envelope, commandName, id);
  }

  async function requestDone(command: string, payload: BackendPayload) {
    return requestLifecycle.requestDone(command, payload);
  }

  async function cancelRequest(requestId: string) {
    return requestLifecycle.cancelRequest(requestId, {
      ready,
      supportsCancelRequest,
    });
  }

  function queueActiveDateFormatsUpdate(raw: string) {
    queueConfigValue("date_format_profiles", {
      ...buildDateFormatsUpdate({
        config: settingsState.config,
        raw,
      }),
    });
  }

  function clearConfigDebounceTimers() {
    for (const timerId of configDebounceTimers.values()) {
      clearTimeout(timerId);
    }
    configDebounceTimers.clear();
  }

  async function flushAllConfigValues(config: RuntimeConfig) {
    const entries = Object.entries(config) as Array<[RuntimeConfigKey, RuntimeConfig[RuntimeConfigKey]]>;
    for (const [key, value] of entries) {
      await flushConfigValue(key, value, false);
    }
    syncActiveProfileSnapshot();
  }

  async function flushConfigValue(
    key: RuntimeConfigKey,
    value: RuntimeConfig[RuntimeConfigKey],
    syncProfile = true,
  ) {
    if (!supportsConfig || !ready) return;
    try {
      const response = await requestDone(BACKEND_COMMANDS.updateConfig, {
        key,
        value,
      });
      const committedValue = response.value ?? value;
      settingsState.committedConfig = {
        ...settingsState.committedConfig,
        [key]: committedValue,
      };
      settingsState.config = {
        ...settingsState.config,
        [key]: committedValue,
      };
      if (syncProfile) {
        syncActiveProfileSnapshot();
      }
    } catch (error) {
      const previous = settingsState.committedConfig[key];
      settingsState.config = { ...settingsState.config, [key]: previous };
      pushLog("system", `Config update failed for ${key}: ${String(error)}`);
    }
  }

  function queueConfigValue(
    key: RuntimeConfigKey,
    value: RuntimeConfig[RuntimeConfigKey],
  ) {
    settingsState.config = { ...settingsState.config, [key]: value };
    syncActiveProfileSnapshot();
    const existing = configDebounceTimers.get(key);
    if (existing) clearTimeout(existing);
    const timer = setTimeout(() => {
      configDebounceTimers.delete(key);
      void flushConfigValue(key, value);
    }, 450);
    configDebounceTimers.set(key, timer);
  }

  async function loadSpacyModels() {
    if (!supportsSpacyModels || !ready) {
      settingsState.spacyModels = [];
      return;
    }
    const response = await requestDone(BACKEND_COMMANDS.listSpacyModels, {});
    const payloadModels = response.models;
    if (!Array.isArray(payloadModels)) {
      settingsState.spacyModels = [];
      return;
    }
    settingsState.spacyModels = asObjectArray(payloadModels)
      .map((row) => ({
        name: String(row.name ?? ""),
        installed: Boolean(row.installed),
        active: Boolean(row.active),
      }))
      .filter((row) => row.name.length > 0);
  }

  async function loadOllamaModels() {
    if (!supportsOllamaModelList || !ready) {
      settingsState.ollamaModels = [];
      return;
    }
    const response = await requestDone(BACKEND_COMMANDS.listOllamaModels, {});
    const payloadModels = response.models;
    if (!Array.isArray(payloadModels)) {
      settingsState.ollamaModels = [];
      return;
    }
    settingsState.ollamaModels = asObjectArray(payloadModels)
      .map((row) => ({
        name: String(row.name ?? ""),
        active: Boolean(row.active),
      }))
      .filter((row) => row.name.length > 0);
  }

  async function loadOllamaModelInfo(model: string) {
    if (!ready || !supportsOllamaModelInfo) {
      settingsState.askModelContextTokens = null;
      return;
    }
    if (modelInfoRequestId) {
      void cancelRequest(modelInfoRequestId);
      modelInfoRequestId = null;
    }
    const requestId = makeId();
    modelInfoRequestId = requestId;
    try {
      const response = await sendEnvelope(
        {
          id: requestId,
          command: BACKEND_COMMANDS.getOllamaModelInfo,
          payload: { model },
        },
        BACKEND_COMMANDS.getOllamaModelInfo,
        requestId,
      );
      if (modelInfoRequestId !== requestId) return;
      const context = Number(response.context_tokens ?? 0);
      settingsState.askModelContextTokens = context > 0 ? context : null;
    } catch {
      if (modelInfoRequestId !== requestId) return;
      settingsState.askModelContextTokens = null;
    } finally {
      if (modelInfoRequestId === requestId) {
        modelInfoRequestId = null;
      }
    }
  }

  async function loadStorageEstimate() {
    const profileBytes = new Blob([JSON.stringify(settingsState.settingsProfiles)]).size;
    if (!ready || !supportsStorageStats) {
      settingsState.storageEstimateLabel = `~${(profileBytes / 1024).toFixed(1)} KB (profiles/local only)`;
      return;
    }
    try {
      const response = await requestDone(BACKEND_COMMANDS.getStorageStats, {});
      const dbBytes = Number(response.db_bytes ?? 0);
      const total = Math.max(0, dbBytes) + profileBytes;
      settingsState.storageEstimateLabel = `~${(total / (1024 * 1024)).toFixed(2)} MB (DB + profiles)`;
    } catch {
      settingsState.storageEstimateLabel = `~${(profileBytes / 1024).toFixed(1)} KB (profiles/local only)`;
    }
  }

  async function loadConfigAndThemes() {
    if (!ready) return;
    if (loadConfigAndThemesTask) {
      await loadConfigAndThemesTask;
      return;
    }
    loadConfigAndThemesTask = (async () => {
      try {
        if (supportsConfig) {
          const configResponse = await requestDone(BACKEND_COMMANDS.getConfig, {});
          const configData = configResponse.config;
          if (isRecord(configData)) {
            settingsState.config = parseRuntimeConfig(configData);
            settingsState.committedConfig = { ...settingsState.config };
            const selectedModel = String(
              settingsState.config.ollama_model ?? "",
            ).trim();
            if (selectedModel) {
              settingsState.askModel = selectedModel;
            }
          }
        }
        if (supportsThemes) {
          const themesResponse = await requestDone(BACKEND_COMMANDS.listThemes, {});
          const payloadThemes = themesResponse.themes;
          if (Array.isArray(payloadThemes)) {
            settingsState.themes = payloadThemes.filter(
              (value): value is string => typeof value === "string",
            );
          }
        }
        if (supportsSpacyModels) await loadSpacyModels();
        if (supportsOllamaModelList) await loadOllamaModels();
        if (supportsOllamaModelInfo) await loadOllamaModelInfo(settingsState.askModel);
        await loadStorageEstimate();
      } catch (error) {
        pushLog(
          "system",
          `Failed to load startup settingsState.config data: ${String(error)}`,
        );
      }
    })();
    try {
      await loadConfigAndThemesTask;
    } finally {
      loadConfigAndThemesTask = null;
    }
  }

  async function refreshBackendStatus() {
    if (!hasTauriBridge()) {
      enableBrowserMockMode("Tauri bridge unavailable");
      await loadConfigAndThemes();
      return;
    }
    try {
      const status = await invoke<BackendStatus>("backend_status");
      ready = status.ready;
      featureMap = status.feature_map ?? [];
      startupError = status.startup_error;
      if (ready) await loadConfigAndThemes();
    } catch (error) {
      enableBrowserMockMode(`status check failed: ${String(error)}`);
      await loadConfigAndThemes();
    }
  }

  function handleBackendMessage(message: BackendMessage) {
    if (message.type === "READY") {
      ready = true;
      startupError = null;
      const available = message.payload.feature_map;
      if (Array.isArray(available)) {
        featureMap = available.filter(
          (value): value is string => typeof value === "string",
        );
      }
      void loadConfigAndThemes();
      return;
    }

    const messageId = message.id ?? "";

    if (message.type === "PROGRESS") {
      const logType =
        message.payload.log_type === "engine" ? "engine" : "system";
      const text = String(message.payload.message ?? "Progress");
      const pct = Number(message.payload.pct ?? 0);
      pushLog(logType, text, pct);
      return;
    }

    if (message.type === "CHUNK" && message.payload.stream === "ollama") {
      const target = String(message.payload.target ?? "");
      const token = String(message.payload.text ?? "");
      if (messageId === workbenchState.inputAskRequestId && target === "input")
        workbenchState.inputAskResponse += token;
      else if (messageId === workbenchState.outputAskRequestId && target === "output")
        workbenchState.outputAskResponse += token;
      return;
    }

    if (
      message.type === "CHUNK" &&
      messageId === workbenchState.activeRequestId &&
      message.payload.stream === "file_progress"
    ) {
      const phase = String(message.payload.phase ?? "");
      if (phase === "queue") {
        const files = message.payload.files;
        if (Array.isArray(files)) {
          const rows = asObjectArray(files).map((row, idx) => ({
              id: `queue-${idx + 1}-${String(row.name ?? "file")}`,
              name: String(row.name ?? `file-${idx + 1}`),
              status: "queued" as const,
              progressPct: Number(row.progress_pct ?? 0),
              detail: String(row.detail ?? "Queued"),
            }));
          if (rows.length > 0) {
            workbenchState.fileQueue = rows;
          }
        }
        return;
      }
      const fileIndex = Number(message.payload.file_index ?? 0);
      const status = String(message.payload.status ?? "");
      const detail = String(message.payload.detail ?? "");
      const progressPct = Number(message.payload.progress_pct ?? 0);
      if (fileIndex >= 1 && status) {
        if (
          status === "processing" ||
          status === "queued" ||
          status === "done" ||
          status === "failed"
        ) {
          updateQueueRowByIndex(fileIndex, {
            status,
            progressPct,
            detail: detail || status,
          });
        }
      }
      return;
    }

    if (message.type === "CHUNK" && messageId === workbenchState.activeRequestId) {
      const chunkText = String(message.payload.text ?? "");
      workbenchState.outputText += chunkText;
      const parsedSegments = parseOutputSegments(message.payload.segments);
      if (parsedSegments.length > 0) {
        workbenchState.outputSegments = [
          ...workbenchState.outputSegments,
          ...parsedSegments,
        ];
      } else {
        workbenchState.outputSegments = [
          ...workbenchState.outputSegments,
          { text: chunkText, entity_type: null, replaced: false },
        ];
      }
      return;
    }

    if (message.type === "ERROR") {
      const code = String(message.payload.code ?? "UNKNOWN");
      const errorMessage = String(
        message.payload.message ?? "Unknown backend error",
      );
      const isIntentionalCancellation =
        code === "REQUEST_CANCELLED" &&
        requestLifecycle.hasIntentionalCancellation(messageId);
      if (!isIntentionalCancellation) {
        pushLog("system", `[${code}] ${errorMessage}`);
      } else {
        requestLifecycle.clearIntentionalCancellation(messageId);
      }
      const pending = requestLifecycle.takePending(messageId);
      if (pending) {
        pending.reject(new Error(errorMessage));
      }
      if (messageId === workbenchState.activeRequestId) {
        markPendingQueueRowsAsFailed(errorMessage);
        clearRunWatchdog();
        workbenchState.activeRequestId = null;
        processing = false;
        if (workbenchState.outputText.trim()) {
          captureRevision();
        }
      }
      if (messageId === workbenchState.inputAskRequestId) {
        workbenchState.inputAskRequestId = null;
        workbenchState.inputAskBusy = false;
      }
      if (messageId === workbenchState.outputAskRequestId) {
        workbenchState.outputAskRequestId = null;
        workbenchState.outputAskBusy = false;
      }
      if (messageId === modelInfoRequestId) {
        modelInfoRequestId = null;
      }
      return;
    }

    if (message.type === "DONE") {
      const pending = requestLifecycle.takePending(messageId);
      const command = pending?.command ?? "";
      if (pending) {
        pending.resolve(message.payload);
      }
      if (messageId === workbenchState.activeRequestId) {
        const rawFiles = message.payload.files;
        const payloadOutputText = String(message.payload.output_text ?? "");
        if (Array.isArray(rawFiles)) {
          const rawFileObjects = asObjectArray(rawFiles);
          // Convert manual-input.txt → converted-input.txt so inline text gets its own file entry
          const parsed = rawFileObjects.map((row) => {
              const name = String(row.name ?? "output.txt");
              return {
                id: makeId(),
                name: name === "manual-input.txt" ? "converted-input.txt" : name,
                text: String(row.text ?? ""),
                segments: parseOutputSegments(row.segments),
                sourceText:
                  row.source_text == null ? null : String(row.source_text),
                enabledEntities: [...workbenchState.activeRunEntities],
                editTheme: String(settingsState.config.active_theme ?? "default"),
                editStrength: strengthFromConfig(),
              };
            })
            .filter((row) => row.text.trim().length > 0);
          if (parsed.length > 0) {
            workbenchState.outputAttachments = parsed;
            // Clear the concatenated chunk output — attachments are the source of truth
            workbenchState.outputText = "";
            workbenchState.outputSegments = [];
            // Auto-select first attachment so output pane shows content immediately
            workbenchState.activeOutputAttachmentId = parsed[0].id;
          } else {
            workbenchState.outputAttachments = [];
            workbenchState.activeOutputAttachmentId = null;
            if (payloadOutputText.trim()) {
              workbenchState.outputText = payloadOutputText;
              workbenchState.outputSegments = [
                { text: payloadOutputText, entity_type: null, replaced: false },
              ];
            }
          }
        } else if (
          command === BACKEND_COMMANDS.processFile &&
          workbenchState.attachedFiles.length > 0 &&
          workbenchState.outputText.trim()
        ) {
          const source = workbenchState.attachedFiles[0];
          const sourceText =
            message.payload.source_text == null
              ? null
              : String(message.payload.source_text);
          const sourceName = String(message.payload.source_name ?? source.name);
          workbenchState.outputAttachments = [
            {
              id: makeId(),
              name: sourceName,
              text: workbenchState.outputText,
              segments: workbenchState.outputSegments.map((segment) => ({ ...segment })),
              sourceText,
              enabledEntities: [...workbenchState.activeRunEntities],
              editTheme: String(settingsState.config.active_theme ?? "default"),
              editStrength: strengthFromConfig(),
            },
          ];
          workbenchState.activeOutputAttachmentId = null;
        } else if (command === BACKEND_COMMANDS.processText && workbenchState.outputText.trim()) {
          workbenchState.outputAttachments = [];
          workbenchState.activeOutputAttachmentId = null;
        }
        ensureOutputPreviewSelection();
        clearRunWatchdog();
        workbenchState.activeRequestId = null;
        processing = false;
        if (workbenchState.outputText.trim()) {
          captureRevision();
        }
      }
      if (messageId === workbenchState.inputAskRequestId) {
        workbenchState.inputAskRequestId = null;
        workbenchState.inputAskBusy = false;
        const finalResponse = String(
          message.payload.response ?? workbenchState.inputAskResponse,
        );
        if (finalResponse) workbenchState.inputAskResponse = finalResponse;
      }
      if (messageId === workbenchState.outputAskRequestId) {
        workbenchState.outputAskRequestId = null;
        workbenchState.outputAskBusy = false;
        const finalResponse = String(
          message.payload.response ?? workbenchState.outputAskResponse,
        );
        if (finalResponse) workbenchState.outputAskResponse = finalResponse;
      }
      if (messageId === modelInfoRequestId) {
        modelInfoRequestId = null;
      }
      requestLifecycle.clearIntentionalCancellation(messageId);
    }
  }

  async function processSubmission() {
    if (!ready || processing) return;
    if (!supportsProcessText && !supportsProcessFile && !supportsProcessFiles) {
      pushLog("system", "No processing command available in feature map.");
      return;
    }

    pushUndoSnapshot();
    logs = [];
    workbenchState.outputText = "";
    workbenchState.outputSegments = [];
    workbenchState.outputAttachments = [];
    resetFileQueue();
    workbenchState.activeOutputAttachmentId = null;
    setOutputPreviewBaseline("", { supported: true });
    processing = true;
    const id = makeId();
    workbenchState.activeRequestId = id;
    armRunWatchdog(id);
    const entities = Array.from(workbenchState.activeEntityFilters);
    workbenchState.activeRunEntities = [...entities];
    const {
      inlineAttachments,
      pathAttachments,
      queueItems,
      skippedUnsupported,
    } = splitAttachmentsByCapability(workbenchState.attachedFiles);
    const hasInlineInput = workbenchState.inputText.trim().length > 0;

    if (queueItems.length > 0) {
      initializeFileQueue(
        queueItems.map((row) => ({
          id: row.id,
          name: row.name,
        })),
      );
      for (const row of queueItems) {
        if (!row.status) continue;
        const idx = workbenchState.fileQueue.findIndex((item) => item.id === row.id);
        if (idx < 0) continue;
        updateQueueRowByIndex(idx + 1, {
          status: row.status,
          progressPct: row.status === "unsupported" ? 100 : 0,
          detail:
            row.detail ??
            (row.status === "unsupported" ? "Unsupported" : "Queued"),
        });
      }
    }

    let command: string = BACKEND_COMMANDS.processText;
    let payload: BackendPayload = { text: workbenchState.inputText, entities };

    if (
      pathAttachments.length === 1 &&
      inlineAttachments.length === 0 &&
      !hasInlineInput &&
      supportsProcessFile
    ) {
      command = BACKEND_COMMANDS.processFile;
      payload = { path: pathAttachments[0].path, entities };
      workbenchState.droppedFilePath = pathAttachments[0].path;
    } else if (
      (pathAttachments.length > 0 || inlineAttachments.length > 0) &&
      supportsProcessFiles
    ) {
      const inlineDocs: { name: string; text: string }[] = [];
      const queueItems: { id: string; name: string }[] = [];
      for (const file of pathAttachments) {
        queueItems.push({ id: file.id, name: file.name });
      }
      for (const file of inlineAttachments) {
        if (!file.file) continue;
        inlineDocs.push({ name: file.name, text: await file.file.text() });
        queueItems.push({ id: file.id, name: file.name });
      }
      if (hasInlineInput) {
        inlineDocs.push({ name: "manual-input.txt", text: workbenchState.inputText });
        queueItems.push({ id: "manual-input", name: "manual-input.txt" });
      }
      command = BACKEND_COMMANDS.processFiles;
      payload = {
        paths: pathAttachments
          .map((row) => row.path)
          .filter((row): row is string => Boolean(row)),
        inline_docs: inlineDocs,
        entities,
      };
      workbenchState.droppedFilePath =
        pathAttachments.length === 1 ? pathAttachments[0].path : null;
    } else if (pathAttachments.length > 0 && !supportsProcessFiles) {
      pushLog(
        "system",
        "Multiple file processing requires PROCESS_FILES backend support.",
      );
      processing = false;
      workbenchState.activeRequestId = null;
      clearRunWatchdog();
      return;
    } else {
      workbenchState.droppedFilePath = null;
    }

    if (skippedUnsupported > 0) {
      pushLog(
        "system",
        `Skipped ${skippedUnsupported} unsupported attachment${skippedUnsupported === 1 ? "" : "s"}.`,
      );
    }

    const hasProcessableAttachments =
      pathAttachments.length > 0 || inlineAttachments.length > 0;
    if (!hasProcessableAttachments && !hasInlineInput) {
      processing = false;
      workbenchState.activeRequestId = null;
      clearRunWatchdog();
      pushLog("system", "No supported input available for conversion.");
      return;
    }

    try {
      await sendEnvelope({ id, command, payload }, command, id);
    } catch (error) {
      clearRunWatchdog();
      pushLog("system", String(error));
      processing = false;
      workbenchState.activeRequestId = null;
    }
  }

  async function reverseOutputText() {
    if (!ready || processing || !supportsReverseText || !workbenchState.outputText.trim())
      return;
    if (!Boolean(settingsState.config.reversible_mapping_enabled ?? false)) {
      pushLog(
        "system",
        "Enable Reversible Mapping in Advanced Settings before reversing.",
      );
      return;
    }
    try {
      const response = await requestDone(BACKEND_COMMANDS.reverseText, {
        text: workbenchState.outputText,
        entities: Array.from(workbenchState.activeEntityFilters),
      });
      const reversed = String(response.output_text ?? "");
      if (!reversed) return;
      pushUndoSnapshot();
      workbenchState.outputText = reversed;
      workbenchState.outputSegments = [{ text: reversed, entity_type: null, replaced: false }];
      pushLog("system", "Reverse mapping applied to output.");
    } catch (error) {
      pushLog("system", `Reverse mapping failed: ${String(error)}`);
    }
  }

  async function pasteFromClipboard() {
    try {
      const text = hasTauriBridge()
        ? await invoke<string>("read_clipboard_text")
        : await navigator.clipboard.readText();
      if (text) {
        pushUndoSnapshot();
        workbenchState.inputText = text;
        workbenchState.droppedFilePath = null;
      }
    } catch (error) {
      pushLog("system", `Clipboard read failed: ${String(error)}`);
    }
  }

  function handleIncomingFiles(incoming: FileAttachInput[]) {
    const result = mergeAttachedFiles({
      current: workbenchState.attachedFiles,
      incoming,
      createId: makeId,
    });
    if (!result.shouldPushUndoSnapshot) {
      for (const message of result.logs) {
        pushLog("system", message);
      }
      return;
    }
    pushUndoSnapshot();
    workbenchState.attachedFiles = result.nextAttachedFiles;
    if (result.shouldResetQueue) resetFileQueue();
    for (const message of result.logs) {
      pushLog("system", message);
    }
  }

  function handleDropzoneFiles(files: FileAttachInput[]) {
    // Reject path-only drops (Tauri drag-drop) that have no recognised extension.
    // Extensionless paths are almost always directories; passing them to the
    // backend causes an unrecoverable error that makes the UI unresponsive.
    // Browser File objects from the file picker are allowed through as-is because
    // the <input accept=...> already constrains them and extensionless plain-text
    // files are legitimate inline attachments.
    const filtered = files.filter((item) => {
      if (item.file) return true;
      if (!item.path) return false;
      const ext = extensionFromName(item.path);
      return ext !== "" && SUPPORTED_PATH_EXTENSIONS.has(ext);
    });
    if (filtered.length < files.length) {
      const skipped = files.length - filtered.length;
      pushLog("system", skipped === 1
        ? "Skipped 1 unsupported or folder item."
        : `Skipped ${skipped} unsupported or folder items.`);
    }
    handleIncomingFiles(filtered);
  }

  async function handleFilePickerChange(event: Event) {
    const target = event.currentTarget as HTMLInputElement;
    const files = Array.from(target.files ?? []) as Array<
      File & { path?: string }
    >;
    const normalized: FileAttachInput[] = [];
    for (const file of files) {
      const path =
        typeof file.path === "string" && file.path.trim().length > 0
          ? file.path
          : undefined;
      const ext = extensionFromName(file.name);
      // PDF/DOCX require a native path; without one (browser File object) they can't be processed.
      if (!path && (ext === ".pdf" || ext === ".docx" || ext === ".pages")) {
        pushLog(
          "system",
          `"${file.name}" requires a native file path. Open the app as a desktop app (Tauri) to attach PDF/DOCX files.`,
        );
        continue;
      }
      normalized.push(path ? { file, path } : { file });
    }
    if (normalized.length > 0) handleIncomingFiles(normalized);
    target.value = "";
  }

  function clearAttachedFileById(id: string) {
    pushUndoSnapshot();
    workbenchState.attachedFiles = workbenchState.attachedFiles.filter((file) => file.id !== id);
    resetFileQueue();
    if (workbenchState.attachedFiles.length === 0) {
      workbenchState.droppedFilePath = null;
    }
  }

  function outputDownloadName(format: "txt" | "md") {
    return buildOutputDownloadName(workbenchState.droppedFilePath, format);
  }

  async function saveBlobWithPicker(blob: Blob, filename: string) {
    await saveBlobWithPickerHelper({
      blob,
      filename,
      hasTauriBridge,
      saveBinaryDialog: async (defaultName, bytes) => {
        await invoke("save_binary_dialog", { defaultName, bytes });
      },
    });
  }

  async function downloadOutput() {
    if (!workbenchState.outputText.trim()) return;
    const mime =
      workbenchState.outputSaveFormat === "md"
        ? "text/markdown;charset=utf-8"
        : "text/plain;charset=utf-8";
    const filename = outputDownloadName(workbenchState.outputSaveFormat);
    if (hasTauriBridge()) {
      try {
        await invoke("save_text_dialog", {
          defaultName: filename,
          content: workbenchState.outputText,
        });
        return;
      } catch (error) {
        if (String(error).includes("USER_CANCELLED")) return;
      }
    }
    const blob = new Blob([workbenchState.outputText], { type: mime });
    await saveBlobWithPicker(blob, filename);
  }

  function outputAttachmentById(id: string) {
    return workbenchState.outputAttachments.find((row) => row.id === id) ?? null;
  }

  function openOutputAttachmentPreview(id: string, editMode = false) {
    const attachment = outputAttachmentById(id);
    if (!attachment) return;
    workbenchState.activeOutputAttachmentId = id;
    workbenchState.filePreviewAttachmentId = attachment.id;
    workbenchState.filePreviewCanEdit = attachment.text.trim().length > 0;
    workbenchState.filePreviewEditEntities = attachment.enabledEntities?.length
      ? [...attachment.enabledEntities]
      : [...workbenchState.activeEntityFilters];
    workbenchState.filePreviewEditTheme = String(
      attachment.editTheme ?? settingsState.config.active_theme ?? "default",
    );




    workbenchState.filePreviewEditStrength = Math.max(
      0,
      Math.min(1, Number(attachment.editStrength ?? strengthFromConfig())),
    );
    workbenchState.filePreviewSegments = attachment.segments?.length
      ? attachment.segments.map((segment) => ({ ...segment }))
      : [{ text: attachment.text, entity_type: null, replaced: false }];
    workbenchState.filePreviewHighlightTags = true;
    workbenchState.filePreviewEditMode = editMode && workbenchState.filePreviewCanEdit;
    openFilePreview(attachment.name, attachment.text, "text", "text");
  }

  function selectOutputAttachment(id: string) {
    if (id === "main") {
      workbenchState.activeOutputAttachmentId = null;
    } else {
      const attachment = outputAttachmentById(id);
      if (!attachment) return;
      workbenchState.activeOutputAttachmentId = attachment.id;
    }
    const target = resolveActiveOutputPreviewTarget();
    if (!target) return;
    setOutputPreviewBaseline(target.text, { supported: target.supported });
  }

  function editOutputAttachment(id: string) {
    openOutputAttachmentPreview(id, true);
  }

  async function reconvertTextContent(params: {
    text: string;
    entities: string[];
    theme: string;
    scoreThreshold: number;
  }) {
    const response = await requestDone(BACKEND_COMMANDS.processText, {
      text: params.text,
      entities: params.entities,
      theme: params.theme,
      score_threshold: params.scoreThreshold,
    });
    const mapped = String(response.output_text ?? "");
    const mappedSegments = parseOutputSegments(response.segments);
    return {
      mapped,
      segments:
        mappedSegments.length > 0
          ? mappedSegments
          : [{ text: mapped, entity_type: null, replaced: false }],
    };
  }

  async function saveOutputPreviewChanges() {
    if (workbenchState.outputPreviewSaving || !workbenchState.outputPreviewSupported || !workbenchState.outputPreviewDirty)
      return;
    workbenchState.outputPreviewSaving = true;
    clearOutputPreviewDebounce();
    try {
      if (!workbenchState.activeOutputAttachmentId) {
        const result = await reconvertTextContent({
          text: workbenchState.outputPreviewText,
          entities: Array.from(workbenchState.activeEntityFilters),
          theme: String(settingsState.config.active_theme ?? "default"),
          scoreThreshold: Math.max(0, Math.min(1, Number(settingsState.config.score_threshold ?? 0.35))),
        });
        workbenchState.outputText = result.mapped;
        workbenchState.outputSegments = result.segments;
        setOutputPreviewBaseline(result.mapped, { supported: true });
      } else {
        const attachment = outputAttachmentById(workbenchState.activeOutputAttachmentId);
        if (!attachment) return;
        const entities = attachment.enabledEntities?.length
          ? attachment.enabledEntities
          : [...workbenchState.activeEntityFilters];
        const theme = String(attachment.editTheme ?? settingsState.config.active_theme ?? "default");
        const scoreThreshold = Math.max(
          0,
          Math.min(1, 1 - Number(attachment.editStrength ?? strengthFromConfig())),
        );
        const result = await reconvertTextContent({
          text: workbenchState.outputPreviewText,
          entities,
          theme,
          scoreThreshold,
        });
        workbenchState.outputAttachments = workbenchState.outputAttachments.map((row) =>
          row.id === attachment.id
            ? {
                ...row,
                text: result.mapped,
                segments: result.segments,
                sourceText: workbenchState.outputPreviewText,
              }
            : row,
        );
        setOutputPreviewBaseline(result.mapped, { supported: true });
      }
      pushLog("system", "Preview changes saved.");
    } catch (error) {
      pushLog("system", `Preview save failed: ${String(error)}`);
    } finally {
      workbenchState.outputPreviewSaving = false;
    }
  }

  function resetFilePreviewObjectUrl() {
    if (!workbenchState.filePreviewObjectUrl) return;
    URL.revokeObjectURL(workbenchState.filePreviewObjectUrl);
    workbenchState.filePreviewObjectUrl = null;
  }

  function openFilePreview(
    title: string,
    content: string,
    kind: "text" | "image" | "unsupported" = "text",
    badge = "",
    options: { resetObjectUrl?: boolean } = {},
  ) {
    if (options.resetObjectUrl ?? true) resetFilePreviewObjectUrl();
    if (!workbenchState.filePreviewAttachmentId) {
      workbenchState.filePreviewCanEdit = false;
      workbenchState.filePreviewSegments = [];
      workbenchState.filePreviewHighlightTags = true;
      workbenchState.filePreviewEditMode = false;
      workbenchState.filePreviewEditEntities = [];
      workbenchState.filePreviewEditTheme = String(settingsState.config.active_theme ?? "default");
      workbenchState.filePreviewEditStrength = strengthFromConfig();
    }
    workbenchState.filePreviewTitle = title;
    workbenchState.filePreviewContent = content;
    workbenchState.filePreviewKind = kind;
    workbenchState.filePreviewBadge = badge;
    workbenchState.filePreviewVisible = true;
  }

  function toggleFilePreviewEditMode() {
    if (!workbenchState.filePreviewCanEdit) return;
    workbenchState.filePreviewEditMode = !workbenchState.filePreviewEditMode;
  }

  function toggleFilePreviewEntity(entity: string) {
    if (!workbenchState.filePreviewCanEdit || workbenchState.filePreviewEditBusy)
      return;
    const next = new Set(workbenchState.filePreviewEditEntities);
    if (next.has(entity)) next.delete(entity);
    else next.add(entity);
    workbenchState.filePreviewEditEntities = [...next];
  }

  function onFilePreviewThemeChange(theme: string) {
    workbenchState.filePreviewEditTheme = theme;
  }

  function onFilePreviewStrengthChange(strength: number) {
    workbenchState.filePreviewEditStrength = Math.max(0, Math.min(1, strength));
  }

  function toggleFilePreviewTags() {
    workbenchState.filePreviewHighlightTags = !workbenchState.filePreviewHighlightTags;
  }

  async function reconvertPreviewAttachment() {
    if (!workbenchState.filePreviewCanEdit || workbenchState.filePreviewEditBusy || !workbenchState.filePreviewAttachmentId)
      return;
    const attachment = outputAttachmentById(workbenchState.filePreviewAttachmentId);
    if (!attachment) return;
    const sourceText =
      typeof attachment.sourceText === "string" &&
      attachment.sourceText.trim().length > 0
        ? attachment.sourceText
        : attachment.text;
    if (!sourceText.trim()) return;
    workbenchState.filePreviewEditBusy = true;
    try {
      const result = await reconvertTextContent({
        text: sourceText,
        entities: workbenchState.filePreviewEditEntities,
        theme: workbenchState.filePreviewEditTheme,
        scoreThreshold: Math.max(0, Math.min(1, 1 - workbenchState.filePreviewEditStrength)),
      });
      const mapped = result.mapped;
      const mappedSegments = result.segments;
      workbenchState.outputAttachments = workbenchState.outputAttachments.map((row) =>
        row.id === attachment.id
          ? {
              ...row,
              text: mapped,
              segments:
                mappedSegments.length > 0
                  ? mappedSegments
                  : [{ text: mapped, entity_type: null, replaced: false }],
              enabledEntities: [...workbenchState.filePreviewEditEntities],
              editTheme: workbenchState.filePreviewEditTheme,
              editStrength: workbenchState.filePreviewEditStrength,
            }
          : row,
      );
      workbenchState.filePreviewContent = mapped;
      workbenchState.filePreviewSegments =
        mappedSegments.length > 0
          ? mappedSegments
          : [{ text: mapped, entity_type: null, replaced: false }];
      workbenchState.filePreviewHighlightTags = true;
      pushLog(
        "system",
        `Reconverted file with ${workbenchState.filePreviewEditEntities.length} enabled PII tag(s).`,
      );
    } catch (error) {
      pushLog("system", `Attachment reconvert failed: ${String(error)}`);
    } finally {
      workbenchState.filePreviewEditBusy = false;
    }
  }

  async function previewInputAttachment(id: string) {
    const file = workbenchState.attachedFiles.find((row) => row.id === id);
    if (!file) return;
    workbenchState.filePreviewAttachmentId = null;
    const fallbackKind = inferPreviewKind(file.name);
    if (file.file) {
      if (fallbackKind === "image") {
        const objectUrl = URL.createObjectURL(file.file);
        resetFilePreviewObjectUrl();
        workbenchState.filePreviewObjectUrl = objectUrl;
        openFilePreview(file.name, objectUrl, "image", "image", {
          resetObjectUrl: false,
        });
        return;
      }
      if (fallbackKind === "text") {
        const text = await file.file.text();
        openFilePreview(file.name, text, "text", "text");
        return;
      }
      openFilePreview(
        file.name,
        "Preview not supported for this file type.",
        "unsupported",
        "preview not supported",
      );
      return;
    }
    if (file.path && supportsPreviewFile) {
      try {
        const response = await requestDone(BACKEND_COMMANDS.previewFile, {
          path: file.path,
        });
        const supported = Boolean(response.preview_supported);
        const fileType = String(response.file_type ?? "unknown");
        const text = String(response.preview_text ?? "");
        if (supported) {
          openFilePreview(file.name, text, "text", fileType);
        } else {
          const message = String(
            response.message ?? "Preview not supported for this file type.",
          );
          openFilePreview(
            file.name,
            message,
            "unsupported",
            "preview not supported",
          );
        }
        return;
      } catch (error) {
        openFilePreview(
          file.name,
          `Preview failed: ${String(error)}`,
          "unsupported",
          "preview not supported",
        );
        return;
      }
    }
    openFilePreview(
      file.name,
      "Preview not supported for this file type.",
      "unsupported",
      "preview not supported",
    );
  }

  async function downloadOutputAttachment(id: string) {
    const attachment = outputAttachmentById(id);
    if (!attachment) return;
    const filename = outputAttachmentDownloadName(
      attachment.name,
      workbenchState.outputSaveFormat,
    );
    if (hasTauriBridge()) {
      try {
        await invoke("save_text_dialog", {
          defaultName: filename,
          content: attachment.text,
        });
        return;
      } catch (error) {
        if (String(error).includes("USER_CANCELLED")) return;
      }
    }
    const blob = new Blob([attachment.text], {
      type: "text/plain;charset=utf-8",
    });
    await saveBlobWithPicker(blob, filename);
  }

  async function copyOutput() {
    if (!workbenchState.outputText.trim()) return;
    try {
      if (hasTauriBridge()) {
        await invoke("write_clipboard_text", { text: workbenchState.outputText });
      } else {
        await navigator.clipboard.writeText(workbenchState.outputText);
      }
      pushLog("system", "Output copied to clipboard.");
    } catch (error) {
      pushLog("system", `Clipboard write failed: ${String(error)}`);
    }
  }

  async function exportZipPlaceholder() {
    if (!workbenchState.outputText.trim()) return;
    try {
      const mainName = outputDownloadName(workbenchState.outputSaveFormat);
      const blob = await buildExportZipBlob({
        mainName,
        outputText: workbenchState.outputText,
        attachments: workbenchState.outputAttachments,
      });
      await saveBlobWithPicker(blob, "deid-export.zip");
      pushLog("system", "ZIP export generated.");
    } catch (error) {
      pushLog("system", `ZIP export failed: ${String(error)}`);
    }
  }

  async function exportCurrentConfig() {
    try {
      const payload = {
        exported_at: new Date().toISOString(),
        config: configSnapshot(),
        active_entities: [...workbenchState.activeEntityFilters],
        profile: settingsState.activeProfileName,
      };
      const blob = new Blob([JSON.stringify(payload, null, 2)], {
        type: "application/json;charset=utf-8",
      });
      await saveBlobWithPicker(blob, "deid-config.json");
      pushLog("system", "Config exported.");
    } catch (error) {
      pushLog("system", `Config export failed: ${String(error)}`);
    }
  }

  async function importConfigFileChange(event: Event) {
    const target = event.currentTarget as HTMLInputElement;
    const file = target.files?.[0];
    target.value = "";
    if (!file) return;
    try {
      const text = await file.text();
      const parsed = parseJsonObject(text);
      const importedConfig =
        parsed.config && isRecord(parsed.config)
          ? parseRuntimeConfig(parsed.config)
          : parseRuntimeConfig(parsed);
      const importedEntities = Array.isArray(parsed.active_entities)
        ? parsed.active_entities.filter(
            (row): row is string => typeof row === "string",
          )
        : null;
      settingsState.config = { ...settingsState.config, ...importedConfig };
      for (const [key, value] of Object.entries(importedConfig) as Array<
        [RuntimeConfigKey, RuntimeConfig[RuntimeConfigKey]]
      >) {
        await flushConfigValue(key, value, false);
      }
      if (importedEntities && importedEntities.length > 0) {
        workbenchState.activeEntityFilters = new Set(importedEntities);
      }
      syncActiveProfileSnapshot();
      pushLog("system", `Config imported from ${file.name}.`);
    } catch (error) {
      pushLog("system", `Config import failed: ${String(error)}`);
    }
  }

  async function resetData() {
    const proceed = window.confirm(
      "Reset app data and runtime settingsState.config to defaults?",
    );
    if (!proceed) return;
    if (supportsResetData) {
      try {
        await requestDone(BACKEND_COMMANDS.resetData, {});
      } catch (error) {
        pushLog("system", `Backend reset failed: ${String(error)}`);
      }
    }
    pushUndoSnapshot();
    workbenchState.attachedFiles = [];
    workbenchState.outputAttachments = [];
    resetFileQueue();
    workbenchState.outputText = "";
    workbenchState.outputSegments = [];
    workbenchState.runHistory = [];
    workbenchState.historyIndex = -1;
    logs = [];
    await loadConfigAndThemes();
    await loadStorageEstimate();
    pushLog("system", "Data reset complete.");
  }

  async function purgeOldData() {
    const days = Math.max(1, Math.min(3650, Math.round(settingsState.purgeDays)));
    if (supportsPurgeData) {
      try {
        await requestDone(BACKEND_COMMANDS.purgeData, { days });
      } catch (error) {
        pushLog("system", `Purge failed: ${String(error)}`);
        return;
      }
    }
    pushLog("system", `Purge completed for data older than ${days} days.`);
  }

  function captureRevision() {
    const revision = captureRunRevision({
      inputText: workbenchState.inputText,
      outputText: workbenchState.outputText,
      outputSegments: workbenchState.outputSegments,
      droppedFilePath: workbenchState.droppedFilePath,
    });
    workbenchState.runHistory = [...workbenchState.runHistory, revision].slice(-30);
    workbenchState.historyIndex = workbenchState.runHistory.length - 1;
  }

  function historyPlaceholder(direction: "prev" | "next") {
    const nav = navigateRunHistory({
      runHistory: workbenchState.runHistory,
      historyIndex: workbenchState.historyIndex,
      direction,
    });
    if (!nav) return;
    workbenchState.historyIndex = nav.historyIndex;
    const snapshot = nav.snapshot;
    workbenchState.inputText = snapshot.inputText;
    workbenchState.outputText = snapshot.outputText;
    workbenchState.outputSegments = snapshot.outputSegments.map((segment) => ({ ...segment }));
    workbenchState.droppedFilePath = snapshot.droppedFilePath;
  }

  async function setTheme(theme: string) {
    if (!supportsThemes || !ready) return;
    const previous = settingsState.config.active_theme;
    settingsState.config = { ...settingsState.config, active_theme: theme };
    try {
      await requestDone(BACKEND_COMMANDS.setTheme, { theme });
      settingsState.committedConfig = {
        ...settingsState.committedConfig,
        active_theme: theme,
      };
      syncActiveProfileSnapshot();
    } catch (error) {
      settingsState.config = { ...settingsState.config, active_theme: previous };
      pushLog("system", `Theme update failed: ${String(error)}`);
    }
  }

  async function importThemePack() {
    if (!supportsThemePackImport || !ready || !settingsState.themePackPath.trim()) return;
    try {
      await requestDone(BACKEND_COMMANDS.importThemePack, {
        path: settingsState.themePackPath.trim(),
      });
      await loadConfigAndThemes();
      pushLog("system", `Imported theme pack from ${settingsState.themePackPath.trim()}.`);
    } catch (error) {
      pushLog("system", `Theme pack import failed: ${String(error)}`);
    }
  }

  async function installSpacyModel(model: string) {
    if (!supportsSpacyModels || !ready || processing) return;
    try {
      processing = true;
      await requestDone(BACKEND_COMMANDS.installSpacyModel, { model });
      await loadSpacyModels();
      pushLog("system", `spaCy model installed: ${model}`);
    } catch (error) {
      pushLog("system", `spaCy install failed for ${model}: ${String(error)}`);
    } finally {
      processing = false;
    }
  }

  async function askOllama(target: AskTarget) {
    if (!supportsOllamaAsk || !ready) return;
    const instruction = (
      target === "input" ? workbenchState.inputAskInstruction : workbenchState.outputAskInstruction
    ).trim();
    if (!instruction) {
      pushLog("system", `Ask ${target}: instruction is required.`);
      return;
    }
    const id = makeId();
    const history = target === "input" ? workbenchState.inputAskHistory : workbenchState.outputAskHistory;
    const currentText = target === "input" ? workbenchState.inputText : workbenchState.outputText;
    const otherText = target === "input" ? workbenchState.outputText : workbenchState.inputText;
    const previousRequestId =
      target === "input" ? workbenchState.inputAskRequestId : workbenchState.outputAskRequestId;
    if (previousRequestId) {
      void cancelRequest(previousRequestId);
    }

    if (target === "input") {
      workbenchState.inputAskBusy = true;
      workbenchState.inputAskRequestId = id;
      workbenchState.inputAskResponse = "";
    } else {
      workbenchState.outputAskBusy = true;
      workbenchState.outputAskRequestId = id;
      workbenchState.outputAskResponse = "";
    }

    try {
      const payload = {
        target,
        instruction,
        current_text: currentText,
        other_text: otherText,
        history,
        model: settingsState.askModel,
      };
      const donePayload = await sendEnvelope(
        { id, command: BACKEND_COMMANDS.askOllama, payload },
        BACKEND_COMMANDS.askOllama,
        id,
      );
      const finalResponse = String(donePayload.response ?? "");
      if (target === "input") {
        if (finalResponse) workbenchState.inputAskResponse = finalResponse;
        workbenchState.inputAskHistory = [
          ...workbenchState.inputAskHistory,
          { role: "user", content: instruction },
          { role: "assistant", content: finalResponse || workbenchState.inputAskResponse },
        ];
      } else {
        if (finalResponse) workbenchState.outputAskResponse = finalResponse;
        workbenchState.outputAskHistory = [
          ...workbenchState.outputAskHistory,
          { role: "user", content: instruction },
          { role: "assistant", content: finalResponse || workbenchState.outputAskResponse },
        ];
      }
    } catch (error) {
      if (!requestLifecycle.hasIntentionalCancellation(id)) {
        pushLog("system", `Ask ${target} failed: ${String(error)}`);
      } else {
        requestLifecycle.clearIntentionalCancellation(id);
      }
      if (target === "input") {
        workbenchState.inputAskBusy = false;
        workbenchState.inputAskRequestId = null;
      } else {
        workbenchState.outputAskBusy = false;
        workbenchState.outputAskRequestId = null;
      }
    }
  }

  function applyAskResponse(target: AskTarget) {
    if (target === "input") {
      if (workbenchState.inputAskResponse.trim()) {
        pushUndoSnapshot();
        workbenchState.inputText = workbenchState.inputAskResponse;
        workbenchState.droppedFilePath = null;
      }
      return;
    }
    if (workbenchState.outputAskResponse.trim()) {
      pushUndoSnapshot();
      workbenchState.outputText = workbenchState.outputAskResponse;
      workbenchState.outputSegments = [
        { text: workbenchState.outputAskResponse, entity_type: null, replaced: false },
      ];
    }
  }

  function clearAskState(target: AskTarget) {
    if (target === "input") {
      workbenchState.inputAskInstruction = "";
      workbenchState.inputAskResponse = "";
      return;
    }
    workbenchState.outputAskInstruction = "";
    workbenchState.outputAskResponse = "";
  }

  function onAskModelChange(value: string) {
    const next = value.trim();
    if (!next) return;
    settingsState.askModel = next;
    queueConfigValue("ollama_model", next);
    void loadOllamaModelInfo(next);
  }

  function estimateAskTokens(target: AskTarget) {
    const instruction =
      target === "input" ? workbenchState.inputAskInstruction : workbenchState.outputAskInstruction;
    const current = target === "input" ? workbenchState.inputText : workbenchState.outputText;
    const other = target === "input" ? workbenchState.outputText : workbenchState.inputText;
    const roughChars = instruction.length + current.length + other.length;
    return Math.max(1, Math.round(roughChars / 4));
  }

  function onToggleSidebarCollapsed() {
    sidebarCollapsed = !sidebarCollapsed;
  }

  $effect(() => {
    workbenchState.outputText;
    workbenchState.outputAttachments;
    workbenchState.activeOutputAttachmentId;
    if (!workbenchState.activeOutputAttachmentId && !workbenchState.outputText.trim() && workbenchState.outputAttachments[0]) {
      workbenchState.activeOutputAttachmentId = workbenchState.outputAttachments[0].id;
      return;
    }
    const target = resolveActiveOutputPreviewTarget();
    if (!target) {
      setOutputPreviewBaseline("", { supported: true });
      return;
    }
    const sameTargetText =
      workbenchState.outputPreviewSavedText === target.text &&
      workbenchState.outputPreviewSupported === target.supported &&
      workbenchState.outputPreviewDirty === false;
    if (sameTargetText) return;
    if (workbenchState.outputPreviewDirty) return;
    setOutputPreviewBaseline(target.text, { supported: target.supported });
  });

  onMount(() => {
    initTheme();
    const currentT = getTheme();
    mainBackgroundUrl = currentT === 'light' ? backgroundUrlLight : backgroundUrlDark;
    const unsubTheme = onThemeChange((t) => {
      mainBackgroundUrl = t === 'light' ? backgroundUrlLight : backgroundUrlDark;
    });

    let unlisten: (() => void) | null = null;
    void (async () => {
      try {
        loadProfiles();
        if (hasTauriBridge()) {
          unlisten = await listen<BackendMessage>(BACKEND_EVENT, (event) => {
            handleBackendMessage(event.payload);
          });
        }
        await afterFirstPaint();
        await refreshBackendStatus();
        if (settingsState.settingsProfiles.length === 0) {
          saveActiveProfileAs("Default");
        } else {
          void applyProfile(settingsState.activeProfileName, {
            deferBackendSync: true,
          });
        }
      } catch (error) {
        enableBrowserMockMode(`event bridge init failed: ${String(error)}`);
        await loadConfigAndThemes();
        if (settingsState.settingsProfiles.length === 0) {
          saveActiveProfileAs("Default");
        } else {
          void applyProfile(settingsState.activeProfileName, {
            deferBackendSync: true,
          });
        }
      }
    })();

    return () => {
      clearRunWatchdog();
      clearConfigDebounceTimers();
      clearOutputPreviewDebounce();
      if (unlisten) unlisten();
      if(unsubTheme) unsubTheme()
      if (hasTauriBridge() && !browserMockMode) {
        void invoke("shutdown_backend").catch(() => {});
      }
    };
  });
</script>

<svelte:window
  onkeydown={(event) => {
    const isUndo =
      (event.metaKey || event.ctrlKey) &&
      !event.shiftKey &&
      event.key.toLowerCase() === "z";
    if (!isUndo) return;
    // Skip when the user is actively editing text — let the browser handle
    // native undo for inputs/textareas. History navigation is available via
    // the ◀ ▶ arrows in the OutputPane header.
    const target = event.target as HTMLElement | null;
    if (target) {
      const tag = target.tagName.toLowerCase();
      if (tag === "input" || tag === "textarea" || tag === "select") return;
      if (target.isContentEditable) return;
    }
    event.preventDefault();
    restoreUndoSnapshot();
  }}
/>

<DropzoneWrapper
  tag="div"
  ariaLabel="App dropzone"
  disabled={processing}
  onFiles={handleDropzoneFiles}
>
  <div class="app-shell" style="background: url('{mainBackgroundUrl}')  center/cover no-repeat fixed;">
    <div
      class="sidebar-layer"
      style={`width: ${sidebarDisplayWidth()}px`}
      class:collapsed={sidebarCollapsed}
    >
      <SidebarPanel
        {ready}
        {processing}
        {browserMockMode}
        {startupError}
        {entityFilters}
        activeEntityFilters={workbenchState.activeEntityFilters}
        {supportsThemes}
        themes={settingsState.themes}
        activeTheme={String(settingsState.config.active_theme ?? "default")}
        strength={strengthFromConfig()}
        collapsed={sidebarCollapsed}
        profiles={profileNames()}
        activeProfileName={settingsState.activeProfileName}
        onToggleEntity={toggleEntityFilter}
        onSetTheme={setTheme}
        onSetStrength={(value) =>
          queueConfigValue("score_threshold", 1 - value)}
        onOpenAdvanced={() => { pushUndoSnapshot(); showAdvanced = true; }}
        onToggleCollapsed={onToggleSidebarCollapsed}
        onSelectProfile={(name) => void applyProfile(name)}
      />
    </div>

    <main>
      <div class="workbench">
        <InputPane
          {ready}
          {processing}
          model={{
            inputText: workbenchState.inputText,
            attachedFiles: workbenchState.attachedFiles,
            fileQueue: workbenchState.fileQueue,
          }}
          ask={{
            enabled: supportsOllamaAsk,
            instruction: workbenchState.inputAskInstruction,
            response: workbenchState.inputAskResponse,
            busy: workbenchState.inputAskBusy,
            modelOptions: buildAvailableOllamaModels({
              askModel: settingsState.askModel,
              config: settingsState.config,
              ollamaModels: settingsState.ollamaModels,
            }),
            selectedModel: settingsState.askModel,
            modelContextTokens: settingsState.askModelContextTokens,
            estimatedTokens: estimateAskTokens("input"),
          }}
          actions={{
            paste: pasteFromClipboard,
            run: processSubmission,
            attachClick: () => inputFilePicker?.click(),
            clearAttached: clearAttachedFileById,
            openAttached: (id: string) => {
              void previewInputAttachment(id);
            },
            downloadAttached: (id: string) => {
              const file = workbenchState.attachedFiles.find((row) => row.id === id);
              if (!file) return;
              if (file.file) {
                void saveBlobWithPicker(file.file, file.name);
              } else if (file.path) {
                void saveBlobWithPicker(
                  new Blob([file.path], { type: "text/plain;charset=utf-8" }),
                  `${file.name}.path.txt`,
                );
              }
            },
            inputChange: (value: string) => (workbenchState.inputText = value),
            askInstructionChange: (value: string) => (workbenchState.inputAskInstruction = value),
            ollamaModelChange: onAskModelChange,
            ask: () => askOllama("input"),
            applyAsk: () => applyAskResponse("input"),
            clearAsk: () => clearAskState("input"),
          }}
        />

        <OutputPane
          model={{
            outputText: workbenchState.outputText,
            outputSegments: workbenchState.outputSegments,
            previewText: workbenchState.outputPreviewText,
            previewSupported: workbenchState.outputPreviewSupported,
            previewDirty: workbenchState.outputPreviewDirty,
            previewSaving: workbenchState.outputPreviewSaving,
            activePreviewIsMain: workbenchState.activeOutputAttachmentId === null,
            droppedFilePath: workbenchState.droppedFilePath,
            outputAttachments: workbenchState.outputAttachments,
            activeOutputAttachmentId: workbenchState.activeOutputAttachmentId,
            outputSaveFormat: workbenchState.outputSaveFormat,
            canHistoryPrev: hasHistoryPrev,
            canHistoryNext: hasHistoryNext,
          }}
          features={{
            supportsReverseText,
            reversibleMappingEnabled: Boolean(settingsState.config.reversible_mapping_enabled ?? false),
            supportsOllamaAsk,
          }}
          ask={{
            instruction: workbenchState.outputAskInstruction,
            response: workbenchState.outputAskResponse,
            busy: workbenchState.outputAskBusy,
            modelOptions: buildAvailableOllamaModels({
              askModel: settingsState.askModel,
              config: settingsState.config,
              ollamaModels: settingsState.ollamaModels,
            }),
            selectedModel: settingsState.askModel,
            modelContextTokens: settingsState.askModelContextTokens,
            estimatedTokens: estimateAskTokens("output"),
          }}
          actions={{
            copy: copyOutput,
            reverse: () => void reverseOutputText(),
            previewInput: queueOutputPreviewDiffCheck,
            savePreview: () => void saveOutputPreviewChanges(),
            history: historyPlaceholder,
            download: () => void downloadOutput(),
            selectOutputAttachment,
            downloadOutputAttachment: (id: string) => void downloadOutputAttachment(id),
            editOutputAttachment: editOutputAttachment,
            exportZip: () => void exportZipPlaceholder(),
            saveFormatChange: (format: "txt" | "md") => (workbenchState.outputSaveFormat = format),
            askInstructionChange: (value: string) => (workbenchState.outputAskInstruction = value),
            ollamaModelChange: onAskModelChange,
            ask: () => askOllama("output"),
            applyAsk: () => applyAskResponse("output"),
            clearAsk: () => clearAskState("output"),
          }}
        />
      </div>

      <footer class="app-footer">
        <div class="footer-status">
          <span class="status-dot" class:online={supportsOllamaAsk}></span>
          Ollama {supportsOllamaAsk ? "connected" : "unavailable"}
          <span class="footer-sep">·</span>
          {String(settingsState.config.ollama_model ?? "qwen3.5:9b")}
        </div>
        <div class="footer-info">
          Engine: <strong>{String(settingsState.config.spacy_model ?? "en_core_web_lg")}</strong>
          <span class="footer-sep">·</span>
          v1.4.5
        </div>
      </footer>
    </main>

    <input
      bind:this={inputFilePicker}
      type="file"
      multiple
      hidden
      accept={FILE_PICKER_ACCEPT}
      onchange={handleFilePickerChange}
    />
  </div>
</DropzoneWrapper>

<AdvancedSettingsModal
  visible={showAdvanced}
  {ready}
  {processing}
  {supportsThemePackImport}
  config={settingsState.config}
  themes={settingsState.themes}
  spacyModels={settingsState.spacyModels}
  fallbackSpacyModels={fallbackSpacyModels()}
  ollamaModels={settingsState.ollamaModels}
  themePackPath={settingsState.themePackPath}
  purgeDays={settingsState.purgeDays}
  {supportsResetData}
  {supportsPurgeData}
  storageEstimateLabel={settingsState.storageEstimateLabel}
  profiles={profileNames()}
  activeProfileName={settingsState.activeProfileName}
  onClose={() => (showAdvanced = false)}
  onSetTheme={setTheme}
  onSetStrength={(value) => queueConfigValue("score_threshold", 1 - value)}
  onConfig={queueConfigValue}
  onThemePackPath={(value) => (settingsState.themePackPath = value)}
  onImportThemePack={importThemePack}
  onInstallSpacyModel={installSpacyModel}
  onSelectProfile={(name) => void applyProfile(name)}
  onSaveProfileAs={(name) => saveActiveProfileAs(name)}
  onSaveConfig={exportCurrentConfig}
  onDeleteProfile={() => {
    const current = settingsState.activeProfileName;
    if (settingsState.settingsProfiles.length <= 1) {
      pushLog("system", "Cannot delete the last profile.");
      return;
    }
    const remaining = settingsState.settingsProfiles.filter((p) => p.name !== current);
    persistProfiles(remaining);
    void applyProfile(remaining[0].name);
    pushLog("system", `Profile "${current}" deleted.`);
  }}
  onRenameProfile={(name) => {
    const trimmed = name.trim();
    const current = settingsState.activeProfileName;
    if (!trimmed || trimmed === current) return;
    if (settingsState.settingsProfiles.some((p) => p.name === trimmed)) {
      pushLog("system", `Profile "${trimmed}" already exists.`);
      return;
    }
    const updated = settingsState.settingsProfiles.map((p) =>
      p.name === current ? { ...p, name: trimmed } : p,
    );
    persistProfiles(updated.sort((a, b) => a.name.localeCompare(b.name)));
    settingsState.activeProfileName = trimmed;
    pushLog("system", `Profile renamed to "${trimmed}".`);
  }}
  onPurgeDays={(value) => (settingsState.purgeDays = value)}
  onPurgeData={() => void purgeOldData()}
  onResetData={() => void resetData()}
/>

<FilePreviewModal
  visible={workbenchState.filePreviewVisible}
  title={workbenchState.filePreviewTitle}
  content={workbenchState.filePreviewContent}
  segments={workbenchState.filePreviewSegments}
  highlightTags={workbenchState.filePreviewHighlightTags}
  kind={workbenchState.filePreviewKind}
  canEdit={workbenchState.filePreviewCanEdit}
  editBusy={workbenchState.filePreviewEditBusy}
  editEntities={workbenchState.filePreviewEditEntities}
  {entityFilters}
  {supportsThemes}
  themes={settingsState.themes}
  editTheme={workbenchState.filePreviewEditTheme}
  editStrength={workbenchState.filePreviewEditStrength}
  onToggleTags={toggleFilePreviewTags}
  onToggleEditEntity={toggleFilePreviewEntity}
  onEditThemeChange={onFilePreviewThemeChange}
  onEditStrengthChange={onFilePreviewStrengthChange}
  onReconvert={() => void reconvertPreviewAttachment()}
  onDownload={() => {
    if (workbenchState.filePreviewAttachmentId) {
      void downloadOutputAttachment(workbenchState.filePreviewAttachmentId);
    } else {
      void downloadOutput();
    }
  }}
  onClose={() => {
    resetFilePreviewObjectUrl();
    workbenchState.filePreviewVisible = false;
    workbenchState.filePreviewTitle = "";
    workbenchState.filePreviewContent = "";
    workbenchState.filePreviewKind = "text";
    workbenchState.filePreviewBadge = "";
    workbenchState.filePreviewCanEdit = false;
    workbenchState.filePreviewSegments = [];
    workbenchState.filePreviewHighlightTags = true;
    workbenchState.filePreviewEditMode = false;
    workbenchState.filePreviewEditBusy = false;
    workbenchState.filePreviewEditEntities = [];
    workbenchState.filePreviewEditTheme = String(settingsState.config.active_theme ?? "default");
    workbenchState.filePreviewEditStrength = strengthFromConfig();
    workbenchState.filePreviewAttachmentId = null;
  }}
/>

<input
  bind:this={configImportPicker}
  type="file"
  accept=".json"
  hidden
  onchange={importConfigFileChange}
/>

<style>
  .app-shell {
    display: flex;
    height: 100dvh;
    min-height: 100dvh;
    width: 100%;
    overflow: hidden;
    box-sizing: border-box;
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
    transition: background-image var(--duration-slow) var(--ease-out);
  }

  .sidebar-layer {
    position: relative;
    overflow: hidden;
    transition: width var(--duration-normal) ease;
    border-right: 1px solid var(--border-soft);
    flex: 0 0 auto;
  }

  .sidebar-layer.collapsed {
    width: 48px;
  }

  main {
    flex: 1;
    min-width: 0;
    height: 100%;
    display: flex;
    flex-direction: column;
    padding: var(--space-md);
    gap: var(--space-md);
    overflow: hidden;
    min-height: 0;
    box-sizing: border-box;
  }

  .workbench {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--space-md);
    flex: 1;
    width: 100%;
    min-height: 0;
  }

  .app-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 10px;
    font-weight: 500;
    color: var(--text-secondary);
    padding: 4px var(--space-sm);
    flex: 0 0 auto;
    letter-spacing: 0.02em;
  }

  .footer-status,
  .footer-info {
    display: flex;
    align-items: center;
    gap: 5px;
  }

  .footer-info strong {
    font-weight: 600;
    color: var(--text-primary);
  }

  .footer-sep {
    opacity: 0.4;
  }

  .status-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--text-muted);
    flex-shrink: 0;
  }

  .status-dot.online {
    background: var(--status-done);
    box-shadow: 0 0 0 3px var(--entity-loc-bg);
  }

  @media (max-width: 1180px) {
    .app-shell {
      flex-direction: column;
      height: auto;
      min-height: 100vh;
      overflow: auto;
    }

    .workbench {
      grid-template-columns: 1fr;
    }

    .app-footer {
      flex-direction: column;
      gap: 4px;
    }
  }
</style>
