import { inferPreviewKind, supportsOutputPreview } from "$lib/domain/policies/fileCapabilities";
import type { OutputAttachment } from "$lib/types/ui";

export type OutputPreviewTarget = {
  id: string;
  text: string;
  supported: boolean;
  kind: "text" | "unsupported";
};

export function resolveActiveOutputPreviewTarget(params: {
  activeOutputAttachmentId: string | null;
  outputAttachments: OutputAttachment[];
  outputText: string;
}) {
  const { activeOutputAttachmentId, outputAttachments, outputText } = params;
  if (activeOutputAttachmentId) {
    const attachment = outputAttachments.find(
      (row) => row.id === activeOutputAttachmentId,
    );
    if (attachment) {
      const supported = supportsOutputPreview(attachment.name);
      return {
        id: attachment.id,
        text: attachment.text,
        supported,
        kind: supported ? "text" : "unsupported",
      } as const;
    }
  }
  if (outputText.trim().length > 0) {
    return {
      id: "main",
      text: outputText,
      supported: true,
      kind: "text",
    } as const;
  }
  const firstAttachment = outputAttachments[0];
  if (!firstAttachment) return null;
  const supported = supportsOutputPreview(firstAttachment.name);
  return {
    id: firstAttachment.id,
    text: firstAttachment.text,
    supported,
    kind: supported ? "text" : "unsupported",
  } as const;
}

export function createOutputPreviewDiffController() {
  let timer: ReturnType<typeof setTimeout> | null = null;

  function clear() {
    if (!timer) return;
    clearTimeout(timer);
    timer = null;
  }

  function queue(params: {
    nextText: string;
    setText: (text: string) => void;
    getText: () => string;
    getSavedText: () => string;
    setDirty: (dirty: boolean) => void;
  }) {
    params.setText(params.nextText);
    clear();
    timer = setTimeout(() => {
      params.setDirty(params.getText() !== params.getSavedText());
      timer = null;
    }, 700);
  }

  return {
    clear,
    queue,
  };
}

export { inferPreviewKind };
