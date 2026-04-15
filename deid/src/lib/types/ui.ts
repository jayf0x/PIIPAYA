export type LogType = "engine" | "system";

export type OutputSegment = {
  text: string;
  entity_type: string | null;
  replaced: boolean;
};

export type SpacyModelInfo = {
  name: string;
  installed: boolean;
  active: boolean;
};

export type OllamaModelInfo = {
  name: string;
  active: boolean;
};

export type OllamaTurn = {
  role: "user" | "assistant";
  content: string;
};

export type EntityFilter = {
  key: string;
  label: string;
  entity: string;
  color: string;
  textColor: string;
  dataType: string;
};

export type AttachedInputFile = {
  id: string;
  name: string;
  path: string | null;
  file: File | null;
};

export type FileQueueStatus =
  | "queued"
  | "processing"
  | "done"
  | "failed"
  | "unsupported";

export type FileQueueItem = {
  id: string;
  name: string;
  status: FileQueueStatus;
  progressPct: number;
  detail: string;
};

export type OutputAttachment = {
  id: string;
  name: string;
  text: string;
  segments?: OutputSegment[];
  sourceText?: string | null;
  enabledEntities?: string[];
  editTheme?: string | null;
  editStrength?: number | null;
};

export type LogEntry = {
  type: LogType;
  message: string;
  pct: number;
  timestamp: string;
};
