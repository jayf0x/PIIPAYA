import {
  BACKEND_COMMANDS,
  type BackendEnvelope,
  type BackendPayload,
  type RuntimeConfig,
} from "$lib/domain/backend/contract";
import type { OllamaModelInfo, OllamaTurn } from "$lib/types/ui";

export type AskTarget = "input" | "output";

export function availableOllamaModels(params: {
  askModel: string;
  config: RuntimeConfig;
  ollamaModels: OllamaModelInfo[];
}) {
  const names = new Set<string>();
  for (const row of params.ollamaModels) {
    if (row.name.trim()) names.add(row.name.trim());
  }
  const configModel = String(params.config.ollama_model ?? "").trim();
  if (configModel) names.add(configModel);
  if (params.askModel.trim()) names.add(params.askModel.trim());
  if (names.size === 0) names.add("qwen3.5:9b");
  return Array.from(names);
}

export function estimateAskTokens(params: {
  inputAskInstruction: string;
  outputAskInstruction: string;
  inputText: string;
  outputText: string;
  target: AskTarget;
}) {
  const instruction =
    params.target === "input"
      ? params.inputAskInstruction
      : params.outputAskInstruction;
  const current = params.target === "input" ? params.inputText : params.outputText;
  const other = params.target === "input" ? params.outputText : params.inputText;
  const roughChars = instruction.length + current.length + other.length;
  return Math.max(1, Math.round(roughChars / 4));
}

export async function runAskAssistRequest(params: {
  askModel: string;
  cancelRequest: (requestId: string) => void;
  currentText: string;
  history: OllamaTurn[];
  instruction: string;
  makeId: () => string;
  otherText: string;
  previousRequestId: string | null;
  sendEnvelope: (
    envelope: BackendEnvelope,
    commandName: string,
    id: string,
  ) => Promise<BackendPayload>;
  target: AskTarget;
}) {
  const id = params.makeId();
  if (params.previousRequestId) {
    params.cancelRequest(params.previousRequestId);
  }

  const payload = {
    target: params.target,
    instruction: params.instruction,
    current_text: params.currentText,
    other_text: params.otherText,
    history: params.history,
    model: params.askModel,
  };
  const donePayload = await params.sendEnvelope(
    { id, command: BACKEND_COMMANDS.askOllama, payload },
    BACKEND_COMMANDS.askOllama,
    id,
  );
  const finalResponse = String(donePayload.response ?? "");
  const nextHistory: OllamaTurn[] = [
    ...params.history,
    { role: "user", content: params.instruction },
    { role: "assistant", content: finalResponse },
  ];

  return {
    finalResponse,
    id,
    nextHistory,
  };
}
