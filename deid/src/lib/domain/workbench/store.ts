import { resolveActiveOutputPreviewTarget } from "$lib/domain/workbench/preview";
import type { RuntimeConfig } from "$lib/domain/backend/contract";
import type {
  AttachedInputFile,
  FileQueueItem,
  OutputAttachment,
  OutputSegment,
} from "$lib/types/ui";

export type RunRevision = {
  inputText: string;
  outputText: string;
  outputSegments: OutputSegment[];
  droppedFilePath: string | null;
  timestamp: string;
};

export type UndoSnapshot = {
  inputText: string;
  outputText: string;
  outputSegments: OutputSegment[];
  outputAttachments: OutputAttachment[];
  attachedFiles: AttachedInputFile[];
  activeEntityFilters: string[];
  droppedFilePath: string | null;
  fileQueue: FileQueueItem[];
  config: RuntimeConfig | null;
  activeProfileName: string | null;
};

export type WorkbenchState = {
  inputText: string;
  outputText: string;
  outputSegments: OutputSegment[];
  outputAttachments: OutputAttachment[];
  activeOutputAttachmentId: string | null;
  outputPreviewText: string;
  outputPreviewSavedText: string;
  outputPreviewDirty: boolean;
  outputPreviewSaving: boolean;
  outputPreviewSupported: boolean;
  outputSaveFormat: "txt" | "md";
  activeEntityFilters: Set<string>;
  droppedFilePath: string | null;
  attachedFiles: AttachedInputFile[];
  fileQueue: FileQueueItem[];
  inputAskInstruction: string;
  outputAskInstruction: string;
  inputAskResponse: string;
  outputAskResponse: string;
  inputAskBusy: boolean;
  outputAskBusy: boolean;
  inputAskRequestId: string | null;
  outputAskRequestId: string | null;
  inputAskHistory: Array<{ role: "user" | "assistant"; content: string }>;
  outputAskHistory: Array<{ role: "user" | "assistant"; content: string }>;
  runHistory: RunRevision[];
  historyIndex: number;
  undoStack: UndoSnapshot[];
  activeRequestId: string | null;
  activeRunEntities: string[];
  filePreviewVisible: boolean;
  filePreviewTitle: string;
  filePreviewContent: string;
  filePreviewKind: "text" | "image" | "unsupported";
  filePreviewBadge: string;
  filePreviewObjectUrl: string | null;
  filePreviewCanEdit: boolean;
  filePreviewSegments: OutputSegment[];
  filePreviewHighlightTags: boolean;
  filePreviewEditMode: boolean;
  filePreviewEditBusy: boolean;
  filePreviewEditEntities: string[];
  filePreviewEditTheme: string;
  filePreviewEditStrength: number;
  filePreviewAttachmentId: string | null;
};

export function createWorkbenchState(params: {
  defaultInput: string;
  entityTypes: string[];
}): WorkbenchState {
  return {
    inputText: params.defaultInput,
    outputText: "",
    outputSegments: [],
    outputAttachments: [],
    activeOutputAttachmentId: null,
    outputPreviewText: "",
    outputPreviewSavedText: "",
    outputPreviewDirty: false,
    outputPreviewSaving: false,
    outputPreviewSupported: true,
    outputSaveFormat: "txt",
    activeEntityFilters: new Set(params.entityTypes),
    droppedFilePath: null,
    attachedFiles: [],
    fileQueue: [],
    inputAskInstruction: "",
    outputAskInstruction: "",
    inputAskResponse: "",
    outputAskResponse: "",
    inputAskBusy: false,
    outputAskBusy: false,
    inputAskRequestId: null,
    outputAskRequestId: null,
    inputAskHistory: [],
    outputAskHistory: [],
    runHistory: [],
    historyIndex: -1,
    undoStack: [],
    activeRequestId: null,
    activeRunEntities: [],
    filePreviewVisible: false,
    filePreviewTitle: "",
    filePreviewContent: "",
    filePreviewKind: "text",
    filePreviewBadge: "",
    filePreviewObjectUrl: null,
    filePreviewCanEdit: false,
    filePreviewSegments: [],
    filePreviewHighlightTags: true,
    filePreviewEditMode: false,
    filePreviewEditBusy: false,
    filePreviewEditEntities: [],
    filePreviewEditTheme: "default",
    filePreviewEditStrength: 0.65,
    filePreviewAttachmentId: null,
  };
}

export function createUndoSnapshot(state: {
  inputText: string;
  outputText: string;
  outputSegments: OutputSegment[];
  outputAttachments: OutputAttachment[];
  attachedFiles: AttachedInputFile[];
  activeEntityFilters: Set<string>;
  droppedFilePath: string | null;
  fileQueue: FileQueueItem[];
  config?: RuntimeConfig | null;
  activeProfileName?: string | null;
}): UndoSnapshot {
  return {
    inputText: state.inputText,
    outputText: state.outputText,
    outputSegments: state.outputSegments.map((segment) => ({ ...segment })),
    outputAttachments: state.outputAttachments.map((attachment) => ({
      ...attachment,
    })),
    attachedFiles: state.attachedFiles.map((file) => ({ ...file })),
    activeEntityFilters: [...state.activeEntityFilters],
    droppedFilePath: state.droppedFilePath,
    fileQueue: state.fileQueue.map((row) => ({ ...row })),
    config: state.config ? { ...state.config } : null,
    activeProfileName: state.activeProfileName ?? null,
  };
}

export function restoreUndoSnapshot(snapshot: UndoSnapshot) {
  return {
    inputText: snapshot.inputText,
    outputText: snapshot.outputText,
    outputSegments: snapshot.outputSegments.map((segment) => ({ ...segment })),
    outputAttachments: snapshot.outputAttachments.map((attachment) => ({
      ...attachment,
    })),
    attachedFiles: snapshot.attachedFiles.map((file) => ({ ...file })),
    activeEntityFilters: new Set(snapshot.activeEntityFilters),
    droppedFilePath: snapshot.droppedFilePath,
    fileQueue: snapshot.fileQueue.map((row) => ({ ...row })),
    config: snapshot.config ? { ...snapshot.config } : null,
    activeProfileName: snapshot.activeProfileName,
  };
}

export function captureRunRevision(state: {
  inputText: string;
  outputText: string;
  outputSegments: OutputSegment[];
  droppedFilePath: string | null;
}) {
  return {
    inputText: state.inputText,
    outputText: state.outputText,
    outputSegments: state.outputSegments.map((segment) => ({ ...segment })),
    droppedFilePath: state.droppedFilePath,
    timestamp: new Date().toISOString(),
  } satisfies RunRevision;
}

export function navigateRunHistory(params: {
  runHistory: RunRevision[];
  historyIndex: number;
  direction: "prev" | "next";
}) {
  if (params.runHistory.length < 2) return null;
  const nextIndex =
    params.direction === "prev"
      ? Math.max(0, params.historyIndex - 1)
      : Math.min(params.runHistory.length - 1, params.historyIndex + 1);
  if (nextIndex === params.historyIndex) return null;
  const snapshot = params.runHistory[nextIndex];
  return {
    historyIndex: nextIndex,
    snapshot,
  };
}

export function outputDownloadName(
  droppedFilePath: string | null,
  format: "txt" | "md",
) {
  const extension = format === "md" ? ".md" : ".txt";
  if (!droppedFilePath) return `anonymized-output${extension}`;
  const parts = droppedFilePath.split(/[\\/]/);
  const label = parts[parts.length - 1] || droppedFilePath;
  const lastDot = label.lastIndexOf(".");
  if (lastDot <= 0) return `${label}.anonymized${extension}`;
  return `${label.slice(0, lastDot)}.anonymized${extension}`;
}

export function ensureOutputPreviewSelection(state: {
  activeOutputAttachmentId: string | null;
  outputAttachments: OutputAttachment[];
  outputText: string;
}) {
  const hasActiveAttachment =
    !!state.activeOutputAttachmentId &&
    state.outputAttachments.some((row) => row.id === state.activeOutputAttachmentId);

  let activeOutputAttachmentId = state.activeOutputAttachmentId;
  if (activeOutputAttachmentId && !hasActiveAttachment) {
    activeOutputAttachmentId = null;
  }
  if (!activeOutputAttachmentId && !state.outputText.trim() && state.outputAttachments[0]) {
    activeOutputAttachmentId = state.outputAttachments[0].id;
  }

  const target = resolveActiveOutputPreviewTarget({
    activeOutputAttachmentId,
    outputAttachments: state.outputAttachments,
    outputText: state.outputText,
  });

  return {
    activeOutputAttachmentId,
    target,
  };
}
