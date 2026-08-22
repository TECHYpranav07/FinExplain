export interface DocRecord {
  id: string;
  name: string;
  productId: string;
  productName: string;
  uploadedAt: string;
  status: "processed" | "processing" | "failed" | "indexed";
  chunks: number;
  sizeBytes?: number;
  message?: string;
}

export const STORAGE_KEY = "finexplain_documents";

export function listDocuments(): DocRecord[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return [];
    }
    return JSON.parse(raw);
  } catch {
    return [];
  }
}

export function getDocument(id: string): DocRecord | undefined {
  const docs = listDocuments();
  return docs.find((d) => d.id === id);
}

export function saveDocument(doc: DocRecord): void {
  try {
    const docs = listDocuments();
    const existingIndex = docs.findIndex((d) => d.id === doc.id);
    if (existingIndex >= 0) {
      docs[existingIndex] = doc;
    } else {
      docs.unshift(doc);
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(docs));
  } catch (err) {
    console.error("Failed to save document record to localStorage:", err);
  }
}

export function removeDocument(id: string): void {
  try {
    const docs = listDocuments().filter((d) => d.id !== id);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(docs));
  } catch (err) {
    console.error("Failed to remove document record from localStorage:", err);
  }
}

export function formatBytes(bytes?: number): string {
  if (!bytes || bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}
