"use client"

import { useState } from "react"
import { useNavigate } from "@tanstack/react-router"
import { useQuery } from "@tanstack/react-query"
import { Badge } from "@/components/ui/badge"
import { Checkbox } from "@/components/ui/checkbox"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import {
  Building2, Store, Cpu, Briefcase, Inbox,
  ChevronLeft, ChevronRight, RefreshCw, Archive,
  Edit3, ArrowLeft, Target, ShieldCheck, CheckCircle2, XCircle, Clock, Trash2,
  BarChart3, Settings, Download, Send, Play, FileCheck,
  Mail,
  Smartphone,
  FileText,
  Plus,
} from "lucide-react"

import { cn } from "@/lib/utils"
import { createFileRoute } from "@tanstack/react-router"
import { ResearchBackgroundWidget } from "./ResearchBackgroundWidget"

// ─── TYPES ───
type ContentItem = {
  id: string
  icon: "fintech" | "ecom" | "tech" | "service"
  title: string // Tên doanh nghiệp / Thương hiệu
  type: string  // Lĩnh vực hoạt động
  status: "draft" | "published" | "scheduled" // Trạng thái kiểm duyệt hồ sơ
  preview: string // Tóm tắt định vị nhanh
  time: string
  
  // Dữ liệu Brand Voice chi tiết của doanh nghiệp
  positioning: string   // Định vị thương hiệu
  targetAudience: string // Khách hàng mục tiêu
  usp: string           // Điểm khác biệt cốt lõi
  voiceModel: string    // Hình mẫu ngôn từ / Khẩu khí
  dos: string[]         // Quy tắc nên làm
  donts: string[]       // Quy tắc cần tránh
}

// ─── CONSTANTS (PREMIUM BRAND PROFILE STYLES) ───
const STATUS_STYLES = {
  draft:     "bg-amber-50/50 text-amber-700 border-amber-200/50 dark:bg-amber-950/20 dark:text-amber-400 dark:border-amber-900/40",
  published: "bg-emerald-50/50 text-emerald-700 border-emerald-200/50 dark:bg-emerald-950/20 dark:text-emerald-400 dark:border-emerald-900/40",
  scheduled: "bg-blue-50/50 text-blue-700 border-blue-200/50 dark:bg-blue-950/20 dark:text-blue-400 dark:border-blue-900/40",
} as const

const STATUS_LABELS = { 
  draft: "Chờ tối ưu", 
  published: "Đã duyệt", 
  scheduled: "Bản nháp AI" 
} as const

const ICON_BG = {
  fintech: "bg-blue-50/70 text-blue-600 dark:bg-blue-950/40 dark:text-blue-400",
  ecom:    "bg-rose-50/70 text-rose-600 dark:bg-rose-950/40 dark:text-rose-400",
  tech:    "bg-purple-50/70 text-purple-600 dark:bg-purple-950/40 dark:text-purple-400",
  service: "bg-emerald-50/70 text-emerald-600 dark:bg-emerald-950/40 dark:text-emerald-400",
} as const

const TYPE_ICONS = {
  fintech: Building2, ecom: Store, tech: Cpu, service: Briefcase,
} as const

// ─── MOCK DATA (REAL BRAND PROFILES) ───
const MOCK_DATA: ContentItem[] = [
  {
    id: "1", icon: "fintech", type: "Fintech", status: "published",
    title: "Acme Corp",
    preview: "Ngân hàng số dành riêng cho cộng đồng doanh nghiệp vừa và nhỏ (SME)...",
    time: "2 giờ trước",
    positioning: "Ngân hàng số toàn diện dành riêng cho phân khúc doanh nghiệp vừa và nhỏ (SME).",
    targetAudience: "Chủ doanh nghiệp nhỏ, startup có quy mô từ 25 - 50 nhân sự tại Việt Nam.",
    usp: "Tối ưu hóa và tiết kiệm đến 30% thời gian xử lý nghiệp vụ quản lý tài chính dòng tiền.",
    voiceModel: "Chuyên nghiệp, đáng tin cậy, sử dụng cấu trúc ngôn từ rõ ràng, minh bạch thông tin.",
    dos: ["Dùng số liệu chứng minh cụ thể", "Thuật ngữ tài chính chuẩn xác", "Xưng hô đối tác trang trọng"],
    donts: ["Không sử dụng từ lóng/slang", "Tránh viết câu quá dài, mơ hồ", "Không hứa hẹn thiếu cơ sở"]
  },
  {
    id: "2", icon: "ecom", type: "E-Commerce", status: "draft",
    title: "ShopX Việt Nam",
    preview: "Nền tảng chuỗi cung ứng mỹ phẩm thiên nhiên, phong cách trẻ trung...",
    time: "5 phút trước",
    positioning: "Hệ thống phân phối mỹ phẩm thuần chay, định hướng phong cách sống xanh bền vững.",
    targetAudience: "Thế hệ người tiêu dùng trẻ (Gen Z & Millennials) quan tâm đến sức khỏe và môi trường.",
    usp: "100% nguyên liệu bản địa đạt chứng nhận hữu cơ quốc tế với mức giá dễ tiếp cận.",
    voiceModel: "Thân thiện, gần gũi, truyền cảm hứng tích cực, sử dụng ngôn từ sinh động mộc mạc.",
    dos: ["Lồng ghép câu chuyện thực tế", "Sử dụng từ ngữ gợi mở cảm xúc", "Tập trung vào yếu tố an lành"],
    donts: ["Tránh giọng điệu quá cứng nhắc", "Không dùng thuật ngữ hóa học nặng nề", "Hạn chế so sánh tiêu cực"]
  },
  {
    id: "3", icon: "tech", type: "TechFlow", status: "draft",
    title: "TechFlow Solutions",
    preview: "Giải pháp tự động hóa quy trình bằng hạ tầng trí tuệ nhân tạo (AI)...",
    time: "1 ngày trước",
    positioning: "Đơn vị cung ứng hạ tầng tự động hóa quy trình cốt lõi bằng công nghệ Trí tuệ nhân tạo (AI).",
    targetAudience: "Giám đốc công nghệ (CTO), Trưởng phòng vận hành doanh nghiệp sản xuất và Logistics.",
    usp: "Tăng 80% hiệu suất vận hành chuỗi cung ứng nhờ thuật toán tối ưu hóa tọa độ thời gian thực.",
    voiceModel: "Mang tính chuyên gia, học thuật sắc sảo, đáng tin cậy và có thẩm quyền cao.",
    dos: ["Đưa thông số kỹ thuật rõ ràng", "Phân tích logic nguyên nhân - kết quả", "Dẫn chứng case study thực tế"],
    donts: ["Không sử dụng lối nói đại khái", "Hạn chế mỹ từ sáo rỗng", "Tránh đơn giản hóa vấn đề quá mức"]
  }
]

// ─── SHARED ───
function StatusBadge({ status }: { status: ContentItem["status"] }) {
  return (
    <Badge variant="outline" className={cn("text-[11px] font-medium px-2 py-0.5 rounded-full select-none tracking-wide", STATUS_STYLES[status])}>
      {STATUS_LABELS[status]}
    </Badge>
  )
}

function TypeIcon({ icon, className }: { icon: ContentItem["icon"]; className?: string }) {
  const Icon = TYPE_ICONS[icon]
  return (
    <span className={cn("inline-flex items-center justify-center w-7 h-7 rounded-lg flex-shrink-0 transition-transform duration-250 group-hover:scale-105", ICON_BG[icon], className)}>
      <Icon className="h-3.5 w-3.5" />
    </span>
  )
}

// ─── FILTER CHIPS ───
const FILTERS = [
  { label: "Tất cả thương hiệu", value: "all" },
  { label: "Fintech", value: "Fintech" },
  { label: "E-Commerce", value: "E-Commerce" },
  { label: "TechFlow", value: "TechFlow" },
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
            <span className="hidden sm:inline">Đồng bộ lại</span>
          </Button>
          <Button variant="ghost" size="sm" className="h-8 text-xs gap-1.5 text-muted-foreground hover:bg-muted/80">
            <Archive className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Lưu kho hồ sơ</span>
          </Button>
          {selected.size > 0 && (
            <Button variant="ghost" size="sm" className="h-8 text-xs gap-1.5 text-destructive hover:bg-destructive/10 hover:text-destructive">
              <Trash2 className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Gỡ bỏ ({selected.size})</span>
            </Button>
          )}
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <span className="text-xs text-muted-foreground hidden sm:inline font-medium">
            Hồ sơ: {filtered.length} thương hiệu
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
            <p className="text-xs font-medium">Danh sách thương hiệu trống</p>
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
                  <span className="text-[13.5px] font-semibold text-foreground truncate max-w-[240px] sm:max-w-none">
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
// ─── DETAIL VIEW (ĐỒNG BỘ 100% VỚI REAL SCREENSHOTS) ───


function DetailView({ item, onClose }: { item: any; onClose: () => void }) {
  const [isEditModalOpen, setIsEditModalOpen] = useState(false)

  return (
    <div className="flex flex-col h-full bg-background animate-in fade-in-40 duration-200">
      {/* TOOLBAR */}
      <div className="shrink-0 flex items-center justify-between px-4 h-12 border-b border-border/60 bg-background gap-2 select-none">
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" className="h-8 w-8 rounded-lg hover:bg-muted" onClick={onClose}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <Separator orientation="vertical" className="h-4 mx-2" />
          <span className="text-xs font-semibold text-muted-foreground">Hồ sơ ngôn sắc</span>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <Badge variant="outline" className="text-[11px] font-medium px-2 py-0.5 rounded-full bg-emerald-50/50 text-emerald-700 border-emerald-200/50 dark:bg-emerald-950/20 dark:text-emerald-400">
            Đã duyệt
          </Badge>
          <Separator orientation="vertical" className="h-4 mx-1" />
          <Button 
            size="sm" 
            variant="outline"
            className="h-8 text-xs gap-1.5 font-medium px-3"
            onClick={() => setIsEditModalOpen(true)}
          >
            <Edit3 className="h-3.5 w-3.5" />
            <span>Chỉnh sửa</span>
          </Button>
          <Button size="sm" variant="outline" className="h-8 text-xs gap-1.5 font-medium px-3">
            <Download className="h-3.5 w-3.5" />
            <span>Export</span>
          </Button>
        </div>
      </div>

      {/* BODY CONTAINER */}
      <div className="flex-1 overflow-y-auto bg-slate-50/40 dark:bg-background">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6 space-y-6">
          
          {/* TOP SECTION: KẾT QUẢ PHÂN TÍCH THƯƠNG HIỆU */}
          <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
            
            {/* Cột trái: Tone Analysis Graph Mockup */}
            <div className="md:col-span-7 bg-background border border-border/60 rounded-xl p-5 shadow-xs">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold tracking-tight text-foreground">Tone Analysis</h3>
              </div>
              {/* Giữ nguyên khung Canvas/SVG Biểu đồ mạng nhện của bạn tại đây */}
              <div className="h-64 bg-muted/20 border border-dashed border-border/60 rounded-xl flex items-center justify-center text-xs text-muted-foreground/80 font-medium">
                [ Khung hiển thị Biểu đồ Radar Tone ]
              </div>
              <div className="grid grid-cols-2 gap-4 mt-4 pt-4 border-t border-border/40 text-center">
                <div>
                  <div className="text-2xl font-bold tracking-tight text-foreground">90%</div>
                  <div className="text-[11px] text-muted-foreground font-medium uppercase tracking-wider">Chuyên nghiệp</div>
                </div>
                <div>
                  <div className="text-2xl font-bold tracking-tight text-foreground">85%</div>
                  <div className="text-[11px] text-muted-foreground font-medium uppercase tracking-wider">Đáng tin cậy</div>
                </div>
              </div>
            </div>

            {/* Cột phải: Brand Summary */}
            <div className="md:col-span-5 bg-background border border-border/60 rounded-xl p-5 shadow-xs flex flex-col justify-between">
              <div>
                <h3 className="text-sm font-semibold tracking-tight text-foreground mb-4">Brand Summary</h3>
                <div className="space-y-4">
                  <div>
                    <span className="block text-[10px] font-bold tracking-wider text-muted-foreground/80 uppercase mb-0.5">Định vị thương hiệu</span>
                    <p className="text-[13px] text-foreground/90 font-medium">{item.positioning}</p>
                  </div>
                  <div>
                    <span className="block text-[10px] font-bold tracking-wider text-muted-foreground/80 uppercase mb-0.5">Khách hàng mục tiêu</span>
                    <p className="text-[13px] text-foreground/90 font-medium">{item.targetAudience}</p>
                  </div>
                  <div>
                    <span className="block text-[10px] font-bold tracking-wider text-muted-foreground/80 uppercase mb-0.5">Giá trị cốt lõi / USP</span>
                    <p className="text-[13px] text-foreground/90 font-medium">{item.usp}</p>
                  </div>
                  <div>
                    <span className="block text-[10px] font-bold tracking-wider text-muted-foreground/80 uppercase mb-0.5">Hình mẫu ngôn từ</span>
                    <p className="text-[13.5px] text-foreground/90 font-semibold italic">"{item.voiceModel}"</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* MIDDLE SECTION: GRID CHỌN LOẠI CONTENT ENGINE */}
          <div className="bg-background border border-border/60 rounded-xl p-5 shadow-xs space-y-4">
            <div className="flex items-baseline justify-between">
              <h3 className="text-sm font-semibold tracking-tight text-foreground">AI Viết Content</h3>
              <span className="text-[11px] text-muted-foreground font-medium">Chọn loại định dạng — Hệ thống tự động căn chỉnh khẩu khí</span>
            </div>
            
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3.5">
              {[
                { label: "Email", style: "Professional + Warm", color: "bg-blue-50 text-blue-600 dark:bg-blue-950/40" },
                { label: "Social", style: "Professional + Playful", color: "bg-rose-50 text-rose-600 dark:bg-rose-950/40" },
                { label: "Blog", style: "Professional + Educational", color: "bg-purple-50 text-purple-600 dark:bg-purple-950/40" },
                { label: "Ads", style: "Professional + Persuasive", color: "bg-amber-50 text-amber-600 dark:bg-amber-950/40" },
                { label: "PR", style: "Professional + Formal", color: "bg-emerald-50 text-emerald-600 dark:bg-emerald-950/40" },
              ].map((card, i) => (
                <div key={i} className="group border border-border/60 hover:border-foreground/20 rounded-xl p-4 flex flex-col items-center text-center cursor-pointer hover:bg-muted/30 transition-all duration-200">
                  <span className={cn("w-8 h-8 rounded-lg flex items-center justify-center mb-2.5 shadow-2xs", card.color)}>
                    {i === 0 && <Mail className="h-4 w-4" />}
                    {i === 1 && <Smartphone className="h-4 w-4" />}
                    {i === 2 && <FileText className="h-4 w-4" />}
                    {i === 3 && <Target className="h-4 w-4" />}
                    {i === 4 && <FileCheck className="h-4 w-4" />}
                  </span>
                  <span className="text-[13px] font-semibold text-foreground mb-0.5">{card.label}</span>
                  <span className="text-[10px] text-muted-foreground/80 font-medium whitespace-nowrap">{card.style}</span>
                </div>
              ))}
            </div>
          </div>

          {/* LOWER SECTION: AI TEST PANEL */}
          <div className="bg-background border border-border/60 rounded-xl p-5 shadow-xs space-y-3">
            <div className="flex items-baseline justify-between">
              <h3 className="text-sm font-semibold tracking-tight text-foreground">AI Test Panel</h3>
              <span className="text-[11px] text-muted-foreground font-medium">Thử nghiệm cấu trúc câu từ trước khi phân tách chiến dịch</span>
            </div>
            <div className="flex items-center gap-2">
              <input 
                type="text" 
                placeholder="Ví dụ: Viết đoạn mô tả ngắn giới thiệu giải pháp dòng tiền số..." 
                className="flex-1 h-9 bg-background border border-border/80 rounded-lg px-3 text-xs font-medium focus:outline-none focus:border-foreground/30 placeholder:text-muted-foreground/60 shadow-2xs"
              />
              <Button size="sm" className="h-9 text-xs gap-1.5 font-medium px-4 shadow-sm">
                <RefreshCw className="h-3.5 w-3.5" />
                <span>Kiểm tra thử</span>
              </Button>
            </div>
          </div>

          {/* BOTTOM SECTION: LỊCH SỬ SỬ DỤNG */}
          <div className="bg-background border border-border/60 rounded-xl overflow-hidden shadow-xs">
            <div className="px-5 py-4 border-b border-border/40">
              <h3 className="text-sm font-semibold tracking-tight text-foreground">Nhật ký phát hành</h3>
            </div>
            <div className="divide-y divide-border/30">
              {[
                { title: "Email Định vị Thương hiệu tháng 6", date: "12/06/2026", status: "Đã gửi", color: "text-emerald-600" },
                { title: "Nội dung truyền thông Mạng xã hội Q2", date: "10/06/2026", status: "Đang chạy", color: "text-blue-600" },
                { title: "Trang đích Sản phẩm Ngân hàng số", date: "05/06/2026", status: "Đã duyệt", color: "text-muted-foreground" },
              ].map((log, idx) => (
                <div key={idx} className="flex items-center justify-between px-5 h-12 hover:bg-muted/20 transition-colors text-xs select-none">
                  <div className="flex items-center gap-3">
                    <span className="w-6 h-6 rounded-md bg-muted/40 flex items-center justify-center text-muted-foreground">
                      {idx === 0 ? <Mail className="h-3 w-3" /> : idx === 1 ? <Smartphone className="h-3 w-3" /> : <FileCheck className="h-3 w-3" />}
                    </span>
                    <div>
                      <div className="font-semibold text-foreground/90">{log.title}</div>
                      <div className="text-[10px] text-muted-foreground/70 font-medium">{log.date}</div>
                    </div>
                  </div>
                  <span className={cn("font-semibold text-[11px]", log.color)}>{log.status}</span>
                </div>
              ))}
            </div>
          </div>

        </div>
      </div>

      {/* ─── MODAL CHỈNH SỬA (ĐỒNG BỘ THEO SCREENSHOT 15-24-14) ─── */}
      {isEditModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/40 backdrop-blur-xs select-none animate-in fade-in-20">
          <div className="bg-background border border-border/80 w-full max-w-xl rounded-xl shadow-lg flex flex-col max-h-[90vh] overflow-hidden">
            
            {/* Modal Header */}
            <div className="px-5 py-4 border-b border-border/40 flex items-center justify-between shrink-0">
              <div>
                <h2 className="text-base font-bold text-foreground">Chỉnh sửa: {item.title}</h2>
                <p className="text-[11px] text-muted-foreground/80 font-medium mt-0.5">Dữ liệu được phân tích tự động từ Nghiên cứu #123</p>
              </div>
              <button onClick={() => setIsEditModalOpen(false)} className="text-muted-foreground hover:text-foreground text-sm font-semibold">✕</button>
            </div>

            {/* Modal Content Scrollable */}
            <div className="p-5 overflow-y-auto space-y-5 flex-1">
              {/* Sliders Container */}
              <div className="space-y-4 bg-muted/10 border border-border/40 p-4 rounded-xl">
                <span className="block text-[11px] font-bold text-muted-foreground uppercase tracking-wider mb-2">Tone Cấu Hình (Kéo điều chỉnh nếu AI phân tích sai)</span>
                
                {[
                  { left: "Hài hước", right: "Trang trọng" },
                  { left: "Nghiêm túc", right: "Thân thiện" },
                  { left: "Tôn kính", right: "Suồng sã" },
                  { left: "Nhiệt huyết", right: "Thực tế" }
                ].map((slider, idx) => (
                  <div key={idx} className="space-y-1">
                    <div className="flex justify-between text-[11px] font-medium text-muted-foreground/90 px-0.5">
                      <span>{slider.left}</span>
                      <span>{slider.right}</span>
                    </div>
                    <div className="relative w-full h-1.5 bg-muted rounded-full flex items-center">
                      <div className="absolute left-[70%] w-3.5 h-3.5 rounded-full bg-primary border-2 border-background shadow-xs transform -translate-x-1/2 cursor-pointer" />
                    </div>
                  </div>
                ))}
              </div>

              {/* Voice Description Description Box */}
              <div className="space-y-1.5">
                <span className="block text-[11px] font-bold text-muted-foreground uppercase tracking-wider">Đặc tả khẩu khí (AI generated)</span>
                <textarea 
                  rows={3}
                  className="w-full bg-background border border-border/80 rounded-xl p-3 text-xs font-medium leading-relaxed focus:outline-none focus:border-foreground/30 shadow-2xs"
                  defaultValue="Giọng điệu chuyên nghiệp, đáng tin cậy, dùng ngôn ngữ rõ ràng và có cấu trúc. Thích hợp cho khối B2B tài chính, đối tượng doanh nghiệp SME cần sự chắc chắn, an toàn tối đa."
                />
              </div>

              {/* DO'S & DON'TS BOXES */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* DO'S */}
                <div className="bg-emerald-50/20 dark:bg-emerald-950/10 border border-emerald-500/20 p-3.5 rounded-xl">
                  <div className="flex items-center gap-1.5 text-emerald-700 dark:text-emerald-400 font-bold text-[11px] uppercase tracking-wider mb-2">
                    <CheckCircle2 className="h-3.5 w-3.5" /> Quy tắc nên làm
                  </div>
                  <ul className="space-y-1.5 text-xs text-foreground/80 font-medium">
                    <li className="flex items-center gap-2">✓ Dùng số liệu thực tế chứng minh</li>
                    <li className="flex items-center gap-2">✓ Giải thích lợi ích rõ ràng</li>
                    <li className="flex items-center gap-2">✓ Giọng điệu ổn định, trang nhã</li>
                  </ul>
                </div>

                {/* DON'TS */}
                <div className="bg-rose-50/20 dark:bg-rose-950/10 border border-rose-500/20 p-3.5 rounded-xl">
                  <div className="flex items-center gap-1.5 text-rose-700 dark:text-rose-400 font-bold text-[11px] uppercase tracking-wider mb-2">
                    <XCircle className="h-3.5 w-3.5" /> Quy tắc cần tránh
                  </div>
                  <ul className="space-y-1.5 text-xs text-foreground/80 font-medium">
                    <li className="flex items-center gap-2">✕ Không dùng từ lóng, tiếng bồi</li>
                    <li className="flex items-center gap-2">✕ Không hứa hẹn vô căn cứ</li>
                    <li className="flex items-center gap-2">✕ Không so sánh tiêu cực đối thủ</li>
                  </ul>
                </div>
              </div>
            </div>

            {/* Modal Footer Buttons */}
            <div className="px-5 py-3.5 border-t border-border/40 bg-muted/10 flex items-center justify-between text-xs shrink-0">
              <span className="text-[10px] text-muted-foreground/70 font-medium">Cập nhật: Phân tích ngày 15/06 lúc 14:30</span>
              <div className="flex items-center gap-2">
                <Button variant="ghost" size="sm" className="h-8 text-xs font-semibold px-3" onClick={() => setIsEditModalOpen(false)}>
                  Hủy bỏ
                </Button>
                <Button size="sm" className="h-8 text-xs font-semibold px-4 shadow-sm" onClick={() => setIsEditModalOpen(false)}>
                  Lưu thay đổi
                </Button>
              </div>
            </div>

          </div>
        </div>
      )}
    </div>
  )
}

// ─── ROUTE ───
export const Route = createFileRoute("/brand")({
  validateSearch: (search: Record<string, unknown>) => ({
    contentId: (search.contentId as string) || undefined,
  }),
  component: ContentPage,
})

// ─── PAGE ───
function ContentPage() {
  const search = Route.useSearch()
  const navigate = useNavigate()
  const [localItems, setLocalItems] = useState<ContentItem[]>(MOCK_DATA)

  const { data: items = [], isLoading } = useQuery({
    queryKey: ["content-list"],
    queryFn: async () => MOCK_DATA,
  })

  const activeItem = items.find((i) => i.id === search.contentId)

  const setId = (id: string | undefined) =>
    navigate({ search: (prev) => ({ ...prev, contentId: id }) } as any)


  if (isLoading) return (
    <div className="flex h-[50vh] items-center justify-center">
      <RefreshCw className="h-4 w-4 animate-spin text-muted-foreground/80" />
    </div>
  )

  return (
  <div className="h-[calc(100vh-4rem)] overflow-hidden bg-background relative">
    {activeItem ? (
      <DetailView item={activeItem} onClose={() => setId(undefined)} />
    ) : (
      <ListView 
        items={items} 
        onSelect={(id) => setId(id)} 
      />
    )}
  </div>
)
}