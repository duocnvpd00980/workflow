
export const S = {
  // Layout
  layout: "flex h-screen bg-white",
  main: "flex-1 flex flex-col min-w-0",
  
  // Sidebar (Notion-style)
  sidebar: "w-60 bg-gray-50 border-r border-gray-200 flex flex-col flex-shrink-0",
  sidebarHeader: "p-3 flex items-center gap-2",
  sidebarLogo: "w-6 h-6 bg-black rounded flex items-center justify-center",
  sidebarTitle: "font-semibold text-sm text-gray-900",
  sidebarNav: "px-2 py-1 space-y-0.5",
  sidebarItem: "flex items-center gap-2 px-2 py-1.5 rounded-md text-sm transition-colors",
  sidebarItemActive: "bg-gray-200 text-gray-900 font-medium",
  sidebarItemInactive: "text-gray-600 hover:bg-gray-100",
  sidebarIcon: "w-4 h-4 text-gray-500",
  sidebarIconActive: "w-4 h-4 text-gray-900",
  sidebarFooter: "mt-auto p-3 border-t border-gray-200",
  sidebarFooterItem: "flex items-center gap-2 px-2 py-1.5 text-xs text-gray-500",
  
  // Top Bar (Jasper-style)
  topbar: "h-12 border-b border-gray-200 flex items-center justify-between px-4 bg-white",
  topbarLeft: "flex items-center gap-3",
  topbarTitle: "font-semibold text-sm text-gray-900",
  topbarBreadcrumb: "text-xs text-gray-400",
  topbarRight: "flex items-center gap-2",
  topbarBtn: "px-3 py-1.5 rounded-md text-xs font-medium transition-colors",
  topbarBtnPrimary: "bg-gray-900 text-white hover:bg-gray-800",
  topbarBtnSecondary: "bg-white border border-gray-200 text-gray-700 hover:bg-gray-50",
  
  // Content Area
  content: "flex-1 overflow-y-auto",
  contentInner: "max-w-4xl mx-auto px-8 py-8",
  
  // Hero Input (Notion AI style)
  hero: "mb-8",
  heroTitle: "text-3xl font-bold text-gray-900 mb-2",
  heroDesc: "text-sm text-gray-500 mb-6",
  inputBox: "relative",
  inputField: "w-full px-4 py-3 pr-12 bg-white border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent shadow-sm",
  inputBtn: "absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 bg-gray-900 text-white rounded-md flex items-center justify-center text-xs hover:bg-gray-800",
  
  // Quick Actions (Notion-style pills)
  quickActions: "flex flex-wrap gap-2 mt-4",
  quickAction: "px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded-md text-xs text-gray-600 transition-colors cursor-pointer",
  
  // Progress (Jasper-style)
  progressCard: "bg-white border border-gray-200 rounded-lg p-4 mb-6",
  progressHeader: "flex items-center justify-between mb-3",
  progressTitle: "text-sm font-medium text-gray-900",
  progressStatus: "text-xs text-gray-500",
  progressBar: "w-full h-1.5 bg-gray-100 rounded-full overflow-hidden",
  progressFill: "h-1.5 bg-blue-500 rounded-full transition-all duration-500",
  progressSteps: "flex items-center gap-4 mt-3",
  progressStep: "flex items-center gap-1.5 text-xs",
  progressStepDone: "text-gray-900",
  progressStepActive: "text-blue-600 font-medium",
  progressStepPending: "text-gray-400",
  progressStepIcon: "w-4 h-4",
  
  // Cards (Jasper-style clean)
  card: "bg-white border border-gray-200 rounded-lg overflow-hidden",
  cardHeader: "px-4 py-3 border-b border-gray-100 flex items-center justify-between",
  cardTitle: "text-sm font-semibold text-gray-900",
  cardBadge: "text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-600",
  cardBody: "px-4 py-4",
  cardFooter: "px-4 py-3 bg-gray-50 border-t border-gray-100",
  
  // Insight List
  insightList: "space-y-0",
  insightItem: "flex items-start gap-3 py-3 border-b border-gray-100",
  insightItemLast: "flex items-start gap-3 py-3",
  insightNumber: "w-5 h-5 rounded-full bg-gray-900 text-white flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5",
  insightContent: "flex-1",
  insightTitle: "text-sm font-medium text-gray-900 mb-1",
  insightText: "text-sm text-gray-600 leading-relaxed",
  insightSource: "text-xs text-gray-400 mt-1 flex items-center gap-1",
  
  // Competitor Grid
  compGrid: "grid grid-cols-3 gap-3",
  compCard: "bg-gray-50 rounded-lg p-3 border border-gray-100",
  compName: "font-semibold text-sm text-gray-900 mb-2",
  compMeta: "space-y-1.5",
  compRow: "flex items-center justify-between text-xs",
  compLabel: "text-gray-500",
  compValue: "text-gray-900 font-medium",
  compBar: "w-full h-1 bg-gray-200 rounded-full mt-1",
  compBarFill: "h-1 bg-gray-900 rounded-full",
  compTags: "flex flex-wrap gap-1 mt-2",
  compTag: "text-xs px-1.5 py-0.5 rounded bg-white border border-gray-200",
  compTagGreen: "text-xs px-1.5 py-0.5 rounded bg-green-50 text-green-700 border border-green-200",
  compTagRed: "text-xs px-1.5 py-0.5 rounded bg-red-50 text-red-700 border border-red-200",
  
  // Audience
  audienceGrid: "grid grid-cols-2 gap-3",
  audienceCard: "bg-white border border-gray-200 rounded-lg p-4",
  audienceHeader: "flex items-center gap-2 mb-3",
  audienceIcon: "w-8 h-8 bg-gray-100 rounded-lg flex items-center justify-center",
  audienceName: "font-semibold text-sm text-gray-900",
  audienceSubtitle: "text-xs text-gray-500",
  audienceStats: "grid grid-cols-2 gap-2 mb-3",
  audienceStat: "bg-gray-50 rounded-md p-2",
  audienceStatValue: "text-lg font-bold text-gray-900",
  audienceStatLabel: "text-xs text-gray-500",
  audienceTags: "flex flex-wrap gap-1",
  audienceTag: "text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-600",
  
  // Sources
  sourceList: "space-y-1",
  sourceItem: "flex items-center gap-3 p-2 hover:bg-gray-50 rounded-md transition-colors",
  sourceFavicon: "w-5 h-5 bg-gray-200 rounded flex items-center justify-center text-xs flex-shrink-0",
  sourceInfo: "flex-1 min-w-0",
  sourceTitle: "text-sm text-gray-900 truncate",
  sourceUrl: "text-xs text-gray-400 truncate",
  sourceType: "text-xs px-1.5 py-0.5 rounded bg-gray-100 text-gray-500 flex-shrink-0",
  
  // Recent Jobs (Notion database style)
  jobsList: "space-y-1",
  jobItem: "flex items-center gap-3 p-2 hover:bg-gray-50 rounded-md cursor-pointer transition-colors",
  jobIcon: "w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0",
  jobInfo: "flex-1 min-w-0",
  jobTitle: "text-sm font-medium text-gray-900 truncate",
  jobMeta: "text-xs text-gray-500 flex items-center gap-2",
  jobStatus: "text-xs px-2 py-0.5 rounded-full flex-shrink-0",
  jobStatusDone: "bg-green-100 text-green-700",
  jobStatusRunning: "bg-blue-100 text-blue-700",
  
  // Action Bar
  actionBar: "fixed bottom-0 left-60 right-0 bg-white border-t border-gray-200 px-6 py-3 flex items-center justify-between",
  actionBarInfo: "text-sm text-gray-600",
  actionBarActions: "flex items-center gap-2",
  
  // Buttons
  btn: "px-3 py-1.5 rounded-md text-xs font-medium transition-colors",
  btnPrimary: "bg-gray-900 text-white hover:bg-gray-800",
  btnSecondary: "bg-white border border-gray-200 text-gray-700 hover:bg-gray-50",
  btnGhost: "text-gray-500 hover:text-gray-900",
  
  // Tabs
  tabs: "flex items-center gap-1 border-b border-gray-200 mb-6",
  tab: "px-3 py-2 text-sm font-medium border-b-2 transition-colors",
  tabActive: "border-gray-900 text-gray-900",
  tabInactive: "border-transparent text-gray-500 hover:text-gray-700",
  
  // Empty State
  empty: "text-center py-16",
  emptyIcon: "text-4xl text-gray-300 mb-3",
  emptyTitle: "text-sm font-medium text-gray-900 mb-1",
  emptyDesc: "text-xs text-gray-400",
  
  // Loading
  loading: "flex items-center justify-center py-12 gap-2 text-xs text-gray-500",
  spinner: "w-4 h-4 animate-spin text-blue-500",
  
  // Modal
  modalOverlay: "fixed inset-0 bg-black/40 z-50 flex items-center justify-center",
  modal: "bg-white rounded-lg shadow-xl max-h-[90vh] overflow-hidden flex flex-col w-[600px]",
  modalHeader: "px-4 py-3 border-b border-gray-200 flex items-center justify-between",
  modalTitle: "text-sm font-semibold text-gray-900",
  modalBody: "flex-1 overflow-y-auto p-4",
  modalFooter: "px-4 py-3 border-t border-gray-200 flex items-center justify-end gap-2",
  modalClose: "w-6 h-6 rounded hover:bg-gray-100 flex items-center justify-center",
  
  // Form
  formGroup: "space-y-1.5",
  formLabel: "text-xs font-medium text-gray-700",
  formInput: "w-full px-3 py-2 bg-white border border-gray-200 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500",
  formTextarea: "w-full px-3 py-2 bg-white border border-gray-200 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none",
  
  // Slider
  slider: "w-full h-1.5 bg-gray-200 rounded-full appearance-none cursor-pointer",
  
  // Tags
  tagList: "flex flex-wrap gap-1",
  tag: "text-xs px-2 py-0.5 rounded-md bg-gray-100 text-gray-700 flex items-center gap-1",
  tagRemove: "w-3 h-3 rounded-full hover:bg-gray-200 flex items-center justify-center",
  tagInput: "h-7 text-xs bg-white",
} as const

export const RESEARCH_TYPES = {
  competitor: { label: "Phân tích đối thủ", icon: "fa-users", color: "blue" },
  audience: { label: "Nghiên cứu khách hàng", icon: "fa-user-friends", color: "purple" },
  market: { label: "Xu hướng thị trường", icon: "fa-chart-line", color: "green" },
  product: { label: "Nghiên cứu sản phẩm", icon: "fa-box", color: "orange" },
  positioning: { label: "Định vị thương hiệu", icon: "fa-bullseye", color: "red" },
} as const

export const STATUS_MAP = {
  completed: { label: "Hoàn thành", class: "bg-green-100 text-green-700" },
  pending: { label: "Đang chạy", class: "bg-blue-100 text-blue-700" },
  failed: { label: "Thất bại", class: "bg-red-100 text-red-700" },
} as const