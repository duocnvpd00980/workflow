"use client";

import { useState, useRef, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { MenuIcon, UploadCloud, Globe, Search, FileText, Link2, Trash2, Database, ShieldCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { toast } from "sonner";
import { createFileRoute } from "@tanstack/react-router";
import SidebarNav from "@/layout/navbar";

// ─── Types ────────────────────────────────────────────────
interface DocOut {
  id: number;
  title: string;
  status: "completed" | "failed" | "processing";
  chunk_count: number;
  file_size: string | null;
  created_at: string;
}

// ─── API (inline) ─────────────────────────────────────────
const BASE = "http://localhost:8000/api/v1/rag";

const api = {
  list: (): Promise<DocOut[]> =>
    fetch(`${BASE}/`).then((r) => {
      if (!r.ok) throw new Error("Lỗi tải danh sách");
      return r.json();
    }),

  upload: async (title: string, file: File) => {
    const form = new FormData();
    form.append("title", title);
    form.append("file", file);
    const r = await fetch(`${BASE}/upload/`, { method: "POST", body: form });
    if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.detail ?? "Upload thất bại"); }
    return r.json();
  },

  // POST /rag/crawl/ — body JSON { url, title }
  crawl: async (url: string) => {
    const r = await fetch(`${BASE}/crawl/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, title: url }),
    });
    if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.detail ?? "Crawl thất bại"); }
    return r.json();
  },

  delete: async (id: number) => {
    const r = await fetch(`${BASE}/${id}/`, { method: "DELETE" });
    if (!r.ok) throw new Error("Xóa thất bại");
  },
};

// ─── Helpers ──────────────────────────────────────────────
const isUrl = (s: string) => /^https?:\/\/.+/.test(s.trim());

const STATUS_BADGE: Record<DocOut["status"], React.ReactNode> = {
  completed:  <Badge className="bg-indigo-50 text-indigo-700 border-none text-[10px]">Đã vector hóa</Badge>,
  processing: <Badge className="bg-amber-50 text-amber-700 border-none text-[10px] animate-pulse">Đang xử lý…</Badge>,
  failed:     <Badge className="bg-rose-50 text-rose-700 border-none text-[10px]">Thất bại</Badge>,
};

export const Route = createFileRoute("/knowledge")({ component: KnowledgePage });

export default function KnowledgePage() {
  const qc      = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);

  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [search, setSearch]           = useState("");
  const [selectedId, setSelectedId]   = useState<number | null>(null);
  const [urlInput, setUrlInput]       = useState("");

  // ── GET /rag/ ─────────────────────────────────────────
  const { data: docs = [], isLoading } = useQuery({
    queryKey: ["rag-docs"],
    queryFn: api.list,
    refetchInterval: 5_000,
  });

  // ── POST /rag/upload/ ─────────────────────────────────
  const uploadMutation = useMutation({
    mutationFn: ({ title, file }: { title: string; file: File }) => api.upload(title, file),
    onSuccess: (data) => {
      toast.success(`"${data.title}" đã được ingest!`);
      qc.invalidateQueries({ queryKey: ["rag-docs"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  // ── POST /rag/crawl/ ──────────────────────────────────
  const crawlMutation = useMutation({
    mutationFn: (url: string) => api.crawl(url),
    onSuccess: (data) => {
      toast.success(`Đã crawl: "${data.title}"`);
      setUrlInput("");
      qc.invalidateQueries({ queryKey: ["rag-docs"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  // ── DELETE /rag/{id}/ ─────────────────────────────────
  const deleteMutation = useMutation({
    mutationFn: api.delete,
    onMutate: async (id) => {
      await qc.cancelQueries({ queryKey: ["rag-docs"] });
      const prev = qc.getQueryData<DocOut[]>(["rag-docs"]);
      qc.setQueryData<DocOut[]>(["rag-docs"], (old = []) => old.filter((d) => d.id !== id));
      return { prev };
    },
    onError: (_e, _id, ctx) => {
      qc.setQueryData(["rag-docs"], ctx?.prev);
      toast.error("Xóa thất bại.");
    },
    onSuccess: () => toast.success("Đã xóa tài liệu."),
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    uploadMutation.mutate({ title: file.name, file });
    e.target.value = "";
  };

  const handleCrawl = () => {
    const url = urlInput.trim();
    if (!url) return;
    if (!isUrl(url)) { toast.error("URL không hợp lệ (phải bắt đầu bằng http:// hoặc https://)"); return; }
    crawlMutation.mutate(url);
  };

  const filtered = useMemo(
    () => docs.filter((d) => d.title.toLowerCase().includes(search.toLowerCase())),
    [docs, search],
  );

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-50 text-slate-900 antialiased font-sans select-none">

      {/* Sidebar trái */}
      <aside className={`fixed inset-y-0 left-0 z-30 flex w-[240px] flex-col border-r bg-white transition-transform duration-200 md:relative md:translate-x-0 ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}`}>
        <SidebarNav />
        <div className="p-3 mt-auto border-t space-y-2">
          <p className="text-[9px] font-bold text-slate-400 uppercase tracking-wider px-1">Vector DB</p>
          <div className="p-2.5 rounded-lg border border-indigo-100 bg-indigo-50/30 text-[11px] space-y-0.5">
            <div className="flex items-center justify-between font-semibold text-slate-700">
              <span className="flex items-center gap-1"><Database size={11} className="text-indigo-500" /> Pinecone</span>
              <span className="text-indigo-600 font-mono">Active</span>
            </div>
            <p className="text-slate-400">24,105 vectors • 12ms latency</p>
          </div>
        </div>
        <div className="border-t p-3 flex items-center gap-2 bg-slate-50/50 shrink-0">
          <div className="h-7 w-7 rounded-full bg-indigo-100 text-indigo-700 text-[11px] font-bold flex items-center justify-center shrink-0">TH</div>
          <span className="text-[13px] font-medium text-slate-700">Thành</span>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden">

        {/* Header */}
        <header className="h-13 bg-white border-b flex items-center gap-3 px-5 shrink-0">
          <button onClick={() => setSidebarOpen(true)} className="md:hidden p-1 rounded hover:bg-slate-100 text-slate-500">
            <MenuIcon size={18} />
          </button>
          <h2 className="font-bold text-[14px] text-slate-800">Cơ sở tri thức (RAG)</h2>
          <Separator orientation="vertical" className="h-4" />
          <span className="text-[11px] text-slate-400 hidden sm:block">Dữ liệu nguồn để Agent tra cứu ngữ cảnh</span>
        </header>

        {/* Toolbar: Upload + Crawl URL + Search */}
        <div className="flex flex-wrap items-center gap-2 px-5 py-3 bg-white border-b shrink-0">

          {/* Upload file */}
          <input ref={fileRef} type="file" accept=".pdf,.docx,.txt,.csv,.xlsx,.md" className="hidden" onChange={handleFileChange} />
          <Button
            size="sm"
            onClick={() => fileRef.current?.click()}
            disabled={uploadMutation.isPending}
            className="gap-1.5 bg-indigo-600 hover:bg-indigo-700 text-white h-8 text-[12px] shrink-0"
          >
            <UploadCloud size={14} />
            {uploadMutation.isPending ? "Đang tải…" : "Tải file"}
          </Button>

          <Separator orientation="vertical" className="h-5 hidden sm:block" />

          {/* Crawl URL */}
          <div className="flex items-center gap-2 flex-1 min-w-[240px] max-w-sm">
            <div className="relative flex-1">
              <Globe size={13} className="absolute left-2.5 top-[9px] text-slate-400" />
              <Input
                value={urlInput}
                onChange={(e) => setUrlInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleCrawl()}
                placeholder="https://example.com/docs"
                className="pl-7 h-8 text-[12px] bg-slate-50 border-slate-200"
                disabled={crawlMutation.isPending}
              />
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={handleCrawl}
              disabled={crawlMutation.isPending || !urlInput.trim()}
              className="h-8 text-[12px] shrink-0 gap-1"
            >
              {crawlMutation.isPending ? "Đang crawl…" : "Crawl"}
            </Button>
          </div>

          {/* Search docs */}
          <div className="relative ml-auto">
            <Search className="absolute left-2.5 top-2 h-3.5 w-3.5 text-slate-400" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Tìm tài liệu..."
              className="pl-8 h-8 text-[12px] bg-slate-50 border-slate-200 w-44"
            />
          </div>

          <span className="text-[11px] text-slate-400 shrink-0">{filtered.length} tài liệu</span>
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto p-4">
          <div className="max-w-[800px] mx-auto bg-white rounded-xl border border-slate-100 divide-y divide-slate-100 overflow-hidden">

            {isLoading && (
              <div className="p-10 text-center text-[12px] text-slate-400 animate-pulse">Đang tải…</div>
            )}

            {!isLoading && filtered.length === 0 && (
              <div className="p-10 text-center text-[12px] text-slate-400">
                Chưa có tài liệu nào. Tải file hoặc nhập URL để bắt đầu!
              </div>
            )}

            {filtered.map((doc) => {
              const isWeb = doc.title.startsWith("http");
              return (
                <div
                  key={doc.id}
                  onClick={() => setSelectedId(doc.id)}
                  className={`flex items-center gap-3 px-4 py-3 cursor-pointer transition-colors hover:bg-slate-50 ${selectedId === doc.id ? "bg-indigo-50/40" : ""}`}
                >
                  {/* Icon: web hoặc file */}
                  <div className={`p-1.5 rounded-lg shrink-0 ${isWeb ? "bg-emerald-50 text-emerald-600" : "bg-blue-50 text-blue-600"}`}>
                    {isWeb ? <Link2 size={15} /> : <FileText size={15} />}
                  </div>

                  <div className="flex-1 min-w-0">
                    <p className="text-[12.5px] font-semibold text-slate-800 truncate">{doc.title}</p>
                    <p className="text-[10px] text-slate-400 mt-0.5">
                      #{doc.id}
                      {doc.file_size && <> • {doc.file_size}</>}
                      {doc.status === "completed" && <> • {doc.chunk_count} đoạn</>}
                      {" • "}{new Date(doc.created_at).toLocaleDateString("vi-VN")}
                    </p>
                  </div>

                  <div className="shrink-0">{STATUS_BADGE[doc.status]}</div>

                  <button
                    onClick={(e) => { e.stopPropagation(); deleteMutation.mutate(doc.id); }}
                    disabled={deleteMutation.isPending}
                    className="p-1 rounded hover:bg-rose-50 text-slate-300 hover:text-rose-500 transition-colors shrink-0 disabled:opacity-40"
                    title="Xóa"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              );
            })}
          </div>
        </div>

        {/* Footer */}
        <div className="shrink-0 border-t bg-white px-5 py-2 flex items-center gap-2">
          <ShieldCheck size={12} className="text-emerald-500 shrink-0" />
          <p className="text-[10px] text-slate-400">Tài liệu được lưu trữ Private Cloud — không dùng cho training công khai.</p>
        </div>
      </main>

    </div>
  );
}