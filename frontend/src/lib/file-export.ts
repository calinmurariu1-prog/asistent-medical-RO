import { Capacitor } from "@capacitor/core";

const ROOT = "medical-exports";
const RETENTION_MS = 24 * 60 * 60 * 1000;
let exporting = false;

export async function saveExport(blob: Blob, filename: string): Promise<string> {
  if (exporting) throw new Error("Un export este deja în curs.");
  exporting = true;
  try {
    if (!Capacitor.isNativePlatform()) {
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      try {
        link.href = url; link.download = filename;
        document.body.appendChild(link); link.click();
      } finally {
        link.remove(); setTimeout(() => URL.revokeObjectURL(url), 30_000);
      }
      return "Descărcarea a fost inițiată. Verifică fișierele descărcate în browser.";
    }
    if (blob.size > 25 * 1024 * 1024) {
      throw new Error("Exportul depășește 25 MB. Descarcă-l din versiunea web.");
    }
    try {
    const { Filesystem, Directory } = await import("@capacitor/filesystem");
    const { Share } = await import("@capacitor/share");
    if (!(await Share.canShare()).value) throw new Error("Dialogul de partajare nu este disponibil.");
    // A fixed private cache directory; never accept a caller-provided path.
    try {
      await Filesystem.mkdir({ path: ROOT, directory: Directory.Cache, recursive: true });
    } catch { /* Existing directory is verified by readdir below. */ }
    const entries = await Filesystem.readdir({ path: ROOT, directory: Directory.Cache });
    for (const entry of entries.files) {
      if (/^\d{13}-[0-9a-f-]{36}$/.test(entry.name) &&
          Date.now() - Number(entry.name.slice(0, 13)) > RETENTION_MS) {
        await Filesystem.rmdir({ path: `${ROOT}/${entry.name}`, directory: Directory.Cache, recursive: true });
      }
    }
    const folder = `${ROOT}/${Date.now()}-${crypto.randomUUID()}`;
    const extension = filename.match(/\.([a-zA-Z0-9]{1,8})$/)?.[1]?.toLowerCase() || "bin";
    const path = `${folder}/export.${extension}`;
    const bytes = new Uint8Array(await blob.arrayBuffer());
    let binary = "";
    for (let offset = 0; offset < bytes.length; offset += 8192) {
      binary += String.fromCharCode(...bytes.subarray(offset, offset + 8192));
    }
    const written = await Filesystem.writeFile({ path, directory: Directory.Cache,
      data: btoa(binary), recursive: true });
    // The recipient may read after the chooser resolves; do not delete immediately.
    await Share.share({ title: "Export dosar medical", dialogTitle: "Salvează sau partajează exportul",
      files: [written.uri] });
    return "Dialogul sistemului s-a închis. Verifică destinația aleasă; salvarea nu este confirmată de aplicație.";
    } catch {
      throw new Error("Exportul nativ nu a fost confirmat. Dacă ai anulat dialogul, poți reîncerca.");
    }
  } finally { exporting = false; }
}
