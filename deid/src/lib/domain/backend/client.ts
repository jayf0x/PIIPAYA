import { BACKEND_COMMANDS } from "$lib/domain/backend/contract";
import type {
  BackendCommand,
  BackendEnvelope,
  BackendPayload,
} from "$lib/domain/backend/contract";

export type PendingRequest = {
  command: string;
  resolve: (payload: BackendPayload) => void;
  reject: (error: Error) => void;
};

type CreateBackendRequestLifecycleOptions = {
  sendEnvelope: (envelope: BackendEnvelope) => Promise<void>;
  makeId: () => string;
};

export function createBackendRequestLifecycle(
  options: CreateBackendRequestLifecycleOptions,
) {
  const pendingRequests = new Map<string, PendingRequest>();
  const intentionallyCancelledRequests = new Set<string>();

  async function sendEnvelope(
    envelope: BackendEnvelope,
    commandName: string,
    id: string,
  ): Promise<BackendPayload> {
    return new Promise(async (resolve, reject) => {
      pendingRequests.set(id, { command: commandName, resolve, reject });
      try {
        await options.sendEnvelope(envelope);
      } catch (error) {
        pendingRequests.delete(id);
        reject(error as Error);
      }
    });
  }

  async function requestDone(
    command: BackendCommand | string,
    payload: BackendPayload,
  ) {
    const id = options.makeId();
    return sendEnvelope({ id, command, payload }, command, id);
  }

  async function cancelRequest(
    requestId: string,
    options: { ready: boolean; supportsCancelRequest: boolean },
  ) {
    if (!requestId) return;
    intentionallyCancelledRequests.add(requestId);
    if (!options.ready || !options.supportsCancelRequest) return;
    try {
      await requestDone(BACKEND_COMMANDS.cancelRequest, {
        request_id: requestId,
      });
    } catch {
      // Ignore cancellation transport errors.
    }
  }

  function takePending(messageId: string) {
    const pending = pendingRequests.get(messageId);
    if (pending) {
      pendingRequests.delete(messageId);
    }
    return pending;
  }

  return {
    cancelRequest,
    deletePending(id: string) {
      pendingRequests.delete(id);
    },
    hasIntentionalCancellation(messageId: string) {
      return intentionallyCancelledRequests.has(messageId);
    },
    requestDone,
    sendEnvelope,
    takePending,
    clearIntentionalCancellation(messageId: string) {
      intentionallyCancelledRequests.delete(messageId);
    },
  };
}
