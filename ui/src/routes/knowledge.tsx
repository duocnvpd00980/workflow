"use client";

import { useState, useRef, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  UploadCloud,
  Globe,
  Search,
  FileText,
  Link2,
  Trash2,
  ShieldCheck,
  Loader2,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { toast } from "sonner";
import { createFileRoute } from "@tanstack/react-router";
import { BASE } from "@/config";
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
    if (!r.ok) {
      const e = await r.json().catch(() => ({}));
      throw new Error(e.detail ?? "Upload thất bại");
    }
    return r.json();
  },

  crawl: async (url: string) => {
    const r = await fetch(`${BASE}/crawl/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, title: url }),
    });
    if (!r.ok) {
      const e = await r.json().catch(() => ({}));
      throw new Error(e.detail ?? "Crawl thất bại");
    }
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
  completed: (
    <Badge className="bg-emerald-50 text-emerald-700 border-none text-[10px]">
      Sẵn sàng
    </Badge>
  ),
  processing: (
    <Badge className="bg-amber-50 text-amber-700 border-none text-[10px] animate-pulse">
      Đang xử lý
    </Badge>
  ),
  failed: (
    <Badge className="bg-rose-50 text-rose-700 border-none text-[10px]">
      Lỗi
    </Badge>
  ),
};

const formatDate = (dateStr: string) => {
  const date = new Date(dateStr);
  const day = String(date.getDate()).padStart(2, "0");
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const year = date.getFullYear();
  return `${day}/${month}/${year}`;
};

export const Route = createFileRoute("/knowledge")({
  component: KnowledgePage,
});

export default function KnowledgePage() {
  const qc = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);

  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [urlInput, setUrlInput] = useState("");
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteDocId, setDeleteDocId] = useState<number | null>(null);

  // ── GET /rag/ ─────────────────────────────────────────
  const { data: docs = [], isLoading } = useQuery({
    queryKey: ["rag-docs"],
    queryFn: api.list,
    refetchInterval: 5_000,
  });

  // ── POST /rag/upload/ ─────────────────────────────────
  const uploadMutation = useMutation({
    mutationFn: ({ title, file }: { title: string; file: File }) =>
      api.upload(title, file),
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
      qc.setQueryData<DocOut[]>(["rag-docs"], (old = []) =>
        old.filter((d) => d.id !== id)
      );
      return { prev };
    },
    onError: (_e, _id, ctx) => {
      qc.setQueryData(["rag-docs"], ctx?.prev);
      toast.error("Xóa thất bại");
    },
    onSuccess: () => {
      toast.success("Đã xóa tài liệu");
      setDeleteDialogOpen(false);
      setDeleteDocId(null);
    },
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
    if (!isUrl(url)) {
      return;
    }
    crawlMutation.mutate(url);
  };

  const handleDeleteClick = (id: number) => {
    setDeleteDocId(id);
    setDeleteDialogOpen(true);
  };

  const handleConfirmDelete = () => {
    if (deleteDocId !== null) {
      deleteMutation.mutate(deleteDocId);
    }
  };

  const urlError = urlInput.trim() !== "" && !isUrl(urlInput);

  const filtered = useMemo(
    () =>
      docs.filter((d) =>
        d.title.toLowerCase().includes(search.toLowerCase())
      ),
    [docs, search]
  );

  const isEmpty = !isLoading && filtered.length === 0;

  return (
    <div className="flex flex-col h-full bg-white">
      {/* ─── TOOLBAR (56px, fixed) ───────────────────────────── */}
      <div className="h-14 border-b border-slate-200 flex items-center gap-2 px-4 shrink-0 bg-white">
        {/* Upload Button */}
        <input
          ref={fileRef}
          type="file"
          accept=".pdf,.docx,.txt,.csv,.xlsx,.md"
          className="hidden"
          onChange={handleFileChange}
        />
        <Button
          size="sm"
          onClick={() => fileRef.current?.click()}
          disabled={uploadMutation.isPending}
          className="gap-1.5 h-8 text-xs bg-indigo-600 hover:bg-indigo-700 shrink-0"
        >
          {uploadMutation.isPending ? (
            <Loader2 size={13} className="animate-spin" />
          ) : (
            <UploadCloud size={13} />
          )}
          <span className="hidden sm:inline">Tải file</span>
        </Button>

        {/* Separator */}
        <div className="h-4 w-px bg-slate-200 hidden sm:block" />

        {/* URL Input + Crawl */}
        <div className="flex-1 hidden sm:flex items-start gap-2 min-w-0 max-w-sm">
          <div className="relative flex-1">
            <Globe
              size={13}
              className="absolute left-2 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none"
            />
            <Input
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleCrawl()}
              placeholder="https://example.com"
              className={`pl-7 h-8 text-xs bg-slate-50 border-slate-200 ${
                urlError ? "border-rose-500 bg-rose-50" : ""
              }`}
              disabled={crawlMutation.isPending}
            />
            {urlError && (
              <p className="text-[10px] text-rose-600 mt-0.5">
                URL không hợp lệ (http:// hoặc https://)
              </p>
            )}
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={handleCrawl}
            disabled={crawlMutation.isPending || !urlInput.trim() || urlError}
            className="h-8 text-xs shrink-0 gap-1 mt-0"
          >
            {crawlMutation.isPending ? (
              <Loader2 size={13} className="animate-spin" />
            ) : (
              <Globe size={13} />
            )}
            <span className="hidden md:inline">Crawl</span>
          </Button>
        </div>

        {/* Mobile URL Button (only on mobile) */}
        <Button
          size="sm"
          variant="ghost"
          className="h-8 w-8 p-0 sm:hidden text-slate-600 hover:bg-slate-100 shrink-0"
          title="Import URL"
        >
          <Globe size={16} />
        </Button>

        {/* Spacer */}
        <div className="flex-1 hidden sm:block" />

        {/* Search Input */}
        <div className="relative w-44 hidden sm:block">
          <Search
            size={13}
            className="absolute left-2 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none"
          />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Tìm kiếm…"
            className="pl-7 h-8 text-xs bg-slate-50 border-slate-200"
          />
        </div>

        {/* Mobile Search Button */}
        <Button
          size="sm"
          variant="ghost"
          className="h-8 w-8 p-0 sm:hidden text-slate-600 hover:bg-slate-100 shrink-0"
          title="Tìm kiếm"
        >
          <Search size={16} />
        </Button>

        {/* Count */}
        <span className="text-xs font-medium text-slate-500 shrink-0 ml-2">
          Tài liệu ({filtered.length})
        </span>
      </div>

      {/* ─── MOBILE TOOLBAR (only on mobile) ─────────────────── */}
      <div className="sm:hidden flex flex-col gap-2 px-4 py-2 border-b border-slate-200 bg-white shrink-0">
        {/* URL Input Row */}
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <div className="relative flex-1">
              <Globe
                size={13}
                className="absolute left-2 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none"
              />
              <Input
                value={urlInput}
                onChange={(e) => setUrlInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleCrawl()}
                placeholder="https://example.com"
                className={`pl-7 h-8 text-xs bg-slate-50 border-slate-200 ${
                  urlError ? "border-rose-500 bg-rose-50" : ""
                }`}
                disabled={crawlMutation.isPending}
              />
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={handleCrawl}
              disabled={crawlMutation.isPending || !urlInput.trim() || urlError}
              className="h-8 text-xs shrink-0"
            >
              {crawlMutation.isPending ? (
                <Loader2 size={13} className="animate-spin" />
              ) : (
                "Crawl"
              )}
            </Button>
          </div>
          {urlError && (
            <p className="text-[10px] text-rose-600">
              URL không hợp lệ (http:// hoặc https://)
            </p>
          )}
        </div>

        {/* Search Row */}
        <div className="relative">
          <Search
            size={13}
            className="absolute left-2 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none"
          />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Tìm kiếm…"
            className="pl-7 h-8 text-xs bg-slate-50 border-slate-200 w-full"
          />
        </div>
      </div>

      {/* ─── CONTENT ──────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto w-full px-4 py-4 max-w-[1100px]">
          {/* Empty State */}
          {isEmpty && (
            <div className="flex flex-col items-center justify-center text-center py-12">
              <div className="h-12 w-12 rounded-lg bg-slate-100 flex items-center justify-center mb-3 mx-auto">
                <UploadCloud size={20} className="text-slate-400" />
              </div>
              <h3 className="text-sm font-medium text-slate-900 mb-1">
                Chưa có tài liệu nào
              </h3>
              <p className="text-xs text-slate-500 mb-4 max-w-xs">
                Tải file hoặc nhập URL để xây dựng cơ sở tri thức
              </p>
              <Button
                size="sm"
                onClick={() => fileRef.current?.click()}
                className="gap-1 h-8 text-xs bg-indigo-600 hover:bg-indigo-700"
              >
                <UploadCloud size={13} />
                Tải file
              </Button>
            </div>
          )}

          {/* Loading Skeleton */}
          {isLoading && (
            <div className="space-y-2">
              {[1, 2, 3, 4, 5].map((i) => (
                <div
                  key={i}
                  className="h-16 bg-slate-100 rounded-lg animate-pulse"
                />
              ))}
            </div>
          )}

          {/* Document List */}
          {!isLoading && filtered.length > 0 && (
            <div className="divide-y divide-slate-200 border border-slate-200 rounded-lg overflow-hidden bg-white">
              {filtered.map((doc) => {
                const isWeb = doc.title.startsWith("http");
                return (
                  <div
                    key={doc.id}
                    onClick={() => setSelectedId(doc.id)}
                    className={`flex items-center gap-3 px-4 py-3 cursor-pointer transition-colors ${
                      selectedId === doc.id
                        ? "bg-indigo-50/50"
                        : "hover:bg-slate-50/50"
                    }`}
                  >
                    {/* Icon */}
                    <div
                      className={`p-1.5 rounded shrink-0 ${
                        isWeb
                          ? "bg-emerald-50 text-emerald-600"
                          : "bg-blue-50 text-blue-600"
                      }`}
                    >
                      {isWeb ? <Link2 size={16} /> : <FileText size={16} />}
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-slate-900 truncate">
                        {doc.title}
                      </p>
                      <div className="flex items-center gap-1.5 mt-0.5 text-xs text-slate-500 line-clamp-1">
                        <span>#{doc.id}</span>
                        {doc.file_size && (
                          <>
                            <span>•</span>
                            <span>{doc.file_size}</span>
                          </>
                        )}
                        {doc.status === "completed" && (
                          <>
                            <span>•</span>
                            <span>{doc.chunk_count} đoạn</span>
                          </>
                        )}
                        <span>•</span>
                        <span>Tạo: {formatDate(doc.created_at)}</span>
                      </div>
                    </div>

                    {/* Status */}
                    <div className="shrink-0 hidden sm:block">
                      {STATUS_BADGE[doc.status]}
                    </div>

                    {/* Delete */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteClick(doc.id);
                      }}
                      disabled={deleteMutation.isPending}
                      className="h-11 w-11 flex items-center justify-center rounded hover:bg-rose-50 text-slate-300 hover:text-rose-500 transition-colors shrink-0 disabled:opacity-50"
                      aria-label="Xóa tài liệu"
                      title="Xóa"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                );
              })}
            </div>
          )}

          {/* Privacy Notice */}
          {!isEmpty && (
            <div className="flex items-start gap-2 text-xs text-slate-500 mt-4 pt-4 border-t border-slate-200">
              <ShieldCheck size={14} className="mt-px shrink-0 text-emerald-600" />
              <span>
                Tài liệu được lưu trữ Private Cloud — không dùng cho training
                công khai
              </span>
            </div>
          )}
        </div>
      </div>

      {/* ─── DELETE CONFIRM DIALOG ────────────────────────────── */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogTitle>Xóa tài liệu?</AlertDialogTitle>
          <AlertDialogDescription>
            Hành động này không thể hoàn tác. Tài liệu sẽ bị xóa vĩnh viễn khỏi
            cơ sở tri thức.
          </AlertDialogDescription>
          <div className="flex gap-2 justify-end pt-4">
            <AlertDialogCancel className="h-8">Hủy</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmDelete}
              disabled={deleteMutation.isPending}
              className="h-8 bg-rose-600 hover:bg-rose-700"
            >
              {deleteMutation.isPending ? "Đang xóa…" : "Xóa"}
            </AlertDialogAction>
          </div>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}