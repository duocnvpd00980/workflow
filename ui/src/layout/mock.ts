export const mockBrands = [
  { id: "1", name: "Acme Corp", active: true },
  { id: "2", name: "StartupX", active: false },
  { id: "3", name: "Brand C", active: false },
];

export const mockRunningTasks = [
  { id: "t1", label: 'Gen blog "AI Trends"', percent: 45, etaMin: 2 },
  { id: "t2", label: "Research thị trường VN", percent: 12, etaMin: 5 },
];

export const mockDoneTasks = [
  { id: "t3", label: 'Gen email "Promo T6"', ago: "2 phút" },
  { id: "t4", label: "Research đối thủ A", ago: "1 giờ" },
  { id: "t5", label: "Gen social post T6", ago: "3 giờ" },
];

export const mockNotifications = [
  { id: "n1", text: 'Brand "StartupX" đã được tạo', read: false, ago: "5p" },
  { id: "n2", text: 'Task "Gen blog" hoàn thành', read: false, ago: "2h" },
  { id: "n3", text: "Upload RAG thành công (3 files)", read: true, ago: "1 ngày" },
];

export const recentSearches = [
  "AI Trends",
  "Blog post tháng 6",
  "Brand: StartupX",
];

export const mockSearchResults = {
  content: [
    { id: "c1", label: "Blog: AI Trends 2024" },
    { id: "c2", label: "Email: Promo T6" },
  ],
  brands: [{ id: "b1", label: "StartupX" }],
  rag: [{ id: "r1", label: "Brand Guidelines" }],
  tasks: [{ id: "t1", label: 'Gen blog "AI Trends" (đang chạy)' }],
};