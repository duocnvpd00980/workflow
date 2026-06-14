import { createFileRoute } from '@tanstack/react-router'
import React, { useState } from "react"
import { S, getStatusClass, STATUS_LABEL, TEMPLATE_CONFIG, COLOR_MAP } from "./brand"

// ─── Types ───────────────────────────────────────────────────────────────
interface Brand {
  id: string
  name: string
  description: string
  status: "approved" | "pending" | "archived"
  tone: string
  campaigns: number
  updatedAt: string
  icon: string
  iconColor: string
}

interface Template {
  id: string
  name: string
  icon: string
  tone: string
  color: string
}

interface Campaign {
  id: string
  name: string
  type: string
  date: string
  status: "sent" | "running" | "published"
}

// ─── Mock Data ───────────────────────────────────────────────────────────
const MOCK_BRANDS: Brand[] = [
  {
    id: "1",
    name: "Acme Corp",
    description: "Ngân hàng số cho SME",
    status: "approved",
    tone: "Professional, trustworthy",
    campaigns: 3,
    updatedAt: "2h trước",
    icon: "fa-building",
    iconColor: "blue",
  },
  {
    id: "2",
    name: "ShopX",
    description: "Thời trang trẻ trung",
    status: "pending",
    tone: "Friendly, playful",
    campaigns: 1,
    updatedAt: "5p trước",
    icon: "fa-shopping-bag",
    iconColor: "pink",
  },
  {
    id: "3",
    name: "TechFlow",
    description: "AI/ML platform",
    status: "pending",
    tone: "Technical, authoritative",
    campaigns: 0,
    updatedAt: "1 ngày trước",
    icon: "fa-microchip",
    iconColor: "purple",
  },
]

const MOCK_TEMPLATES: Template[] = [
  { id: "email", name: "Email", icon: "fa-envelope", tone: "Professional + Warm", color: "green" },
  { id: "social", name: "Social", icon: "fa-share-alt", tone: "Professional + Playful", color: "blue" },
  { id: "blog", name: "Blog", icon: "fa-file-alt", tone: "Professional + Educational", color: "purple" },
  { id: "ads", name: "Ads", icon: "fa-bullseye", tone: "Professional + Persuasive", color: "orange" },
  { id: "pr", name: "PR", icon: "fa-newspaper", tone: "Professional + Formal", color: "gray" },
]

const MOCK_CAMPAIGNS: Campaign[] = [
  { id: "1", name: "Email Marketing tháng 6", type: "email", date: "12/06/2026", status: "sent" },
  { id: "2", name: "Social Media Q2", type: "social", date: "10/06/2026", status: "running" },
  { id: "3", name: "Landing Page Product", type: "landing", date: "08/06/2026", status: "published" },
]

export const Route = createFileRoute("/brand")({
  validateSearch: (search: Record<string, unknown>) => ({
    syncOpen: (search.syncOpen as boolean) || undefined,
    selectedBrandId: (search.selectedBrandId as string) || undefined,
  }),
  component: ScreenBrandVoice,
});

// ─── Component ───────────────────────────────────────────────────────────
export default function ScreenBrandVoice() {
  const [selectedBrand, setSelectedBrand] = useState<Brand>(MOCK_BRANDS[0])
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null)
  const [showEdit, setShowEdit] = useState(false)
  const [showTestResult, setShowTestResult] = useState(false)
  const [testPrompt, setTestPrompt] = useState("")
  const [contentPrompt, setContentPrompt] = useState("")
  const [filter, setFilter] = useState("all")

  const filteredBrands = MOCK_BRANDS.filter((b) => {
    if (filter === "all") return true
    return b.status === filter
  })

  const handleSelectBrand = (brand: Brand) => {
    setSelectedBrand(brand)
    setSelectedTemplate(null)
    setShowTestResult(false)
  }

  const handleSelectTemplate = (templateId: string) => {
    setSelectedTemplate(templateId)
  }

  const handleGenerateContent = () => {
    if (!contentPrompt) return
    alert(`AI đang viết ${selectedTemplate} với tone ${selectedBrand.tone}...\n\nChủ đề: ${contentPrompt}`)
  }

  const handleRunTest = () => {
    if (!testPrompt) return
    setShowTestResult(true)
  }

  const handleSaveEdit = () => {
    setShowEdit(false)
    alert("Đã lưu thay đổi!")
  }

  return (
    <div className={S.appContainer}>
      {/* ─── Sidebar ─── */}
      <aside className={S.sidebar}>
        <div className={S.sidebarLogo}>
          <div className={S.sidebarLogoIcon}>
            <i className="fas fa-bolt text-white text-sm" />
          </div>
          <span className={S.sidebarLogoText}>Agent</span>
        </div>

        <div className={S.sidebarSection}>
          <div className={S.sidebarSectionLabel}>Chính</div>
          <nav className="space-y-0.5">
            {["Tạo", "Tri thức", "Brand", "Kế hoạch", "Tra cứu"].map((item, i) => (
              <a
                key={item}
                href="#"
                className={`${S.sidebarItem} ${item === "Brand" ? S.sidebarItemActive : S.sidebarItemInactive}`}
              >
                <i className={`fas ${["fa-bolt", "fa-brain", "fa-palette", "fa-bolt", "fa-bolt"][i]} w-4 text-center`} />
                <span>{item}</span>
              </a>
            ))}
          </nav>
        </div>

        <div className={S.sidebarSection}>
          <div className={S.sidebarSectionLabel}>Quản lý</div>
          <nav className="space-y-0.5">
            {["Kho", "Lịch sử", "Thống kê", "Tích hợp"].map((item, i) => (
              <a key={item} href="#" className={`${S.sidebarItem} ${S.sidebarItemInactive}`}>
                <i className={`fas ${["fa-cube", "fa-clock", "fa-chart-bar", "fa-plug"][i]} w-4 text-center`} />
                <span>{item}</span>
              </a>
            ))}
          </nav>
        </div>

        <div className={S.sidebarFooter}>
          <div className={S.sidebarFooterBadge}>
            <i className="fas fa-route text-green-400" />
            <span>TanStack Router</span>
          </div>
        </div>
      </aside>

      {/* ─── Main ─── */}
      <main className={S.mainContent}>
        {/* Header */}
        <header className={S.header}>
          <div className={S.headerContent}>
            <div>
              <h1 className={S.headerTitle}>Brand Voice</h1>
              <p className={S.headerSubtitle}>AI viết content đúng tone thương hiệu</p>
            </div>
            <div className={S.headerActions}>
              <button className={`${S.btn} ${S.btnSecondary}`}>
                <i className="fas fa-sync-alt mr-2" />
                Research mới
              </button>
              <button className={`${S.btn} ${S.btnPrimary}`}>
                <i className="fas fa-plus mr-2" />
                Tạo Brand Voice
              </button>
            </div>
          </div>
        </header>

        {/* Toolbar */}
        <div className={S.toolbar}>
          <div className={S.toolbarContent}>
            <div className={S.toolbarLeft}>
              <div className={S.searchBox}>
                <i className={`fas fa-search ${S.searchIcon}`} />
                <input type="text" placeholder="Tìm brand voice..." className={S.searchInput} />
              </div>
              <div className={S.filterTabs}>
                {["all", "approved", "pending"].map((f) => (
                  <button
                    key={f}
                    onClick={() => setFilter(f)}
                    className={`${S.filterTab} ${filter === f ? S.filterTabActive : S.filterTabInactive}`}
                  >
                    {f === "all" ? "Tất cả" : f === "approved" ? "Đã duyệt" : "Chờ duyệt"}
                  </button>
                ))}
              </div>
            </div>
            <span className={S.toolbarCount}>{filteredBrands.length} brand voices</span>
          </div>
        </div>

        {/* Split View */}
        <div className={S.splitView}>
          {/* Brand List */}
          <div className={S.brandList}>
            <div className={S.brandListHeader}>Thương hiệu</div>
            {filteredBrands.map((brand) => (
              <div
                key={brand.id}
                onClick={() => handleSelectBrand(brand)}
                className={`${S.brandItem} ${selectedBrand.id === brand.id ? S.brandItemSelected : S.brandItemDefault}`}
              >
                <div className="flex items-start gap-3">
                  <div className={`${S.brandItemIcon} ${COLOR_MAP[brand.iconColor]}`}>
                    <i className={`fas ${brand.icon}`} />
                  </div>
                  <div className={S.brandItemContent}>
                    <div className={S.brandItemHeader}>
                      <span className={S.brandItemName}>{brand.name}</span>
                      <span className={`${S.statusBadge} ${getStatusClass(brand.status)}`}>
                        {STATUS_LABEL[brand.status]}
                      </span>
                    </div>
                    <p className={S.brandItemDesc}>{brand.description}</p>
                    <div className={S.brandItemMeta}>
                      <span className={S.brandItemMetaText}>
                        <i className="fas fa-robot mr-1" />
                        {brand.updatedAt}
                      </span>
                      <span className={S.brandItemMetaText}>• {brand.campaigns} chiến dịch</span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Preview Panel */}
          <div className={S.previewPanel}>
            {/* Preview Header */}
            <div className={S.previewHeader}>
              <div className={S.previewHeaderContent}>
                <div className={S.previewBrandInfo}>
                  <div className={`${S.previewBrandIcon} ${COLOR_MAP[selectedBrand.iconColor]}`}>
                    <i className={`fas ${selectedBrand.icon} text-lg`} />
                  </div>
                  <div>
                    <h2 className={S.previewBrandName}>{selectedBrand.name}</h2>
                    <div className={S.previewBrandMeta}>
                      <span className={`${S.statusBadge} ${getStatusClass(selectedBrand.status)}`}>
                        {STATUS_LABEL[selectedBrand.status]}
                      </span>
                      <span className="text-xs text-gray-400">• AI phân tích từ Research #123</span>
                      <span className="text-xs text-gray-400">• {selectedBrand.updatedAt}</span>
                    </div>
                  </div>
                </div>
                <div className={S.previewActions}>
                  <button onClick={() => setShowEdit(true)} className={`${S.btn} ${S.btnSecondary} ${S.btnIcon}`}>
                    <i className="fas fa-edit mr-2" />
                    Chỉnh sửa
                  </button>
                  <button className={`${S.btn} ${S.btnSecondary} ${S.btnIcon}`}>
                    <i className="fas fa-file-export mr-2" />
                    Export
                  </button>
                </div>
              </div>
            </div>

            {/* Preview Content */}
            <div className="p-6 space-y-6">
              {/* Tone Radar + Summary */}
              <div className="grid grid-cols-2 gap-6">
                <div className={S.card}>
                  <h3 className={S.cardTitle}>Tone Analysis</h3>
                  <div className={S.radarContainer}>
                    <canvas id="toneRadar" width="220" height="220" />
                  </div>
                  <div className={S.radarStats}>
                    {[
                      { value: "90%", label: "Professional" },
                      { value: "85%", label: "Trustworthy" },
                      { value: "80%", label: "Clear" },
                      { value: "75%", label: "Formal" },
                    ].map((stat) => (
                      <div key={stat.label} className={S.radarStat}>
                        <div className={S.radarStatValue}>{stat.value}</div>
                        <div className={S.radarStatLabel}>{stat.label}</div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className={S.card}>
                  <h3 className={S.cardTitle}>Brand Summary</h3>
                  <div className={S.summarySection}>
                    {[
                      { label: "Vị trí", value: "Ngân hàng số cho doanh nghiệp SME" },
                      { label: "Đối tượng", value: "Doanh nghiệp nhỏ 25-50 nhân viên" },
                      { label: "Điểm khác biệt", value: "Tiết kiệm 30% thời gian quản lý tài chính" },
                      { label: "Voice", value: `"Chuyên nghiệp, đáng tin cậy, dùng ngôn ngữ rõ ràng"` },
                    ].map((item) => (
                      <div key={item.label} className={S.summaryItem}>
                        <div className={S.summaryLabel}>{item.label}</div>
                        <p className={S.summaryValue}>{item.value}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Templates */}
              <div className={S.card}>
                <div className="flex items-center justify-between mb-4">
                  <h3 className={S.cardTitle}>AI Viết Content</h3>
                  <span className={S.cardSubtitle}>Chọn loại content — AI tự điều chỉnh tone</span>
                </div>
                <div className={S.templatesGrid}>
                  {MOCK_TEMPLATES.map((template) => (
                    <div
                      key={template.id}
                      onClick={() => handleSelectTemplate(template.id)}
                      className={`${S.templateCard} ${S.templateCardHover} ${selectedTemplate === template.id ? S.templateCardSelected : ""}`}
                    >
                      <div className={`${S.templateIcon} ${COLOR_MAP[template.color]}`}>
                        <i className={`fas ${template.icon} text-lg`} />
                      </div>
                      <div className={S.templateName}>{template.name}</div>
                      <div className={S.templateTone}>{template.tone}</div>
                    </div>
                  ))}
                </div>
                <div className={`${S.templateAction} ${selectedTemplate ? S.templateActionVisible : ""}`}>
                  <input
                    type="text"
                    value={contentPrompt}
                    onChange={(e) => setContentPrompt(e.target.value)}
                    placeholder="Nhập chủ đề content..."
                    className={S.testInputField}
                  />
                  <button onClick={handleGenerateContent} className={`${S.btn} ${S.btnPrimary}`}>
                    <i className="fas fa-magic mr-2" />
                    AI Viết
                  </button>
                </div>
              </div>

              {/* AI Test Panel */}
              <div className={S.card}>
                <div className="flex items-center justify-between mb-4">
                  <h3 className={S.cardTitle}>AI Test Panel</h3>
                  <span className={S.cardSubtitle}>Verify tone trước khi dùng</span>
                </div>
                <div className={S.testInput}>
                  <input
                    type="text"
                    value={testPrompt}
                    onChange={(e) => setTestPrompt(e.target.value)}
                    placeholder="Viết email giới thiệu sản phẩm mới..."
                    className={S.testInputField}
                  />
                  <button onClick={handleRunTest} className={`${S.btn} ${S.btnPrimary}`}>
                    <i className="fas fa-sync-alt mr-2" />
                    Test
                  </button>
                </div>
                <div className={`${S.testResult} ${showTestResult ? S.testResultVisible : ""}`}>
                  <div className={S.testResultHeader}>
                    <div className={S.testResultIcon}>
                      <i className="fas fa-robot text-white text-xs" />
                    </div>
                    <div className={S.testResultContent}>
                      <p className={S.testResultText}>
                        "Kính gửi Anh/Chị,<br /><br />
                        Acme Corp trân trọng giới thiệu tính năng quản lý dòng tiền thông minh — giải pháp giúp doanh nghiệp SME tiết kiệm 30% thời gian xử lý tài chính hàng ngày.<br /><br />
                        Trân trọng,<br />
                        Đội ngũ Acme Corp"
                      </p>
                      <div className={S.testResultActions}>
                        <button className={`${S.testResultAction} ${S.testResultActionSuccess}`}>
                          <i className="fas fa-check mr-1" />Đúng tone
                        </button>
                        <button className={`${S.testResultAction} ${S.testResultActionError}`}>
                          <i className="fas fa-times mr-1" />Sai tone
                        </button>
                        <button className={`${S.testResultAction} ${S.testResultActionNeutral}`}>
                          <i className="fas fa-redo mr-1" />Generate lại
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Usage History */}
              <div className={S.card}>
                <h3 className={S.cardTitle}>Lịch sử sử dụng</h3>
                <div className={S.historyList}>
                  {MOCK_CAMPAIGNS.map((campaign, i) => (
                    <div key={campaign.id} className={i === MOCK_CAMPAIGNS.length - 1 ? S.historyItemLast : S.historyItem}>
                      <div className={S.historyItemInfo}>
                        <div className={`${S.historyItemIcon} ${COLOR_MAP[["green", "blue", "purple"][i]]}`}>
                          <i className={`fas ${["fa-envelope", "fa-share-alt", "fa-file-alt"][i]} text-xs`} />
                        </div>
                        <div>
                          <div className={S.historyItemName}>{campaign.name}</div>
                          <div className="text-xs text-gray-400">{campaign.date}</div>
                        </div>
                      </div>
                      <span className={`${S.historyItemStatus} ${campaign.status === "sent" || campaign.status === "published" ? S.historyStatusSuccess : S.historyStatusRunning}`}>
                        {campaign.status === "sent" ? "Đã gửi" : campaign.status === "running" ? "Đang chạy" : "Đã publish"}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* ─── Edit Modal ─── */}
      {showEdit && (
        <div className={S.modalOverlay} onClick={() => setShowEdit(false)}>
          <div className={`${S.modalContent} w-[600px]`} onClick={(e) => e.stopPropagation()}>
            <div className={S.modalHeader}>
              <div>
                <h2 className={S.modalTitle}>Chỉnh sửa: {selectedBrand.name}</h2>
                <p className={S.modalSubtitle}>AI phân tích từ Research #123 • Chỉnh sửa nếu không chính xác</p>
              </div>
              <button onClick={() => setShowEdit(false)} className={S.modalClose}>
                <i className="fas fa-times text-gray-500" />
              </button>
            </div>
            <div className={S.modalBody}>
              <div className="space-y-5">
                {/* Tone Sliders */}
                <div>
                  <label className={S.formLabel}>
                    Tone Sliders <span className="text-xs text-gray-400 font-normal">(kéo nếu AI phân tích sai)</span>
                  </label>
                  <div className="space-y-4 bg-gray-50 rounded-lg p-4">
                    {[
                      { label: "Funny", opposite: "Serious", value: 85 },
                      { label: "Formal", opposite: "Casual", value: 75 },
                      { label: "Respectful", opposite: "Irreverent", value: 80 },
                      { label: "Enthusiastic", opposite: "Matter-of-fact", value: 60 },
                    ].map((slider) => (
                      <div key={slider.label}>
                        <div className="flex justify-between text-xs text-gray-500 mb-1">
                          <span>{slider.label}</span>
                          <span>{slider.opposite}</span>
                        </div>
                        <input type="range" defaultValue={slider.value} className={S.slider} />
                      </div>
                    ))}
                  </div>
                </div>

                {/* Voice Description */}
                <div>
                  <label className={S.formLabel}>
                    Voice Description <span className="text-xs text-gray-400 font-normal">(AI generated)</span>
                  </label>
                  <textarea
                    defaultValue='"Giọng điệu chuyên nghiệp, đáng tin cậy, dùng ngôn ngữ rõ ràng và có cấu trúc. Thích hợp cho B2B tài chính."'
                    rows={3}
                    className={S.formTextarea}
                  />
                </div>

                {/* Writing Rules */}
                <div>
                  <label className={S.formLabel}>Writing Rules</label>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                      <div className="text-xs font-medium text-green-700 mb-2">DO'S</div>
                      <div className="space-y-1.5">
                        {["Dùng số liệu cụ thể", "Giải thích lợi ích rõ ràng", "Giọng điệu ổn định"].map((rule) => (
                          <div key={rule} className="flex items-center gap-2 text-sm text-gray-700">
                            <i className="fas fa-check text-green-500 text-xs" />
                            {rule}
                          </div>
                        ))}
                      </div>
                    </div>
                    <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                      <div className="text-xs font-medium text-red-700 mb-2">DON'TS</div>
                      <div className="space-y-1.5">
                        {["Không dùng slang", "Không hứa hẹn vô căn cứ", "Không so sánh đối thủ"].map((rule) => (
                          <div key={rule} className="flex items-center gap-2 text-sm text-gray-700">
                            <i className="fas fa-times text-red-500 text-xs" />
                            {rule}
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div className={S.modalFooter}>
              <div className="text-xs text-gray-400">Nguồn: Research #123 • AI phân tích 15/06 14:30</div>
              <div className="flex items-center gap-2">
                <button onClick={() => setShowEdit(false)} className={`${S.btn} ${S.btnSecondary}`}>
                  Hủy
                </button>
                <button onClick={handleSaveEdit} className={`${S.btn} ${S.btnPrimary}`}>
                  Lưu thay đổi
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}