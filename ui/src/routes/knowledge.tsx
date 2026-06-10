"use client";

import { useState, useRef, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  UploadCloud,
  Globe,
  Search,
  Trash2,
  ShieldCheck,
  Loader2,
  Book,
  Palette,
  BarChart3,
  Sparkles,
  ChevronRight,
  X,
  ExternalLink,
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
import { MarkdownRenderer } from "@/components/ui/markdown-renderer";
import { useNavigate } from "@tanstack/react-router";


// ─── Types ────────────────────────────────────────────────
interface DocOut {
  id: number;
  title: string;
  status: "completed" | "failed" | "processing";
  document_type: string;
  chunk_count: number;
  file_size: string | null;
  created_at: string;
}

interface PageSummary {
  id: number;
  url: string;
  title: string;
  created_at: string;
}

interface PageDetail {
  id: number;
  document_id: number;
  url: string;
  title: string;
  content: string | null;
  extracted: {
    identity?: {
      brand_name?: string;
      description?: string;
      mission?: string;
      vision?: string;
      story?: string;
      values?: string[];
      strengths?: string[];
      tone?: string[];
    };
    brand_pages?: string[];
    rag_text?: string;
    word_count?: number;
  } | null;
  created_at: string;
}

// ─── Constants ────────────────────────────────────────────
const DOC_TYPE_META: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  product_knowledge: {
    label: "Sản phẩm & dịch vụ",
    color: "bg-blue-50 text-blue-600",
    icon: <Book size={14} />,
  },
  brand: {
    label: "Thương hiệu",
    color: "bg-violet-50 text-violet-600",
    icon: <Sparkles size={14} />,
  },

};

// ─── API ──────────────────────────────────────────────────
const api = {
  list: (): Promise<DocOut[]> =>
    fetch(`${BASE}/`).then((r) => {
      if (!r.ok) throw new Error("Lỗi tải danh sách");
      return r.json();
    }),

  upload: async (title: string, file: File, document_type: string) => {
    const form = new FormData();
    form.append("title", title);
    form.append("file", file);
    form.append("document_type", document_type);
    const r = await fetch(`${BASE}/upload/`, { method: "POST", body: form });
    if (!r.ok) {
      const e = await r.json().catch(() => ({}));
      throw new Error(e.detail ?? "Upload thất bại");
    }
    return r.json();
  },

  crawl: async (url: string, docType: string) => {
    const r = await fetch(`${BASE}/crawl/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, title: url, document_type: docType }),
    });
    if (!r.ok) {
      const e = await r.json().catch(() => ({}));
      throw new Error(e.detail ?? "Crawl thất bại");
    }
    return r.json();
  },

  crawlBusiness: async (url: string) => {
    const r = await fetch(`${BASE}/crawl-business/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, title: url, document_type: "brand" }),
    });
    if (!r.ok) {
      const e = await r.json().catch(() => ({}));
      throw new Error(e.detail ?? "Crawl brand thất bại");
    }
    return r.json();
  },

  delete: async (id: number) => {
    const r = await fetch(`${BASE}/${id}/`, { method: "DELETE" });
    if (!r.ok) throw new Error("Xóa thất bại");
  },

  pages: (docId: number): Promise<PageSummary[]> =>
    fetch(`${BASE}/doc/${docId}/pages`).then((r) => {
      if (!r.ok) throw new Error("Lỗi tải pages");
      return r.json();
    }),

  pageDetail: (pageId: number): Promise<PageDetail> =>
    fetch(`${BASE}/page/${pageId}`).then((r) => {
      if (!r.ok) throw new Error("Lỗi tải page detail");
      return r.json();
    }),
};

// ─── Helpers ──────────────────────────────────────────────
const isUrl = (s: string) => /^https?:\/\/.+/.test(s.trim());

const STATUS_BADGE: Record<DocOut["status"], React.ReactNode> = {
  completed: (
    <Badge className="bg-emerald-50 text-emerald-700 border-none text-[10px]">Sẵn sàng</Badge>
  ),
  processing: (
    <Badge className="bg-amber-50 text-amber-700 border-none text-[10px] animate-pulse">
      Đang xử lý
    </Badge>
  ),
  failed: (
    <Badge className="bg-rose-50 text-rose-700 border-none text-[10px]">Lỗi</Badge>
  ),
};

const formatDate = (dateStr: string) => {
  const d = new Date(dateStr);
  return `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")}/${d.getFullYear()}`;
};

// ─── Brand Identity Panel (Right Drawer UI Modified) ──────
function BrandIdentityPanel({ pageId, onClose }: { pageId: number; onClose: () => void }) {
  const { data, isLoading } = useQuery({
    queryKey: ["page-detail", pageId],
    queryFn: () => api.pageDetail(pageId),
  });


  const identity = data?.extracted?.identity;
  const brandPages = data?.extracted?.brand_pages ?? [];
  const wordCount = data?.extracted?.word_count;
  const content = data?.content;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">


      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm transition-opacity animate-in fade-in duration-300"
        onClick={onClose}
      />

      {/* Khung nội dung mọc từ bên phải (Right Drawer) */}
      <div className="relative bg-white h-full w-full max-w-md md:max-w-lg shadow-2xl flex flex-col z-10 border-l border-slate-200 animate-in slide-in-from-right duration-300 ease-out">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200 shrink-0">
          <div className="flex items-center gap-2">
            <Sparkles size={16} className="text-violet-500" />
            <span className="text-sm font-semibold text-slate-800">
              Brand Identity
            </span>
            {wordCount && (
              <span className="text-[10px] text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">
                {wordCount} từ trong RAG
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            className="h-7 w-7 flex items-center justify-center rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        {/* Content */}
        <div className="overflow-y-auto flex-1 px-5 py-5 space-y-5">


          {isLoading && (
            <div className="space-y-3">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-12 bg-slate-100 rounded-lg animate-pulse" />
              ))}
            </div>
          )}

          {!isLoading && !identity && (
            <p className="text-sm text-slate-400 text-center py-6">
              Chưa có dữ liệu brand identity
            </p>
          )}

          {identity && (
            <div className="space-y-4">
              {identity.brand_name && (
                <Field label="Tên thương hiệu" value={identity.brand_name} highlight />
              )}
              {identity.description && (
                <Field label="Mô tả" value={identity.description} />
              )}
              {identity.mission && (
                <Field label="Sứ mệnh" value={identity.mission} />
              )}
              {identity.vision && (
                <Field label="Tầm nhìn" value={identity.vision} />
              )}
              {identity.story && (
                <Field label="Câu chuyện thương hiệu" value={identity.story} />
              )}
              {identity.values && identity.values.length > 0 && (
                <TagField label="Giá trị cốt lõi" items={identity.values} color="violet" />
              )}
              {identity.strengths && identity.strengths.length > 0 && (
                <TagField label="Thế mạnh" items={identity.strengths} color="blue" />
              )}
              {identity.tone && identity.tone.length > 0 && (
                <TagField label="Phong cách" items={identity.tone} color="emerald" />
              )}
            </div>
          )}

          {/* Pages followed */}
          {brandPages.length > 0 && (
            <div className="pt-2 border-t border-slate-100">
              <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wide mb-2">
                Trang brand đã crawl ({brandPages.length})
              </p>
              <div className="space-y-1">
                {brandPages.map((u) => (
                  <a
                    key={u}
                    href={u}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-violet-600 truncate py-0.5"
                  >
                    <ExternalLink size={11} className="shrink-0" />
                    <span className="truncate">{u}</span>
                  </a>
                ))}
              </div>
            </div>
          )}


          <MarkdownRenderer content={content || "Chưa có nội dung..."} />
        </div>
      </div>
    </div>
  );
}

function Field({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className="bg-slate-50/50 p-3 rounded-lg border border-slate-100">
      <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wide mb-1">{label}</p>
      <p className={`text-xs md:text-sm ${highlight ? "font-semibold text-indigo-900" : "text-slate-600"} leading-relaxed`}>
        {value}
      </p>
    </div>
  );
}

function TagField({ label, items, color }: { label: string; items: string[]; color: string }) {
  const colorMap: Record<string, string> = {
    violet: "bg-violet-50 text-violet-700 border-violet-100",
    blue: "bg-blue-50 text-blue-700 border-blue-100",
    emerald: "bg-emerald-50 text-emerald-700 border-emerald-100",
  };
  return (
    <div className="bg-slate-50/50 p-3 rounded-lg border border-slate-100">
      <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wide mb-1.5">{label}</p>
      <div className="flex flex-wrap gap-1.5">
        {items.map((item) => (
          <span key={item} className={`text-[11px] px-2 py-0.5 rounded-md border ${colorMap[color]}`}>
            {item}
          </span>
        ))}
      </div>
    </div>
  );
}

// ─── Route ────────────────────────────────────────────────
export const Route = createFileRoute("/knowledge")({
  component: KnowledgePage,
});

export default function KnowledgePage() {
  const qc = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [brandPanelPageId, setBrandPanelPageId] = useState<number | null>(null);
  const [urlInput, setUrlInput] = useState("");
  const docType = "brand";
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteDocId, setDeleteDocId] = useState<number | null>(null);

  const { data: docs = [], isLoading } = useQuery({
    queryKey: ["rag-docs"],
    queryFn: api.list,
    refetchInterval: 5_000,
  });

  const { data: docPages = [] } = useQuery({
    queryKey: ["doc-pages", selectedId],
    queryFn: () => api.pages(selectedId!),
    enabled: !!selectedId && docs.find((d) => d.id === selectedId)?.document_type === "brand",
  });

  const uploadMutation = useMutation({
    mutationFn: ({ title, file }: { title: string; file: File }) =>
      api.upload(title, file, docType),
    onSuccess: (data) => {
      toast.success(`"${data.title}" đã được ingest!`);
      qc.invalidateQueries({ queryKey: ["rag-docs"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });



  const crawlBrandMutation = useMutation({
    mutationFn: (url: string) => api.crawlBusiness(url),
    onSuccess: (data) => {
      toast.success(`Đã crawl brand: "${data.title}"`);
      setUrlInput("");
      qc.invalidateQueries({ queryKey: ["rag-docs"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

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
      toast.error("Xóa thất bại");
    },
    onSuccess: () => {
      toast.success("Đã xóa tài liệu");
      setDeleteDialogOpen(false);
      setDeleteDocId(null);
      setSelectedId(null);
    },
  });

  const isCrawling = crawlBrandMutation.isPending;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    uploadMutation.mutate({ title: file.name, file });
    e.target.value = "";
  };

  const handleCrawl = () => {
    const url = urlInput.trim();
    if (!url || !isUrl(url)) return;
    crawlBrandMutation.mutate(url);  // Luôn dùng brand
  };

  const handleDocClick = async (doc: DocOut) => {
    setSelectedId(doc.id);
    if (doc.document_type === "brand" && doc.status === "completed") {
      const pages = await api.pages(doc.id);
      if (pages.length > 0) {
        setBrandPanelPageId(pages[0].id);
      }
    }
  };

  const urlError = urlInput.trim() !== "" && !isUrl(urlInput);
  const filtered = useMemo(
    () => docs.filter((d) => d.title.toLowerCase().includes(search.toLowerCase())),
    [docs, search],
  );
  const isEmpty = !isLoading && filtered.length === 0;

  const CrawlButtonLabel = () => {
    if (isCrawling) return <Loader2 size={13} className="animate-spin" />;
    if (docType === "brand") return <Sparkles size={13} />;
    return <Globe size={13} />;
  };

  return (
    <div className="flex flex-col h-full bg-white">

      <div className="flex items-center gap-1  sm:flex shrink-0">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => navigate({ to: "/knowledge" })}
          className="h-8 text-xs text-slate-600 hover:text-slate-900 gap-1"
        >
          <Sparkles size={13} />
          <span>Thương hiệu</span>
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => navigate({ to: "/products" })}
          className="h-8 text-xs text-slate-600 hover:text-slate-900 gap-1"
        >
          <Book size={13} />
          <span>Sản phẩm & dịch vụ</span>
        </Button>
      </div>
      {/* ─── TOOLBAR ──────────────────────────────────────────── */}
      <div className="h-14 border-b border-slate-200 flex items-center gap-2 px-4 shrink-0 bg-white">
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
          {uploadMutation.isPending ? <Loader2 size={13} className="animate-spin" /> : <UploadCloud size={13} />}
          <span className="hidden sm:inline">Tải file</span>
        </Button>





        <div className="flex-1 hidden sm:flex items-start gap-2 min-w-0 max-w-sm">
          <div className="relative flex-1">
            <Globe size={13} className="absolute left-2 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
            <Input
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleCrawl()}
              placeholder={docType === "brand" ? "https://brand-homepage.com" : "https://example.com"}
              className={`pl-7 h-8 text-xs bg-slate-50 border-slate-200 ${urlError ? "border-rose-500 bg-rose-50" : ""}`}
              disabled={isCrawling}
            />
            {urlError && <p className="text-[10px] text-rose-600 mt-0.5">URL không hợp lệ</p>}
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={handleCrawl}
            disabled={isCrawling || !urlInput.trim() || urlError}
            className={`h-8 text-xs shrink-0 gap-1 ${docType === "brand" ? "border-violet-200 text-violet-600 hover:bg-violet-50" : ""}`}
          >
            <CrawlButtonLabel />
            <span className="hidden md:inline">
              {docType === "brand" ? "Crawl Brand" : "Crawl"}
            </span>
          </Button>
        </div>

        <div className="flex-1 hidden sm:block" />

        <div className="relative w-44 hidden sm:block">
          <Search size={13} className="absolute left-2 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Tìm kiếm…"
            className="pl-7 h-8 text-xs bg-slate-50 border-slate-200"
          />
        </div>

        <span className="text-xs font-medium text-slate-500 shrink-0 ml-2">
          Tài liệu ({filtered.length})
        </span>
      </div>

      {/* ─── MOBILE TOOLBAR ───────────────────────────────────── */}
      <div className="sm:hidden flex flex-col gap-2 px-4 py-2 border-b border-slate-200 bg-white shrink-0">

        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <Globe size={13} className="absolute left-2 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
            <Input
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleCrawl()}
              placeholder="https://example.com"
              className={`pl-7 h-8 text-xs bg-slate-50 border-slate-200 ${urlError ? "border-rose-500 bg-rose-50" : ""}`}
              disabled={isCrawling}
            />
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={handleCrawl}
            disabled={isCrawling || !urlInput.trim() || urlError}
            className={`h-8 text-xs shrink-0 ${docType === "brand" ? "border-violet-200 text-violet-600" : ""}`}
          >
            {isCrawling ? <Loader2 size={13} className="animate-spin" /> : docType === "brand" ? "Brand" : "Crawl"}
          </Button>
        </div>
        {urlError && <p className="text-[10px] text-rose-600">URL không hợp lệ</p>}
        <div className="relative">
          <Search size={13} className="absolute left-2 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
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
          {isEmpty && (
            <div className="flex flex-col items-center justify-center text-center py-12">
              <div className="h-12 w-12 rounded-lg bg-slate-100 flex items-center justify-center mb-3">
                <UploadCloud size={20} className="text-slate-400" />
              </div>
              <h3 className="text-sm font-medium text-slate-900 mb-1">Chưa có tài liệu nào</h3>
              <p className="text-xs text-slate-500 mb-4 max-w-xs">
                Tải file hoặc nhập URL để xây dựng cơ sở tri thức
              </p>
              <Button
                size="sm"
                onClick={() => fileRef.current?.click()}
                className="gap-1 h-8 text-xs bg-indigo-600 hover:bg-indigo-700"
              >
                <UploadCloud size={13} />Tải file
              </Button>
            </div>
          )}

          {isLoading && (
            <div className="space-y-2">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="h-16 bg-slate-100 rounded-lg animate-pulse" />
              ))}
            </div>
          )}

          {!isLoading && filtered.length > 0 && (
            <div className="divide-y divide-slate-200 border border-slate-200 rounded-lg overflow-hidden bg-white">
              {filtered.map((doc) => {
                const meta = DOC_TYPE_META[doc.document_type] ?? DOC_TYPE_META.product_knowledge;
                const isBrand = doc.document_type === "brand";
                return (
                  <div
                    key={doc.id}
                    onClick={() => handleDocClick(doc)}
                    className={`flex items-center gap-3 px-4 py-3 cursor-pointer transition-colors ${selectedId === doc.id ? "bg-indigo-50/50" : "hover:bg-slate-50/50"
                      }`}
                  >
                    <div className={`p-1.5 rounded shrink-0 ${meta.color}`}>{meta.icon}</div>

                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-slate-900 truncate">{doc.title}</p>
                      <div className="flex items-center gap-1.5 mt-0.5 text-xs text-slate-500 flex-wrap">
                        <span className="px-2 py-0.5 bg-slate-100 rounded text-[10px] font-medium whitespace-nowrap">
                          {meta.label}
                        </span>
                        <span>#{doc.id}</span>
                        {doc.file_size && <><span>•</span><span>{doc.file_size}</span></>}
                        {doc.status === "completed" && <><span>•</span><span>{doc.chunk_count} đoạn</span></>}
                        <span>•</span>
                        <span>Tạo: {formatDate(doc.created_at)}</span>
                      </div>
                    </div>

                    <div className="shrink-0 hidden sm:block">{STATUS_BADGE[doc.status]}</div>

                    {isBrand && doc.status === "completed" && (
                      <button
                        onClick={(e) => { e.stopPropagation(); handleDocClick(doc); }}
                        className="h-7 px-2 flex items-center gap-1 rounded text-[11px] text-violet-600 bg-violet-50 hover:bg-violet-100 transition-colors shrink-0"
                        title="Xem brand identity"
                      >
                        <Sparkles size={11} />
                        <span className="hidden sm:inline">Identity</span>
                        <ChevronRight size={11} />
                      </button>
                    )}

                    <button
                      onClick={(e) => { e.stopPropagation(); setDeleteDocId(doc.id); setDeleteDialogOpen(true); }}
                      disabled={deleteMutation.isPending}
                      className="h-11 w-11 flex items-center justify-center rounded hover:bg-rose-50 text-slate-300 hover:text-rose-500 transition-colors shrink-0 disabled:opacity-50"
                      aria-label="Xóa"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                );
              })}
            </div>
          )}

          {!isEmpty && (
            <div className="flex items-start gap-2 text-xs text-slate-500 mt-4 pt-4 border-t border-slate-200">
              <ShieldCheck size={14} className="mt-px shrink-0 text-emerald-600" />
              <span>Tài liệu được lưu trữ Private Cloud — không dùng cho training công khai</span>
            </div>
          )}
        </div>
      </div>

      {/* ─── BRAND IDENTITY PANEL ─────────────────────────────── */}
      {brandPanelPageId && (
        <BrandIdentityPanel
          pageId={brandPanelPageId}
          onClose={() => setBrandPanelPageId(null)}
        />
      )}

      {/* ─── DELETE DIALOG ────────────────────────────────────── */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogTitle>Xóa tài liệu?</AlertDialogTitle>
          <AlertDialogDescription>
            Hành động này không thể hoàn tác. Tài liệu sẽ bị xóa vĩnh viễn khỏi cơ sở tri thức.
          </AlertDialogDescription>
          <div className="flex gap-2 justify-end pt-4">
            <AlertDialogCancel className="h-8">Hủy</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => deleteDocId !== null && deleteMutation.mutate(deleteDocId)}
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