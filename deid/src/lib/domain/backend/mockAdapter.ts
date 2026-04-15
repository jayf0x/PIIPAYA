import {
  BACKEND_COMMANDS,
  DEFAULT_RUNTIME_CONFIG,
  MOCK_BASE_FEATURES,
  asObjectArray,
  isRecord,
  parseRuntimeConfig,
  type BackendEnvelope,
  type BackendMessage,
  type BackendPayload,
  type RuntimeConfig,
} from "$lib/domain/backend/contract";
import { supportsBackendTextPreview } from "$lib/domain/policies/fileCapabilities";
import type { OutputSegment } from "$lib/types/ui";

type MockChunkResult = {
  text: string;
  segments: OutputSegment[];
};

type CreateBrowserMockAdapterOptions = {
  onMessage: (message: BackendMessage) => void;
};

export function createBrowserMockAdapter(options: CreateBrowserMockAdapterOptions) {
  const mockNameCache = new Map<string, string>();
  const mockReverseNameCache = new Map<string, string>();
  const mockThemes: Record<string, string[]> = {
    default: ["Avery", "Jordan", "Rowan", "Quinn", "Morgan", "Taylor"],
    noir: ["Marlowe", "Vivian", "Spade", "Brigid", "Archer"],
  };

  let mockConfigStore: RuntimeConfig = { ...DEFAULT_RUNTIME_CONFIG };
  let mockInstalledSpacyModels = new Set(["en_core_web_lg"]);
  let mockOllamaInstalled = true;
  let mockOllamaRunning = true;

  function emit(
    type: BackendMessage["type"],
    payload: BackendPayload,
    id: string,
  ) {
    queueMicrotask(() => {
      options.onMessage({ id, type, payload });
    });
  }

  function stableHash(raw: string): number {
    let hash = 2166136261;
    for (let idx = 0; idx < raw.length; idx += 1) {
      hash ^= raw.charCodeAt(idx);
      hash = Math.imul(hash, 16777619);
    }
    return Math.abs(hash >>> 0);
  }

  function defaultMockConfig() {
    return { ...DEFAULT_RUNTIME_CONFIG };
  }

  function featureMap() {
    const enabled = Boolean(mockConfigStore.ollama_enabled);
    if (enabled && mockOllamaInstalled) {
      return [
        ...MOCK_BASE_FEATURES,
        BACKEND_COMMANDS.listOllamaModels,
        BACKEND_COMMANDS.getOllamaModelInfo,
        BACKEND_COMMANDS.askOllama,
      ];
    }
    return [...MOCK_BASE_FEATURES];
  }

  function loadConfig() {
    if (typeof localStorage === "undefined") {
      mockConfigStore = defaultMockConfig();
      return;
    }
    const raw = localStorage.getItem("deid:mock-config");
    if (!raw) {
      mockConfigStore = defaultMockConfig();
      return;
    }
    try {
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed === "object") {
        mockConfigStore = {
          ...defaultMockConfig(),
          ...parseRuntimeConfig(parsed),
        };
        return;
      }
    } catch {
      mockConfigStore = defaultMockConfig();
      return;
    }
    mockConfigStore = defaultMockConfig();
  }

  function persistConfig() {
    if (typeof localStorage === "undefined") {
      return;
    }
    localStorage.setItem("deid:mock-config", JSON.stringify(mockConfigStore));
  }

  function mapMockPersonToken(token: string) {
    const normalized = token.toLowerCase();
    const existing = mockNameCache.get(normalized);
    if (existing) {
      return existing;
    }
    const activeTheme = String(mockConfigStore.active_theme ?? "default");
    const pool = mockThemes[activeTheme] ?? mockThemes.default;
    const mapped =
      pool[stableHash(`${normalized}:${activeTheme}`) % pool.length] ?? "Anon";
    mockNameCache.set(normalized, mapped);
    return mapped;
  }

  function processText(input: string, entitiesToMask: string[]): MockChunkResult {
    const personPattern = /\b[A-Z][a-z]{2,}\b/g;
    const segments: OutputSegment[] = [];
    let cursor = 0;
    let output = "";
    const scoreThreshold = Math.max(
      0,
      Math.min(1, Number(mockConfigStore.score_threshold ?? 0.35)),
    );
    const strength = 1 - scoreThreshold;
    for (const match of input.matchAll(personPattern)) {
      const start = match.index ?? -1;
      if (start < 0) continue;
      const raw = match[0];
      const end = start + raw.length;
      if (cursor < start) {
        const unchanged = input.slice(cursor, start);
        segments.push({ text: unchanged, entity_type: null, replaced: false });
        output += unchanged;
      }
      const score = stableHash(`${raw}:${cursor}:likeliness`) % 1000;
      const shouldReplace = score < strength * 1000;
      const personEnabled = entitiesToMask.includes("PERSON");
      if (shouldReplace && personEnabled) {
        const replacement = mapMockPersonToken(raw);
        mockReverseNameCache.set(replacement, raw);
        segments.push({
          text: replacement,
          entity_type: "PERSON",
          replaced: true,
        });
        output += replacement;
      } else {
        segments.push({ text: raw, entity_type: null, replaced: false });
        output += raw;
      }
      cursor = end;
    }
    if (cursor < input.length) {
      const tail = input.slice(cursor);
      segments.push({ text: tail, entity_type: null, replaced: false });
      output += tail;
    }
    if (segments.length === 0) {
      return {
        text: input,
        segments: [{ text: input, entity_type: null, replaced: false }],
      };
    }
    return { text: output, segments };
  }

  function handleEnvelope(envelope: BackendEnvelope) {
    const id = envelope.id;
    const command = String(envelope.command ?? "");
    const payload = isRecord(envelope.payload) ? envelope.payload : {};

    if (command === BACKEND_COMMANDS.getConfig) {
      emit("DONE", { config: mockConfigStore }, id);
      return;
    }
    if (command === BACKEND_COMMANDS.updateConfig) {
      const key = String(payload.key ?? "");
      mockConfigStore = { ...mockConfigStore, [key]: payload.value };
      persistConfig();
      emit("DONE", { key, value: payload.value }, id);
      if (
        key === "ollama_enabled" ||
        key === "ollama_model" ||
        key === "ollama_endpoint"
      ) {
        emit("READY", { feature_map: featureMap() }, "mock-ready");
      }
      return;
    }
    if (command === BACKEND_COMMANDS.listThemes) {
      emit("DONE", { themes: Object.keys(mockThemes) }, id);
      return;
    }
    if (command === BACKEND_COMMANDS.setTheme) {
      const theme = String(payload.theme ?? "default");
      mockConfigStore = { ...mockConfigStore, active_theme: theme };
      persistConfig();
      emit("DONE", { active_theme: theme }, id);
      return;
    }
    if (command === BACKEND_COMMANDS.listSpacyModels) {
      const active = String(mockConfigStore.spacy_model ?? "en_core_web_lg");
      const models = ["en_core_web_sm", "en_core_web_md", "en_core_web_lg"].map(
        (name) => ({
          name,
          installed: mockInstalledSpacyModels.has(name),
          active: name === active,
        }),
      );
      emit("DONE", { models }, id);
      return;
    }
    if (command === BACKEND_COMMANDS.installSpacyModel) {
      const model = String(payload.model ?? "");
      if (!model) {
        emit(
          "ERROR",
          { code: "INVALID_PAYLOAD", message: "Missing model." },
          id,
        );
        return;
      }
      mockInstalledSpacyModels = new Set([...mockInstalledSpacyModels, model]);
      emit("DONE", { model, installed: true, already_installed: false }, id);
      return;
    }
    if (command === BACKEND_COMMANDS.listOllamaModels) {
      if (
        !Boolean(mockConfigStore.ollama_enabled) ||
        !mockOllamaInstalled ||
        !mockOllamaRunning
      ) {
        emit(
          "ERROR",
          { code: "OLLAMA_NOT_AVAILABLE", message: "Ollama is unavailable." },
          id,
        );
        return;
      }
      const active = String(mockConfigStore.ollama_model ?? "qwen3.5:9b");
      const names = ["gemma3:270m-it-qat", "qwen3.5:9b"];
      emit(
        "DONE",
        {
          models: names.map((name) => ({ name, active: name === active })),
          available: true,
        },
        id,
      );
      return;
    }

    if (command === BACKEND_COMMANDS.getOllamaModelInfo) {
      const model = String(payload.model ?? mockConfigStore.ollama_model ?? "qwen3.5:9b");
      const presets: Record<string, number> = {
        "qwen3.5:9b": 32768,
        "gemma3:270m-it-qat": 8192,
      };
      emit("DONE", { model, context_tokens: presets[model] ?? 8192 }, id);
      return;
    }
    if (command === BACKEND_COMMANDS.cancelRequest) {
      emit("DONE", { cancelled: true, request_id: payload.request_id }, id);
      return;
    }
    if (command === BACKEND_COMMANDS.processText) {
      const text = String(payload.text ?? "");
      const entities = Array.isArray(payload.entities)
        ? payload.entities.filter((row): row is string => typeof row === "string")
        : ["PERSON"];
      const themeOverride =
        typeof payload.theme === "string" && payload.theme.trim()
          ? payload.theme.trim()
          : null;
      const scoreOverride =
        typeof payload.score_threshold === "number"
          ? Math.max(0, Math.min(1, Number(payload.score_threshold)))
          : null;
      const prevTheme = mockConfigStore.active_theme;
      const prevScore = mockConfigStore.score_threshold;
      if (themeOverride) {
        mockConfigStore = { ...mockConfigStore, active_theme: themeOverride };
      }
      if (scoreOverride != null) {
        mockConfigStore = { ...mockConfigStore, score_threshold: scoreOverride };
      }
      const processed = processText(text, entities);
      if (themeOverride) {
        mockConfigStore = { ...mockConfigStore, active_theme: prevTheme };
      }
      if (scoreOverride != null) {
        mockConfigStore = { ...mockConfigStore, score_threshold: prevScore };
      }
      emit(
        "PROGRESS",
        { log_type: "system", message: "Mock processing started.", pct: 10 },
        id,
      );
      emit("CHUNK", { text: processed.text, segments: processed.segments }, id);
      emit(
        "PROGRESS",
        { log_type: "engine", message: "Mock processing complete.", pct: 95 },
        id,
      );
      emit(
        "DONE",
        { total_chars: processed.text.length, segments: processed.segments },
        id,
      );
      return;
    }
    if (command === BACKEND_COMMANDS.processFiles) {
      const paths = Array.isArray(payload.paths)
        ? payload.paths.filter((row): row is string => typeof row === "string")
        : [];
      const inlineDocs = Array.isArray(payload.inline_docs)
        ? asObjectArray(payload.inline_docs)
        : [];
      const entities = Array.isArray(payload.entities)
        ? payload.entities.filter((row): row is string => typeof row === "string")
        : ["PERSON"];
      const docs = [
        ...inlineDocs.map((row) => ({
          name: String(row.name ?? "inline.txt"),
          text: String(row.text ?? ""),
        })),
        ...paths.map((path) => ({
          name: path.split(/[\\/]/).pop() ?? path,
          text: `[Attached path queued] ${path}`,
        })),
      ];
      const processedFiles = docs.map((doc) => {
        const processed = processText(doc.text, entities);
        return {
          name: doc.name,
          text: processed.text,
          segments: processed.segments,
        };
      });
      const combined = processedFiles
        .map((row) => `\n\n--- ${row.name} ---\n\n${row.text}`)
        .join("")
        .trim();
      emit(
        "CHUNK",
        {
          stream: "file_progress",
          phase: "queue",
          files: docs.map((doc, index) => ({
            file_index: index + 1,
            file_total: docs.length,
            name: doc.name,
            status: "queued",
            progress_pct: 0,
            detail: "Queued",
          })),
        },
        id,
      );
      emit(
        "PROGRESS",
        {
          log_type: "system",
          message: "Mock multi-file processing started.",
          pct: 10,
        },
        id,
      );
      for (let index = 0; index < processedFiles.length; index += 1) {
        const row = processedFiles[index];
        emit(
          "CHUNK",
          {
            stream: "file_progress",
            phase: "processing",
            file_index: index + 1,
            file_total: processedFiles.length,
            name: row.name,
            status: "processing",
            progress_pct: 20,
            detail: `Processing ${index + 1}/${processedFiles.length}`,
          },
          id,
        );
        emit(
          "CHUNK",
          {
            stream: "file_progress",
            phase: "done",
            file_index: index + 1,
            file_total: processedFiles.length,
            name: row.name,
            status: "done",
            progress_pct: 100,
            detail: `Done (${row.text.length} chars)`,
          },
          id,
        );
      }
      emit("CHUNK", { text: combined, segments: [] }, id);
      emit(
        "DONE",
        {
          total_chars: combined.length,
          files: processedFiles,
          output_text: combined,
        },
        id,
      );
      return;
    }
    if (command === BACKEND_COMMANDS.previewFile) {
      const path = String(payload.path ?? "");
      const name = path.split(/[\\/]/).pop() ?? path ?? "file";
      const ext = name.includes(".") ? name.slice(name.lastIndexOf(".")).toLowerCase() : "";
      const supported = supportsBackendTextPreview(name);
      emit(
        "DONE",
        {
          name,
          file_type: ext || "[no extension]",
          preview_supported: supported,
          preview_text: supported ? `[Mock preview]\n${path}` : "",
        },
        id,
      );
      return;
    }
    if (command === BACKEND_COMMANDS.reverseText) {
      const text = String(payload.text ?? "");
      if (!Boolean(mockConfigStore.reversible_mapping_enabled ?? false)) {
        emit(
          "ERROR",
          {
            code: "REVERSIBLE_MAPPING_DISABLED",
            message: "Enable reversible mapping first.",
          },
          id,
        );
        return;
      }
      let reversed = text;
      for (const [mapped, original] of mockReverseNameCache.entries()) {
        reversed = reversed.replaceAll(mapped, original);
      }
      emit("DONE", { total_chars: reversed.length, output_text: reversed }, id);
      return;
    }
    if (command === BACKEND_COMMANDS.askOllama) {
      if (
        !Boolean(mockConfigStore.ollama_enabled) ||
        !mockOllamaInstalled ||
        !mockOllamaRunning
      ) {
        emit(
          "ERROR",
          { code: "OLLAMA_NOT_AVAILABLE", message: "Ollama is unavailable." },
          id,
        );
        return;
      }
      const target = String(payload.target ?? "input");
      const instruction = String(payload.instruction ?? "").trim();
      const sourceText = String(payload.current_text ?? "");
      let response = sourceText;
      const switchMatch = instruction.match(
        /switch\s+([A-Za-z]+)\s+with\s+([A-Za-z]+)/i,
      );
      if (switchMatch) {
        const from = switchMatch[1];
        const to = switchMatch[2];
        response = sourceText.replace(new RegExp(`\\b${from}\\b`, "gi"), to);
      }
      emit("PROGRESS", { log_type: "system", message: "Mock Ask started.", pct: 10 }, id);
      for (const token of response.match(/\S+\s*/g) ?? [response]) {
        emit("CHUNK", { stream: "ollama", target, text: token }, id);
      }
      emit("DONE", { target, response }, id);
      return;
    }

    if (command === BACKEND_COMMANDS.resetData) {
      mockConfigStore = defaultMockConfig();
      persistConfig();
      emit("READY", { feature_map: featureMap() }, "mock-ready");
      emit("DONE", { reset: true }, id);
      return;
    }

    if (command === BACKEND_COMMANDS.purgeData) {
      const days = Math.max(1, Math.round(Number(payload.days ?? 30)));
      emit("DONE", { purged: true, days, deleted_records: 0 }, id);
      return;
    }

    if (command === BACKEND_COMMANDS.getStorageStats) {
      emit(
        "DONE",
        {
          db_bytes: 180224,
          config_keys: Object.keys(mockConfigStore).length,
          themes: Object.keys(mockThemes).length,
        },
        id,
      );
      return;
    }

    emit(
      "ERROR",
      { code: "UNKNOWN_COMMAND", message: `Unsupported command: ${command}` },
      id,
    );
  }

  return {
    featureMap,
    loadConfig,
    async sendEnvelope(envelope: BackendEnvelope) {
      handleEnvelope(envelope);
    },
  };
}
