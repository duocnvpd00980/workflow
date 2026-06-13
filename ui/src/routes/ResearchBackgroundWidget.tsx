"use client"

import { useState, useEffect } from "react"
import { 
  Bot, Loader2, Search, Minus, Maximize2, X, 
  AlertCircle, Check, CheckCircle2, ArrowRight, Sparkles 
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

type WidgetStep = "INPUT_FORM" | "ANALYZING" | "RESEARCH_DONE"

interface ResearchBackgroundWidgetProps {
  isOpen: boolean
  onClose: () => void
  onComplete: (data: any) => void
}

export function ResearchBackgroundWidget({ 
  isOpen, 
  onClose, 
  onComplete 
}: ResearchBackgroundWidgetProps) {
  const [isMinimized, setIsMinimized] = useState(false)
  const [step, setStep] = useState<WidgetStep>("INPUT_FORM")
  
  // Form States
  const [companyName, setCompanyName] = useState("")
  const [website, setWebsite] = useState("")
  const [industry, setIndustry] = useState("")

  // Simulation Progress (Trong thực tế sẽ đồng bộ qua SSE hoặc WebSocket)
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    let interval: any
    if (step === "ANALYZING") {
      interval = setInterval(() => {
        setProgress((p) => {
          if (p >= 100) {
            clearInterval(interval)
            setStep("RESEARCH_DONE")
            setIsMinimized(false) // Tự động bung to khi job chạy ngầm hoàn tất
            return 100
          }
          return p + 1
        })
      }, 250)
    }
    return () => clearInterval(interval)
  }, [step])

  if (!isOpen) return null

  const handleStart = (e: React.FormEvent) => {
    e.preventDefault()
    if (!companyName) return
    setStep("ANALYZING")
    setIsMinimized(true) // Thu nhỏ xuống góc ngay lập tức để giải phóng UI cho người dùng
  }

  const handleApply = () => {
    onComplete({
      title: companyName,
      type: industry || "General",
      positioning: `Hệ thống định vị chiến lược toàn diện cho thị trường ${industry || "Doanh nghiệp"}.`,
      targetAudience: "Nhóm khách hàng mục tiêu chuyển đổi số thế hệ mới.",
      usp: "Tự động hóa bóc tách insights hành vi người dùng tối ưu hóa phễu nội dung.",
      voiceModel: "Sắc sảo, thực tế, uy tín hàng đầu ngành.",
      icon: industry === "Fintech" ? "fintech" : industry === "E-Commerce" ? "ecom" : "tech"
    })
    
    // Reset Form Trạng thái ban đầu
    setCompanyName("")
    setWebsite("")
    setIndustry("")
    setProgress(0)
    setStep("INPUT_FORM")
    onClose()
  }

  return (
    <div 
      className={cn(
        // Mobile: Trở thành Bottom Sheet chiếm trọn chiều ngang | Desktop: Góc phải màn hình giống Gmail
        "fixed bottom-0 left-0 right-0 sm:left-auto sm:right-4 z-50 bg-background border border-border/80 rounded-t-xl shadow-2xl transition-all duration-300 flex flex-col overflow-hidden select-none",
        isMinimized 
          ? "h-11 sm:w-80" 
          : "h-[80vh] sm:h-[540px] w-full sm:w-[440px]"
      )}
    >
      {/* WIDGET HEADER (CLICK ĐỂ TOGGLE THU NHỎ / PHÓNG TO) */}
      <div 
        onClick={() => setIsMinimized(!isMinimized)}
        className="shrink-0 h-11 bg-slate-900 text-slate-100 dark:bg-zinc-800 dark:text-zinc-100 px-3.5 flex items-center justify-between cursor-pointer hover:bg-slate-850"
      >
        <div className="flex items-center gap-2 min-w-0">
          <Bot className={cn("h-4 w-4 shrink-0 text-sky-400", step === "ANALYZING" && "animate-spin")} />
          <span className="text-xs font-bold truncate">
            {step === "INPUT_FORM" && "Tạo Brand Voice tự động"}
            {step === "ANALYZING" && `Đang quét: ${companyName} (${progress}%)`}
            {step === "RESEARCH_DONE" && `✨ Đã hoàn thành: ${companyName}`}
          </span>
        </div>
        
        {/* WINDOW SYSTEM CONTROLS */}
        <div className="flex items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
          <button 
            onClick={() => setIsMinimized(!isMinimized)}
            className="p-1 hover:bg-white/10 rounded-md text-slate-400 hover:text-white transition-colors"
          >
            {isMinimized ? <Maximize2 className="h-3 w-3" /> : <Minus className="h-3 w-3" />}
          </button>
          <button 
            onClick={onClose}
            className="p-1 hover:bg-white/10 rounded-md text-slate-400 hover:text-white transition-colors"
          >
            <X className="h-3 w-3" />
          </button>
        </div>
      </div>

      {/* WIDGET BODY CONTENT */}
      {!isMinimized && (
        <div className="flex-1 overflow-y-auto p-4 bg-background flex flex-col justify-between space-y-4">
          
          {/* STEP 1: INPUT FORM */}
          {step === "INPUT_FORM" && (
            <form onSubmit={handleStart} className="space-y-4 h-full flex flex-col justify-between flex-1">
              <div className="space-y-3.5">
                <div className="flex items-start gap-2.5 p-2.5 bg-muted/30 border border-border/40 rounded-lg">
                  <AlertCircle className="h-4 w-4 text-muted-foreground shrink-0 mt-0.5" />
                  <p className="text-[11px] text-muted-foreground/90 font-medium leading-normal">
                    Tác vụ Deep Research tốn khoảng 1-2 giờ chạy ngầm trên Cloud Cluster. Bạn hoàn toàn có thể đóng khay này hoặc tắt máy, tiến trình phân tích không bị gián đoạn.
                  </p>
                </div>
                
                <div className="space-y-1">
                  <label className="text-[11px] font-bold text-foreground/80">Tên doanh nghiệp / Thương hiệu *</label>
                  <input 
                    type="text" required placeholder="VD: ShopX Việt Nam" value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    className="w-full h-9 bg-background border border-border/80 focus:outline-none focus:border-foreground/30 rounded-lg px-2.5 text-xs font-medium"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] font-bold text-foreground/80">Website liên kết (URL)</label>
                  <input 
                    type="url" placeholder="https://shopx.vn" value={website}
                    onChange={(e) => setWebsite(e.target.value)}
                    className="w-full h-9 bg-background border border-border/80 focus:outline-none focus:border-foreground/30 rounded-lg px-2.5 text-xs font-medium"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] font-bold text-foreground/80">Lĩnh vực chính kinh doanh</label>
                  <select 
                    value={industry} onChange={(e) => setIndustry(e.target.value)}
                    className="w-full h-9 bg-background border border-border/80 focus:outline-none rounded-lg px-2 text-xs font-medium text-foreground/80"
                  >
                    <option value="">-- Chọn nhóm ngành phân tích --</option>
                    <option value="Fintech">Fintech</option>
                    <option value="E-Commerce">E-Commerce</option>
                    <option value="TechFlow">AI & DeepTech</option>
                  </select>
                </div>
              </div>

              <div className="pt-4 border-t border-border/40 flex justify-end">
                <Button type="submit" size="sm" className="h-9 text-xs font-bold gap-1.5 px-4 bg-slate-900 text-white dark:bg-zinc-800">
                  <Sparkles className="h-3.5 w-3.5" />
                  <span>Kích hoạt tác vụ ngầm</span>
                </Button>
              </div>
            </form>
          )}

          {/* STEP 2: ANALYZING WITH SUB-TASKS SYSTEM */}
          {step === "ANALYZING" && (
            <div className="flex-1 flex flex-col justify-between h-full animate-in fade-in duration-200">
              <div className="space-y-3.5">
                <div className="flex items-center gap-3 p-3 bg-slate-50 dark:bg-zinc-950 rounded-lg border border-border/50">
                  <div className="relative w-8 h-8 flex items-center justify-center shrink-0">
                    <Loader2 className="h-6 w-6 text-slate-800 dark:text-zinc-400 animate-spin absolute" />
                    <Search className="h-3 w-3 text-slate-600" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <h4 className="text-xs font-bold text-foreground truncate">Đang phân tích: {companyName}</h4>
                    <p className="text-[10px] text-muted-foreground font-medium">Báo cáo cấu trúc đang xử lý tuần tự.</p>
                  </div>
                </div>

                {/* Thanh tiến trình chung */}
                <div className="space-y-1">
                  <div className="flex justify-between text-[10px] font-bold text-muted-foreground">
                    <span>Tổng tiến độ Core Engine</span>
                    <span>{progress}%</span>
                  </div>
                  <div className="w-full h-1.5 bg-muted rounded-full overflow-hidden">
                    <div className="h-full bg-slate-950 dark:bg-zinc-400 transition-all duration-300" style={{ width: `${progress}%` }} />
                  </div>
                </div>

                {/* SUB-TASKS LIST TIẾN TRÌNH CON CHẠY THỰC TẾ */}
                <div className="border border-border/40 rounded-lg bg-muted/10 p-3 space-y-3 max-h-[240px] overflow-y-auto">
                  <span className="text-[9px] font-bold text-muted-foreground/80 uppercase tracking-wider block">
                    Tiến trình phân rã (Sub-tasks)
                  </span>

                  {/* Task nhỏ 1 */}
                  <div className="flex items-start gap-2 text-xs">
                    <Check className="h-3.5 w-3.5 text-emerald-600 shrink-0 mt-0.5 bg-emerald-50 dark:bg-emerald-950 rounded-full p-0.5" />
                    <div className="space-y-0.5">
                      <p className="font-semibold text-foreground/90">Phân tích cấu trúc Sitemap & Khởi tạo Crawler</p>
                      <p className="text-[10px] text-muted-foreground">Đã thiết lập pipeline bảo mật, bóc tách toàn bộ cây URL gốc.</p>
                    </div>
                  </div>

                  {/* Task nhỏ 2 */}
                  <div className="flex items-start gap-2 text-xs">
                    {progress > 35 ? (
                      <Check className="h-3.5 w-3.5 text-emerald-600 shrink-0 mt-0.5 bg-emerald-50 dark:bg-emerald-950 rounded-full p-0.5" />
                    ) : (
                      <Loader2 className="h-3.5 w-3.5 text-sky-600 animate-spin shrink-0 mt-0.5" />
                    )}
                    <div className="space-y-0.5">
                      <p className={cn("font-semibold", progress > 35 ? "text-foreground/90" : "text-sky-600 dark:text-sky-400")}>
                        Quét sâu văn bản nội dung công khai (Scraping)
                      </p>
                      <p className="text-[10px] text-muted-foreground">
                        {progress > 35 ? "Hoàn tất xử lý thô văn bản thuộc trang sản phẩm." : `Đang bóc tách trang tài nguyên: ${Math.min(Math.floor(progress * 0.5), 30)}/30...`}
                      </p>
                    </div>
                  </div>

                  {/* Task nhỏ 3 */}
                  <div className={cn("flex items-start gap-2 text-xs transition-opacity duration-200", progress <= 35 ? "opacity-40" : "opacity-100")}>
                    {progress > 70 ? (
                      <Check className="h-3.5 w-3.5 text-emerald-600 shrink-0 mt-0.5 bg-emerald-50 dark:bg-emerald-950 rounded-full p-0.5" />
                    ) : progress > 35 ? (
                      <Loader2 className="h-3.5 w-3.5 text-sky-600 animate-spin shrink-0 mt-0.5" />
                    ) : (
                      <div className="h-3.5 w-3.5 border border-dashed border-muted-foreground/60 rounded-full shrink-0 mt-0.5" />
                    )}
                    <div className="space-y-0.5">
                      <p className={cn("font-semibold", progress > 70 ? "text-foreground/90" : progress > 35 ? "text-sky-600 dark:text-sky-400" : "text-muted-foreground")}>
                        Phát hiện USP & Mô hình hóa Khẩu khí (LLM Layer)
                      </p>
                      <p className="text-[10px] text-muted-foreground">Embedding không gian vector, tính toán cấu trúc từ khóa cốt lõi.</p>
                    </div>
                  </div>

                  {/* Task nhỏ 4 */}
                  <div className={cn("flex items-start gap-2 text-xs transition-opacity duration-200", progress <= 70 ? "opacity-40" : "opacity-100")}>
                    {progress >= 100 ? (
                      <Check className="h-3.5 w-3.5 text-emerald-600 shrink-0 mt-0.5 bg-emerald-50 dark:bg-emerald-950 rounded-full p-0.5" />
                    ) : progress > 70 ? (
                      <Loader2 className="h-3.5 w-3.5 text-sky-600 animate-spin shrink-0 mt-0.5" />
                    ) : (
                      <div className="h-3.5 w-3.5 border border-dashed border-muted-foreground/60 rounded-full shrink-0 mt-0.5" />
                    )}
                    <div className="space-y-0.5">
                      <p className={cn("font-semibold", progress >= 100 ? "text-foreground/90" : progress > 70 ? "text-sky-600 dark:text-sky-400" : "text-muted-foreground")}>
                        Kiểm định Rule Do's/Dont's & Chuẩn hóa Hồ sơ
                      </p>
                      <p className="text-[10px] text-muted-foreground">Kiểm tra tính đồng bộ nội dung, đóng gói payload JSON sạch.</p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="pt-3 border-t border-border/40 flex">
                <Button 
                  variant="outline" size="sm" className="h-9 text-xs font-bold text-muted-foreground w-full"
                  onClick={() => setIsMinimized(true)}
                >
                  Thu nhỏ ẩn xuống góc làm việc khác
                </Button>
              </div>
            </div>
          )}

          {/* STEP 3: DONE & PREVIEW INSIGHTS */}
          {step === "RESEARCH_DONE" && (
            <div className="flex-1 flex flex-col justify-between h-full animate-in zoom-in-98 duration-200">
              <div className="space-y-3.5">
                <div className="flex items-center gap-2 p-2.5 bg-emerald-50/50 border border-emerald-200/60 dark:bg-emerald-950/20 dark:border-emerald-900/40 rounded-lg">
                  <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
                  <span className="text-xs font-bold text-emerald-800 dark:text-emerald-400">Hệ thống AI tổng hợp thành công dữ liệu!</span>
                </div>

                <div className="border border-border/60 rounded-lg p-3 bg-muted/20 space-y-2">
                  <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider block">Bản tóm tắt sơ bộ từ Core</span>
                  <div className="space-y-2 text-xs font-medium">
                    <div>
                      <span className="text-muted-foreground text-[11px]">Hình mẫu Brand Voice:</span>
                      <p className="text-foreground font-semibold italic mt-0.5">"Chuyên nghiệp, tin cậy cao, lập luận dựa trên dữ liệu thực tế."</p>
                    </div>
                    <div>
                      <span className="text-muted-foreground text-[11px]">Mô hình cốt lõi:</span>
                      <p className="text-foreground/90 font-medium mt-0.5">Tập trung xử lý bài toán vận hành của phân khúc {industry || "Doanh nghiệp"}.</p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="pt-4 border-t border-border/40 flex items-center justify-between">
                <Button variant="ghost" size="sm" className="h-9 text-xs font-semibold text-muted-foreground" onClick={() => setStep("INPUT_FORM")}>
                  Quét lại
                </Button>
                <Button size="sm" className="h-9 text-xs font-bold gap-1 px-3.5 bg-slate-900 text-white dark:bg-zinc-800" onClick={handleApply}>
                  <span>Đồng bộ Hồ sơ</span>
                  <ArrowRight className="h-3.5 w-3.5" />
                </Button>
              </div>
            </div>
          )}

        </div>
      )}
    </div>
  )
}