import type { OutputSegment } from "$lib/types/ui";

export const BACKEND_EVENT = "backend:event";

export const BACKEND_COMMANDS = {
  askOllama: "ASK_OLLAMA",
  cancelRequest: "CANCEL_REQUEST",
  getConfig: "GET_CONFIG",
  getOllamaModelInfo: "GET_OLLAMA_MODEL_INFO",
  getStorageStats: "GET_STORAGE_STATS",
  importThemePack: "IMPORT_THEME_PACK",
  installSpacyModel: "INSTALL_SPACY_MODEL",
  listOllamaModels: "LIST_OLLAMA_MODELS",
  listSpacyModels: "LIST_SPACY_MODELS",
  listThemes: "LIST_THEMES",
  previewFile: "PREVIEW_FILE",
  processFile: "PROCESS_FILE",
  processFiles: "PROCESS_FILES",
  processText: "PROCESS_TEXT",
  purgeData: "PURGE_DATA",
  resetData: "RESET_DATA",
  reverseText: "REVERSE_TEXT",
  setTheme: "SET_THEME",
  updateConfig: "UPDATE_CONFIG",
} as const;

export type BackendCommand =
  (typeof BACKEND_COMMANDS)[keyof typeof BACKEND_COMMANDS];

export const BACKEND_CAPABILITIES = {
  askOllama: BACKEND_COMMANDS.askOllama,
  cancelRequest: BACKEND_COMMANDS.cancelRequest,
  getConfig: BACKEND_COMMANDS.getConfig,
  getOllamaModelInfo: BACKEND_COMMANDS.getOllamaModelInfo,
  getStorageStats: BACKEND_COMMANDS.getStorageStats,
  importThemePack: BACKEND_COMMANDS.importThemePack,
  installSpacyModel: BACKEND_COMMANDS.installSpacyModel,
  listOllamaModels: BACKEND_COMMANDS.listOllamaModels,
  listSpacyModels: BACKEND_COMMANDS.listSpacyModels,
  listThemes: BACKEND_COMMANDS.listThemes,
  previewFile: BACKEND_COMMANDS.previewFile,
  processFile: BACKEND_COMMANDS.processFile,
  processFiles: BACKEND_COMMANDS.processFiles,
  processText: BACKEND_COMMANDS.processText,
  purgeData: BACKEND_COMMANDS.purgeData,
  resetData: BACKEND_COMMANDS.resetData,
  reverseText: BACKEND_COMMANDS.reverseText,
  setTheme: BACKEND_COMMANDS.setTheme,
  updateConfig: BACKEND_COMMANDS.updateConfig,
} as const;

export type BackendCapability =
  (typeof BACKEND_CAPABILITIES)[keyof typeof BACKEND_CAPABILITIES];

export type BackendPayload = Record<string, unknown>;

export type RuntimeConfig = {
  seed: string;
  likeliness: number;
  consistency: number;
  spacy_model: string;
  analysis_language: string;
  score_threshold: number;
  low_confidence_score_multiplier: number;
  low_score_entity_names: string[];
  labels_to_ignore: string[];
  custom_detectors: Array<Record<string, unknown>>;
  chunk_size_chars: number;
  max_workers: number;
  reload_nlp_on_run: boolean;
  active_theme: string;
  email_domain_pool: string[];
  preserve_phone_country_prefix: boolean;
  phone_default_region: string;
  date_shift_days_min: number;
  date_shift_days_max: number;
  date_format_profiles: Record<string, string[]>;
  reversible_mapping_enabled: boolean;
  ollama_endpoint: string;
  ollama_model: string;
  ollama_enabled: boolean;
};

export const DEFAULT_RUNTIME_CONFIG: RuntimeConfig = {
  seed: "global_salt_v1",
  likeliness: 1,
  consistency: 0.1,
  spacy_model: "en_core_web_lg",
  analysis_language: "en",
  score_threshold: 0.35,
  low_confidence_score_multiplier: 0.4,
  low_score_entity_names: ["ORG", "ORGANIZATION"],
  labels_to_ignore: [],
  custom_detectors: [],
  chunk_size_chars: 2000,
  max_workers: 1,
  reload_nlp_on_run: false,
  active_theme: "default",
  email_domain_pool: ["example.com", "mail.test", "corp.local"],
  preserve_phone_country_prefix: true,
  phone_default_region: "US",
  date_shift_days_min: -365,
  date_shift_days_max: 365,
  date_format_profiles: {
    default: ["%m/%d/%Y", "%Y-%m-%d", "%B %d, %Y"],
  },
  reversible_mapping_enabled: false,
  ollama_endpoint: "http://127.0.0.1:11434",
  ollama_model: "qwen3.5:9b",
  ollama_enabled: true,
};

export type BackendMessage = {
  id: string | null;
  type: "READY" | "PROGRESS" | "CHUNK" | "DONE" | "ERROR";
  payload: BackendPayload;
};

export type BackendEnvelope = {
  id: string;
  command: BackendCommand | string;
  payload: BackendPayload;
};

export type BackendStatus = {
  ready: boolean;
  feature_map: string[];
  startup_error: string | null;
};

export const MOCK_BASE_FEATURES: string[] = [
  BACKEND_COMMANDS.processText,
  BACKEND_COMMANDS.processFile,
  BACKEND_COMMANDS.processFiles,
  BACKEND_COMMANDS.previewFile,
  BACKEND_COMMANDS.reverseText,
  BACKEND_COMMANDS.getConfig,
  BACKEND_COMMANDS.updateConfig,
  BACKEND_COMMANDS.listThemes,
  BACKEND_COMMANDS.setTheme,
  BACKEND_COMMANDS.listSpacyModels,
  BACKEND_COMMANDS.installSpacyModel,
  BACKEND_COMMANDS.getStorageStats,
  BACKEND_COMMANDS.resetData,
  BACKEND_COMMANDS.purgeData,
  BACKEND_COMMANDS.cancelRequest,
];

export function hasCapability(
  featureMap: string[],
  capability: BackendCapability,
) {
  return featureMap.includes(capability);
}

export function hasAllCapabilities(
  featureMap: string[],
  capabilities: BackendCapability[],
) {
  return capabilities.every((capability) => featureMap.includes(capability));
}

export function parseOutputSegments(raw: unknown): OutputSegment[] {
  if (!Array.isArray(raw)) return [];
  return raw
    .filter(
      (row): row is Record<string, unknown> =>
        typeof row === "object" && row !== null,
    )
    .map((row) => ({
      text: String(row.text ?? ""),
      entity_type: row.entity_type == null ? null : String(row.entity_type),
      replaced: Boolean(row.replaced),
    }))
    .filter((row) => row.text.length > 0);
}

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export function asObjectArray(raw: unknown) {
  if (!Array.isArray(raw)) return [];
  return raw.filter((row): row is Record<string, unknown> => isRecord(row));
}

export function parseJsonObject(raw: string) {
  const parsed: unknown = JSON.parse(raw);
  return isRecord(parsed) ? parsed : {};
}

export function parseRuntimeConfig(raw: unknown): RuntimeConfig {
  if (!isRecord(raw)) return { ...DEFAULT_RUNTIME_CONFIG };
  const next = { ...DEFAULT_RUNTIME_CONFIG };
  for (const [key, value] of Object.entries(raw)) {
    if (!(key in next)) continue;
    if (key === "date_format_profiles" && isRecord(value)) {
      const mapped: Record<string, string[]> = {};
      for (const [theme, formats] of Object.entries(value)) {
        if (!Array.isArray(formats)) continue;
        mapped[theme] = formats
          .filter((row): row is string => typeof row === "string")
          .map((row) => row.trim())
          .filter((row) => row.length > 0);
      }
      if (Object.keys(mapped).length > 0) {
        next.date_format_profiles = mapped;
      }
      continue;
    }
    (next as Record<string, unknown>)[key] = value;
  }
  return next;
}
