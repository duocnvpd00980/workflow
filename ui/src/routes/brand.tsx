// app/(dashboard)/content/page.tsx
"use client"

import { useNavigate } from "@tanstack/react-router"
import { useQuery } from "@tanstack/react-query"
import { Badge } from "@/components/ui/badge"
import { Checkbox } from "@/components/ui/checkbox"
import { 
  Mail, Smartphone, Target, FileText, Inbox, MoreHorizontal, 
  ChevronLeft, ChevronRight, RefreshCw, Trash2, Archive, Edit3, ArrowLeft
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
  content?: string
}

const fetchContentData = async (): Promise<ContentItem[]> => {
  return [
    { id: "1", icon: "email", title: "Email marketing Q3", type: "Email", status: "draft", preview: "Dear valued customer, we are excited to announce our Q3 product lineup...", time: "2m ago", content: "<h1>Email marketing Q3</h1><p>Dear valued customer,</p><p>We are excited to announce our Q3 product lineup featuring advanced AI workflows and cinematic engine integration...</p>" },
    { id: "2", icon: "social", title: "Social July campaign", type: "Social", status: "published", preview: "Summer sale is here! 🌞 Giảm giá lên đến 50%...", time: "1d ago", content: "<p>Summer sale is here! 🌞 Giảm giá lên đến 50% cho tất cả dịch vụ trong tháng 7 này. Đăng ký ngay hôm nay!</p>" },
    { id: "3", icon: "ads", title: "Google Ads Tết 2026", type: "Ads", status: "scheduled", preview: "Giảm giá Tết lên đến 50% cho doanh nghiệp SME...", time: "Tomorrow", content: "<p><strong>Headline:</strong> Giải Pháp AI Cho Doanh Nghiệp SME<br/><strong>Description:</strong> Giảm giá Tết lên đến 50% cho doanh nghiệp SME khi đăng ký sớm hệ thống tự động hóa marketing.</p>" },
    { id: "4", icon: "blog", title: "Blog: AI cho SME", type: "Blog", status: "draft", preview: "Trí tuệ nhân tạo đang thay đổi cách doanh nghiệp...", time: "3h ago", content: "<p>Trí tuệ nhân tạo đang thay đổi cách doanh nghiệp vận hành. Trong bài viết này, chúng ta sẽ tìm hiểu sâu về Creative Campaign Engine...</p>" },
  ]
}

// ─── SUB-COMPONENTS ───
function StatusBadge({ status }: { status: ContentItem["status"] }) {
  const variants = {
    draft: "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/40 dark:text-amber-400 dark:border-amber-900",
    published: "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-400 dark:border-emerald-900",
    scheduled: "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950/40 dark:text-blue-400 dark:border-blue-900",
  }
  const labels = { draft: "Draft", published: "Published", scheduled: "Scheduled" }
  return (
    <Badge variant="outline" className={cn("text-[10px] font-medium px-1.5 py-0 rounded-[4px]", variants[status])}>
      {labels[status]}
    </Badge>
  )
}

function TypeIcon({ type }: { type: ContentItem["icon"] }) {
  const icons = { email: Mail, social: Smartphone, ads: Target, blog: FileText }
  const Icon = icons[type]
  return <Icon className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
}

// ─── RESPONSIVE LIST HEADER ───
function GmailListHeader({ totalItems }: { totalItems: number }) {
  return (
    <div className="flex items-center justify-between px-3 sm:px-4 bg-background border-b border-border/80 h-14 shrink-0 w-full select-none">
      {/* Cụm trái: Checkbox + Action Buttons */}
      <div className="flex items-center gap-1.5 sm:gap-2.5 min-w-0">
        <div className="flex items-center justify-center p-1 hover:bg-accent rounded cursor-pointer transition-colors shrink-0">
          <Checkbox id="select-all" className="h-4 w-4 rounded-[3px]" />
        </div>
        
        <div className="h-4 w-[1px] bg-border shrink-0 mx-0.5 sm:mx-1" />

        {/* Nút Làm mới - Ẩn chữ trên mobile */}
        <button className="flex items-center gap-1 px-2 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-accent border border-border/50 rounded-md shadow-sm transition-colors bg-card shrink-0">
          <RefreshCw className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">Làm mới</span>
        </button>

        {/* Nút Lưu trữ - Ẩn chữ trên mobile */}
        <button className="flex items-center gap-1 px-2 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-accent border border-border/50 rounded-md shadow-sm transition-colors bg-card shrink-0">
          <Archive className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">Lưu trữ</span>
        </button>

        {/* Nút Xóa chọn - Ẩn chữ trên mobile */}
        <button className="flex items-center gap-1 px-2 py-1.5 text-xs font-medium text-destructive hover:bg-destructive/10 border border-destructive/20 rounded-md shadow-sm transition-colors bg-card shrink-0">
          <Trash2 className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">Xóa chọn</span>
        </button>
      </div>

      {/* Cụm phải: Phân trang - Ép shrink-0 để không bị bóp méo width */}
      <div className="flex items-center gap-2 sm:gap-4 text-xs text-muted-foreground font-medium shrink-0 ml-2">
        <span className="text-[11px] sm:text-xs whitespace-nowrap">1-{totalItems} / {totalItems}</span>
        <div className="flex items-center gap-0.5 sm:gap-1 border border-border/60 rounded-md p-0.5 bg-card">
          <button disabled className="p-1 hover:bg-accent rounded disabled:opacity-30 transition-colors">
            <ChevronLeft className="h-3.5 w-3.5" />
          </button>
          <div className="h-3 w-[1px] bg-border" />
          <button disabled className="p-1 hover:bg-accent rounded disabled:opacity-30 transition-colors">
            <ChevronRight className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── RESPONSIVE DETAIL PANEL ───
function ContentDetailPanel({ contentId, onClose }: { contentId: string, onClose: () => void }) {
  const { data } = useQuery({ queryKey: ["content-list"], queryFn: fetchContentData })
  const activeItem = data?.find(item => item.id === contentId)

  if (!activeItem) {
    return (
      <div className="flex h-full flex-col items-center justify-center text-muted-foreground p-4 text-left w-full bg-background">
        <Inbox className="h-8 w-8 opacity-40 mb-2" />
        <p className="text-xs">Không tìm thấy nội dung hoặc đã bị xóa</p>
        <button onClick={onClose} className="mt-4 text-xs text-blue-600 font-medium underline">Quay lại danh sách</button>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col bg-background text-left w-full overflow-hidden animate-in fade-in duration-150">
      {/* Detail Toolbar tối ưu responsive */}
      <div className="flex items-center justify-between px-3 sm:px-4 border-b border-border/80 h-14 shrink-0 bg-background w-full select-none">
        <div className="flex items-center gap-1 sm:gap-2">
          <button 
            onClick={onClose} 
            className="flex items-center justify-center p-1.5 hover:bg-accent rounded-full text-muted-foreground hover:text-foreground transition-colors group" 
            title="Quay lại danh sách"
          >
            <ArrowLeft className="h-4 w-4 group-hover:-translate-x-0.5 transition-transform" />
          </button>
          
          <div className="h-4 w-[1px] bg-border mx-0.5 sm:mx-1" />

          <button title="Lưu trữ bản ghi" className="flex items-center gap-1 px-2 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-accent border border-border/50 rounded-md shadow-sm bg-card transition-colors">
            <Archive className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Lưu kho</span>
          </button>
          <button title="Xóa bản ghi này" className="flex items-center gap-1 px-2 py-1.5 text-xs font-medium text-destructive hover:bg-destructive/10 border border-destructive/20 rounded-md shadow-sm bg-card transition-colors">
            <Trash2 className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Xóa bỏ</span>
          </button>
        </div>

        <div className="flex items-center gap-1.5 sm:gap-3">
          <span className="text-[10px] sm:text-xs font-medium px-1.5 sm:px-2 py-0.5 bg-muted border border-border/40 rounded flex items-center gap-1">
            <TypeIcon type={activeItem.icon} />
            <span className="hidden xs:inline">{activeItem.type}</span>
          </span>
          <StatusBadge status={activeItem.status} />
          
          <div className="h-4 w-[1px] bg-border mx-0.5 sm:mx-1" />
          
          <button className="flex items-center gap-1 px-2.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium rounded-md shadow transition-colors">
            <Edit3 className="h-3.5 w-3.5" /> 
            <span className="hidden sm:inline">Sửa nội dung</span>
          </button>
        </div>
      </div>

      {/* Body Viewport */}
      <div className="flex-1 overflow-y-auto bg-slate-50/40 dark:bg-zinc-950/20 p-4 sm:p-6 md:p-8">
        <div className="max-w-3xl mx-auto bg-background border border-border/60 rounded-xl shadow-sm p-5 sm:p-6 md:p-8 space-y-6">
          <div className="flex items-start justify-between gap-4 w-full">
            <h1 className="text-lg sm:text-xl md:text-2xl font-bold tracking-tight text-foreground/95 leading-snug">{activeItem.title}</h1>
            <span className="text-[11px] text-muted-foreground whitespace-nowrap mt-1 bg-muted/80 px-2 py-0.5 rounded border border-border/30 shrink-0">{activeItem.time}</span>
          </div>
          
          <hr className="border-border/60" />
          
          <div 
            className="prose prose-sm dark:prose-invert max-w-none text-sm md:text-base text-foreground/90 space-y-4 leading-relaxed"
            dangerouslySetInnerHTML={{ __html: activeItem.content || activeItem.preview }}
          />
        </div>
      </div>
    </div>
  )
}

export const Route = createFileRoute("/brand")({
  validateSearch: (search: Record<string, unknown>) => ({
    contentId: (search.contentId as string) || undefined,
  }),
  component: ContentPage,
})

// ─── MAIN COMPONENT ───
function ContentPage() {
  const search = Route.useSearch()
  const navigate = useNavigate()
  
  const { data: contentItems = [], isLoading } = useQuery({
    queryKey: ["content-list"],
    queryFn: fetchContentData
  })

  const currentId = search.contentId

  const handleSelectId = (id: string) => {
    navigate({
      search: (prev) => ({ ...prev, contentId: id })
    })
  }

  const handleCloseDetail = () => {
    navigate({
      search: (prev) => ({ ...prev, contentId: undefined })
    })
  }

  if (isLoading) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (contentItems.length === 0) {
    return (
      <div className="flex h-[60vh] flex-col items-center justify-center px-4 text-center">
        <Inbox className="h-12 w-12 text-muted-foreground/30" />
        <p className="mt-4 text-sm text-muted-foreground font-medium">Chưa có nội dung marketing nào</p>
      </div>
    )
  }

  return (
    <div className="flex h-[calc(100vh-4rem)] overflow-hidden bg-background w-full">
      {!currentId ? (
        <div className="h-full flex flex-col min-w-0 w-full overflow-hidden text-left items-stretch justify-start">
          <GmailListHeader totalItems={contentItems.length} />

          {/* Vùng cuộn danh sách */}
          <div className="flex-1 overflow-y-auto divide-y divide-border/40 w-full bg-card/20">
            {contentItems.map((item) => {
              return (
                <div
                  key={item.id}
                  onClick={() => handleSelectId(item.id)}
                  className="group flex items-start gap-2.5 sm:gap-3 px-3 sm:px-4 py-3.5 cursor-pointer border-b border-border/40 bg-background hover:bg-accent/40 transition-all select-none text-left justify-start w-full"
                >
                  <div className="mt-0.5 flex items-center justify-center shrink-0" onClick={(e) => e.stopPropagation()}>
                    <Checkbox className="h-3.5 w-3.5 rounded-[3px] opacity-70 group-hover:opacity-100" />
                  </div>

                  <div className="mt-0.5 text-muted-foreground shrink-0 flex items-center justify-center">
                    <TypeIcon type={item.icon} />
                  </div>

                  <div className="min-w-0 flex-1 text-left flex flex-col items-start justify-start">
                    <div className="flex items-center gap-2 w-full justify-start">
                      <span className="text-[10px] sm:text-[11px] uppercase tracking-wider font-semibold text-muted-foreground">
                        {item.type}
                      </span>
                      <StatusBadge status={item.status} />
                      <span className="text-[10px] sm:text-[11px] text-muted-foreground ml-auto whitespace-nowrap shrink-0">{item.time}</span>
                    </div>

                    <h3 className="text-sm mt-1 font-medium text-foreground/90 truncate w-full text-left">
                      {item.title}
                    </h3>

                    <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1 w-full text-left">
                      {item.preview}
                    </p>
                  </div>

                  {/* Nút ẩn bớt trên mobile để tránh lệch layout */}
                  <div className="shrink-0 self-center hidden sm:block">
                    <button
                      onClick={(e) => e.stopPropagation()}
                      className="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-muted rounded text-muted-foreground hover:text-foreground"
                    >
                      <MoreHorizontal className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      ) : (
        <div className="flex-1 min-w-0 h-full w-full">
          <ContentDetailPanel contentId={currentId} onClose={handleCloseDetail} />
        </div>
      )}
    </div>
  )
}