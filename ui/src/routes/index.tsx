"use client"

import { useState } from "react"
import { useNavigate } from "@tanstack/react-router"
import { useQuery } from "@tanstack/react-query"
import { Badge } from "@/components/ui/badge"
import { Checkbox } from "@/components/ui/checkbox"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import {
  Mail, Smartphone, Target, FileText, Inbox,
  ChevronLeft, ChevronRight, RefreshCw, Trash2,
  Archive, Edit3, ArrowLeft, User, Radio, Clock, Plus,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { createFileRoute } from "@tanstack/react-router"

// ─── TYPES ───
type ContentItem = {
  id: string
  icon: "email" | "social" | "ads" | "blog"
  title: string
  type: string
  status: "draft" | "published" | "scheduled"
  preview: string
  time: string
  author?: string
  channel?: string
  content?: string
}

// ─── CONSTANTS ───
const STATUS_STYLES = {
  draft:     "bg-amber-50/60 text-amber-700 border-amber-200/60 dark:bg-amber-950/20 dark:text-amber-400 dark:border-amber-900/50",
  published: "bg-emerald-50/60 text-emerald-700 border-emerald-200/60 dark:bg-emerald-950/20 dark:text-emerald-400 dark:border-emerald-900/50",
  scheduled: "bg-blue-50/60 text-blue-700 border-blue-200/60 dark:bg-blue-950/20 dark:text-blue-400 dark:border-blue-900/50",
} as const
const STATUS_LABELS = { draft: "Bản nháp", published: "Đã đăng", scheduled: "Lên lịch" } as const

const ICON_BG = {
  email:  "bg-blue-50 text-blue-600 dark:bg-blue-950/50 dark:text-blue-400",
  social: "bg-pink-50 text-pink-600 dark:bg-pink-950/50 dark:text-pink-400",
  ads:    "bg-amber-50 text-amber-600 dark:bg-amber-950/50 dark:text-amber-400",
  blog:   "bg-emerald-50 text-emerald-600 dark:bg-emerald-950/50 dark:text-emerald-400",
} as const

const TYPE_ICONS = {
  email: Mail, social: Smartphone, ads: Target, blog: FileText,
} as const

const MOCK_DATA: ContentItem[] = [
  {
    id: "1", icon: "email", type: "Email", status: "draft",
    title: "Email marketing Q3",
    preview: "Dear valued customer, we are excited to announce our Q3 product lineup...",
    time: "2 phút trước", author: "Nguyễn Văn A", channel: "Mailchimp",
    content: "<p>Dear valued customer,</p><p>We are excited to announce our <strong>Q3 product lineup</strong> featuring advanced AI workflows and cinematic engine integration.</p><p>Đây là chiến dịch email quan trọng nhất của quý, tập trung vào giá trị gia tăng cho khách hàng trung thành.</p>",
  },
  {
    id: "2", icon: "social", type: "Social", status: "published",
    title: "Social July campaign",
    preview: "Summer sale is here! Giảm giá lên đến 50%...",
    time: "1 ngày trước", author: "Trần Thị B", channel: "Facebook, Instagram",
    content: "<p>Summer sale is here!</p><p>Giảm giá lên đến <strong>50%</strong> cho tất cả dịch vụ trong tháng 7 này.</p><p>Đăng ký ngay hôm nay để nhận ưu đãi đặc biệt!</p>",
  },
  {
    id: "3", icon: "ads", type: "Ads", status: "scheduled",
    title: "Google Ads Tết 2026",
    preview: "Giảm giá Tết lên đến 50% cho doanh nghiệp SME...",
    time: "Ngày mai", author: "Lê Văn C", channel: "Google Ads",
    content: "<p><strong>Headline:</strong> Giải Pháp AI Cho Doanh Nghiệp SME</p><p><strong>Description:</strong> Giảm giá Tết lên đến 50% khi đăng ký sớm hệ thống tự động hóa marketing.</p><p><strong>CTA:</strong> Đăng ký ngay và nhận tư vấn miễn phí trong 30 ngày đầu.</p>",
  },
  {
    id: "4", icon: "blog", type: "Blog", status: "draft",
    title: "Blog: AI cho SME Việt Nam",
    preview: "Trí tuệ nhân tạo đang thay đổi cách doanh nghiệp vận hành...",
    time: "3 giờ trước", author: "Phạm Thị D", channel: "Website",
    content: "<p>Trí tuệ nhân tạo đang thay đổi cách doanh nghiệp vận hành.</p><p>Trong bài viết này, chúng ta sẽ tìm hiểu sâu về <strong>Creative Campaign Engine</strong> — nền tảng AI giúp doanh nghiệp SME tạo nội dung marketing tự động, tiết kiệm 80% thời gian sản xuất.</p>",
  },
  {
    id: "2", icon: "social", type: "Social", status: "published",
    title: "Social July campaign",
    preview: "Summer sale is here! Giảm giá lên đến 50%...",
    time: "1 ngày trước", author: "Trần Thị B", channel: "Facebook, Instagram",
    content: "<p>Summer sale is here!</p><p>Giảm giá lên đến <strong>50%</strong> cho tất cả dịch vụ trong tháng 7 này.</p><p>Đăng ký ngay hôm nay để nhận ưu đãi đặc biệt!</p>",
  },
  {
    id: "3", icon: "ads", type: "Ads", status: "scheduled",
    title: "Google Ads Tết 2026",
    preview: "Giảm giá Tết lên đến 50% cho doanh nghiệp SME...",
    time: "Ngày mai", author: "Lê Văn C", channel: "Google Ads",
    content: "<p><strong>Headline:</strong> Giải Pháp AI Cho Doanh Nghiệp SME</p><p><strong>Description:</strong> Giảm giá Tết lên đến 50% khi đăng ký sớm hệ thống tự động hóa marketing.</p><p><strong>CTA:</strong> Đăng ký ngay và nhận tư vấn miễn phí trong 30 ngày đầu.</p>",
  },
  {
    id: "4", icon: "blog", type: "Blog", status: "draft",
    title: "Blog: AI cho SME Việt Nam",
    preview: "Trí tuệ nhân tạo đang thay đổi cách doanh nghiệp vận hành...",
    time: "3 giờ trước", author: "Phạm Thị D", channel: "Website",
    content: "<p>Trí tuệ nhân tạo đang thay đổi cách doanh nghiệp vận hành.</p><p>Trong bài viết này, chúng ta sẽ tìm hiểu sâu về <strong>Creative Campaign Engine</strong> — nền tảng AI giúp doanh nghiệp SME tạo nội dung marketing tự động, tiết kiệm 80% thời gian sản xuất.</p>",
  },
  {
    id: "4", icon: "blog", type: "Blog", status: "draft",
    title: "Blog: AI cho SME Việt Nam",
    preview: "Trí tuệ nhân tạo đang thay đổi cách doanh nghiệp vận hành...",
    time: "3 giờ trước", author: "Phạm Thị D", channel: "Website",
    content: "<p>Trí tuệ nhân tạo đang thay đổi cách doanh nghiệp vận hành.</p><p>Trong bài viết này, chúng ta sẽ tìm hiểu sâu về <strong>Creative Campaign Engine</strong> — nền tảng AI giúp doanh nghiệp SME tạo nội dung marketing tự động, tiết kiệm 80% thời gian sản xuất.</p>",
  },
  {
    id: "2", icon: "social", type: "Social", status: "published",
    title: "Social July campaign",
    preview: "Summer sale is here! Giảm giá lên đến 50%...",
    time: "1 ngày trước", author: "Trần Thị B", channel: "Facebook, Instagram",
    content: "<p>Summer sale is here!</p><p>Giảm giá lên đến <strong>50%</strong> cho tất cả dịch vụ trong tháng 7 này.</p><p>Đăng ký ngay hôm nay để nhận ưu đãi đặc biệt!</p>",
  },
  {
    id: "3", icon: "ads", type: "Ads", status: "scheduled",
    title: "Google Ads Tết 2026",
    preview: "Giảm giá Tết lên đến 50% cho doanh nghiệp SME...",
    time: "Ngày mai", author: "Lê Văn C", channel: "Google Ads",
    content: "<p><strong>Headline:</strong> Giải Pháp AI Cho Doanh Nghiệp SME</p><p><strong>Description:</strong> Giảm giá Tết lên đến 50% khi đăng ký sớm hệ thống tự động hóa marketing.</p><p><strong>CTA:</strong> Đăng ký ngay và nhận tư vấn miễn phí trong 30 ngày đầu.</p>",
  },
  {
    id: "4", icon: "blog", type: "Blog", status: "draft",
    title: "Blog: AI cho SME Việt Nam",
    preview: "Trí tuệ nhân tạo đang thay đổi cách doanh nghiệp vận hành...",
    time: "3 giờ trước", author: "Phạm Thị D", channel: "Website",
    content: "<p>Trí tuệ nhân tạo đang thay đổi cách doanh nghiệp vận hành.</p><p>Trong bài viết này, chúng ta sẽ tìm hiểu sâu về <strong>Creative Campaign Engine</strong> — nền tảng AI giúp doanh nghiệp SME tạo nội dung marketing tự động, tiết kiệm 80% thời gian sản xuất.</p>",
  },
]

// ─── SHARED ───
function StatusBadge({ status }: { status: ContentItem["status"] }) {
  return (
    <Badge variant="outline" className={cn("text-[11px] font-medium px-2 py-0.5 rounded-full select-none", STATUS_STYLES[status])}>
      {STATUS_LABELS[status]}
    </Badge>
  )
}

function TypeIcon({ icon, className }: { icon: ContentItem["icon"]; className?: string }) {
  const Icon = TYPE_ICONS[icon] || Mail 

  if (!Icon) {
    return <span className="inline-flex w-7 h-7 rounded-lg bg-muted" />
  }

  return (
    <span className={cn("inline-flex items-center justify-center w-7 h-7 rounded-lg flex-shrink-0 transition-transform duration-250 group-hover:scale-105", ICON_BG[icon], className)}>
      <Icon className="h-3.5 w-3.5" />
    </span>
  )
}

// ─── FILTER CHIPS ───
const FILTERS = [
  { label: "Tất cả", value: "all" },
  { label: "Email",  value: "Email" },
  { label: "Social", value: "Social" },
  { label: "Ads",    value: "Ads" },
  { label: "Blog",   value: "Blog" },
] as const

// ─── LIST VIEW ───
function ListView({
  items,
  onSelect,
}: {
  items: ContentItem[]
  onSelect: (id: string) => void
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
          <Button variant="ghost" size="sm" className="h-8 text-xs gap-1.5 text-muted-foreground hover:bg-muted/80">
            <RefreshCw className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Làm mới</span>
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
            return (
              <div
                key={item.id}
                onClick={() => onSelect(item.id)}
                className={cn(
                  "group flex items-center gap-3.5 px-4 h-14 cursor-pointer hover:bg-muted/40 transition-colors select-none",
                  isChecked && "bg-muted/30"
                )}
              >
                <div 
                  onClick={(e) => e.stopPropagation()} 
                  className="w-5 h-5 flex items-center justify-center"
                >
                  <Checkbox
                    className={cn(
                      "h-3.5 w-3.5 rounded-[4px] transition-all duration-150",
                      "opacity-100 sm:opacity-0 sm:group-hover:opacity-100",
                      isChecked && "sm:opacity-100"
                    )}
                    checked={isChecked}
                    onCheckedChange={(c) => toggleOne(item.id, !!c)}
                  />
                </div>

                <TypeIcon icon={item.icon} />

                <div className="flex-1 min-w-0 flex items-baseline gap-2.5">
                  <span className="text-[13.5px] font-medium text-foreground truncate max-w-[240px] sm:max-w-none">
                    {item.title}
                  </span>
                  <StatusBadge status={item.status} />
                  <span className="text-xs text-muted-foreground truncate hidden md:block font-normal max-w-sm">
                    {item.preview}
                  </span>
                </div>

                <span className="text-[11px] text-muted-foreground/80 font-medium whitespace-nowrap shrink-0">
                  {item.time}
                </span>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}

// ─── DETAIL VIEW ───
function DetailView({ item, onClose }: { item: ContentItem; onClose: () => void }) {
  return (
    <div className="flex flex-col h-full bg-background animate-in fade-in-40 duration-200">
      {/* TOOLBAR */}
      <div className="shrink-0 flex items-center justify-between px-4 h-12 border-b border-border/60 bg-background gap-2 select-none">
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" className="h-8 w-8 rounded-lg hover:bg-muted" onClick={onClose}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <Separator orientation="vertical" className="h-4 mx-2" />
          <Button variant="ghost" size="sm" className="h-8 text-xs gap-1.5 text-muted-foreground hover:bg-muted/80">
            <Archive className="h-3.5 w-3.5" />
            <span>Lưu kho</span>
          </Button>
          <Button variant="ghost" size="sm" className="h-8 text-xs gap-1.5 text-destructive hover:bg-destructive/10 hover:text-destructive">
            <Trash2 className="h-3.5 w-3.5" />
            <span>Xóa</span>
          </Button>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <StatusBadge status={item.status} />
          <Separator orientation="vertical" className="h-4 mx-1" />
          <Button size="sm" className="h-8 text-xs gap-1.5 font-medium shadow-xs px-3">
            <Edit3 className="h-3.5 w-3.5" />
            <span>Chỉnh sửa</span>
          </Button>
        </div>
      </div>

      {/* BODY */}
      <div className="flex-1 overflow-y-auto bg-background">
        <div className="max-w-2xl mx-auto px-6 sm:px-8 py-8">

          {/* Eyebrow */}
          <div className="flex items-center gap-2 mb-4">
            <TypeIcon icon={item.icon} />
            <span className="text-xs font-semibold tracking-wider text-muted-foreground uppercase">{item.type}</span>
          </div>

          {/* Title */}
          <h1 className="text-2xl font-bold tracking-tight text-foreground mb-4 leading-snug">
            {item.title}
          </h1>

          {/* Meta row */}
          <div className="flex flex-wrap items-center gap-4 pb-4 mb-6 border-b border-border/40 text-xs text-muted-foreground/90 font-medium">
            {item.author && (
              <span className="flex items-center gap-1.5 bg-muted/40 px-2 py-0.5 rounded-md">
                <User className="h-3.5 w-3.5 opacity-80" /> {item.author}
              </span>
            )}
            {item.channel && (
              <span className="flex items-center gap-1.5 bg-muted/40 px-2 py-0.5 rounded-md">
                <Radio className="h-3.5 w-3.5 opacity-80" /> {item.channel}
              </span>
            )}
            <span className="flex items-center gap-1.5 px-0.5">
              <Clock className="h-3.5 w-3.5 opacity-80" /> {item.time}
            </span>
          </div>

          {/* Content */}
          <div
            className="prose prose-sm dark:prose-invert max-w-none text-[14.5px] leading-7 text-foreground/90 bg-card/30 border border-border/40 p-6 rounded-xl shadow-xs"
            dangerouslySetInnerHTML={{ __html: item.content || item.preview }}
          />
        </div>
      </div>
    </div>
  )
}

// ─── ROUTE ───
export const Route = createFileRoute("/")({
  validateSearch: (search: Record<string, unknown>) => ({
    contentId: (search.contentId as string) || undefined,
  }),
  component: ContentPage,
})

// ─── PAGE ───
function ContentPage() {
  const search = Route.useSearch()
  const navigate = useNavigate()

  const { data: items = [], isLoading } = useQuery({
    queryKey: ["content-list"],
    queryFn: async () => MOCK_DATA,
  })

  const activeItem = items.find((i) => i.id === search.contentId)

  const setId = (id: string | undefined) =>
    navigate({ search: (prev) => ({ ...prev, contentId: id }) })

  if (isLoading) return (
    <div className="flex h-[50vh] items-center justify-center">
      <RefreshCw className="h-4 w-4 animate-spin text-muted-foreground/80" />
    </div>
  )

  return (
    <div className="h-[calc(100vh-4rem)] overflow-hidden bg-background relative">
      
      {/* CỘT DANH SÁCH: Luôn luôn tồn tại trong DOM, chỉ ẩn bằng class 'hidden' khi có activeItem */}
      <div className={cn("h-full", activeItem ? "hidden" : "block")}>
        <ListView items={items} onSelect={(id) => setId(id)} />
      </div>

      {/* CỘT CHI TIẾT: Chỉ render khi được chọn */}
      {activeItem && (
        <div className="absolute inset-0 z-10 h-full w-full bg-background">
          <DetailView item={activeItem} onClose={() => setId(undefined)} />
        </div>
      )}

    </div>
  )
}