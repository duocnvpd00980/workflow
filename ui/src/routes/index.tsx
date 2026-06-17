"use client"

import { useState, useCallback } from "react"
import { useNavigate } from "@tanstack/react-router"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Checkbox } from "@/components/ui/checkbox"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import {
  Inbox,
  ChevronLeft, ChevronRight, RefreshCw, Trash2,
  Archive,
  Mail,
  AlertCircle,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { createFileRoute } from "@tanstack/react-router"
import {
  api,
  type SessionListResponse,
  type ContentItem,
  FILTERS,
  mapSessionToContentItem,
  STATUS_LABELS,
  TYPE_ICONS,
  STATUS_STYLES,
  ICON_BG,
} from "./home/types"
import { DetailView } from "./home/detail-view"
import { Badge } from "@/components/ui/badge"



// ─── SHARED COMPONENTS ───
export function StatusBadge({ status }: { status: ContentItem["status"] }) {
  return (
    <Badge variant="outline" className={cn("text-[11px] font-medium px-2 py-0.5 rounded-full select-none", STATUS_STYLES[status])}>
      {STATUS_LABELS[status]}
    </Badge>
  )
}

export function TypeIcon({ icon, className }: { icon: ContentItem["icon"]; className?: string }) {
  const Icon = TYPE_ICONS[icon] || Mail
  return (
    <span className={cn("inline-flex items-center justify-center w-7 h-7 rounded-lg flex-shrink-0 transition-transform duration-250 group-hover:scale-105", ICON_BG[icon], className)}>
      <Icon className="h-3.5 w-3.5" />
    </span>
  )
}

// ─── ERROR STATE ───
export function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-[50vh] gap-4 text-muted-foreground">
      <AlertCircle className="h-10 w-10 text-destructive/60" />
      <div className="text-center">
        <p className="text-sm font-medium text-destructive mb-1">Đã xảy ra lỗi</p>
        <p className="text-xs max-w-xs">{message}</p>
      </div>
      <Button variant="outline" size="sm" onClick={onRetry} className="gap-1.5">
        <RefreshCw className="h-3.5 w-3.5" />
        Thử lại
      </Button>
    </div>
  )
}
// ─── LIST VIEW ───
function ListView({
  items,
  onSelect,
  onRefresh,
  onDelete,
  onArchive,
  isDeleting,
  deletingIds,
}: {
  items: ContentItem[]
  onSelect: (id: string) => void
  onRefresh: () => void
  onDelete: (ids: string[]) => void
  onArchive: (ids: string[]) => void
  isDeleting: boolean
  deletingIds: Set<string>
}) {
  const [filter, setFilter] = useState("all")
  const [selected, setSelected] = useState<Set<string>>(new Set())

  const filtered = filter === "all" ? items : items.filter((i) => i.type === filter)

  const toggleOne = (id: string, checked: boolean) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (checked) next.add(id)
      else next.delete(id)
      return next
    })
  }

  const toggleAll = (checked: boolean) => {
    setSelected(checked ? new Set(filtered.map((i) => i.id)) : new Set())
  }

  const isAllChecked = filtered.length > 0 && selected.size === filtered.length

  const handleDelete = () => {
    if (selected.size === 0) return
    onDelete(Array.from(selected))
    setSelected(new Set())
  }

  const handleArchive = () => {
    if (selected.size === 0) return
    onArchive(Array.from(selected))
    setSelected(new Set())
  }

  return (
    <div className="flex flex-col h-full bg-background/50">
      {/* TOOLBAR */}
      <div className="shrink-0 flex items-center justify-between px-4 h-12 border-b border-border/60 bg-background gap-2 select-none">
        <div className="flex items-center gap-1">
          <div className="w-6 h-6 flex items-center justify-center">
            <Checkbox
              className="h-3.5 w-3.5 rounded-[4px]"
              checked={isAllChecked}
              onCheckedChange={(c) => toggleAll(!!c)}
            />
          </div>
          <Separator orientation="vertical" className="h-4 mx-1.5" />
          <Button
            variant="ghost"
            size="sm"
            className="h-8 text-xs gap-1.5 text-muted-foreground hover:bg-muted/80"
            onClick={onRefresh}
          >
            <RefreshCw className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Làm mới</span>
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-8 text-xs gap-1.5 text-muted-foreground hover:bg-muted/80"
            onClick={handleArchive}
            disabled={selected.size === 0}
          >
            <Archive className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Lưu trữ</span>
          </Button>
          {selected.size > 0 && (
            <Button
              variant="ghost"
              size="sm"
              className="h-8 text-xs gap-1.5 text-destructive hover:bg-destructive/10 hover:text-destructive"
              onClick={handleDelete}
              disabled={isDeleting}
            >
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
      <div className="shrink-0 flex items-center gap-1.5 px-4 h-11 border-b border-border/40 bg-muted/20 overflow-x-auto scrollbar-none select-none">
        {FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => setFilter(f.value)}
            className={cn(
              "inline-flex items-center px-3 h-6 rounded-full text-xs font-medium whitespace-nowrap transition-all duration-150",
              filter === f.value
                ? "bg-foreground text-background shadow-xs font-semibold"
                : "text-muted-foreground hover:text-foreground hover:bg-accent/80"
            )}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* SCROLLABLE LIST */}
      <div className="flex-1 overflow-y-auto divide-y divide-border/30">
        {filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-3 text-muted-foreground py-12">
            <Inbox className="h-9 w-9 opacity-30 stroke-[1.5]" />
            <p className="text-xs font-medium">Không có nội dung nào</p>
          </div>
        ) : (
          filtered.map((item) => {
            const isChecked = selected.has(item.id)
            const isItemDeleting = deletingIds.has(item.id)
            return (
              <div
                key={item.id}
                onClick={() => !isItemDeleting && onSelect(item.id)}
                role="listitem"
                aria-label={`${item.title}, ${item.status}, ${item.time}`}
                className={cn(
                  "group relative flex items-center h-12 px-3 cursor-pointer select-none",
                  "border-b border-border/10 hover:bg-muted/15",
                  "transition-[background-color] duration-75",
                  "contain-layout-paint",
                  isChecked && "bg-muted/25",
                  (isItemDeleting || isDeleting) && "opacity-50 pointer-events-none"
                )}
              >
                {/* Status indicator - Linear style: instant scan */}
                <div
                  className={cn(
                    "absolute left-0 top-2 bottom-2 w-[3px] rounded-r-full",
                    "transition-transform duration-150",
                    item.status === "completed" && "bg-emerald-400",
                    item.status === "paused" && "bg-amber-400",
                    item.status === "running" && "bg-violet-400",
                    item.status === "error" && "bg-red-400",
                    isChecked ? "scale-y-100" : "scale-y-0 group-hover:scale-y-100"
                  )}
                  role="status"
                  aria-label={`Trạng thái: ${item.status}`}
                />

                {/* Checkbox - Gmail style */}
                <div
                  onClick={(e) => e.stopPropagation()}
                  className="flex items-center justify-center w-8 h-8 -ml-1 mr-1"
                  aria-label={`Chọn ${item.title}`}
                >
                  <div className={cn(
                    "transition-opacity duration-100",
                    !isChecked && "opacity-0 group-hover:opacity-100"
                  )}>
                    <Checkbox
                      className="h-4 w-4 rounded-[3px] border-border/40"
                      checked={isChecked}
                      onCheckedChange={(c) => toggleOne(item.id, !!c)}
                      disabled={isItemDeleting}
                    />
                  </div>
                </div>

                {/* Icon - Notion style: subtle */}
                <div className="flex items-center justify-center w-7 h-7 mr-2 shrink-0">
                  <TypeIcon icon={item.icon} />
                </div>

                {/* Content: Title + Badge + Preview - Apple Mail hierarchy */}
                <div className="flex-1 min-w-0 flex items-center gap-2 mr-3">
                  {/* Title: primary, bold, flexible width */}
                  <span className="text-sm font-semibold text-foreground truncate shrink-0 max-w-[45%]">
                    {item.title}
                  </span>

                  {/* Badge: inline, compact, high contrast */}
                  <span className="shrink-0">
                    <StatusBadge status={item.status} />
                  </span>

                  {/* Preview: secondary, only when space available */}
                  <span className="hidden lg:block text-sm text-muted-foreground/70 truncate">
                    {item.preview}
                  </span>
                </div>

                {/* Right: Time + Actions - Gmail pattern */}
                <div className="flex items-center gap-1 shrink-0">
                  {/* Actions: hover reveal */}
                  <div className={cn(
                    "flex items-center gap-0.5",
                    "opacity-0 group-hover:opacity-100 transition-opacity duration-100",
                    isChecked && "opacity-100"
                  )}>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-muted-foreground/50 hover:text-foreground"
                      onClick={(e) => { e.stopPropagation(); onArchive([item.id]); }}
                      aria-label="Lưu trữ"
                    >
                      <Archive className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-muted-foreground/50 hover:text-destructive"
                      onClick={(e) => { e.stopPropagation(); onDelete([item.id]); }}
                      aria-label="Xóa"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>

                  {/* Time: tabular, right align, hide on hover */}
                  <span className={cn(
                    "text-xs text-muted-foreground/50 whitespace-nowrap w-16 text-right tabular-nums",
                    "group-hover:hidden",
                    isChecked && "hidden"
                  )}>
                    {item.time}
                  </span>
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}

// ─── ROUTE ───
export const Route = createFileRoute("/")({
  validateSearch: (search: Record<string, unknown>) => ({
    contentId: (search.contentId as string) || undefined,
    convId: (search.convId as string) || undefined,  // ← Thêm
  }),
  component: ContentPage,
})

// ─── PAGE ───
function ContentPage() {
  const search = Route.useSearch()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const {
    data: sessionsData,
    isLoading,
    error,
    refetch,
  } = useQuery<SessionListResponse>({
    queryKey: ["marketing-sessions"],
    queryFn: () => api("/marketing/sessions?limit=50&offset=0"),
    refetchInterval: 5000,
    retry: 2,
  })

  const [itemOverrides, setItemOverrides] = useState<Record<string, Partial<ContentItem>>>({})

  const items = (sessionsData?.items || []).map((s) => {
    const mapped = mapSessionToContentItem(s)
    return itemOverrides[mapped.id] ? { ...mapped, ...itemOverrides[mapped.id] } : mapped
  })
  const activeItem = items.find((i) => i.id === search.contentId)

  const setId = useCallback(
    async (id: string | undefined) => {
      if (id) {
        // Tìm session để lấy conversation_id
        const session = sessionsData?.items?.find(s => s.session_id === id)
        const convId = session?.conversation_id  // ← Lấy từ API response

        await queryClient.invalidateQueries({ queryKey: ["marketing-sessions"] })
        await queryClient.prefetchQuery({
          queryKey: ["marketing-detail", id],
          queryFn: () => api(`/marketing/${id}`),
        })

        // Truyền cả contentId và convId
        navigate({
          search: (prev) => ({
            ...prev,
            contentId: id,
            ...(convId && { convId })  // ← Thêm convId nếu có
          })
        } as any)
      } else {
        // Đóng detail - xóa cả 2
        navigate({
          search: (prev) => {
            const next = { ...prev }
            delete next.convId
            delete next.contentId
            return next
          }
        } as any)
      }
    },
    [navigate, queryClient, sessionsData]
  )

  const deleteMutation = useMutation({
    mutationFn: (sessionId: string) => api(`/marketing/session/${sessionId}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["marketing-sessions"] })
      if (search.contentId) setId(undefined)
    },
  })

  const archiveMutation = useMutation({
    mutationFn: (sessionId: string) => {
      const item = items.find(i => i.id === sessionId);
      const group = item?.group || "blog_web";
      
      return api(`/marketing/${sessionId}/resume`, {
        method: "POST",
        body: JSON.stringify({ 
          action: "reject",
          group,  // ✅ Thêm group
        }),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["marketing-sessions"] });
    },
  });

  const [deletingIds, setDeletingIds] = useState<Set<string>>(new Set())

  const handleDelete = useCallback(async (ids: string[]) => {
    setDeletingIds(new Set(ids))
    try {
      await Promise.all(ids.map((id) => deleteMutation.mutateAsync(id)))
    } finally {
      setDeletingIds(new Set())
    }
  }, [deleteMutation])

  const handleArchive = useCallback(async (ids: string[]) => {
    setDeletingIds(new Set(ids))
    try {
      await Promise.all(ids.map((id) => archiveMutation.mutateAsync(id)))
    } finally {
      setDeletingIds(new Set())
    }
  }, [archiveMutation])

  const handleDeleteSingle = useCallback((id: string) => handleDelete([id]), [handleDelete])
  const handleArchiveSingle = useCallback((id: string) => handleArchive([id]), [handleArchive])

  const handleUpdateItem = useCallback((updatedItem: ContentItem) => {
    setItemOverrides(prev => ({
      ...prev,
      [updatedItem.id]: { content: updatedItem.content },
    }))
    // Cập nhật cache list luôn để không bị override
    queryClient.setQueryData(["marketing-sessions"], (old: SessionListResponse | undefined) => {
      if (!old) return old
      return {
        ...old,
        items: old.items.map((s) =>
          s.session_id === updatedItem.id
            ? { ...s, draft: { ...s.draft, content: updatedItem.content } }
            : s
        ),
      }
    })
  }, [queryClient])

  if (isLoading) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <RefreshCw className="h-4 w-4 animate-spin text-muted-foreground/80" />
      </div>
    )
  }

  if (error) {
    return (
      <ErrorState
        message={error instanceof Error ? error.message : "Không thể tải danh sách nội dung"}
        onRetry={() => refetch()}
      />
    )
  }

  return (
    <div className="h-[calc(100vh-4rem)] overflow-hidden bg-background relative">
      <div className={cn("h-full", activeItem ? "hidden" : "block")}>
        <ListView
          items={items}
          onSelect={(id) => setId(id)}
          onRefresh={() => refetch()}
          onDelete={handleDelete}
          onArchive={handleArchive}
          isDeleting={deleteMutation.isPending || archiveMutation.isPending}
          deletingIds={deletingIds}
        />
      </div>

      {activeItem && (
        <div className="absolute inset-0 z-10 h-full w-full bg-background">
          <DetailView
            item={activeItem}
            onClose={() => setId(undefined)}
            onDelete={handleDeleteSingle}
            onArchive={handleArchiveSingle}
            isLoading={deleteMutation.isPending || archiveMutation.isPending}
            onUpdate={handleUpdateItem}
          />
        </div>
      )}
    </div>
  )
}