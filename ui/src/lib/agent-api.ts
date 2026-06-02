export interface AgentStep {
  id: string;
  label: string;
  status: "pending" | "running" | "completed" | "failed";
  progress: number;
}

export interface AgentMission {
  id: string;
  title: string;
  status: "executing" | "paused" | "completed";
  progress: number;
  currentStep: number;
  steps: AgentStep[];
  memoryUsage: string;
  cpuUsage: number;
}

export const mockApi = {
  // Trả về dữ liệu giả lập giống hệt giao diện bạn muốn
  getMissionDetails: (): AgentMission => ({
    id: "AGENT-8829-X",
    title: "Chiến dịch tháng 6",
    status: "executing",
    progress: 60,
    currentStep: 2,
    memoryUsage: "2.4GB / 8GB",
    cpuUsage: 34,
    steps: [
      { id: "1", label: "Research AI trends 2025", status: "completed", progress: 100 },
      { id: "2", label: "Viết blog 1,500 từ", status: "running", progress: 65 },
      { id: "3", label: "Tạo 3 ảnh banner", status: "pending", progress: 0 },
      { id: "4", label: "Tạo 2 bộ ads Facebook", status: "pending", progress: 0 },
      { id: "5", label: "Lên lịch đăng tuần tới", status: "pending", progress: 0 },
    ]
  })
};