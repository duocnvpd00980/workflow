"use client";

import {
  MenuIcon, MessageSquarePlus,
  Save, Sliders, Shield, Key, Cpu, HelpCircle, AlertCircle, Eye, EyeOff,
  CheckCircle2, Info, Plus, Trash2, ToggleLeft, ToggleRight
} from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { createFileRoute } from "@tanstack/react-router";
import SidebarNav from "@/layout/navbar";

// ─── Mock Data cấu hình các Sub-Agents ───────────────────────────────────────
const INITIAL_SUB_AGENTS = [
  { id: "sa-1", name: "Writer Agent", role: "Tạo nội dung & Blog", model: "Claude 4 Sonnet", isActive: true },
  { id: "sa-2", name: "Research Agent", role: "Thu thập & Phân tích web", model: "Gemini 2.0 Flash", isActive: true },
  { id: "sa-3", name: "Designer Agent", role: "Tạo ảnh & Banner", model: "DALL-E 3 (OpenAI)", isActive: false },
];


export const Route = createFileRoute('/settings')({
  component: AgentSettingsPage,
})


export default function AgentSettingsPage() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // ── States cấu hình Agent chính ───────────────────────────────────────────
  const [agentName, setAgentName] = useState("Hệ thống thực thi Marketing tổng lực");
  const [systemPrompt, setSystemPrompt] = useState(
    "Bạn là một AI Lead Agent có khả năng lập kế hoạch nhiều bước. Khi nhận lệnh từ user, hãy chia nhỏ thành các task, phân phối cho các Sub-Agent phù hợp, tự động kiểm tra lỗi trước khi trả kết quả."
  );
  const [temperature, setTemperature] = useState(0.4);
  const [maxTokens, setMaxTokens] = useState(4096);
  const [showApiKey, setShowApiKey] = useState(false);
  const [subAgents, setSubAgents] = useState(INITIAL_SUB_AGENTS);

  const handleSave = () => {
    toast.success("Đã lưu toàn bộ cấu hình Agent thành công!");
  };

  const toggleSubAgent = (id: string) => {
    setSubAgents(prev => prev.map(sa => sa.id === id ? { ...sa, isActive: !sa.isActive } : sa));
    toast.info("Đã cập nhật trạng thái Sub-Agent");
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#fafbfc] text-slate-900 select-none antialiased font-sans">

      {/* ─── 1. SIDEBAR TRÁI (Đồng bộ cấu trúc 100% từ các trang trước) ─── */}
      <aside className={`fixed inset-y-0 left-0 z-30 flex w-[260px] flex-col border-r bg-white transition-transform duration-200 md:relative md:translate-x-0 ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}`}>

        <SidebarNav />

        <div className="flex-1 overflow-y-auto px-3 py-4 flex flex-col min-h-0">
          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider px-1 mb-2">Trạng thái cấu hình</p>
          <div className="p-3 border border-emerald-100 rounded-xl bg-emerald-50/20 text-emerald-800 text-[11px] font-medium flex gap-2 items-start">
            <CheckCircle2 size={14} className="text-emerald-600 mt-0.5 shrink-0" />
            <span>Agent đang ở trạng thái tối ưu, sẵn sàng nhận lệnh.</span>
          </div>
        </div>

        <div className="border-t p-3 shrink-0 flex items-center justify-between bg-slate-50/50">
          <div className="flex items-center gap-2 min-w-0">
            <div className="flex h-7 w-7 items-center justify-center rounded-full bg-indigo-100 text-indigo-700 text-[11px] font-bold shrink-0">TH</div>
            <span className="text-[13px] font-medium text-slate-700 truncate">Thành</span>
          </div>
          <button title="Tạo Session mới" className="p-1.5 hover:bg-slate-200/60 text-slate-400 hover:text-slate-600 rounded-md transition-colors">
            <MessageSquarePlus size={16} />
          </button>
        </div>
      </aside>

      {/* ─── 2. MAIN CENTER (Form Tinh Chỉnh Cấu Hình & Prompt Hệ Thống) ─── */}
      <main className="flex-1 flex flex-col min-w-0 bg-slate-50/60 overflow-hidden relative">
        {/* Header chính */}
        <header className="h-14 bg-white border-b flex items-center justify-between px-6 shrink-0 z-10 shadow-xs">
          <div className="flex items-center gap-3 min-w-0">
            <button onClick={() => setSidebarOpen(true)} className="p-1.5 -ml-1.5 hover:bg-slate-100 rounded-md text-slate-500 md:hidden shrink-0">
              <MenuIcon size={18} />
            </button>
            <h2 className="font-bold text-[15px] text-slate-800">Cấu hình thực thi Agent</h2>
            <div className="h-4 w-px bg-slate-200" />
            <span className="text-[11px] text-slate-500 font-medium hidden sm:inline">Tinh chỉnh tham số lõi & phân quyền</span>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button onClick={handleSave} className="h-8 px-3 text-[11px] bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-bold flex items-center gap-1.5 shadow-md transition-all">
              <Save size={13} /> Lưu cấu hình
            </button>
          </div>
        </header>

        {/* Khung Workspace điền thông số */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          <div className="max-w-[760px] mx-auto space-y-6">

            {/* Khối 1: Cấu hình cơ bản (General Settings) */}
            <div className="bg-white border border-slate-100 rounded-2xl p-5 shadow-xs space-y-4">
              <div className="flex items-center gap-2 border-b pb-3">
                <Sliders size={16} className="text-indigo-600" />
                <h3 className="text-[13.5px] font-bold text-slate-800">Cấu hình lõi (Core Parameters)</h3>
              </div>

              <div className="space-y-4">
                {/* Tên Agent */}
                <div className="space-y-1.5">
                  <label className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Tên định danh Agent</label>
                  <input
                    type="text"
                    value={agentName}
                    onChange={(e) => setAgentName(e.target.value)}
                    className="w-full px-3 py-2 text-[13px] border border-slate-200 rounded-xl bg-slate-50/50 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 font-medium text-slate-800"
                  />
                </div>

                {/* System Prompt chuyên sâu */}
                <div className="space-y-1.5">
                  <div className="flex justify-between items-center">
                    <label className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">System Prompt (Chỉ thị tối cao)</label>
                    <span className="text-[10px] text-slate-400 font-medium">Bắt buộc đối với Lead Agent</span>
                  </div>
                  <textarea
                    value={systemPrompt}
                    onChange={(e) => setSystemPrompt(e.target.value)}
                    rows={4}
                    className="w-full px-3 py-2 text-[13px] border border-slate-200 rounded-xl bg-slate-50/50 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 font-mono text-slate-700 leading-relaxed"
                  />
                </div>
              </div>
            </div>

            {/* Khối 2: Quản lý cụm mạng lưới Sub-Agents (Giống layout quản lý mô-đun) */}
            <div className="bg-white border border-slate-100 rounded-2xl p-5 shadow-xs space-y-4">
              <div className="flex justify-between items-center border-b pb-3">
                <div className="flex items-center gap-2">
                  <Cpu size={16} className="text-indigo-600" />
                  <h3 className="text-[13.5px] font-bold text-slate-800">Mạng lưới Sub-Agents kích hoạt</h3>
                </div>
                <button className="text-[11px] font-bold text-indigo-600 flex items-center gap-0.5 hover:underline">
                  <Plus size={12} /> Thêm Sub-Agent
                </button>
              </div>

              {/* Danh sách các sub-agent */}
              <div className="space-y-2">
                {subAgents.map((sa) => (
                  <div key={sa.id} className={`p-3.5 border rounded-xl flex items-center justify-between transition-all ${sa.isActive ? "border-slate-100 bg-white" : "border-slate-100 bg-slate-50/50 opacity-60"}`}>
                    <div className="min-w-0 space-y-0.5">
                      <div className="flex items-center gap-2">
                        <p className="font-bold text-[13px] text-slate-800">{sa.name}</p>
                        <Badge variant="secondary" className="bg-slate-100 text-slate-500 font-mono text-[9px] px-1.5 py-0 border-none">{sa.model}</Badge>
                      </div>
                      <p className="text-[11px] text-slate-400 font-medium">{sa.role}</p>
                    </div>

                    <div className="flex items-center gap-3 shrink-0">
                      <button onClick={() => toggleSubAgent(sa.id)} className="text-slate-400 hover:text-slate-600 transition-colors">
                        {sa.isActive ? <ToggleRight size={24} className="text-indigo-600" /> : <ToggleLeft size={24} />}
                      </button>
                      <button className="p-1 hover:bg-slate-100 text-slate-400 hover:text-rose-600 rounded-md transition-colors">
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Khối 3: Bảo mật & Kết nối API Credential */}
            <div className="bg-white border border-slate-100 rounded-2xl p-5 shadow-xs space-y-4">
              <div className="flex items-center gap-2 border-b pb-3">
                <Key size={16} className="text-indigo-600" />
                <h3 className="text-[13.5px] font-bold text-slate-800">API Key & Xác thực bảo mật</h3>
              </div>

              <div className="space-y-3">
                <div className="space-y-1.5">
                  <label className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Anthropic API Key (Claude)</label>
                  <div className="relative">
                    <input
                      type={showApiKey ? "text" : "password"}
                      value="sk-ant-prd-01293810293123-X9A21"
                      disabled
                      className="w-full pl-3 pr-10 py-2 text-[12px] font-mono border border-slate-200 rounded-xl bg-slate-50 text-slate-500 cursor-not-allowed"
                    />
                    <button onClick={() => setShowApiKey(!showApiKey)} className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-600">
                      {showApiKey ? <EyeOff size={14} /> : <Eye size={14} />}
                    </button>
                  </div>
                </div>
                <p className="text-[10px] text-slate-400 font-medium flex items-start gap-1">
                  <Info size={12} className="text-indigo-500 mt-0.5 shrink-0" />
                  Key được mã hóa bất đối xứng AES-256 trước khi lưu vào cơ sở dữ liệu môi trường Cloud.
                </p>
              </div>
            </div>

          </div>
        </div>
      </main>

      {/* ─── 3. INSPECTOR SIDEBAR PHẢI (Thanh trượt Hyperparameters nâng cao) ─── */}
      <aside className="w-[300px] border-l bg-white hidden xl:flex flex-col shrink-0 overflow-hidden">
        {/* Header */}
        <div className="h-14 border-b flex items-center justify-between px-4 shrink-0">
          <span className="text-[13px] font-bold text-slate-800">Tham số Hyperparameter</span>
          <Shield size={14} className="text-slate-400" />
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-6 flex flex-col min-h-0">

          {/* Slider 1: Temperature */}
          <div className="space-y-2.5 shrink-0">
            <div className="flex justify-between items-center text-[11px]">
              <span className="font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1">
                Temperature
                <HelpCircle size={12} className="text-slate-300 cursor-help" />
              </span>
              <span className="font-mono font-bold text-indigo-600 bg-indigo-50 px-1.5 py-0.2 rounded text-[12px]">{temperature}</span>
            </div>
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={temperature}
              onChange={(e) => setTemperature(parseFloat(e.target.value))}
              className="w-full accent-indigo-600 h-1 bg-slate-100 rounded-lg cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-400 font-medium">
              <span>Chính xác (0.0)</span>
              <span>Sáng tạo (1.0)</span>
            </div>
          </div>

          {/* Slider 2: Max Tokens */}
          <div className="space-y-2.5 shrink-0">
            <div className="flex justify-between items-center text-[11px]">
              <span className="font-bold text-slate-500 uppercase tracking-wider">Max Output Length</span>
              <span className="font-mono font-bold text-slate-700 text-[11px]">{maxTokens} tokens</span>
            </div>
            <input
              type="range"
              min="1024"
              max="16384"
              step="1024"
              value={maxTokens}
              onChange={(e) => setMaxTokens(parseInt(e.target.value))}
              className="w-full accent-indigo-600 h-1 bg-slate-100 rounded-lg cursor-pointer"
            />
            <p className="text-[10px] text-slate-400 font-medium">Giới hạn token tối đa cho mỗi lượt phản hồi của Agent để tránh tràn chi phí.</p>
          </div>

          {/* Khối Cảnh báo tài nguyên (Resource Alert Block) */}
          <div className="bg-rose-50/40 border border-rose-100 rounded-xl p-3.5 space-y-2.5 mt-auto shrink-0">
            <div className="flex items-center gap-1 text-rose-800 font-bold text-[11.5px]">
              <AlertCircle size={14} className="text-rose-500 shrink-0" />
              <span>Chế độ kiểm duyệt an toàn</span>
            </div>
            <p className="text-[11px] text-slate-500 leading-relaxed font-medium">
              Khi bật, hệ thống tự động kiểm tra mã nguồn độc hại, từ chối thực thi các lệnh terminal gây nguy hiểm cho cụm máy chủ gốc.
            </p>
            <div className="pt-1.5 border-t border-rose-200/50 flex justify-between items-center">
              <span className="text-[11px] font-bold text-rose-700">Chế độ Sandbox:</span>
              <Badge className="bg-rose-600 text-white border-none font-bold text-[9px] px-1.5 py-0">BẮT BUỘC</Badge>
            </div>
          </div>

        </div>
      </aside>

    </div>
  );
}