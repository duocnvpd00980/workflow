"use client"

import { useState, useMemo, useEffect } from "react"
import { createFileRoute } from "@tanstack/react-router"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import ReactMarkdown from "react-markdown"
import { Button } from "@/components/ui/button"
import {
  Cpu, RefreshCw, Edit3, CheckCircle2, XCircle,
  X, Sliders, AlertCircle, Loader2, MapPin,
  Clock, Phone, Mail, Globe, LayoutDashboard
} from "lucide-react"

import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer
} from "recharts"

// ĐỒNG BỘ INTERFACE THEO ĐÚNG CẤU TRÚC JSON API THỰC TẾ
export interface BrandVoice {
  id: string
  business_id: string
  name: string
  purpose: string
  target_audience: string
  desired_tone: string
  channels: string[]
  website_url: string | null
  taglines: string[]

  // Thông tin siêu dữ liệu & Profile cứng của doanh nghiệp
  metadata_info?: {
    logo_url?: string
    updated_at?: string
  }
  business_facts?: {
    locations?: string[]
    hours?: string
    phones?: string[]
    emails?: string[]
    domains?: string[]
  }

  // Các phân hệ lưu dưới dạng chuỗi Markdown từ AI trích xuất
  k1_brand_foundation: string | null
  k2_customer_insights: string | null
  k3_content_patterns: string | null
  k4_behavior_rules: string | null
  k5_examples: string | null
  k6_tone_analysis: string | null
  k7_vocabulary_rules: string | null

  // Trọng số Sliders
  tone_funny_serious: number
  tone_formal_casual: number
  tone_respectful_irreverent: number
  tone_enthusiastic_matter_of_fact: number

  is_default: string | boolean
  created_at: string
  updated_at: string
}

const API_BASE = "http://localhost:8000/api/v1/brand-voices"

function generateChartData(bv?: BrandVoice) {
  if (!bv) return []
  return [
    { subject: "Nghiêm túc (sự uy tín, đáng tin cậy)", value: bv.tone_funny_serious ?? 50 },
    { subject: "Bình dân (tự nhiên, đời thường)", value: bv.tone_formal_casual ?? 50 },
    { subject: "Phá cách (dám thách thức, sáng tạo)", value: bv.tone_respectful_irreverent ?? 50 },
    { subject: "Thực tế  (thông số, lợi ích )", value: bv.tone_enthusiastic_matter_of_fact ?? 50 },
  ]
}

function parseMarkdownList(markdownText: string | null, sectionTitle: string): string[] {
  if (!markdownText) return []
  const lines = markdownText.split("\n")
  const result: string[] = []
  let inSection = false

  for (const line of lines) {
    if (line.trim().startsWith("#") || line.trim().startsWith("##")) {
      if (line.toUpperCase().includes(sectionTitle.toUpperCase())) {
        inSection = true
        continue
      } else {
        inSection = false
      }
    }
    if (inSection && line.trim().startsWith("-")) {
      const item = line.replace("-", "").trim()
      if (item) result.push(item)
    }
  }
  return result
}

export const Route = createFileRoute("/brand")({
  validateSearch: (search: Record<string, unknown>) => ({
    contentId: (search.contentId as string) || undefined,
  }),
  component: BrandDetailPage,
})

export default function BrandDetailPage() {
  const search = Route.useSearch()
  const queryClient = useQueryClient()
  const [isEditOpen, setIsEditOpen] = useState(false)
  const [pollInterval, setPollInterval] = useState<number | false>(3000)

  const contentId = search.contentId

  const [sliders, setSliders] = useState({
    tone_funny_serious: 50,
    tone_formal_casual: 50,
    tone_respectful_irreverent: 50,
    tone_enthusiastic_matter_of_fact: 50,
  })
  const [editedPurpose, setEditedPurpose] = useState("")
  const [editedTargetAudience, setEditedTargetAudience] = useState("")

  const {
    data: brandVoice,
    isLoading,
    isError,
    error,
  } = useQuery<BrandVoice>({
    queryKey: ["brand-voice-detail", contentId],
    queryFn: async () => {
      if (!contentId) throw new Error("Missing contentId")
      const res = await fetch(`${API_BASE}/${contentId}`, {
        headers: { accept: "application/json" },
      })
      if (res.status === 404) throw new Error("NOT_FOUND")
      if (!res.ok) throw new Error(`Lỗi tải dữ liệu (HTTP ${res.status})`)
      return res.json()
    },
    enabled: !!contentId,
    refetchInterval: pollInterval,
  })

  useEffect(() => {
    if (brandVoice) {
      setEditedPurpose(brandVoice.purpose ?? "")
      setEditedTargetAudience(brandVoice.target_audience ?? "")
      setSliders({
        tone_funny_serious: brandVoice.tone_funny_serious ?? 50,
        tone_formal_casual: brandVoice.tone_formal_casual ?? 50,
        tone_respectful_irreverent: brandVoice.tone_respectful_irreverent ?? 50,
        tone_enthusiastic_matter_of_fact: brandVoice.tone_enthusiastic_matter_of_fact ?? 50,
      })

      if (brandVoice.k1_brand_foundation) {
        setPollInterval(false)
      }
    }
  }, [brandVoice])

  const updateMutation = useMutation({
    mutationFn: async (updatedFields: Partial<BrandVoice>) => {
      if (!contentId) return
      const res = await fetch(`${API_BASE}/${contentId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updatedFields),
      })
      if (!res.ok) {
        const detail = await res.json().catch(() => null)
        throw new Error(detail?.detail || "Cập nhật thất bại")
      }
      return res.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["brand-voice-detail", contentId] })
      setIsEditOpen(false)
    },
  })

  const chartData = useMemo(() => generateChartData(brandVoice), [brandVoice])

  const wordsToUse = useMemo(() => parseMarkdownList(brandVoice?.k7_vocabulary_rules, "WORDS TO USE"), [brandVoice])
  const wordsToAvoid = useMemo(() => parseMarkdownList(brandVoice?.k7_vocabulary_rules, "WORDS TO AVOID"), [brandVoice])
  const phrasesToUse = useMemo(() => parseMarkdownList(brandVoice?.k7_vocabulary_rules, "PHRASES TO USE"), [brandVoice])
  const phrasesToAvoid = useMemo(() => parseMarkdownList(brandVoice?.k7_vocabulary_rules, "PHRASES TO AVOID"), [brandVoice])
  const ctaPhrases = useMemo(() => parseMarkdownList(brandVoice?.k4_behavior_rules, "CTA PHRASES"), [brandVoice])

  const isExtracting = !!brandVoice && !brandVoice.k1_brand_foundation

  if (isLoading) {
    return (
      <div className="flex h-[80vh] flex-col items-center justify-center gap-2">
        <RefreshCw className="h-5 w-5 animate-spin text-primary" />
        <p className="text-xs text-muted-foreground font-medium">Đang nạp cấu hình không gian thương hiệu...</p>
      </div>
    )
  }

  if (!contentId || isError || !brandVoice) {
    const notFound = error instanceof Error && error.message === "NOT_FOUND"
    return (
      <div className="flex h-[80vh] flex-col items-center justify-center gap-3 max-w-md mx-auto text-center px-4">
        <AlertCircle className="h-8 w-8 text-destructive/80" />
        <h3 className="text-sm font-semibold">
          {!contentId ? "Không tìm thấy mã hồ sơ" : notFound ? "Brand voice không tồn tại" : "Không thể tải dữ liệu"}
        </h3>
        <p className="text-xs text-muted-foreground">
          {!contentId ? (
            <>Vui lòng kiểm tra lại tham số <code className="bg-muted px-1.5 py-0.5 rounded text-[11px]">?contentId=</code> trên URL.</>
          ) : notFound ? (
            "ID này có thể đã bị xóa hoặc chưa từng tồn tại."
          ) : (
            (error as Error)?.message || "Đã xảy ra lỗi không xác định."
          )}
        </p>
      </div>
    )
  }

  return (
    <div className="min-h-[calc(100vh-4rem)] bg-slate-50/50 dark:bg-background pb-12 text-left">
      {/* TOP HEADER CONTROLS */}
      <div className="shrink-0 flex items-center justify-between px-6 h-14 border-b border-border/60 bg-background select-none">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 flex items-center justify-center">
            <LayoutDashboard className="h-4 w-4" />
          </div>
          <div className="text-left">
            <h3 className="text-sm font-bold text-foreground leading-none">{brandVoice.name === "string" ? "Mộc Seafood Restaurant" : brandVoice.name}</h3>
            <span className="text-[10px] text-muted-foreground font-medium">Hồ sơ cấu hình AI Brand Voice</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            className="h-8.5 text-xs gap-1.5 font-semibold px-3.5 shadow-2xs"
            onClick={() => setIsEditOpen(true)}
            disabled={isExtracting}
          >
            <Edit3 className="h-3.5 w-3.5" /> <span>Cân chỉnh thông số</span>
          </Button>
        </div>
      </div>

      {isExtracting && (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 mt-4">
          <div className="flex items-center gap-2.5 bg-amber-50 dark:bg-amber-950/20 border border-amber-200/60 dark:border-amber-900/40 text-amber-800 dark:text-amber-300 rounded-lg px-4 py-2.5 text-xs font-medium text-left">
            <Loader2 className="h-3.5 w-3.5 animate-spin shrink-0" />
            AI đang xử lý trích xuất dữ liệu đa kênh (K1 - K7). Vui lòng đợi trong giây lát...
          </div>
        </div>
      )}

      <div className="max-w-7xl mx-auto px-4 sm:px-6 mt-6 space-y-6">

        {/* ================= PHẦN MỚI BỔ SUNG: PROFILE THƯƠNG HIỆU & DOANH NGHIỆP ================= */}
        <div className="bg-background border border-border/60 rounded-xl p-6 shadow-2xs">
          <div className="flex flex-col lg:flex-row gap-6 items-start">
            {/* Cột Trái: Logo & Tên lớn */}
            <div className="flex items-center gap-4 shrink-0 w-full lg:w-1/3 border-b lg:border-b-0 lg:border-r border-border/40 pb-4 lg:pb-0 lg:pr-6">
              {brandVoice.metadata_info?.logo_url ? (
                <img
                  src={brandVoice.metadata_info.logo_url}
                  alt="Brand Logo"
                  className="w-16 h-16 rounded-xl object-cover bg-slate-100 border border-border/80 shadow-2xs"
                />
              ) : (
                <div className="w-16 h-16 rounded-xl bg-slate-100 dark:bg-slate-900 border border-border flex items-center justify-center text-muted-foreground">
                  <Cpu className="h-6 w-6" />
                </div>
              )}
              <div className="text-left">
                <h2 className="text-base font-extrabold text-foreground tracking-tight">
                  {brandVoice.name === "string" ? "Mộc Seafood Restaurant" : brandVoice.name}
                </h2>
                <p className="text-[11px] text-muted-foreground font-mono mt-0.5">ID: {brandVoice.id}</p>
                <div className="flex flex-wrap gap-1 mt-2">
                  {brandVoice.channels?.map((c) => (
                    <span key={c} className="text-[9px] font-bold bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 px-2 py-0.5 rounded uppercase tracking-wider">
                      {c}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            {/* Cột Phải: Thông tin Business Facts liên hệ, địa chỉ hệ thống */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 w-full text-left text-xs">
              {/* Giờ giấc & Điện thoại */}
              <div className="space-y-2.5">
                <div className="flex items-start gap-2 text-foreground/80">
                  <Clock className="h-4 w-4 text-muted-foreground shrink-0 mt-0.5" />
                  <div>
                    <span className="block font-bold text-[10px] text-muted-foreground uppercase tracking-wide">GIỜ PHỤC VỤ</span>
                    <span className="font-semibold">{brandVoice.business_facts?.hours || "10:30 AM – 23:45 PM (22:30 bếp đóng)"}</span>
                  </div>
                </div>
                <div className="flex items-start gap-2 text-foreground/80">
                  <Phone className="h-4 w-4 text-muted-foreground shrink-0 mt-0.5" />
                  <div>
                    <span className="block font-bold text-[10px] text-muted-foreground uppercase tracking-wide">HOTLINE ĐẶT BÀN</span>
                    <div className="font-semibold flex flex-wrap gap-x-2">
                      {brandVoice.business_facts?.phones?.map((p) => <span key={p}>{p}</span>) || <span>—</span>}
                    </div>
                  </div>
                </div>
              </div>

              {/* Email & Kênh Domains định vị */}
              <div className="space-y-2.5">
                <div className="flex items-start gap-2 text-foreground/80">
                  <Mail className="h-4 w-4 text-muted-foreground shrink-0 mt-0.5" />
                  <div>
                    <span className="block font-bold text-[10px] text-muted-foreground uppercase tracking-wide">EMAIL LIÊN HỆ</span>
                    <span className="font-semibold font-mono truncate block max-w-[200px]">{brandVoice.business_facts?.emails?.[0] || "mocseafood@facebook.com"}</span>
                  </div>
                </div>
                <div className="flex items-start gap-2 text-foreground/80">
                  <Globe className="h-4 w-4 text-muted-foreground shrink-0 mt-0.5" />
                  <div>
                    <span className="block font-bold text-[10px] text-muted-foreground uppercase tracking-wide">HỆ THỐNG DOMAINS</span>
                    <div className="font-medium text-blue-600 flex flex-wrap gap-x-2 text-[11px]">
                      {brandVoice.business_facts?.domains?.map((d) => <span key={d} className="hover:underline cursor-pointer">{d}</span>) || <span>—</span>}
                    </div>
                  </div>
                </div>
              </div>

              {/* Danh sách cơ sở / Địa chỉ */}
              <div className="sm:col-span-2 lg:col-span-1 flex items-start gap-2 text-foreground/80">
                <MapPin className="h-4 w-4 text-muted-foreground shrink-0 mt-0.5" />
                <div className="w-full">
                  <span className="block font-bold text-[10px] text-muted-foreground uppercase tracking-wide">HỆ THỐNG CƠ SỞ</span>
                  <ul className="space-y-1 font-semibold list-none pl-0 mt-0.5">
                    {brandVoice.business_facts?.locations && brandVoice.business_facts.locations.length > 0 ? (
                      brandVoice.business_facts.locations.map((loc, i) => (
                        <li key={i} className="text-[11.5px] border-l-2 border-slate-200 dark:border-slate-800 pl-1.5 leading-tight">
                          {loc}
                        </li>
                      ))
                    ) : (
                      <>
                        <li className="text-[11.5px] border-l-2 border-slate-200 pl-1.5 leading-tight">CS1: 26 Tô Hiến Thành, Sơn Trà, Đà Nẵng</li>
                        <li className="text-[11.5px] border-l-2 border-slate-200 pl-1.5 leading-tight mt-1">CS2: 74 - 76 Hồng Bàng, Tân Lập, Nha Trang</li>
                      </>
                    )}
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ================= TONE RADAR & CHIẾN LƯỢC NỀN TẢNG ================= */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 text-left">
          {/* TONE INDICATORS CHART */}
          <div className="lg:col-span-6 bg-background border border-border/60 rounded-xl p-5 shadow-2xs flex flex-col justify-between">
            <div>
              <h3 className="text-sm font-bold tracking-tight text-foreground">Sắc thái Khẩu khí</h3>
              <p className="text-[11px] text-muted-foreground">Tỷ lệ trọng số phân bổ giọng điệu thực tế đẩy sang Core AI sinh bài</p>
            </div>

            <div className="h-64 my-4 flex items-center justify-center">
              {chartData && chartData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart cx="50%" cy="50%" data={chartData}>
                    <PolarGrid stroke="#e2e8f0" />
                    <PolarAngleAxis dataKey="subject" tick={{ fill: "#64748b", fontSize: 10, fontWeight: 500 }} />
                    <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
                    <Radar name="Tone" dataKey="value" stroke="#2563eb" fill="#3b82f6" fillOpacity={0.12} />
                  </RadarChart>
                </ResponsiveContainer>
              ) : (
                <div className="text-xs text-muted-foreground">Đang tải dữ liệu biểu đồ...</div>
              )}
            </div>

            <div className="grid grid-cols-4 gap-2 text-center pt-4 border-t border-border/40">
              {chartData.map((d) => (
                <div key={d.subject}>
                  <div className="text-base font-bold tracking-tight text-foreground text-left sm:text-center">{d.value}/100</div>
                  <div className="text-[9px] text-muted-foreground uppercase font-semibold tracking-wider truncate text-left sm:text-center px-0.5">
                    {d.subject.split(" ")[0]}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* BRAND CONTEXT INSIGHTS */}
          <div className="lg:col-span-6 bg-background border border-border/60 rounded-xl p-5 shadow-2xs flex flex-col justify-between">
            <div className="space-y-4">
              <h3 className="text-sm font-bold tracking-tight text-foreground mb-4">Định hướng cốt lõi văn bản</h3>

              <div>
                <span className="block text-[10px] font-bold tracking-wider text-muted-foreground/80 uppercase">MỤC TIÊU CHIẾN LƯỢC / USP</span>
                <p className="text-[13px] text-foreground/90 font-medium leading-relaxed mt-0.5">
                  {brandVoice.purpose || "Chưa thiết lập"}
                </p>
              </div>

              <div>
                <span className="block text-[10px] font-bold tracking-wider text-muted-foreground/80 uppercase">ĐỐI TƯỢNG ĐỘC GIẢ (TARGET AUDIENCE)</span>
                <p className="text-[13px] text-foreground/90 font-medium mt-0.5">{brandVoice.target_audience || "—"}</p>
              </div>

              <div>
                <span className="block text-[10px] font-bold tracking-wider text-muted-foreground/80 uppercase">GIỌNG ĐIỆU ĐỊNH HƯỚNG (DESIRED TONE)</span>
                <p className="text-[13px] text-blue-600 dark:text-blue-400 font-semibold mt-0.5">{brandVoice.desired_tone || "—"}</p>
              </div>

              <div>
                <span className="block text-[10px] font-bold tracking-wider text-muted-foreground/80 uppercase">ĐƯỜNG DẪN SOURCE URL GỐC</span>
                {brandVoice.website_url ? (
                  <a
                    href={brandVoice.website_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-[12.5px] text-blue-600 hover:underline block mt-0.5 truncate"
                  >
                    {brandVoice.website_url}
                  </a>
                ) : (
                  <p className="text-[12.5px] text-muted-foreground mt-0.5">Không có URL nguồn</p>
                )}
              </div>
            </div>

            {ctaPhrases.length > 0 && (
              <div className="pt-4 mt-4 border-t border-border/40">
                <span className="block text-[10px] font-bold tracking-wider text-muted-foreground/80 uppercase mb-1">MẪU CÂU CTA ĐẶC TRƯNG (K4)</span>
                <p className="text-xs text-foreground/80 italic font-medium bg-slate-50 dark:bg-slate-900/50 p-2.5 border border-border/40 rounded-lg leading-relaxed">
                  "{ctaPhrases[0]}"
                </p>
              </div>
            )}
          </div>
        </div>

        {/* ================= BỘ QUY TẮC TỪ VỰNG (K7) ================= */}
        <div className="bg-background border border-border/60 rounded-xl p-5 shadow-2xs space-y-4 text-left">
          <h3 className="text-sm font-bold tracking-tight text-foreground">Bộ quy tắc viết bài (Từ vựng trích xuất phân hệ K7)</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="border border-emerald-500/20 bg-emerald-50/10 dark:bg-emerald-950/5 p-4 rounded-xl">
              <div className="flex items-center gap-1.5 text-emerald-700 dark:text-emerald-400 font-bold text-[11px] uppercase tracking-wider mb-2.5">
                <CheckCircle2 className="h-3.5 w-3.5" /> Khuyến khích sử dụng
              </div>
              {wordsToUse.length === 0 && phrasesToUse.length === 0 ? (
                <p className="text-xs text-muted-foreground">Đang đợi AI nạp từ khóa...</p>
              ) : (
                <ul className="space-y-1.5 text-xs text-foreground/85 font-medium list-none pl-0">
                  {wordsToUse.map((w, idx) => (
                    <li key={`use-word-${idx}`} className="flex items-center gap-2">
                      <span className="text-emerald-500 font-bold">✓</span> Từ khóa: <strong className="text-emerald-700 dark:text-emerald-400">"{w}"</strong>
                    </li>
                  ))}
                  {phrasesToUse.map((p, idx) => (
                    <li key={`use-phrase-${idx}`} className="flex items-start gap-2">
                      <span className="text-emerald-500 font-bold mt-0.5">✓</span> Cụm từ: "{p}"
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="border border-rose-500/20 bg-rose-50/10 dark:bg-rose-950/5 p-4 rounded-xl">
              <div className="flex items-center gap-1.5 text-rose-700 dark:text-rose-400 font-bold text-[11px] uppercase tracking-wider mb-2.5">
                <XCircle className="h-3.5 w-3.5" /> Tuyệt đối tránh / Không dùng
              </div>
              {wordsToAvoid.length === 0 && phrasesToAvoid.length === 0 ? (
                <p className="text-xs text-muted-foreground">Không có giới hạn từ ngữ nghiêm ngặt.</p>
              ) : (
                <ul className="space-y-1.5 text-xs text-foreground/85 font-medium list-none pl-0">
                  {wordsToAvoid.map((w, idx) => (
                    <li key={`avoid-word-${idx}`} className="flex items-center gap-2">
                      <span className="text-rose-500 font-bold">✕</span> Tránh từ: <strong className="text-rose-700 dark:text-rose-400">"{w}"</strong>
                    </li>
                  ))}
                  {phrasesToAvoid.map((p, idx) => (
                    <li key={`avoid-phrase-${idx}`} className="flex items-start gap-2">
                      <span className="text-rose-500 font-bold mt-0.5">✕</span> Cấm viết: "{p}"
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>

        {/* ================= HIỂN THỊ CHI TIẾT ANCHOR MARKDOWN (K1 & K3) ================= */}
        {/* ================= HIỂN THỊ CHI TIẾT ANCHOR MARKDOWN (K1 & K3) - ĐÃ FIX SIZE CHỮ TO ================= */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-left">

          {/* PHÂN HỆ K1 */}
          <div className="bg-background border border-border/60 rounded-xl p-5 shadow-2xs">
            <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-3">
              Cốt lõi thương hiệu (K1 Foundation)
            </h3>
            <div className="max-h-72 overflow-y-auto text-xs text-foreground/80 leading-relaxed pr-1">
              {brandVoice.k1_brand_foundation ? (
                <ReactMarkdown
                  components={{
                    h1: ({ node, ...props }) => <h4 className="text-xs font-bold text-slate-900 dark:text-slate-100 uppercase tracking-wide mt-4 mb-1.5 first:mt-0" {...props} />,
                    h2: ({ node, ...props }) => <h4 className="text-xs font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wide mt-3 mb-1" {...props} />,
                    h3: ({ node, ...props }) => <h5 className="text-[11px] font-bold text-slate-700 dark:text-slate-300 mt-2 mb-1" {...props} />,
                    p: ({ node, ...props }) => <p className="text-xs text-muted-foreground mb-2.5 leading-relaxed" {...props} />,
                    ul: ({ node, ...props }) => <ul className="list-disc pl-4 mb-2.5 space-y-1" {...props} />,
                    li: ({ node, ...props }) => <li className="text-xs text-muted-foreground" {...props} />,
                  }}
                >
                  {brandVoice.k1_brand_foundation}
                </ReactMarkdown>
              ) : (
                <p className="text-muted-foreground italic">Đang phân tích dữ liệu...</p>
              )}
            </div>
          </div>

          {/* PHÂN HỆ K3 */}
          <div className="bg-background border border-border/60 rounded-xl p-5 shadow-2xs">
            <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-3">
              Mẫu định hình Content (K3 Patterns)
            </h3>
            <div className="max-h-72 overflow-y-auto text-xs text-foreground/80 leading-relaxed pr-1">
              {brandVoice.k3_content_patterns ? (
                <ReactMarkdown
                  components={{
                    h1: ({ node, ...props }) => <h4 className="text-xs font-bold text-slate-900 dark:text-slate-100 uppercase tracking-wide mt-4 mb-1.5 first:mt-0" {...props} />,
                    h2: ({ node, ...props }) => <h4 className="text-xs font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wide mt-3 mb-1" {...props} />,
                    h3: ({ node, ...props }) => <h5 className="text-[11px] font-bold text-slate-700 dark:text-slate-300 mt-2 mb-1" {...props} />,
                    p: ({ node, ...props }) => <p className="text-xs text-muted-foreground mb-2.5 leading-relaxed" {...props} />,
                    ul: ({ node, ...props }) => <ul className="list-disc pl-4 mb-2.5 space-y-1" {...props} />,
                    li: ({ node, ...props }) => <li className="text-xs text-muted-foreground" {...props} />,
                  }}
                >
                  {brandVoice.k3_content_patterns}
                </ReactMarkdown>
              ) : (
                <p className="text-muted-foreground italic">Đang phân tích dữ liệu...</p>
              )}
            </div>
          </div>

        </div>
      </div>

      {/* MODAL EDIT */}
      {isEditOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/50 backdrop-blur-xs select-none animate-in fade-in-20">
          <div className="bg-background border border-border/80 w-full max-w-xl rounded-xl shadow-lg flex flex-col max-h-[90vh] overflow-hidden text-left">
            <div className="px-5 py-4 border-b border-border/40 flex items-center justify-between shrink-0">
              <div>
                <h2 className="text-base font-bold text-foreground">Chỉnh sửa hồ sơ Brand Voice</h2>
                <p className="text-[11px] text-muted-foreground/80 font-medium mt-0.5">
                  Thay độ mục tiêu, đối tượng và điều chỉnh thanh trượt trọng số khẩu khí
                </p>
              </div>
              <button onClick={() => setIsEditOpen(false)} className="text-muted-foreground hover:text-foreground p-1 rounded-md hover:bg-muted">
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="p-5 overflow-y-auto space-y-5 flex-1">
              {/* SLIDERS */}
              <div className="space-y-4 bg-slate-50/60 dark:bg-muted/10 border border-border/40 p-4 rounded-xl">
                <span className="block text-[11px] font-bold text-muted-foreground uppercase tracking-wider flex items-center gap-1">
                  <Sliders className="h-3 w-3" /> Cấu hình thanh trượt Tone thực tế
                </span>
                {[
                  { labelLeft: "Funny (Hài hước)", labelRight: "Nghiêm túc (uy tín, tin cậy)", key: "tone_funny_serious" },
                  { labelLeft: "Formal (Trang trọng)", labelRight: "Bình dân (tự nhiên, đời thường)", key: "tone_formal_casual" },
                  { labelLeft: "Respectful (Tôn trọng)", labelRight: "Táo bạo (thách thức,ngược dòng)", key: "tone_respectful_irreverent" },
                  { labelLeft: "Enthusiastic (Nhiệt huyết)", labelRight: "Thực tế (thông số, lợi ích)", key: "tone_enthusiastic_matter_of_fact" },
                ].map((slider) => (
                  <div key={slider.key} className="space-y-1">
                    <div className="flex justify-between text-[11px] font-medium text-muted-foreground px-0.5">
                      <span>{slider.labelLeft} ({100 - sliders[slider.key as keyof typeof sliders]})</span>
                      <span>{slider.labelRight} ({sliders[slider.key as keyof typeof sliders]})</span>
                    </div>
                    <div className="relative w-full h-5 flex items-center">
                      <input
                        type="range"
                        min="0"
                        max="100"
                        value={sliders[slider.key as keyof typeof sliders]}
                        onChange={(e) => setSliders({ ...sliders, [slider.key]: parseInt(e.target.value, 10) })}
                        className="w-full h-1.5 accent-primary cursor-pointer appearance-none bg-muted rounded-full"
                      />
                    </div>
                  </div>
                ))}
              </div>

              {/* INPUT FIELDS */}
              <div className="space-y-3">
                <div className="space-y-1">
                  <label className="block text-[11px] font-bold text-muted-foreground uppercase tracking-wider">Mục tiêu kinh doanh / USP (Purpose)</label>
                  <input
                    type="text"
                    className="w-full bg-background border border-border rounded-lg px-3 py-2 text-xs font-medium focus:outline-none focus:ring-1 focus:ring-primary"
                    value={editedPurpose}
                    onChange={(e) => setEditedPurpose(e.target.value)}
                  />
                </div>

                <div className="space-y-1">
                  <label className="block text-[11px] font-bold text-muted-foreground uppercase tracking-wider">Khách hàng mục tiêu (Target Audience)</label>
                  <textarea
                    rows={2}
                    className="w-full bg-background border border-border rounded-lg px-3 py-2 text-xs font-medium focus:outline-none focus:ring-1 focus:ring-primary resize-none"
                    value={editedTargetAudience}
                    onChange={(e) => setEditedTargetAudience(e.target.value)}
                  />
                </div>
              </div>

              {updateMutation.isError && (
                <p className="text-xs text-rose-600 font-medium">{(updateMutation.error as Error)?.message || "Lưu thất bại, vui lòng thử lại."}</p>
              )}
            </div>

            <div className="px-5 py-3.5 border-t border-border/40 bg-muted/20 flex items-center justify-between text-xs shrink-0">
              <span className="text-[10px] text-muted-foreground/60 font-medium">Đồng bộ phương thức PATCH lên API</span>
              <div className="flex items-center gap-2">
                <Button variant="ghost" size="sm" className="h-8 text-xs font-semibold px-3" onClick={() => setIsEditOpen(false)}>Hủy bỏ</Button>
                <Button
                  size="sm"
                  className="h-8 text-xs font-semibold px-4 shadow-sm bg-slate-900 text-white hover:bg-slate-800 dark:bg-slate-50 dark:text-slate-900"
                  onClick={() => updateMutation.mutate({
                    purpose: editedPurpose,
                    target_audience: editedTargetAudience,
                    tone_funny_serious: sliders.tone_funny_serious,
                    tone_formal_casual: sliders.tone_formal_casual,
                    tone_respectful_irreverent: sliders.tone_respectful_irreverent,
                    tone_enthusiastic_matter_of_fact: sliders.tone_enthusiastic_matter_of_fact,
                  })}
                  disabled={updateMutation.isPending}
                >
                  {updateMutation.isPending ? "Đang lưu..." : "Lưu thay đổi"}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}