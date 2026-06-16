"use client"

import { useState, useMemo, useEffect } from "react"
import { createFileRoute } from "@tanstack/react-router"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Button } from "@/components/ui/button"
import {
  Cpu, RefreshCw, Edit3, CheckCircle2,
  XCircle, Download, X, Sliders, AlertCircle, Loader2, Info
} from "lucide-react"

import { 
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer 
} from "recharts"

export interface BrandVoice {
  id: string
  business_id: string
  name: string
  purpose: string
  channels: string[]
  desired_tone: string
  target_audience: string
  personality: string
  tone: {
    base: string[]
    overrides: Record<string, string[]>
  }
  style: { 
    sentenceLength: string; 
    voice: string; 
    perspective: string;
    // Ý 1: Cách xưng hô đặc thù tiếng Việt
    pronouns?: {
      ai: string;     // Đại từ xưng hô của Thương hiệu (Ví dụ: Chúng tôi, Novotel, Mình)
      reader: string; // Đại từ gọi Độc giả (Ví dụ: Quý khách, Bạn, Anh/Chị)
    }
  }
  vocabulary: { 
    wordsToUse: string[]; 
    wordsToAvoid: string[]; 
    phrasesToUse: string[]; 
    phrasesToAvoid: string[];
    topicsToAvoid?: string[]; 
  }
  format_rules: { paragraphMaxSentences: number; useEmoji: boolean; useHashtags: boolean; bulletPointStyle: string }
  cta_style: { style: string; phrases: string[] }
  website_url: string | null
  examples?: string[]
  is_default?: string | boolean
  tone_funny_serious: number
  tone_formal_casual: number
  tone_respectful_irreverent: number
  tone_enthusiastic_matter_of_fact: number
  created_at: string
  updated_at: string
}

const API_BASE = "http://localhost:8000/api/v1/brand-voices"

function generateChartData(bv?: BrandVoice) {
  if (!bv) return []
  return [
    { subject: "Serious (Nghiêm túc)", value: bv.tone_funny_serious ?? 50 },
    { subject: "Casual (Bình dân)", value: bv.tone_formal_casual ?? 50 },
    { subject: "Irreverent (Phá cách)", value: bv.tone_respectful_irreverent ?? 50 },
    { subject: "Fact-based (Thực tế)", value: bv.tone_enthusiastic_matter_of_fact ?? 50 },
  ]
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
  const [editedPersonality, setEditedPersonality] = useState("")

  // State phục vụ việc chỉnh sửa nhanh Cách xưng hô tiếng Việt trong Modal
  const [editedPronouns, setEditedPronouns] = useState({ ai: "", reader: "" })

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
      setEditedPersonality(brandVoice.personality ?? "")
      setEditedPronouns({
        ai: brandVoice.style?.pronouns?.ai ?? "Chúng tôi",
        reader: brandVoice.style?.pronouns?.reader ?? "Quý khách",
      })
      setSliders({
        tone_funny_serious: brandVoice.tone_funny_serious ?? 50,
        tone_formal_casual: brandVoice.tone_formal_casual ?? 50,
        tone_respectful_irreverent: brandVoice.tone_respectful_irreverent ?? 50,
        tone_enthusiastic_matter_of_fact: brandVoice.tone_enthusiastic_matter_of_fact ?? 50,
      })

      if (brandVoice.personality) {
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

  const toneBase = brandVoice?.tone?.base ?? []
  const wordsToUse = brandVoice?.vocabulary?.wordsToUse ?? []
  const wordsToAvoid = brandVoice?.vocabulary?.wordsToAvoid ?? []
  const phrasesToUse = brandVoice?.vocabulary?.phrasesToUse ?? []
  const phrasesToAvoid = brandVoice?.vocabulary?.phrasesToAvoid ?? []
  
  // Trích xuất mảng Chủ đề cần tránh (Ý 2) bọc fallback an toàn đề phòng DB cũ chưa có trường này
  const topicsToAvoid = brandVoice?.vocabulary?.topicsToAvoid ?? []
  
  const isExtracting = !!brandVoice && !brandVoice.personality

  if (isLoading) {
    return (
      <div className="flex h-[80vh] flex-col items-center justify-center gap-2">
        <RefreshCw className="h-5 w-5 animate-spin text-primary" />
        <p className="text-xs text-muted-foreground font-medium">Đang nạp cấu hình khẩu khí...</p>
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
    <div className="min-h-[calc(100vh-4rem)] bg-slate-50/30 dark:bg-background pb-10">
      {/* HEADER */}
      <div className="shrink-0 flex items-center justify-between px-6 h-14 border-b border-border/60 bg-background select-none">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 flex items-center justify-center">
            <Cpu className="h-4 w-4" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-foreground leading-none">{brandVoice.name}</h1>
            <span className="text-[10px] text-muted-foreground font-medium">ID: {brandVoice.id}</span>
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
            <Edit3 className="h-3.5 w-3.5" /> <span>Thanh điều chỉnh khẩu khí</span>
          </Button>
          <Button size="sm" variant="outline" className="h-8.5 text-xs gap-1.5 font-semibold px-3.5 text-muted-foreground">
            <Download className="h-3.5 w-3.5" /> <span>Xuất file</span>
          </Button>
        </div>
      </div>

      {isExtracting && (
        <div className="max-w-6xl mx-auto px-4 sm:px-6 mt-4">
          <div className="flex items-center gap-2.5 bg-amber-50 dark:bg-amber-950/20 border border-amber-200/60 dark:border-amber-900/40 text-amber-800 dark:text-amber-300 rounded-lg px-4 py-2.5 text-xs font-medium">
            <Loader2 className="h-3.5 w-3.5 animate-spin shrink-0" />
            AI đang phân tích và trích xuất khẩu khí thương hiệu. Trang sẽ tự cập nhật khi hoàn tất...
          </div>
        </div>
      )}

      <div className="max-w-6xl mx-auto px-4 sm:px-6 mt-6 space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
          {/* TONE RADAR */}
          <div className="md:col-span-7 bg-background border border-border/60 rounded-xl p-5 shadow-2xs flex flex-col justify-between">
            <div>
              <h3 className="text-sm font-bold tracking-tight text-foreground">Tone Analysis</h3>
              <p className="text-[11px] text-muted-foreground">Tỷ lệ phân phối sắc thái thực tế trích xuất từ dữ liệu nguồn</p>
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
                <div className="text-xs text-muted-foreground">Đang xử lý dữ liệu biểu đồ...</div>
              )}
            </div>

            <div className="grid grid-cols-4 gap-2 text-center pt-4 border-t border-border/40">
              {chartData.map((d) => (
                <div key={d.subject}>
                  <div className="text-base font-bold tracking-tight text-foreground">{d.value}/100</div>
                  <div className="text-[9px] text-muted-foreground uppercase font-semibold tracking-wider truncate px-0.5">
                    {d.subject.split(" ")[0]}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* BRAND SUMMARY */}
          <div className="md:col-span-5 bg-background border border-border/60 rounded-xl p-5 shadow-2xs flex flex-col justify-between">
            <div className="space-y-4">
              <h3 className="text-sm font-bold tracking-tight text-foreground mb-4">Brand Summary</h3>
              <div>
                <span className="block text-[10px] font-bold tracking-wider text-muted-foreground/80 uppercase">VỊ TRÍ / TÍNH CÁCH THƯƠNG HIỆU</span>
                <p className="text-[13px] text-foreground/90 font-medium leading-relaxed mt-0.5">
                  {brandVoice.personality || "Chưa có dữ liệu (đang xử lý)"}
                </p>
              </div>

              {/* HIỂN THỊ Ý 1: Cách xưng hô tiếng Việt (Pronouns Mapping) */}
              <div>
                <span className="block text-[10px] font-bold tracking-wider text-muted-foreground/80 uppercase flex items-center gap-1">
                  ĐẠI TỪ XƯNG HÔ ĐẶC THÙ (VIETNAMESE PRONOUNS)
                </span>
                <div className="mt-1 flex items-center gap-2 text-xs font-semibold text-foreground/90 bg-slate-50 dark:bg-slate-900 px-3 py-2 border border-border/40 rounded-lg">
                  <div>Ta: <span className="text-blue-600 dark:text-blue-400">"{brandVoice.style?.pronouns?.ai || "Chúng tôi"}"</span></div>
                  <div className="text-muted-foreground/40">|</div>
                  <div>Khách: <span className="text-blue-600 dark:text-blue-400">"{brandVoice.style?.pronouns?.reader || "Quý khách"}"</span></div>
                </div>
              </div>

              <div>
                <span className="block text-[10px] font-bold tracking-wider text-muted-foreground/80 uppercase">ĐỐI TƯỢNG ĐỘC GIẢ MỤC TIÊU</span>
                <p className="text-[13px] text-foreground/90 font-medium mt-0.5">{brandVoice.target_audience || "—"}</p>
              </div>
              <div>
                <span className="block text-[10px] font-bold tracking-wider text-muted-foreground/80 uppercase">MỤC TIÊU CHIẾN LƯỢC / USP</span>
                <p className="text-[13px] text-foreground/90 font-medium mt-0.5">{brandVoice.purpose || "—"}</p>
              </div>
              <div>
                <span className="block text-[10px] font-bold tracking-wider text-muted-foreground/80 uppercase">ĐỊNH VỊ ĐƯỜNG DẪN SOURCE URL</span>
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

            <div className="pt-4 mt-4 border-t border-border/40">
              <span className="block text-[10px] font-bold tracking-wider text-muted-foreground/80 uppercase">GIỌNG ĐIỆU CHỦ ĐẠO (VOICE)</span>
              <p className="text-[13.5px] text-foreground/90 font-semibold italic mt-0.5 capitalize">
                {toneBase.length > 0 ? `"${toneBase.join(", ")}"` : "Chưa xác định"}
              </p>
            </div>
          </div>
        </div>

        {/* WRITING RULES */}
        <div className="bg-background border border-border/60 rounded-xl p-5 shadow-2xs space-y-4">
          <h3 className="text-sm font-bold tracking-tight text-foreground">Bộ quy tắc viết bài (Writing Rules)</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="border border-emerald-500/20 bg-emerald-50/10 dark:bg-emerald-950/5 p-4 rounded-xl">
              <div className="flex items-center gap-1.5 text-emerald-700 dark:text-emerald-400 font-bold text-[11px] uppercase tracking-wider mb-2.5">
                <CheckCircle2 className="h-3.5 w-3.5" /> Nên dùng & Khuyến khích
              </div>
              {wordsToUse.length === 0 && phrasesToUse.length === 0 ? (
                <p className="text-xs text-muted-foreground">Chưa có gợi ý.</p>
              ) : (
                <ul className="space-y-1.5 text-xs text-foreground/85 font-medium list-none pl-0">
                  {wordsToUse.map((w, idx) => (
                    <li key={`use-word-${idx}`} className="flex items-center gap-2">
                      <span className="text-emerald-500 font-bold">✓</span> Dùng từ:{" "}
                      <strong className="text-emerald-700 dark:text-emerald-400">"{w}"</strong>
                    </li>
                  ))}
                  {phrasesToUse.map((p, idx) => (
                    <li key={`use-phrase-${idx}`} className="flex items-start gap-2">
                      <span className="text-emerald-500 font-bold mt-0.5">✓</span> Cấu trúc: "{p}"
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="border border-rose-500/20 bg-rose-50/10 dark:bg-rose-950/5 p-4 rounded-xl">
              <div className="flex items-center gap-1.5 text-rose-700 dark:text-rose-400 font-bold text-[11px] uppercase tracking-wider mb-2.5">
                <XCircle className="h-3.5 w-3.5" /> Cần tránh & Tuyệt đối không
              </div>
              
              {wordsToAvoid.length === 0 && phrasesToAvoid.length === 0 && topicsToAvoid.length === 0 ? (
                <p className="text-xs text-muted-foreground">Chưa có gợi ý.</p>
              ) : (
                <ul className="space-y-1.5 text-xs text-foreground/85 font-medium list-none pl-0">
                  {wordsToAvoid.map((w, idx) => (
                    <li key={`avoid-word-${idx}`} className="flex items-center gap-2">
                      <span className="text-rose-500 font-bold">✕</span> Tránh từ:{" "}
                      <strong className="text-rose-700 dark:text-rose-400">"{w}"</strong>
                    </li>
                  ))}
                  {phrasesToAvoid.map((p, idx) => (
                    <li key={`avoid-phrase-${idx}`} className="flex items-start gap-2">
                      <span className="text-rose-500 font-bold mt-0.5">✕</span> Không viết: "{p}"
                    </li>
                  ))}
                  
                  {/* HIỂN THỊ Ý 2: Bộ lọc ý tưởng/chủ đề cần tránh (Topics to Avoid Guardrails) */}
                  {topicsToAvoid.map((t, idx) => (
                    <li key={`avoid-topic-${idx}`} className="flex items-start gap-2 bg-rose-500/5 p-1.5 rounded border border-rose-500/10 mt-1">
                      <span className="text-rose-500 font-bold">⚠️</span> 
                      <div>
                        <span className="font-bold text-rose-800 dark:text-rose-400 text-[11px] block uppercase tracking-wide">CHỦ ĐỀ CẤM:</span>
                        <span className="text-foreground/90 italic">"{t}"</span>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* MODAL EDIT */}
      {isEditOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/50 backdrop-blur-xs select-none animate-in fade-in-20">
          <div className="bg-background border border-border/80 w-full max-w-xl rounded-xl shadow-lg flex flex-col max-h-[90vh] overflow-hidden">
            <div className="px-5 py-4 border-b border-border/40 flex items-center justify-between shrink-0">
              <div>
                <h2 className="text-base font-bold text-foreground">Chỉnh sửa: {brandVoice.name}</h2>
                <p className="text-[11px] text-muted-foreground/80 font-medium mt-0.5">
                  Thay đổi trọng số khẩu khí và mô tả cá tính thương hiệu gửi sang AI sinh Content
                </p>
              </div>
              <button onClick={() => setIsEditOpen(false)} className="text-muted-foreground hover:text-foreground p-1 rounded-md hover:bg-muted">
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="p-5 overflow-y-auto space-y-5 flex-1">
              <div className="space-y-4 bg-slate-50/60 dark:bg-muted/10 border border-border/40 p-4 rounded-xl">
                <span className="block text-[11px] font-bold text-muted-foreground uppercase tracking-wider flex items-center gap-1">
                  <Sliders className="h-3 w-3" /> Tone Sliders (Cập nhật thời gian thực lên API)
                </span>
                {[
                  { labelLeft: "Funny (Hài hước)", labelRight: "Serious (Nghiêm túc)", key: "tone_funny_serious" },
                  { labelLeft: "Formal (Trang trọng)", labelRight: "Casual (Bình dân)", key: "tone_formal_casual" },
                  { labelLeft: "Respectful (Tôn trọng)", labelRight: "Irreverent (Phá cách)", key: "tone_respectful_irreverent" },
                  { labelLeft: "Enthusiastic (Nhiệt huyết)", labelRight: "Matter-of-fact (Thực tế)", key: "tone_enthusiastic_matter_of_fact" },
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

              {/* Ô INPUT CHỈNH SỬA PRONOUNS TRONG MODAL */}
              <div className="grid grid-cols-2 gap-4 bg-blue-50/30 dark:bg-blue-950/5 border border-blue-100 dark:border-blue-900/30 p-4 rounded-xl">
                <div className="space-y-1">
                  <label className="block text-[10px] font-bold text-muted-foreground uppercase">Thương hiệu tự xưng</label>
                  <input 
                    type="text"
                    className="w-full bg-background border border-border rounded-lg px-2.5 py-1.5 text-xs font-semibold focus:outline-none"
                    value={editedPronouns.ai}
                    onChange={(e) => setEditedPronouns({ ...editedPronouns, ai: e.target.value })}
                    placeholder="Ví dụ: Chúng tôi, Novotel..."
                  />
                </div>
                <div className="space-y-1">
                  <label className="block text-[10px] font-bold text-muted-foreground uppercase">Gọi khách hàng là</label>
                  <input 
                    type="text"
                    className="w-full bg-background border border-border rounded-lg px-2.5 py-1.5 text-xs font-semibold focus:outline-none"
                    value={editedPronouns.reader}
                    onChange={(e) => setEditedPronouns({ ...editedPronouns, reader: e.target.value })}
                    placeholder="Ví dụ: Quý khách, Bạn..."
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <span className="block text-[11px] font-bold text-muted-foreground uppercase tracking-wider">Voice Description (Mô tả khẩu khí)</span>
                <textarea
                  rows={4}
                  className="w-full bg-background border border-border rounded-xl p-3 text-xs font-medium focus:outline-none focus:ring-1 focus:ring-primary shadow-2xs resize-none leading-relaxed"
                  value={editedPersonality}
                  onChange={(e) => setEditedPersonality(e.target.value)}
                />
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
                    personality: editedPersonality,
                    style: {
                      ...brandVoice.style,
                      pronouns: editedPronouns
                    },
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