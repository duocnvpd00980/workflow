import { createFileRoute } from '@tanstack/react-router'


import React, { useState } from "react"
import { S, RESEARCH_TYPES, STATUS_MAP } from "./styles_research"



export const Route = createFileRoute('/page_research')({
  component: ScreenResearch,
})




// ─── Types ───────────────────────────────────────────────────────────────
interface ResearchJob {
  id: string
  topic: string
  type: keyof typeof RESEARCH_TYPES
  status: "completed" | "pending" | "failed"
  progress: number
  sources: number
  createdAt: string
}

interface Competitor {
  name: string
  share: number
  strengths: string[]
  weaknesses: string[]
  tone: string
}

interface Audience {
  segment: string
  age: string
  pains: string[]
  motivations: string[]
  channels: string[]
}

// ─── Mock Data ───────────────────────────────────────────────────────────
const JOBS: ResearchJob[] = [
  { id: "1", topic: "Phân tích đối thủ ngân hàng số VN", type: "competitor", status: "completed", progress: 100, sources: 15, createdAt: "2h trước" },
  { id: "2", topic: "Nghiên cứu khách hàng SME", type: "audience", status: "completed", progress: 100, sources: 23, createdAt: "1 ngày trước" },
  { id: "3", topic: "Xu hướng AI marketing 2026", type: "market", status: "pending", progress: 65, sources: 8, createdAt: "Đang chạy" },
]

const COMPETITORS: Competitor[] = [
  { name: "Timo", share: 28, strengths: ["Onboarding nhanh", "UX tốt"], weaknesses: ["Thiếu doanh nghiệp", "Phí cao"], tone: "Trẻ trung" },
  { name: "VietinBank iPay", share: 35, strengths: ["Thương hiệu lớn", "Mạng lưới"], weaknesses: ["UX lỗi thời", "Thủ tục phức"], tone: "Truyền thống" },
  { name: "MoMo", share: 22, strengths: ["Ví #1", "Thanh toán"], weaknesses: ["Chưa đủ ngân hàng", "Phí dịch vụ"], tone: "Tiện lợi" },
]

const AUDIENCES: Audience[] = [
  { segment: "Chủ doanh nghiệp nhỏ", age: "30-45", pains: ["Thủ tục phức tạp", "Quản lý dòng tiền"], motivations: ["Tiết kiệm thời gian", "Minh bạch"], channels: ["Facebook", "Zalo", "Email"] },
  { segment: "Kế toán viên", age: "25-40", pains: ["Nhập liệu thủ công", "Báo cáo tốn tg"], motivations: ["Tự động hóa", "Real-time"], channels: ["LinkedIn", "Email", "Web"] },
]

const INSIGHTS = [
  { title: "Thị trường ngân hàng số tăng 35%/năm", text: "Nhu cầu SME tăng mạnh do thủ tục truyền thống quá phức tạp. Các ngân hàng số mới chiếm 40% thị phần.", source: "Báo cáo NHNN 2026" },
  { title: "Đối thủ chính: Timo, VietinBank, MoMo", text: "Timo dẫn UX nhưng thiếu doanh nghiệp. VietinBank có thương hiệu nhưng UX lỗi thời. MoMo mạnh ví nhưng chưa đủ ngân hàng.", source: "App Store & Google Play" },
  { title: "SME cần: đơn giản, nhanh, minh bạch", text: "68% chủ doanh nghiệp bỏ ngang onboarding do phức tạp. 80% ưu tiên minh bạch phí hơn lãi suất thấp.", source: "Khảo sát SMB Vietnam 2026" },
  { title: "Cơ hội: Onboarding 5 phút, phí rõ ràng", text: "Không đối thủ nào onboarding dưới 10 phút. Phí ẩn là khiếu nại #1 của khách hàng.", source: "Đánh giá khách hàng" },
  { title: "Rủi ro: Big Tech (Grab, Shopee)", text: "Grab và Shopee đang xin giấy phép ngân hàng số. Họ có lợi thế ecosystem và data khách hàng khổng lồ.", source: "Thông cáo NHNN 2026" },
]

const SOURCES = [
  { title: "Báo cáo Ngân hàng Nhà nước 2026", url: "nhnn.gov.vn", type: "Gov" },
  { title: "Khảo sát SMB Vietnam 2026", url: "vista.vn", type: "Survey" },
  { title: "Phân tích App Store & Google Play", url: "sensor-tower.com", type: "Data" },
  { title: "Thông cáo NHNN về fintech", url: "nhnn.gov.vn", type: "Gov" },
  { title: "Báo cáo thị trường ngân hàng số", url: "mckinsey.com", type: "Report" },
]

// ─── Component ───────────────────────────────────────────────────────────
export default function ScreenResearch() {
  const [query, setQuery] = useState("")
  const [isRunning, setIsRunning] = useState(false)
  const [progress, setProgress] = useState(0)
  const [showResults, setShowResults] = useState(false)
  const [tab, setTab] = useState("overview")

  const startResearch = () => {
    if (!query) return
    setIsRunning(true)
    setProgress(0)
    setShowResults(false)
    const interval = setInterval(() => {
      setProgress((p) => {
        if (p >= 100) {
          clearInterval(interval)
          setIsRunning(false)
          setShowResults(true)
          return 100
        }
        return p + 12
      })
    }, 400)
  }

  const setPrompt = (p: string) => setQuery(p)

  return (
    <div className={S.layout}>
      {/* ─── Sidebar ─── */}
      <aside className={S.sidebar}>
        <div className={S.sidebarHeader}>
          <div className={S.sidebarLogo}>
            <i className="fas fa-bolt text-white text-xs" />
          </div>
          <span className={S.sidebarTitle}>Agent</span>
        </div>
        <nav className={S.sidebarNav}>
          {[
            { name: "Tạo", icon: "fa-bolt", active: false },
            { name: "Tri thức", icon: "fa-brain", active: true },
            { name: "Brand", icon: "fa-palette", active: false },
            { name: "Kế hoạch", icon: "fa-bolt", active: false },
            { name: "Tra cứu", icon: "fa-bolt", active: false },
          ].map((item) => (
            <a key={item.name} href="#" className={`${S.sidebarItem} ${item.active ? S.sidebarItemActive : S.sidebarItemInactive}`}>
              <i className={`fas ${item.icon} ${item.active ? S.sidebarIconActive : S.sidebarIcon}`} />
              <span>{item.name}</span>
            </a>
          ))}
        </nav>
        <div className={S.sidebarFooter}>
          <div className={S.sidebarFooterItem}>
            <i className="fas fa-route text-green-500" />
            <span>TanStack Router</span>
          </div>
        </div>
      </aside>

      {/* ─── Main ─── */}
      <main className={S.main}>
        {/* Top Bar */}
        <div className={S.topbar}>
          <div className={S.topbarLeft}>
            <span className={S.topbarTitle}>Nghiên cứu thông minh</span>
            <span className={S.topbarBreadcrumb}> / Tri thức</span>
          </div>
          <div className={S.topbarRight}>
            <button className={`${S.topbarBtn} ${S.topbarBtnSecondary}`}>
              <i className="fas fa-history mr-1" />
              Lịch sử
            </button>
          </div>
        </div>

        {/* Content */}
        <div className={S.content}>
          <div className={S.contentInner}>
            {/* Hero Input */}
            <div className={S.hero}>
              <h1 className={S.heroTitle}>Bạn muốn nghiên cứu gì?</h1>
              <p className={S.heroDesc}>AI tự động tìm nguồn, phân tích và tổng hợp</p>
              <div className={S.inputBox}>
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Phân tích đối thủ ngân hàng số tại Việt Nam..."
                  className={S.inputField}
                  onKeyDown={(e) => e.key === "Enter" && startResearch()}
                />
                <button onClick={startResearch} className={S.inputBtn}>
                  {isRunning ? <i className="fas fa-spinner fa-spin" /> : <i className="fas fa-arrow-right" />}
                </button>
              </div>
              <div className={S.quickActions}>
                {["Phân tích đối thủ", "Nghiên cứu khách hàng", "Xu hướng thị trường", "Định vị thương hiệu", "Nghiên cứu sản phẩm"].map((p) => (
                  <button key={p} onClick={() => setPrompt(p)} className={S.quickAction}>{p}</button>
                ))}
              </div>
            </div>

            {/* Progress */}
            {isRunning && (
              <div className={S.progressCard}>
                <div className={S.progressHeader}>
                  <span className={S.progressTitle}>Đang phân tích: {query}</span>
                  <span className={S.progressStatus}>{progress}%</span>
                </div>
                <div className={S.progressBar}>
                  <div className={S.progressFill} style={{ width: `${progress}%` }} />
                </div>
                <div className={S.progressSteps}>
                  {[
                    { label: "Tìm nguồn", done: progress >= 20 },
                    { label: "Phân tích đối thủ", done: progress >= 40 },
                    { label: "Nghiên cứu KH", done: progress >= 60 },
                    { label: "Tổng hợp", done: progress >= 80 },
                    { label: "Tạo báo cáo", done: progress >= 100 },
                  ].map((step, i) => (
                    <div key={i} className={`${S.progressStep} ${step.done ? S.progressStepDone : progress >= i * 20 && progress < (i + 1) * 20 ? S.progressStepActive : S.progressStepPending}`}>
                      <i className={`fas ${step.done ? "fa-check-circle" : "fa-circle"} ${S.progressStepIcon}`} />
                      <span>{step.label}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Results */}
            {showResults && (
              <>
                {/* Tabs */}
                <div className={S.tabs}>
                  {[
                    { id: "overview", label: "Tổng quan" },
                    { id: "competitor", label: "Đối thủ" },
                    { id: "audience", label: "Khách hàng" },
                    { id: "sources", label: "Nguồn" },
                  ].map((t) => (
                    <button key={t.id} onClick={() => setTab(t.id)} className={`${S.tab} ${tab === t.id ? S.tabActive : S.tabInactive}`}>
                      {t.label}
                    </button>
                  ))}
                </div>

                {/* Overview */}
                {tab === "overview" && (
                  <div className="space-y-4">
                    <div className={S.card}>
                      <div className={S.cardHeader}>
                        <span className={S.cardTitle}>Insights chính</span>
                        <span className={S.cardBadge}>5 insights</span>
                      </div>
                      <div className={S.cardBody}>
                        {INSIGHTS.map((insight, i) => (
                          <div key={i} className={i === INSIGHTS.length - 1 ? S.insightItemLast : S.insightItem}>
                            <div className={S.insightNumber}>{i + 1}</div>
                            <div className={S.insightContent}>
                              <div className={S.insightTitle}>{insight.title}</div>
                              <p className={S.insightText}>{insight.text}</p>
                              <div className={S.insightSource}>
                                <i className="fas fa-link text-xs" />
                                {insight.source}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                    <div className="grid grid-cols-4 gap-3">
                      {[
                        { v: "15", l: "Nguồn", i: "fa-file-alt" },
                        { v: "3", l: "Đối thủ", i: "fa-users" },
                        { v: "2", l: "Phân khúc", i: "fa-user-friends" },
                        { v: "5", l: "Insights", i: "fa-lightbulb" },
                      ].map((s) => (
                        <div key={s.l} className="bg-white border border-gray-200 rounded-lg p-3 text-center">
                          <div className="text-2xl font-bold text-gray-900">{s.v}</div>
                          <div className="text-xs text-gray-500">{s.l}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Competitor */}
                {tab === "competitor" && (
                  <div className={S.card}>
                    <div className={S.cardHeader}>
                      <span className={S.cardTitle}>Phân tích đối thủ</span>
                      <span className={S.cardBadge}>3 đối thủ</span>
                    </div>
                    <div className={S.cardBody}>
                      <div className={S.compGrid}>
                        {COMPETITORS.map((c) => (
                          <div key={c.name} className={S.compCard}>
                            <div className={S.compName}>{c.name}</div>
                            <div className={S.compMeta}>
                              <div className={S.compRow}>
                                <span className={S.compLabel}>Thị phần</span>
                                <span className={S.compValue}>{c.share}%</span>
                              </div>
                              <div className={S.compBar}>
                                <div className={S.compBarFill} style={{ width: `${c.share}%` }} />
                              </div>
                              <div className={S.compRow}>
                                <span className={S.compLabel}>Tone</span>
                                <span className={S.compValue}>{c.tone}</span>
                              </div>
                              <div className={S.compTags}>
                                {c.strengths.map((s) => (
                                  <span key={s} className={S.compTagGreen}>{s}</span>
                                ))}
                                {c.weaknesses.map((w) => (
                                  <span key={w} className={S.compTagRed}>{w}</span>
                                ))}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {/* Audience */}
                {tab === "audience" && (
                  <div className={S.card}>
                    <div className={S.cardHeader}>
                      <span className={S.cardTitle}>Chân dung khách hàng</span>
                      <span className={S.cardBadge}>2 phân khúc</span>
                    </div>
                    <div className={S.cardBody}>
                      <div className={S.audienceGrid}>
                        {AUDIENCES.map((a) => (
                          <div key={a.segment} className={S.audienceCard}>
                            <div className={S.audienceHeader}>
                              <div className={S.audienceIcon}>
                                <i className="fas fa-user text-gray-500" />
                              </div>
                              <div>
                                <div className={S.audienceName}>{a.segment}</div>
                                <div className={S.audienceSubtitle}>{a.age}</div>
                              </div>
                            </div>
                            <div className={S.audienceStats}>
                              <div className={S.audienceStat}>
                                <div className={S.audienceStatValue}>{a.pains.length}</div>
                                <div className={S.audienceStatLabel}>Pain points</div>
                              </div>
                              <div className={S.audienceStat}>
                                <div className={S.audienceStatValue}>{a.motivations.length}</div>
                                <div className={S.audienceStatLabel}>Motivations</div>
                              </div>
                            </div>
                            <div className={S.audienceTags}>
                              {a.channels.map((c) => (
                                <span key={c} className={S.audienceTag}>{c}</span>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {/* Sources */}
                {tab === "sources" && (
                  <div className={S.card}>
                    <div className={S.cardHeader}>
                      <span className={S.cardTitle}>Nguồn dữ liệu</span>
                      <span className={S.cardBadge}>15 nguồn</span>
                    </div>
                    <div className={S.cardBody}>
                      <div className={S.sourceList}>
                        {SOURCES.map((s) => (
                          <div key={s.title} className={S.sourceItem}>
                            <div className={S.sourceFavicon}>
                              <i className="fas fa-file text-gray-400 text-xs" />
                            </div>
                            <div className={S.sourceInfo}>
                              <div className={S.sourceTitle}>{s.title}</div>
                              <div className={S.sourceUrl}>{s.url}</div>
                            </div>
                            <span className={S.sourceType}>{s.type}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}

            {/* Recent Jobs */}
            {!isRunning && !showResults && (
              <>
                <h3 className="text-sm font-semibold text-gray-900 mb-3">Nghiên cứu gần đây</h3>
                <div className={S.jobsList}>
                  {JOBS.map((job) => (
                    <div key={job.id} className={S.jobItem}>
                      <div className={`${S.jobIcon} bg-${RESEARCH_TYPES[job.type].color}-100`}>
                        <i className={`fas ${RESEARCH_TYPES[job.type].icon} text-${RESEARCH_TYPES[job.type].color}-600`} />
                      </div>
                      <div className={S.jobInfo}>
                        <div className={S.jobTitle}>{job.topic}</div>
                        <div className={S.jobMeta}>
                          {RESEARCH_TYPES[job.type].label} • {job.sources} nguồn • {job.createdAt}
                        </div>
                      </div>
                      <span className={`${S.jobStatus} ${STATUS_MAP[job.status].class}`}>
                        {STATUS_MAP[job.status].label}
                      </span>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>

        {/* Action Bar */}
        {showResults && (
          <div className={S.actionBar}>
            <span className={S.actionBarInfo}>
              Research: <strong className="text-gray-900">{query}</strong>
            </span>
            <div className={S.actionBarActions}>
              <button className={`${S.btn} ${S.btnSecondary}`}>
                <i className="fas fa-file-export mr-1" />
                Export
              </button>
              <button className={`${S.btn} ${S.btnPrimary}`}>
                <i className="fas fa-magic mr-1" />
                Tạo Brand Voice
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
