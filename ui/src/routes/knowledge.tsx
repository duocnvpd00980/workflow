"use client";

import { MenuIcon, UploadCloud, Globe, Search, Database, FileText, 
  RefreshCw, Trash2, Link2, Plus, AlertCircle,
  ToggleLeft, ToggleRight, ShieldCheck
} from "lucide-react";
import { useState, useMemo } from "react";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { createFileRoute } from "@tanstack/react-router";
import SidebarNav from "@/layout/navbar";

// ─── Mock Data Hệ Thống RAG ─────────────────────────────────────────────────
const MOCK_KNOWLEDGE_SOURCES = [
  { id: "SRC-01", name: "Chính_sách_Bảo_hành_SaaS_2026.pdf", type: "file", status: "indexed", size: "1.2 MB", chunks: 142, updatedBy: "Thành" },
  { id: "SRC-02", name: "https://docs.agentcommand.com/api", type: "web", status: "synced", size: "450 KB", chunks: 89, updatedBy: "System Bot" },
  { id: "SRC-03", name: "Huong_dan_Onboarding_Nhan_vien.docx", type: "file", status: "indexing", size: "4.8 MB", chunks: 0, updatedBy: "Thành" },
  { id: "SRC-04", name: "https://tiki.vn/blog/quy-dinh-vi-pham", type: "web", status: "error", size: "0 KB", chunks: 0, updatedBy: "Research Agent" },
];


export const Route = createFileRoute('/knowledge')({
  component: KnowledgePage,
})


export default function KnowledgePage() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [activeTab, setActiveTab] = useState("all"); // all, file, web
  const [selectedSrcId, setSelectedSrcId] = useState("SRC-01");
  
  // States cho cổng tìm kiếm ngoài (Web Search Integration)
  const [enableGoogleSearch, setEnableGoogleSearch] = useState(true);
  const [enableTavily, setEnableTavily] = useState(false);

  // Lọc nguồn dữ liệu tri thức
  const filteredSources = useMemo(() => {
    return MOCK_KNOWLEDGE_SOURCES.filter(src => {
      const matchesSearch = src.name.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesTab = activeTab === "all" || src.type === activeTab;
      return matchesSearch && matchesTab;
    });
  }, [searchQuery, activeTab]);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#fafbfc] text-slate-900 select-none antialiased font-sans">
      
      {/* ─── 1. SIDEBAR TRÁI (Đồng bộ cấu trúc 100% điều hướng) ─── */}
      <aside className={`fixed inset-y-0 left-0 z-30 flex w-[260px] flex-col border-r bg-white transition-transform duration-200 md:relative md:translate-x-0 ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}`}>
        
        <SidebarNav />

        {/* Trạng thái Vector DB */}
        <div className="flex-1 overflow-y-auto px-3 py-4 flex flex-col min-h-0">
          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider px-1 mb-2">Vector Database</p>
          <div className="p-3 border border-indigo-100 rounded-xl bg-indigo-50/20 shadow-xs space-y-2">
            <div className="flex justify-between items-center text-[11px] font-semibold text-slate-700">
              <span className="flex items-center gap-1"><Database size={12} className="text-indigo-500"/> Pinecone Vector</span>
              <span className="font-mono text-indigo-600">Active</span>
            </div>
            <div className="text-[10px] text-slate-400 space-y-0.5">
              <p>Tổng số Vector Record: 24,105</p>
              <p>Thời gian phản hồi RAG: 12ms</p>
            </div>
          </div>
        </div>

        <div className="border-t p-3 shrink-0 flex items-center justify-between bg-slate-50/50">
          <div className="flex items-center gap-2 min-w-0">
            <div className="flex h-7 w-7 items-center justify-center rounded-full bg-indigo-100 text-indigo-700 text-[11px] font-bold shrink-0">TH</div>
            <span className="text-[13px] font-medium text-slate-700 truncate">Thành</span>
          </div>
        </div>
      </aside>

      {/* ─── 2. MAIN CENTER (Khu vực Nạp dữ liệu & Quản lý Vector hóa) ─── */}
      <main className="flex-1 flex flex-col min-w-0 bg-slate-50/60 overflow-hidden relative">
        <header className="h-14 bg-white border-b flex items-center justify-between px-6 shrink-0 z-10 shadow-xs">
          <div className="flex items-center gap-3 min-w-0">
            <button onClick={() => setSidebarOpen(true)} className="p-1.5 -ml-1.5 hover:bg-slate-100 rounded-md text-slate-500 md:hidden shrink-0"><MenuIcon size={18} /></button>
            <h2 className="font-bold text-[15px] text-slate-800">Quản lý Cơ sở tri thức (RAG)</h2>
            <div className="h-4 w-px bg-slate-200" />
            <span className="text-[11px] text-slate-500 font-medium hidden sm:inline">Dữ liệu nguồn để Agent tra cứu ngữ cảnh</span>
          </div>
        </header>

        {/* Khối Nạp Dữ Liệu Nhanh (Upload & Web Crawl Inputs) */}
        <div className="p-6 pb-0 grid grid-cols-1 md:grid-cols-2 gap-4 shrink-0 max-w-[860px] mx-auto w-full">
          {/* Nạp File (Kéo thả hoặc Click) */}
          <div className="border-2 border-dashed border-slate-200 hover:border-indigo-400 bg-white rounded-2xl p-4 flex flex-col items-center justify-center text-center cursor-pointer transition-colors shadow-xs group">
            <div className="p-2.5 bg-indigo-50 text-indigo-600 rounded-xl group-hover:scale-105 transition-transform"><UploadCloud size={20}/></div>
            <h4 className="text-[12.5px] font-bold text-slate-700 mt-2">Tải tài liệu lên hệ thống</h4>
            <p className="text-[10px] text-slate-400 mt-0.5">Hỗ trợ PDF, DOCX, TXT, JSON lên tới 25MB</p>
          </div>

          {/* Cào URL Website */}
          <div className="border border-slate-100 bg-white rounded-2xl p-4 flex flex-col justify-between shadow-xs">
            <div className="space-y-1">
              <h4 className="text-[12.5px] font-bold text-slate-700 flex items-center gap-1.5"><Globe size={15} className="text-emerald-500"/> Chỉ định Website / API Docs</h4>
              <p className="text-[10px] text-slate-400">Agent sẽ cào toàn bộ bài viết, cấu trúc link để tự học.</p>
            </div>
            <div className="flex gap-2 mt-3">
              <input 
                type="url" 
                placeholder="https://example.com/docs" 
                className="flex-1 px-3 py-1.5 text-[12px] border rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500/20 bg-slate-50/50"
              />
              <button onClick={() => toast.success("Đã thêm URL vào hàng đợi thu thập!")} className="px-3 bg-slate-900 hover:bg-slate-800 text-white text-[11px] font-bold rounded-xl flex items-center gap-1 shrink-0 transition-colors">
                <Plus size={13}/> Thu thập
              </button>
            </div>
          </div>
        </div>

        {/* Thanh tìm kiếm & Tabs chuyển đổi */}
        <div className="p-6 pb-2 flex items-center justify-between gap-4 max-w-[860px] mx-auto w-full shrink-0">
          <div className="relative w-48 sm:w-64">
            <Search className="absolute left-3 top-2 h-3.5 w-3.5 text-slate-400" />
            <input
              type="text"
              placeholder="Tìm nguồn tri thức..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-4 py-1.2 text-[12px] bg-white border border-slate-200 rounded-xl focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>

          <div className="flex bg-white border rounded-xl p-0.5 shadow-xs">
            {Object.entries({ all: "Tất cả", file: "Tài liệu", web: "Trang web" }).map(([k, v]) => (
              <button
                key={k}
                onClick={() => setActiveTab(k)}
                className={`px-2.5 py-1 text-[11px] font-bold rounded-lg transition-colors ${activeTab === k ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-50"}`}
              >
                {v}
              </button>
            ))}
          </div>
        </div>

        {/* Danh sách các tài nguyên RAG hiện có */}
        <div className="flex-1 overflow-y-auto p-6 pt-2">
          <div className="max-w-[860px] mx-auto bg-white border border-slate-100 rounded-2xl overflow-hidden shadow-xs">
            <div className="divide-y divide-slate-100">
              {filteredSources.map((src) => (
                <div 
                  key={src.id}
                  onClick={() => setSelectedSrcId(src.id)}
                  className={`p-3.5 flex items-center justify-between gap-4 cursor-pointer transition-colors hover:bg-slate-50/70 ${selectedSrcId === src.id ? "bg-indigo-50/30" : ""}`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className={`p-2 rounded-xl shrink-0 ${src.type === "file" ? "bg-blue-50 text-blue-600" : "bg-emerald-50 text-emerald-600"}`}>
                      {src.type === "file" ? <FileText size={16}/> : <Link2 size={16}/>}
                    </div>
                    <div className="min-w-0">
                      <p className="text-[12.5px] font-bold text-slate-800 truncate max-w-[320px] sm:max-w-[450px]">{src.name}</p>
                      <p className="text-[10px] text-slate-400 font-medium">Mã: {src.id} • Dung lượng: {src.size} • Nạp bởi: {src.updatedBy}</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-4 shrink-0">
                    {/* Trạng thái Vector hóa */}
                    {src.status === "indexed" && <Badge className="bg-indigo-50 text-indigo-700 hover:bg-indigo-50 border-none font-bold text-[10px] px-2 py-0.5">Đã Vector hóa ({src.chunks} đoạn)</Badge>}
                    {src.status === "synced" && <Badge className="bg-emerald-50 text-emerald-700 hover:bg-emerald-50 border-none font-bold text-[10px] px-2 py-0.5">Đã đồng bộ</Badge>}
                    {src.status === "indexing" && <Badge className="bg-amber-50 text-amber-700 hover:bg-amber-50 border-none font-bold text-[10px] px-2 py-0.5 animate-pulse">Đang phân tách...</Badge>}
                    {src.status === "error" && <Badge className="bg-rose-50 text-rose-700 hover:bg-rose-50 border-none font-bold text-[10px] px-2 py-0.5">Lỗi chặn Crawl</Badge>}

                    <button title="Xóa tri thức này" className="p-1 hover:bg-slate-100 text-slate-400 hover:text-rose-600 rounded-md transition-colors">
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </main>

      {/* ─── 3. INSPECTOR SIDEBAR PHẢI (Cấu hình Cổng Tìm Kiếm Ngoài & Đồng bộ) ─── */}
      <aside className="w-[320px] border-l bg-white hidden xl:flex flex-col shrink-0 overflow-hidden">
        <div className="h-14 border-b flex items-center justify-between px-4 shrink-0">
          <span className="text-[13px] font-bold text-slate-800">Cổng Tìm kiếm ngoài & Chunking</span>
          <RefreshCw size={13} className="text-slate-400 cursor-pointer hover:rotate-45 transition-transform" />
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-6 flex flex-col min-h-0">
          
          {/* Cấu hình Tìm kiếm trực tiếp ra ngoài Internet khi RAG thiếu */}
          <div className="space-y-3 border-b pb-4 shrink-0">
            <p className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">Tích hợp Search Engine từ ngoài</p>
            
            {/* Google Search Toggle */}
            <div className="flex items-center justify-between p-2.5 border rounded-xl bg-slate-50/50">
              <div className="min-w-0">
                <p className="text-[12px] font-bold text-slate-800">Google Search API</p>
                <p className="text-[10px] text-slate-400 font-medium">Bổ sung tin tức thời gian thực</p>
              </div>
              <button onClick={() => setEnableGoogleSearch(!enableGoogleSearch)} className="text-slate-400 transition-colors">
                {enableGoogleSearch ? <ToggleRight size={24} className="text-indigo-600" /> : <ToggleLeft size={24} />}
              </button>
            </div>

            {/* Tavily AI Search Toggle */}
            <div className="flex items-center justify-between p-2.5 border rounded-xl bg-slate-50/50">
              <div className="min-w-0">
                <p className="text-[12px] font-bold text-slate-800">Tavily AI Search</p>
                <p className="text-[10px] text-slate-400 font-medium">Tìm kiếm tối ưu cho LLM Agent</p>
              </div>
              <button onClick={() => setEnableTavily(!enableTavily)} className="text-slate-400 transition-colors">
                {enableTavily ? <ToggleRight size={24} className="text-indigo-600" /> : <ToggleLeft size={24} />}
              </button>
            </div>
          </div>

          {/* Cấu hình tham số Chunking (Cắt nhỏ file) */}
          <div className="space-y-4 shrink-0">
            <p className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">Thông số nhúng Embeddings</p>
            
            <div className="space-y-1.5">
              <div className="flex justify-between text-[11px] text-slate-600">
                <span>Kích thước đoạn (Chunk Size)</span>
                <span className="font-mono font-bold text-slate-800">500 tokens</span>
              </div>
              <Progress value={35} className="h-1 bg-slate-100 [&>div]:bg-indigo-600" />
            </div>

            <div className="p-3 bg-amber-50/40 border border-amber-100 rounded-xl space-y-1.5 text-[11px] text-slate-600 leading-relaxed font-medium">
              <div className="flex items-center gap-1 text-amber-800 font-bold">
                <AlertCircle size={13} className="shrink-0" />
                <span>Mẹo tối ưu RAG</span>
              </div>
              <span>Kích thước 500 tokens phù hợp nhất với tài liệu văn bản quy định pháp lý hoặc tài liệu kỹ thuật dài để đảm bảo Agent không bị mất ngữ cảnh giữa các đoạn liền kề.</span>
            </div>
          </div>

          {/* Tiêu chuẩn bảo mật dữ liệu tri thức */}
          <div className="mt-auto bg-slate-900 text-white rounded-xl p-4 space-y-2.5 shrink-0 shadow-sm">
            <div className="flex items-center gap-1.5 text-[12px] font-bold text-emerald-400">
              <ShieldCheck size={15} />
              <span>Chính sách bảo mật dữ liệu</span>
            </div>
            <p className="text-[10.5px] text-slate-300 leading-relaxed font-medium">
              Tất cả tài liệu bạn đăng tải lên đều được lưu trữ cục bộ/Private Cloud và không được sử dụng để làm dữ liệu training công khai cho OpenAI hay Anthropic.
            </p>
          </div>

        </div>
      </aside>

    </div>
  );
}