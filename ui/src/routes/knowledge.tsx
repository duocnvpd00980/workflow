"use client";

import { useState, useRef, useMemo, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  UploadCloud,
  Globe,
  Search,
  Trash2,
  ShieldCheck,
  Loader2,
  Book,
  Sparkles,
  ChevronRight,
  ChevronLeft,
  X,
  ExternalLink,
  FileText,
  HelpCircle,
  ShoppingCart,
  RefreshCw,
  Eye,
  Plus,
  Archive,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent } from "@/components/ui/card";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Accordion,
  AccordionItem,
  AccordionTrigger,
  AccordionContent,
} from "@/components/ui/accordion";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { toast } from "sonner";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { BASE } from "@/config";
import { MarkdownRenderer } from "@/components/ui/markdown-renderer";
import { cn } from "@/lib/utils"
import { Separator } from "@/components/ui/separator";

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

// ─── Category model (UI grouping for Tabs / Card grid) ────
// NOTE: "document_type" values returned by the API today are mostly
// "brand" và "product_knowledge". Loại "document" và "qa" được map ở
// đây để phục vụ UI mới — backend có thể cần bổ sung enum sau.
type CategoryKey = "document" | "qa" | "product" | "website";

const CATEGORY_META: Record<
  CategoryKey,
  { label: string; icon: React.ReactNode; color: string }
> = {
  document: {
    label: "Tài liệu",
    icon: <FileText size={14} />,
    color: "bg-blue-50 text-blue-600",
  },
  qa: {
    label: "QA",
    icon: <HelpCircle size={14} />,
    color: "bg-amber-50 text-amber-600",
  },
  product: {
    label: "Sản phẩm",
    icon: <ShoppingCart size={14} />,
    color: "bg-emerald-50 text-emerald-600",
  },
  website: {
    label: "Website",
    icon: <Globe size={14} />,
    color: "bg-violet-50 text-violet-600",
  },
};



// ─── FILTER CHIPS ───
const FILTERS = [
  { label: "Tất cả", value: "all", icon: <HelpCircle size={14} /> },
  { label: "Tài liệu",   value: "Blog" , icon: <FileText size={14} />},
  { label: "QA",  value: "Email", icon: <HelpCircle size={14} />},
  { label: "Sản phẩm", value: "Products", icon: <ShoppingCart size={14} />},
  { label: "Website",    value: "Ads" , icon: <Globe size={14} />},
] as const

function getCategoryKey(documentType: string): CategoryKey {
  switch (documentType) {
    case "product_knowledge":
    case "product":
      return "product";
    case "qa":
      return "qa";
    case "brand":
    case "website":
      return "website";
    default:
      return "document";
  }
}

// ─── Verification badge (MOCK) ─────────────────────────────
// Chưa có field "verified" từ API — tạm suy ra từ "status" cho tới khi
// backend trả về trường xác minh thật.
type VerificationState = "verified" | "review" | "error";

function getVerification(doc: DocOut): VerificationState {
  if (doc.status === "failed") return "error";
  if (doc.status === "processing") return "review";
  return "verified";
}

const VERIFICATION_META: Record<
  VerificationState,
  { label: string; className: string; icon: React.ReactNode }
> = {
  verified: {
    label: "Verified",
    className: "text-emerald-600",
    icon: <ShieldCheck size={12} />,
  },
  review: {
    label: "Needs review",
    className: "text-amber-600",
    icon: <Loader2 size={12} className="animate-spin" />,
  },
  error: {
    label: "Error",
    className: "text-rose-600",
    icon: <X size={12} />,
  },
};

const STATUS_LABEL: Record<DocOut["status"], string> = {
  completed: "Sẵn sàng",
  processing: "Đang xử lý",
  failed: "Lỗi",
};

const STATUS_DOT: Record<DocOut["status"], React.ReactNode> = {
  completed: (
    <span className="flex items-center gap-1 text-[10px] text-emerald-600 shrink-0">
      <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
      Ready
    </span>
  ),
  processing: (
    <span className="flex items-center gap-1 text-[10px] text-amber-600 shrink-0">
      <span className="h-1.5 w-1.5 rounded-full bg-amber-500 animate-pulse" />
      Indexing
    </span>
  ),
  failed: (
    <span className="flex items-center gap-1 text-[10px] text-rose-600 shrink-0">
      <span className="h-1.5 w-1.5 rounded-full bg-rose-500" />
      Error
    </span>
  ),
};

// ─── API (KHÔNG ĐỔI) ────────────────────────────────────────
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

const formatDate = (dateStr: string) => {
  const d = new Date(dateStr);
  return `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")}/${d.getFullYear()}`;
};

// MOCK: chưa có timestamp "last sync" riêng từ API — tạm tính theo created_at
const formatRelative = (dateStr: string) => {
  const diffMs = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return "vừa xong";
  if (mins < 60) return `${mins} phút trước`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} giờ trước`;
  const days = Math.floor(hours / 24);
  return `${days} ngày trước`;
};

interface MockChunk {
  id: number;
  chars: number;
  text: string;
}

// MOCK: chunk-level content chưa có API riêng. Với tài liệu brand, ta có
// "content" đầy đủ từ pageDetail nên tự cắt thành các đoạn để preview.
// Với loại khác, hiển thị placeholder theo chunk_count cho tới khi có API.
function buildMockChunks(
  content: string | null | undefined,
  chunkCount: number,
): MockChunk[] {
  if (content && content.trim().length > 0) {
    const size = 280;
    const chunks: MockChunk[] = [];
    for (let i = 0; i < content.length; i += size) {
      const slice = content.slice(i, i + size).trim();
      if (!slice) continue;
      chunks.push({ id: chunks.length + 1, chars: slice.length, text: slice });
    }
    return chunks;
  }
  return Array.from({ length: Math.max(chunkCount, 0) }, (_, i) => ({
    id: i + 1,
    chars: 0,
    text: "Nội dung đoạn sẽ hiển thị khi API trả về chunk-level content.",
  }));
}

// ─── Small presentational helpers ──────────────────────────
function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wide flex items-center gap-1">
      {children}
    </p>
  );
}

function MetaRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between bg-slate-50/50 rounded px-2 py-1.5 border border-slate-100 text-xs">
      <span className="text-slate-400">{label}</span>
      <span className="font-medium text-slate-700">{value}</span>
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

// ─── Drag & drop file zone ──────────────────────────────────
function DropZone({
  accept,
  hint,
  onFile,
  disabled,
}: {
  accept: string;
  hint: string;
  onFile: (file: File) => void;
  disabled?: boolean;
}) {
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragOver(false);
        if (disabled) return;
        const file = e.dataTransfer.files?.[0];
        if (file) onFile(file);
      }}
      onClick={() => !disabled && inputRef.current?.click()}
      className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
        disabled
          ? "opacity-50 cursor-not-allowed border-slate-200"
          : dragOver
            ? "border-indigo-400 bg-indigo-50 cursor-pointer"
            : "border-slate-200 hover:border-slate-300 cursor-pointer"
      }`}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        disabled={disabled}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) onFile(file);
          e.target.value = "";
        }}
      />
      <UploadCloud size={22} className="mx-auto text-slate-400 mb-2" />
      <p className="text-xs text-slate-600">
        Kéo thả file vào đây hoặc <span className="text-indigo-600 font-medium">chọn file</span>
      </p>
      <p className="text-[10px] text-slate-400 mt-1">{hint}</p>
    </div>
  );
}

// ─── Document card ──────────────────────────────────────────
function DocCard({
  doc,
  onView,
  onDelete,
  onSync,
  isSyncing,
  isDeleting,
}: {
  doc: DocOut;
  onView: (doc: DocOut) => void;
  onDelete: (doc: DocOut) => void;
  onSync: (doc: DocOut) => void;
  isSyncing: boolean;
  isDeleting: boolean;
}) {
  const category = getCategoryKey(doc.document_type);
  const meta = CATEGORY_META[category];
  const verification = getVerification(doc);
  const vMeta = VERIFICATION_META[verification];

  return (
    <Card
      onClick={() => onView(doc)}
      className="cursor-pointer hover:shadow-md hover:border-slate-300 transition-all"
    >
      <CardContent className="p-4 space-y-3">
        <div className="flex items-start justify-between">
          <div className={`p-2 rounded-lg ${meta.color}`}>{meta.icon}</div>
          {STATUS_DOT[doc.status]}
        </div>

        <div className="min-w-0">
          <p className="text-sm font-medium text-slate-900 truncate" title={doc.title}>
            {doc.title}
          </p>
          <div className={`inline-flex items-center gap-1 mt-1 text-[11px] ${vMeta.className}`}>
            {vMeta.icon}
            {vMeta.label}
          </div>
        </div>

        <div className="flex items-center justify-between text-[11px] text-slate-500">
          <span>{doc.status === "completed" ? `${doc.chunk_count} đoạn` : "—"}</span>
          <span>Sync: {formatRelative(doc.created_at)}</span>
        </div>

        <div
          className="flex items-center gap-1 pt-2 border-t border-slate-100"
          onClick={(e) => e.stopPropagation()}
        >
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-slate-400 hover:text-indigo-600"
            onClick={() => onSync(doc)}
            disabled={isSyncing}
            title="Đồng bộ lại"
          >
            {isSyncing ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-slate-400 hover:text-slate-700"
            onClick={() => onView(doc)}
            title="Xem chi tiết"
          >
            <Eye size={14} />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-slate-400 hover:text-rose-500 ml-auto"
            onClick={() => onDelete(doc)}
            disabled={isDeleting}
            title="Xóa"
          >
            <Trash2 size={14} />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Drawer chi tiết tài liệu (Sheet) ───────────────────────
function DocDrawer({
  doc,
  onClose,
  onDelete,
  onSync,
  isSyncing,
  isDeleting,
}: {
  doc: DocOut;
  onClose: () => void;
  onDelete: (doc: DocOut) => void;
  onSync: (doc: DocOut) => void;
  isSyncing: boolean;
  isDeleting: boolean;
}) {
  const category = getCategoryKey(doc.document_type);
  const meta = CATEGORY_META[category];
  const verification = getVerification(doc);
  const vMeta = VERIFICATION_META[verification];
  const isBrand = doc.document_type === "brand";

  const { data: pages = [] } = useQuery({
    queryKey: ["doc-pages", doc.id],
    queryFn: () => api.pages(doc.id),
    enabled: isBrand && doc.status === "completed",
  });

  const firstPageId = pages[0]?.id;
  const { data: pageDetail, isLoading: detailLoading } = useQuery({
    queryKey: ["page-detail", firstPageId],
    queryFn: () => api.pageDetail(firstPageId!),
    enabled: !!firstPageId,
  });

  const identity = pageDetail?.extracted?.identity;
  const brandPages = pageDetail?.extracted?.brand_pages ?? [];
  const wordCount = pageDetail?.extracted?.word_count;
  const content = pageDetail?.content;

  const chunks = useMemo(
    () => buildMockChunks(content, doc.chunk_count),
    [content, doc.chunk_count],
  );

  return (
    <Sheet open onOpenChange={(open) => !open && onClose()}>
      <SheetContent side="right" className="w-full sm:max-w-lg p-0 flex flex-col gap-0">
        {/* Header */}
        <div className="px-5 py-4 border-b border-slate-200 shrink-0">
          <div className="flex items-center gap-2 min-w-0">
            <div className={`p-1.5 rounded shrink-0 ${meta.color}`}>{meta.icon}</div>
            <span className="text-sm font-semibold text-slate-800 truncate">{doc.title}</span>
            {wordCount && (
              <span className="text-[10px] text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full shrink-0">
                {wordCount} từ
              </span>
            )}
          </div>
          <div className="flex items-center gap-1.5 mt-1.5 text-[11px]">
            <span className={`inline-flex items-center gap-1 ${vMeta.className}`}>
              {vMeta.icon}
              {vMeta.label}
            </span>
            <span className="text-slate-300">•</span>
            <span className="text-slate-500">Sync: {formatRelative(doc.created_at)}</span>
          </div>
        </div>

        {/* Content */}
        <div className="overflow-y-auto flex-1 px-5 py-4 space-y-5">
          {/* Ask AI — sắp ra mắt */}
          <div className="relative">
            <Sparkles size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-indigo-400" />
            <Input
              placeholder="Hỏi về tài liệu này..."
              className="pl-8 h-9 text-xs bg-slate-50"
              readOnly
              onFocus={() => toast.info("Tính năng hỏi AI về tài liệu sắp ra mắt")}
            />
          </div>

          {/* Metadata */}
          <div className="space-y-2">
            <SectionLabel>Metadata</SectionLabel>
            <div className="grid grid-cols-2 gap-2">
              <MetaRow label="Loại" value={meta.label} />
              <MetaRow label="Kích thước" value={doc.file_size ?? "—"} />
              <MetaRow label="Số đoạn" value={String(doc.chunk_count)} />
              <MetaRow label="Ngày tạo" value={formatDate(doc.created_at)} />
              <MetaRow label="Nguồn" value={isBrand ? "Website" : "Upload"} />
              <MetaRow label="Trạng thái" value={STATUS_LABEL[doc.status]} />
            </div>
          </div>

          {/* Brand identity (chỉ cho document_type = brand) */}
          {isBrand && (
            <div className="space-y-2 pt-2 border-t border-slate-100">
              <SectionLabel>
                <Sparkles size={11} className="text-violet-500" /> Brand Identity
              </SectionLabel>

              {detailLoading && (
                <div className="space-y-2">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="h-10 bg-slate-100 rounded-lg animate-pulse" />
                  ))}
                </div>
              )}

              {!detailLoading && !identity && (
                <p className="text-xs text-slate-400 text-center py-4">
                  Chưa có dữ liệu brand identity
                </p>
              )}

              {identity && (
                <div className="space-y-2">
                  {identity.brand_name && <Field label="Tên thương hiệu" value={identity.brand_name} highlight />}
                  {identity.description && <Field label="Mô tả" value={identity.description} />}
                  {identity.mission && <Field label="Sứ mệnh" value={identity.mission} />}
                  {identity.vision && <Field label="Tầm nhìn" value={identity.vision} />}
                  {identity.story && <Field label="Câu chuyện thương hiệu" value={identity.story} />}
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

              {brandPages.length > 0 && (
                <div className="pt-2">
                  <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wide mb-2">
                    Trang đã crawl ({brandPages.length})
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
            </div>
          )}

          {/* Chunks */}
          <div className="space-y-2 pt-2 border-t border-slate-100">
            <SectionLabel>Chunks ({chunks.length})</SectionLabel>
            {chunks.length === 0 ? (
              <p className="text-xs text-slate-400 text-center py-2">Chưa có dữ liệu chunk</p>
            ) : (
              <Accordion type="single" collapsible className="w-full">
                {chunks.map((c) => (
                  <AccordionItem key={c.id} value={`chunk-${c.id}`}>
                    <AccordionTrigger className="text-xs py-2">
                      Chunk {c.id} {c.chars > 0 ? `(${c.chars} chars)` : ""}
                    </AccordionTrigger>
                    <AccordionContent className="text-xs text-slate-600 leading-relaxed">
                      {c.text}
                    </AccordionContent>
                  </AccordionItem>
                ))}
              </Accordion>
            )}
          </div>

          {/* Preview */}
          <div className="space-y-2 pt-2 border-t border-slate-100">
            <SectionLabel>Preview</SectionLabel>
            <div className="border border-slate-100 rounded-lg bg-slate-50/50 p-3 max-h-64 overflow-y-auto">
              <MarkdownRenderer content={content || "Chưa có nội dung xem trước."} />
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="border-t border-slate-200 p-3 flex gap-2 shrink-0">
          <Button
            variant="outline"
            size="sm"
            className="flex-1 h-8 text-xs gap-1.5"
            onClick={() => onSync(doc)}
            disabled={isSyncing}
          >
            {isSyncing ? <Loader2 size={13} className="animate-spin" /> : <RefreshCw size={13} />}
            Sync Now
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="flex-1 h-8 text-xs gap-1.5 text-rose-600 border-rose-200 hover:bg-rose-50"
            onClick={() => onDelete(doc)}
            disabled={isDeleting}
          >
            <Trash2 size={13} />
            Delete
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}

// ─── Upload type chooser (Step 1) ───────────────────────────
const UPLOAD_TYPES: { key: CategoryKey; label: string; desc: string }[] = [
  { key: "document", label: "Tài liệu", desc: "PDF, DOC, TXT — tài liệu dài" },
  { key: "qa", label: "QA", desc: "Câu hỏi & trả lời" },
  { key: "product", label: "Sản phẩm", desc: "Thông tin sản phẩm + ảnh" },
  { key: "website", label: "Website", desc: "Crawl nội dung từ URL" },
];

// ─── Route ────────────────────────────────────────────────
export const Route = createFileRoute("/knowledge")({
  component: KnowledgePage,
});

export default function KnowledgePage() {
  const qc = useQueryClient();

  // ── Header / filter state ─────────────────────────────────
  const [search, setSearch] = useState("");
  const [activeCategory, setActiveCategory] = useState<"all" | CategoryKey>("all");

  // ── Drawer state ──────────────────────────────────────────
  const [drawerDocId, setDrawerDocId] = useState<number | null>(null);

  // ── Delete dialog state ────────────────────────────────────
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteDocId, setDeleteDocId] = useState<number | null>(null);

  // ── Upload modal state ──────────────────────────────────────
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [uploadStep, setUploadStep] = useState<1 | 2>(1);
  const [uploadType, setUploadType] = useState<CategoryKey | null>(null);

  // Website crawl
  const [urlInput, setUrlInput] = useState("");
  const [autoCrawl, setAutoCrawl] = useState(true);

  // QA (mock, chưa có API)
  const [qaText, setQaText] = useState("");
  const csvInputRef = useRef<HTMLInputElement>(null);


  const [filter, setFilter] = useState("all")
  const [selected, setSelected] = useState<Set<string>>(new Set())



  
  // ── Queries ─────────────────────────────────────────────────
  const { data: docs = [], isLoading } = useQuery({
    queryKey: ["rag-docs"],
    queryFn: api.list,
    refetchInterval: 5_000,
  });

  // ── Mutations (logic giữ nguyên) ─────────────────────────────
  const uploadMutation = useMutation({
    mutationFn: ({ title, file, document_type }: { title: string; file: File; document_type: string }) =>
      api.upload(title, file, document_type),
    onSuccess: (data) => {
      toast.success(`"${data.title}" đã được ingest!`);
      qc.invalidateQueries({ queryKey: ["rag-docs"] });
      closeUploadModal();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const crawlBrandMutation = useMutation({
    mutationFn: (url: string) => api.crawlBusiness(url),
    onSuccess: (data) => {
      toast.success(`Đã crawl: "${data.title}"`);
      qc.invalidateQueries({ queryKey: ["rag-docs"] });
      closeUploadModal();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  // MOCK: chưa có API cho loại QA — tạm thêm vào danh sách hiển thị phía
  // client, sẽ thay bằng API thật khi backend hỗ trợ.
  const qaMockMutation = useMutation({
    mutationFn: async (text: string) => {
      await new Promise((r) => setTimeout(r, 600));
      const pairs = text.split(/\n\s*\n/).map((p) => p.trim()).filter(Boolean);
      return { count: Math.max(pairs.length, 1) };
    },
    onSuccess: ({ count }) => {
      const fakeDoc: DocOut = {
        id: -Date.now(),
        title: `QA – ${count} cặp câu hỏi`,
        status: "completed",
        document_type: "qa",
        chunk_count: count,
        file_size: null,
        created_at: new Date().toISOString(),
      };
      qc.setQueryData<DocOut[]>(["rag-docs"], (old = []) => [fakeDoc, ...old]);
      toast.success("Đã lưu QA (demo — cần API thật để lưu vĩnh viễn)");
      closeUploadModal();
    },
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
      setDrawerDocId(null);
    },
  });

  // MOCK: chưa có API "sync" — tạm refetch danh sách để giả lập đồng bộ.
  const syncMutation = useMutation({
    mutationFn: async (id: number) => {
      await new Promise((r) => setTimeout(r, 500));
      return id;
    },
    onSuccess: () => {
      toast.success("Đã đồng bộ lại tài liệu");
      qc.invalidateQueries({ queryKey: ["rag-docs"] });
    },
    onError: () => toast.error("Đồng bộ thất bại"),
  });

  // ── Derived data ───────────────────────────────────────────
  const counts = useMemo(() => {
    const c: Record<CategoryKey, number> = { document: 0, qa: 0, product: 0, website: 0 };
    docs.forEach((d) => {
      c[getCategoryKey(d.document_type)] += 1;
    });
    return c;
  }, [docs]);

  const filtered = useMemo(() => {
    return docs.filter((d) => {
      const matchesSearch = d.title.toLowerCase().includes(search.toLowerCase());
      const matchesTab = activeCategory === "all" || getCategoryKey(d.document_type) === activeCategory;
      return matchesSearch && matchesTab;
    });
  }, [docs, search, activeCategory]);

  const isEmpty = !isLoading && filtered.length === 0;
  const drawerDoc = docs.find((d) => d.id === drawerDocId) ?? null;
  const urlError = urlInput.trim() !== "" && !isUrl(urlInput);

  // Simulated progress bar trong upload modal
  const isUploading = uploadMutation.isPending || crawlBrandMutation.isPending || qaMockMutation.isPending;
  const [uploadProgress, setUploadProgress] = useState(0);
  useEffect(() => {
    if (!isUploading) {
      setUploadProgress(0);
      return;
    }
    setUploadProgress(10);
    const interval = setInterval(() => {
      setUploadProgress((p) => (p < 90 ? p + Math.random() * 18 : p));
    }, 300);
    return () => clearInterval(interval);
  }, [isUploading]);

  // ── Handlers ─────────────────────────────────────────────────
  const closeUploadModal = () => {
    setUploadModalOpen(false);
    setUploadStep(1);
    setUploadType(null);
    setQaText("");
    setUrlInput("");
  };

  const handleFileUpload = (file: File, category: "document" | "product") => {
    const document_type = category === "product" ? "product_knowledge" : "document";
    uploadMutation.mutate({ title: file.name, file, document_type });
  };

  const handleCrawl = () => {
    const url = urlInput.trim();
    if (!url || !isUrl(url)) return;
    crawlBrandMutation.mutate(url);
  };

  // MOCK: import CSV cho QA — đọc text thô và nối vào textarea, chưa có
  // parser CSV chính thức / API lưu trữ.
  const handleQaCsv = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const text = String(reader.result ?? "");
      setQaText((prev) => (prev ? `${prev}\n\n${text}` : text));
      toast.success(`Đã nạp ${file.name} (demo)`);
    };
    reader.readAsText(file);
    e.target.value = "";
  };

  const handleDeleteClick = (doc: DocOut) => {
    setDeleteDocId(doc.id);
    setDeleteDialogOpen(true);
  };

  const handleSync = (doc: DocOut) => syncMutation.mutate(doc.id);

  return (
    <div className="flex flex-col h-full bg-background/50">
      
      {/* TOOLBAR */}
      <div className="shrink-0 flex items-center justify-between px-4 h-12 border-b border-border/60 bg-background gap-2 select-none">
        <div className="flex items-center gap-1">
          <Separator orientation="vertical" className="h-4 mx-1.5" />
          <Button onClick={() => setUploadModalOpen(true)} variant="ghost" size="sm" className="h-8 text-xs gap-1.5 text-muted-foreground hover:bg-muted/80">
            <Plus className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Thêm mới</span>
          </Button>
          <Button variant="ghost" size="sm" className="h-8 text-xs gap-1.5 text-muted-foreground hover:bg-muted/80">
            <Archive className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Lưu trữ</span>
          </Button>
          {selected.size > 0 && (
            <Button variant="ghost" size="sm" className="h-8 text-xs gap-1.5 text-destructive hover:bg-destructive/10 hover:text-destructive">
              <Trash2 className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Xóa ({selected.size})</span>
            </Button>
          )}
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <span className="text-xs text-muted-foreground hidden sm:inline font-medium">
            {filtered.length} nội dung
          </span>
          <div className="flex items-center border border-border/60 rounded-lg overflow-hidden bg-background">
            <Button variant="ghost" size="icon" className="h-7 w-7 rounded-none hover:bg-muted" disabled>
              <ChevronLeft className="h-3.5 w-3.5" />
            </Button>
            <Separator orientation="vertical" className="h-3" />
            <Button variant="ghost" size="icon" className="h-7 w-7 rounded-none hover:bg-muted" disabled>
              <ChevronRight className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      </div>

      {/* FILTER BAR */}



      {/* FILTER BAR */}
      <div className="shrink-0 flex items-center gap-1.5 px-4 h-11 border-b border-border/40 bg-muted/20 overflow-x-auto scrollbar-none select-none">
        <Tabs value={activeCategory} onValueChange={(v) => setActiveCategory(v as "all" | CategoryKey)} className="w-full sm:w-auto">
          <TabsList className="bg-transparent p-0 h-auto gap-1 justify-start flex-nowrap overflow-x-auto scrollbar-none w-full sm:flex-wrap sm:overflow-visible sm:w-auto">
            <TabsTrigger
              value="all"
              className="inline-flex items-center px-3 h-6 rounded-full text-xs font-medium whitespace-nowrap shrink-0 transition-all duration-150 data-[state=active]:bg-foreground data-[state=active]:text-background data-[state=active]:shadow-xs data-[state=active]:font-semibold text-muted-foreground hover:text-foreground hover:bg-accent/80"
            >
              Tất cả
            </TabsTrigger>

            {(Object.keys(CATEGORY_META) as CategoryKey[]).map((key) => (
              <TabsTrigger
                key={key}
                value={key}
                className="inline-flex items-center gap-1 px-3 h-6 rounded-full text-xs font-medium whitespace-nowrap shrink-0 transition-all duration-150 data-[state=active]:bg-foreground data-[state=active]:text-background data-[state=active]:shadow-xs data-[state=active]:font-semibold text-muted-foreground hover:text-foreground hover:bg-accent/80"
              >
                {CATEGORY_META[key].label}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
      </div>

      

      {/* ─── CONTENT — CARD GRID ──────────────────────────────── */}
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto w-full px-4 py-4 max-w-[1200px]">
          {isLoading && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-36 bg-slate-100 rounded-lg animate-pulse" />
              ))}
            </div>
          )}

          {isEmpty && (
            <div className="flex flex-col items-center justify-center text-center py-16">
              <div className="h-12 w-12 rounded-lg bg-slate-100 flex items-center justify-center mb-3">
                <UploadCloud size={20} className="text-slate-400" />
              </div>
              <h3 className="text-sm font-medium text-slate-900 mb-1">Chưa có tài liệu nào</h3>
              <p className="text-xs text-slate-500 mb-4 max-w-xs">
                Thêm tài liệu, QA, sản phẩm hoặc website để xây dựng cơ sở tri thức
              </p>
              <Button
                size="sm"
                onClick={() => setUploadModalOpen(true)}
                className="gap-1.5 h-8 text-xs bg-indigo-600 hover:bg-indigo-700"
              >
                <Plus size={13} />
                Thêm tài liệu
              </Button>
            </div>
          )}

          {!isLoading && filtered.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
              {filtered.map((doc) => (
                <DocCard
                  key={doc.id}
                  doc={doc}
                  onView={(d) => setDrawerDocId(d.id)}
                  onDelete={handleDeleteClick}
                  onSync={handleSync}
                  isSyncing={syncMutation.isPending && syncMutation.variables === doc.id}
                  isDeleting={deleteMutation.isPending && deleteMutation.variables === doc.id}
                />
              ))}
            </div>
          )}

         
        </div>
      </div>

      {/* ─── DRAWER CHI TIẾT ──────────────────────────────────── */}
      {drawerDoc && (
        <DocDrawer
          doc={drawerDoc}
          onClose={() => setDrawerDocId(null)}
          onDelete={handleDeleteClick}
          onSync={handleSync}
          isSyncing={syncMutation.isPending && syncMutation.variables === drawerDoc.id}
          isDeleting={deleteMutation.isPending && deleteMutation.variables === drawerDoc.id}
        />
      )}

      {/* ─── UPLOAD MODAL (2 bước) ────────────────────────────── */}
      <Dialog
        open={uploadModalOpen}
        onOpenChange={(open) => (open ? setUploadModalOpen(true) : closeUploadModal())}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Book size={16} className="text-indigo-600" />
              Thêm tài liệu
            </DialogTitle>
          </DialogHeader>

          {/* Step 1: chọn loại */}
          {uploadStep === 1 && (
            <div className="grid grid-cols-2 gap-3 pt-1">
              {UPLOAD_TYPES.map((t) => (
                <button
                  key={t.key}
                  onClick={() => {
                    setUploadType(t.key);
                    setUploadStep(2);
                  }}
                  className="flex flex-col items-center gap-1.5 rounded-lg border border-slate-200 hover:border-indigo-300 hover:bg-indigo-50/40 p-4 transition-colors text-center"
                >
                  <div className={`p-2 rounded-lg ${CATEGORY_META[t.key].color}`}>{CATEGORY_META[t.key].icon}</div>
                  <span className="text-sm font-medium text-slate-800">{t.label}</span>
                  <span className="text-[10px] text-slate-400">{t.desc}</span>
                </button>
              ))}
            </div>
          )}

          {/* Step 2: upload theo loại */}
          {uploadStep === 2 && uploadType && (
            <div className="space-y-4 pt-1">
              <button
                onClick={() => setUploadStep(1)}
                className="text-xs text-slate-500 hover:text-slate-700 flex items-center gap-1 -mt-1"
              >
                <ChevronLeft size={13} />
                Đổi loại tài liệu
              </button>

              {uploadType === "document" && (
                <DropZone
                  accept=".pdf,.docx,.txt,.csv,.xlsx,.md"
                  hint="PDF, DOC, TXT — tối đa 50MB"
                  onFile={(file) => handleFileUpload(file, "document")}
                  disabled={uploadMutation.isPending}
                />
              )}

              {uploadType === "qa" && (
                <div className="space-y-3">
                  <Textarea
                    value={qaText}
                    onChange={(e) => setQaText(e.target.value)}
                    placeholder={"Câu hỏi: ...\nTrả lời: ...\n\n(Mỗi cặp Q&A cách nhau 1 dòng trống)"}
                    className="min-h-[160px] text-xs"
                    disabled={qaMockMutation.isPending}
                  />
                  <div className="flex items-center gap-2">
                    <input
                      ref={csvInputRef}
                      type="file"
                      accept=".csv"
                      className="hidden"
                      onChange={handleQaCsv}
                    />
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-8 text-xs gap-1.5"
                      onClick={() => csvInputRef.current?.click()}
                      disabled={qaMockMutation.isPending}
                    >
                      <UploadCloud size={13} />
                      Import CSV
                    </Button>
                    <span className="text-[10px] text-slate-400">Cột: Question, Answer</span>
                  </div>
                </div>
              )}

              {uploadType === "product" && (
                <div className="space-y-3">
                  <DropZone
                    accept=".pdf,.docx,.txt,.csv,.xlsx,.md"
                    hint="File thông tin sản phẩm — tối đa 50MB"
                    onFile={(file) => handleFileUpload(file, "product")}
                    disabled={uploadMutation.isPending}
                  />
                  <DropZone
                    accept=".zip"
                    hint="Ảnh sản phẩm (.zip) — sẽ hỗ trợ sau"
                    onFile={() => toast.info("Upload ảnh sản phẩm sẽ được hỗ trợ sau")}
                    disabled
                  />
                </div>
              )}

              {uploadType === "website" && (
                <div className="space-y-3">
                  <div className="relative">
                    <Globe size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
                    <Input
                      value={urlInput}
                      onChange={(e) => setUrlInput(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && handleCrawl()}
                      placeholder="https://example.com"
                      className={`pl-8 h-9 text-xs bg-slate-50 border-slate-200 ${urlError ? "border-rose-500 bg-rose-50" : ""}`}
                      disabled={crawlBrandMutation.isPending}
                    />
                  </div>
                  {urlError && <p className="text-[10px] text-rose-600">URL không hợp lệ</p>}
                  <label className="flex items-center gap-2 text-xs text-slate-600 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={autoCrawl}
                      onChange={(e) => setAutoCrawl(e.target.checked)}
                      className="rounded border-slate-300"
                    />
                    Tự động crawl các trang liên quan (sẽ hỗ trợ sau)
                  </label>
                </div>
              )}

              {isUploading && (
                <div className="space-y-1.5">
                  <Progress value={uploadProgress} className="h-1.5" />
                  <p className="text-[10px] text-slate-500">Đang tải lên... {Math.round(uploadProgress)}%</p>
                </div>
              )}

              {uploadType === "qa" && (
                <Button
                  onClick={() => qaMockMutation.mutate(qaText)}
                  disabled={!qaText.trim() || qaMockMutation.isPending}
                  className="w-full h-8 text-xs bg-indigo-600 hover:bg-indigo-700 gap-1.5"
                >
                  {qaMockMutation.isPending && <Loader2 size={13} className="animate-spin" />}
                  Lưu QA
                </Button>
              )}

              {uploadType === "website" && (
                <Button
                  onClick={handleCrawl}
                  disabled={!urlInput.trim() || urlError || crawlBrandMutation.isPending}
                  className="w-full h-8 text-xs bg-indigo-600 hover:bg-indigo-700 gap-1.5"
                >
                  {crawlBrandMutation.isPending ? <Loader2 size={13} className="animate-spin" /> : <Globe size={13} />}
                  Crawl
                </Button>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* ─── DELETE DIALOG (giữ nguyên logic) ─────────────────── */}
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