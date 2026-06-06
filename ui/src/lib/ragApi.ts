import { BASE } from "@/config";


export interface DocOut {
  id: number;
  title: string;
  status: "completed" | "failed" | "processing";
  chunk_count: number;
  file_size: string | null;
  created_at: string;
}

export interface UploadOut {
  id: number;
  title: string;
  status: string;
  message: string;
}

export interface SearchResult {
  text: string;
  score: number;
  meta: Record<string, unknown>;
}

export interface SearchOut {
  query: string;
  results: SearchResult[];
  source: string;
}

// GET /rag/
export async function fetchDocs(): Promise<DocOut[]> {
  const res = await fetch(`${BASE}/`);
  if (!res.ok) throw new Error("Không thể tải danh sách tài liệu");
  return res.json();
}

// POST /rag/upload/
export async function uploadDoc(title: string, file: File): Promise<UploadOut> {
  const form = new FormData();
  form.append("title", title);
  form.append("file", file);
  const res = await fetch(`${BASE}/upload/`, { method: "POST", body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Upload thất bại");
  }
  return res.json();
}

// POST /rag/search/
export async function searchDocs(query: string, top_k = 3): Promise<SearchOut> {
  const form = new FormData();
  form.append("query", query);
  form.append("top_k", String(top_k));
  const res = await fetch(`${BASE}/search/`, { method: "POST", body: form });
  if (!res.ok) throw new Error("Tìm kiếm thất bại");
  return res.json();
}

// DELETE /rag/{doc_id}/
export async function deleteDoc(id: number): Promise<void> {
  const res = await fetch(`${BASE}/${id}/`, { method: "DELETE" });
  if (!res.ok) throw new Error("Xóa thất bại");
}