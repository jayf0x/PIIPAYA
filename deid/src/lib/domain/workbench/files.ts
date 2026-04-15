import type { AttachedInputFile, FileQueueItem } from "$lib/types/ui";
import {
  extensionFromName,
  supportsInlineAttachment,
  supportsPathAttachment,
} from "$lib/domain/policies/fileCapabilities";

export function initializeFileQueueRows(items: { id: string; name: string }[]) {
  return items.map((row) => ({
    id: row.id,
    name: row.name,
    status: "queued" as const,
    progressPct: 0,
    detail: "Queued",
  }));
}

export function patchQueueRowByIndex(
  rows: FileQueueItem[],
  index1Based: number,
  patch: Partial<FileQueueItem>,
) {
  const idx = Math.max(0, index1Based - 1);
  if (idx >= rows.length) return rows;
  return rows.map((row, rowIdx) => (rowIdx === idx ? { ...row, ...patch } : row));
}

export function markPendingQueueRowsAsFailed(rows: FileQueueItem[], detail: string) {
  return rows.map((row) => {
    if (row.status === "done" || row.status === "failed") return row;
    if (row.status === "unsupported") return row;
    return {
      ...row,
      status: "failed" as const,
      progressPct: 0,
      detail,
    };
  });
}

export function splitAttachmentsByCapability(attachedFiles: AttachedInputFile[]) {
  const rawPathAttachments = attachedFiles.filter(
    (file) => typeof file.path === "string" && file.path.length > 0,
  );
  const rawInlineAttachments = attachedFiles.filter((file) => file.file && !file.path);

  const queueItems: { id: string; name: string; status?: FileQueueItem["status"]; detail?: string }[] = [];
  const pathAttachments: AttachedInputFile[] = [];
  const inlineAttachments: AttachedInputFile[] = [];
  let skippedUnsupported = 0;

  for (const file of rawPathAttachments) {
    const ext = extensionFromName(file.name);
    if (supportsPathAttachment(file.name)) {
      pathAttachments.push(file);
      queueItems.push({ id: file.id, name: file.name });
    } else {
      skippedUnsupported += 1;
      queueItems.push({
        id: file.id,
        name: file.name,
        status: "unsupported",
        detail: `Unsupported file type: ${ext || "[no extension]"}`,
      });
    }
  }

  for (const file of rawInlineAttachments) {
    const ext = extensionFromName(file.name);
    if (supportsInlineAttachment(file.name)) {
      inlineAttachments.push(file);
      queueItems.push({ id: file.id, name: file.name });
    } else {
      skippedUnsupported += 1;
      queueItems.push({
        id: file.id,
        name: file.name,
        status: "unsupported",
        detail:
          ext === ".docx" || ext === ".pdf"
            ? "Use a desktop path attachment for DOCX/PDF conversion."
            : `Unsupported inline file type: ${ext || "[no extension]"}`,
      });
    }
  }

  return {
    inlineAttachments,
    pathAttachments,
    queueItems,
    skippedUnsupported,
  };
}

export type FileAttachInput = {
  path?: string;
  file?: File;
};

export type NormalizedAttachFile = {
  name: string;
  path: string | null;
  file: File | null;
};

export type FileAttachResult = {
  nextAttachedFiles: AttachedInputFile[];
  added: NormalizedAttachFile[];
  duplicateCount: number;
  shouldPushUndoSnapshot: boolean;
  shouldResetQueue: boolean;
  logs: string[];
};

function fileNameFromPath(path: string): string {
  const parts = path.split(/[\\/]/);
  return parts[parts.length - 1] || path;
}

function normalizeFileAttachInput(input: FileAttachInput): NormalizedAttachFile | null {
  const rawPath = typeof input.path === "string" ? input.path.trim() : "";
  const file = input.file instanceof File ? input.file : null;
  if (rawPath) {
    return {
      name: file?.name?.trim() || fileNameFromPath(rawPath),
      path: rawPath,
      file,
    };
  }
  if (file) {
    return {
      name: file.name,
      path: null,
      file,
    };
  }
  return null;
}

function fileIdentity(file: { name: string; path: string | null; file: File | null }) {
  if (file.path) return `path:${file.path}`;
  return `name:${file.name}:size:${file.file?.size ?? 0}`;
}

export function mergeAttachedFiles(params: {
  current: AttachedInputFile[];
  incoming: FileAttachInput[];
  createId: () => string;
}): FileAttachResult {
  const { current, incoming, createId } = params;
  const normalizedIncoming = incoming
    .map((item) => normalizeFileAttachInput(item))
    .filter((item): item is NormalizedAttachFile => item !== null);

  if (normalizedIncoming.length === 0) {
    return {
      nextAttachedFiles: current,
      added: [],
      duplicateCount: 0,
      shouldPushUndoSnapshot: false,
      shouldResetQueue: false,
      logs: [],
    };
  }

  const existingIds = new Set(current.map((item) => fileIdentity(item)));
  const nextAttachedFiles = [...current];
  const added: NormalizedAttachFile[] = [];
  let duplicateCount = 0;

  for (const item of normalizedIncoming) {
    const idKey = fileIdentity(item);
    if (existingIds.has(idKey)) {
      duplicateCount += 1;
      continue;
    }
    existingIds.add(idKey);
    nextAttachedFiles.push({
      id: createId(),
      name: item.name,
      path: item.path,
      file: item.file,
    });
    added.push(item);
  }

  const logs: string[] = [];
  for (const row of added) {
    logs.push(`Attached file: ${row.name}`);
  }
  if (duplicateCount > 0) {
    logs.push(
      duplicateCount === 1
        ? "Skipped duplicate file."
        : `Skipped ${duplicateCount} duplicate files.`,
    );
  }

  return {
    nextAttachedFiles,
    added,
    duplicateCount,
    shouldPushUndoSnapshot: added.length > 0,
    shouldResetQueue: added.length > 0,
    logs,
  };
}
