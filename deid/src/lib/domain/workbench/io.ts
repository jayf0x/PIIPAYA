import JSZip from "jszip";
import type { OutputAttachment } from "$lib/types/ui";

export function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export async function saveBlobWithPicker(params: {
  blob: Blob;
  filename: string;
  hasTauriBridge: () => boolean;
  saveBinaryDialog: (defaultName: string, bytes: number[]) => Promise<void>;
}) {
  const { blob, filename } = params;
  if (params.hasTauriBridge()) {
    try {
      const bytes = Array.from(new Uint8Array(await blob.arrayBuffer()));
      await params.saveBinaryDialog(filename, bytes);
      return;
    } catch (error) {
      if (String(error).includes("USER_CANCELLED")) return;
    }
  }
  if ("showSaveFilePicker" in window) {
    try {
      const handle = await (
        window as Window & { showSaveFilePicker: Function }
      ).showSaveFilePicker({
        suggestedName: filename,
      });
      const writable = await handle.createWritable();
      await writable.write(blob);
      await writable.close();
      return;
    } catch (error) {
      const code = (error as { name?: string })?.name;
      if (code === "AbortError") return;
    }
  }
  triggerDownload(blob, filename);
}

export function outputAttachmentDownloadName(
  sourceName: string,
  format: "txt" | "md",
) {
  const extension = format === "md" ? ".md" : ".txt";
  const baseName = sourceName.includes(".")
    ? sourceName.slice(0, sourceName.lastIndexOf("."))
    : sourceName;
  return `${baseName}.anonymized${extension}`;
}

export async function buildExportZipBlob(params: {
  mainName: string;
  outputText: string;
  attachments: OutputAttachment[];
}) {
  const zip = new JSZip();
  zip.file(params.mainName, params.outputText);
  for (const attachment of params.attachments) {
    const filename = attachment.name.trim() || "attachment.txt";
    zip.file(filename, attachment.text);
  }
  return zip.generateAsync({ type: "blob" });
}
