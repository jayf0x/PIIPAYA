import {
  DEFAULT_RUNTIME_CONFIG,
  asObjectArray,
  isRecord,
  parseRuntimeConfig,
  type RuntimeConfig,
} from "$lib/domain/backend/contract";

export type SettingsProfile = {
  name: string;
  config: RuntimeConfig;
  activeEntities: string[];
  updatedAt: string;
};

export type SettingsState = {
  config: RuntimeConfig;
  committedConfig: RuntimeConfig;
  themes: string[];
  themePackPath: string;
  spacyModels: Array<{ name: string; installed: boolean; active: boolean }>;
  ollamaModels: Array<{ name: string; active: boolean }>;
  settingsProfiles: SettingsProfile[];
  activeProfileName: string;
  askModel: string;
  askModelContextTokens: number | null;
  purgeDays: number;
  storageEstimateLabel: string;
};

export function createSettingsState(): SettingsState {
  return {
    config: { ...DEFAULT_RUNTIME_CONFIG },
    committedConfig: { ...DEFAULT_RUNTIME_CONFIG },
    themes: [],
    themePackPath: "",
    spacyModels: [],
    ollamaModels: [],
    settingsProfiles: [],
    activeProfileName: "Default",
    askModel: "qwen3.5:9b",
    askModelContextTokens: null,
    purgeDays: 30,
    storageEstimateLabel: "Estimating...",
  };
}

export function sameConfigValue(left: unknown, right: unknown) {
  if (Object.is(left, right)) return true;
  try {
    return JSON.stringify(left) === JSON.stringify(right);
  } catch {
    return false;
  }
}

export function parseStringList(raw: string) {
  return raw
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter((item) => item.length > 0);
}

export function profileNames(settingsProfiles: SettingsProfile[]) {
  if (settingsProfiles.length === 0) return ["Default"];
  return settingsProfiles.map((row) => row.name);
}

export function configSnapshot(config: RuntimeConfig) {
  return JSON.parse(JSON.stringify(config)) as RuntimeConfig;
}

export function createProfileSnapshot(params: {
  activeEntityFilters: Set<string>;
  activeProfileName: string;
  config: RuntimeConfig;
}) {
  return {
    name: params.activeProfileName.trim(),
    config: configSnapshot(params.config),
    activeEntities: [...params.activeEntityFilters],
    updatedAt: new Date().toISOString(),
  } satisfies SettingsProfile;
}

export function loadProfilesFromStorage(params: {
  profileStorageKey: string;
  activeProfileStorageKey: string;
}) {
  if (typeof localStorage === "undefined") {
    return null;
  }
  const raw = localStorage.getItem(params.profileStorageKey);
  const rawActive = localStorage.getItem(params.activeProfileStorageKey);
  if (!raw) return null;

  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return null;
    const profiles = asObjectArray(parsed)
      .map((row) => ({
        name: String(row.name ?? "").trim(),
        config: parseRuntimeConfig(row.config),
        activeEntities: Array.isArray(row.activeEntities)
          ? row.activeEntities.filter(
              (entity): entity is string => typeof entity === "string",
            )
          : [],
        updatedAt: String(row.updatedAt ?? new Date().toISOString()),
      }))
      .filter((row) => row.name.length > 0)
      .sort((a, b) => a.name.localeCompare(b.name));

    if (profiles.length === 0) return null;

    const selected =
      rawActive && profiles.some((row) => row.name === rawActive)
        ? rawActive
        : profiles[0].name;

    return {
      activeProfileName: selected,
      settingsProfiles: profiles,
    };
  } catch {
    return null;
  }
}

export function persistProfilesToStorage(params: {
  profileStorageKey: string;
  activeProfileStorageKey: string;
  settingsProfiles: SettingsProfile[];
  activeProfileName: string;
}) {
  if (typeof localStorage === "undefined") return;
  localStorage.setItem(
    params.profileStorageKey,
    JSON.stringify(params.settingsProfiles),
  );
  localStorage.setItem(params.activeProfileStorageKey, params.activeProfileName);
}

export function queueActiveDateFormatsUpdate(params: {
  config: RuntimeConfig;
  raw: string;
}) {
  const activeTheme = String(params.config.active_theme);
  const currentProfiles = params.config.date_format_profiles;

  return {
    ...currentProfiles,
    [activeTheme]: parseStringList(params.raw),
  };
}
