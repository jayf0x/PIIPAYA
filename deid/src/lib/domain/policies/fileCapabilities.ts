const INLINE_TEXT_EXTENSIONS = [
  "",
  ".txt",
  ".md",
  ".csv",
  ".json",
  ".log",
  ".py",
  ".js",
  ".jsx",
  ".ts",
  ".tsx",
  ".java",
  ".rb",
  ".go",
  ".rs",
  ".c",
  ".cc",
  ".cpp",
  ".h",
  ".hpp",
  ".sh",
  ".yaml",
  ".yml",
  ".toml",
  ".ini",
  ".xml",
  ".html",
  ".css",
  ".sql",
] as const;

const PATH_ONLY_EXTENSIONS = [
  ".zip",
  ".docx",
  ".pdf",
  ".pages",
  ".png",
  ".jpg",
  ".jpeg",
  ".tif",
  ".tiff",
  ".bmp",
  ".gif",
  ".heic",
] as const;

const IMAGE_EXTENSIONS = new Set([
  ".png",
  ".jpg",
  ".jpeg",
  ".tif",
  ".tiff",
  ".bmp",
  ".gif",
  ".heic",
]);

const BACKEND_TEXT_PREVIEW_EXTENSIONS = new Set([
  "",
  ".txt",
  ".md",
  ".json",
  ".csv",
  ".log",
  ".xml",
  ".html",
  ".yaml",
  ".yml",
  ".docx",
  ".pdf",
  ".pages",
]);

export const SUPPORTED_INLINE_TEXT_EXTENSIONS = new Set<string>(INLINE_TEXT_EXTENSIONS);
export const SUPPORTED_PATH_EXTENSIONS = new Set<string>([
  ...INLINE_TEXT_EXTENSIONS,
  ...PATH_ONLY_EXTENSIONS,
]);
export const OUTPUT_PREVIEW_SUPPORTED_EXTENSIONS = new Set<string>([
  ...INLINE_TEXT_EXTENSIONS,
  ".docx",
  ".pdf",
  ".pages",
]);

export function extensionFromName(name: string) {
  const trimmed = name.trim().toLowerCase();
  const dot = trimmed.lastIndexOf(".");
  if (dot < 0) return "";
  return trimmed.slice(dot);
}

export function supportsInlineAttachment(name: string) {
  return SUPPORTED_INLINE_TEXT_EXTENSIONS.has(extensionFromName(name));
}

export function supportsPathAttachment(name: string) {
  return SUPPORTED_PATH_EXTENSIONS.has(extensionFromName(name));
}

export function supportsBackendTextPreview(name: string) {
  return BACKEND_TEXT_PREVIEW_EXTENSIONS.has(extensionFromName(name));
}

export function supportsOutputPreview(name: string) {
  return OUTPUT_PREVIEW_SUPPORTED_EXTENSIONS.has(extensionFromName(name));
}

export function inferPreviewKind(name: string): "text" | "image" | "unsupported" {
  const ext = extensionFromName(name);
  if (IMAGE_EXTENSIONS.has(ext)) return "image";
  if (supportsInlineAttachment(name)) return "text";
  return "unsupported";
}
