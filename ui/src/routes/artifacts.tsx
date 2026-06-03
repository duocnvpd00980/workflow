
"use client";
import { createFileRoute } from '@tanstack/react-router'
import { 
MenuIcon, MessageSquarePlus,Search, Filter, FileText, Image, FileSpreadsheet, Code,
  Download,Copy, Share2, Trash2, Calendar, HardDrive
} from "lucide-react";
import { useState, useMemo } from "react";

import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import SidebarNav from '@/layout/navbar';

// ─── Mock Data danh sách sản phẩm được tạo ra từ Agent ──────────────────────
const MOCK_ARTIFACTS = [
  {
    id: "ART-0092",
    name: "Kịch_bản_Video_Tiktok_Tháng_6.md",
    type: "document",
    extension: "Markdown",
    size: "14.2 KB",
    createdAt: "2026-06-02T14:30:00Z",
    generatedBy: "Writer Agent",
    jobRef: "JOB-9921-A",
    previewContent: "# KỊCH BẢN VIDEO TIKTOK - XU HƯỚNG AI 2026\n\n## Hook (3 giây đầu):\n\"Bạn có biết 90% Marketer sẽ mất việc nếu không biết công cụ này?\"\n\n## Body:\n- Bước 1: Giới thiệu Agent Command Dashboard...\n- Bước 2: Hướng dẫn cấu hình Sub-Agent...",
  },
  {
    id: "ART-0085",
    name: "Banner_Quang_Cao_SaaS_Creative.png",
    type: "image",
    extension: "PNG Image",
    size: "2.4 MB",
    createdAt: "2026-06-02T11:15:00Z",
    generatedBy: "Designer Agent",
    jobRef: "JOB-9855-C",
    previewUrl: "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=500&auto=format&fit=crop&q=60", // Ảnh trừu tượng dạng UI/Tech
  },
  {
    id: "ART-0071",
    name: "Bao_Cao_Phan_Tich_Doi_Thu_Ecommerce.xlsx",
    type: "spreadsheet",
    extension: "Excel",
    size: "128 KB",
    createdAt: "2026-06-01T23:12:00Z",
    generatedBy: "Research Agent",
    jobRef: "JOB-9701-F",
    previewContent: "[Bảng dữ liệu: 4 cột x 150 dòng]\n- Cột A: Tên đối thủ\n- Cột B: Lưu lượng truy cập (Traffic)\n- Cột C: Công nghệ LLM đang sử dụng\n- Cột D: Điểm yếu bảo mật hệ thống...",
  },
  {
    id: "ART-0060",
    name: "deploy_sandbox_agent_webhook.py",
    type: "code",
    extension: "Python",
    size: "5.8 KB",
    createdAt: "2026-05-31T10:05:00Z",
    generatedBy: "Coder Agent",
    jobRef: "JOB-9511-X",
    previewContent: "import os\nimport requests\n\ndef trigger_agent_webhook(payload):\n    url = os.getenv('AGENT_API_URL')\n    headers = {'Authorization': 'Bearer ' + os.getenv('API_KEY')}\n    response = requests.post(url, json=payload, headers=headers)\n    return response.json()",
  }
];




export const Route = createFileRoute('/artifacts')({
  component: ArtifactsPage,
})



export default function ArtifactsPage() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");
  const [selectedId, setSelectedId] = useState("ART-0092");


  // Tìm sản phẩm đang chọn để hiển thị Preview ở cột phải
  const selectedArtifact = useMemo(() => {
    return MOCK_ARTIFACTS.find(art => art.id === selectedId) || MOCK_ARTIFACTS[0];
  }, [selectedId]);

  // Bộ lọc tìm kiếm & loại tệp tin
  const filteredArtifacts = useMemo(() => {
    return MOCK_ARTIFACTS.filter(art => {
      const matchesSearch = art.name.toLowerCase().includes(searchTerm.toLowerCase()) || art.id.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesType = typeFilter === "all" || art.type === typeFilter;
      return matchesSearch && matchesType;
    });
  }, [searchTerm, typeFilter]);

  // Render Icon đại diện tệp tin chuẩn chỉnh
  const renderFileIcon = (type: string) => {
    switch (type) {
      case "document": return <FileText size={18} className="text-blue-500" />;
      case "image": return <Image size={18} className="text-purple-500" />;
      case "spreadsheet": return <FileSpreadsheet size={18} className="text-emerald-500" />;
      case "code": return <Code size={18} className="text-amber-500" />;
      default: return <FileText size={18} className="text-slate-400" />;
    }
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#fafbfc] text-slate-900 select-none antialiased font-sans">
      
      {/* ─── 1. SIDEBAR TRÁI (Đồng bộ cấu trúc điều hướng hệ thống) ─── */}
      <aside className={`fixed inset-y-0 left-0 z-30 flex w-[260px] flex-col border-r bg-white transition-transform duration-200 md:relative md:translate-x-0 ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}`}>
       

        <SidebarNav />

        <div className="flex-1 overflow-y-auto px-3 py-4 flex flex-col min-h-0">
          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider px-1 mb-2">Dung lượng kho</p>
          <div className="p-3 border border-slate-100 rounded-xl bg-slate-50/50 space-y-1.5">
            <div className="flex justify-between text-[11px] font-semibold text-slate-600">
              <span>Cloud Storage</span>
              <span>12.4 MB / 100 MB</span>
            </div>
            <progress value={12.4} max={100} className="w-full h-1 bg-slate-100 accent-indigo-600 rounded-full" />
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

      {/* ─── 2. MAIN CENTER (Danh sách lưới các sản phẩm / File Grid Manager) ─── */}
      <main className="flex-1 flex flex-col min-w-0 bg-slate-50/60 overflow-hidden relative">
        {/* Header chính */}
        <header className="h-14 bg-white border-b flex items-center justify-between px-6 shrink-0 z-10 shadow-xs">
          <div className="flex items-center gap-3 min-w-0">
            <button onClick={() => setSidebarOpen(true)} className="p-1.5 -ml-1.5 hover:bg-slate-100 rounded-md text-slate-500 md:hidden shrink-0">
              <MenuIcon size={18} />
            </button>
            <h2 className="font-bold text-[15px] text-slate-800">Kho sản phẩm của Agent</h2>
            <div className="h-4 w-px bg-slate-200" />
            <span className="text-[11px] text-slate-500 font-medium hidden sm:inline">{MOCK_ARTIFACTS.length} tài nguyên đã bàn giao</span>
          </div>
        </header>

        {/* Thanh lọc nâng cao (Search & Category filter) */}
        <div className="bg-white border-b p-4 flex flex-col sm:flex-row gap-3 items-center justify-between shrink-0">
          <div className="relative w-full sm:w-64">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <input
              type="text"
              placeholder="Tìm tên file hoặc mã tài sản..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-4 py-1.5 text-[13px] bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
            />
          </div>

          <div className="flex items-center gap-1 overflow-x-auto w-full sm:w-auto">
            <Filter size={13} className="text-slate-400 mr-1 shrink-0 hidden md:inline" />
            {[
              { id: "all", label: "Tất cả" },
              { id: "document", label: "Văn bản (.md, .txt)" },
              { id: "image", label: "Hình ảnh (.png)" },
              { id: "spreadsheet", label: "Bảng tính (.xlsx)" },
              { id: "code", label: "Mã nguồn (.py, .js)" },
            ].map((t) => (
              <button
                key={t.id}
                onClick={() => setTypeFilter(t.id)}
                className={`px-3 py-1.5 text-[11.5px] font-bold rounded-lg transition-colors whitespace-nowrap ${typeFilter === t.id ? "bg-indigo-600 text-white shadow-xs" : "text-slate-600 hover:bg-slate-100"}`}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>

        {/* Vùng hiển thị danh sách dạng bảng tối giản (List View Grid) */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="max-w-[840px] mx-auto bg-white border rounded-2xl overflow-hidden shadow-xs">
            <table className="w-full border-collapse text-left text-[13px]">
              <thead>
                <tr className="bg-slate-50/70 border-b text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                  <th className="p-3.5 pl-5">Tên sản phẩm đầu ra</th>
                  <th className="p-3.5">Được tạo bởi</th>
                  <th className="p-3.5 text-right">Kích thước</th>
                  <th className="p-3.5 pr-5 text-right">Hành động</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-medium text-slate-700">
                {filteredArtifacts.map((art) => (
                  <tr 
                    key={art.id} 
                    onClick={() => setSelectedId(art.id)}
                    className={`hover:bg-slate-50/80 cursor-pointer transition-colors ${selectedId === art.id ? "bg-indigo-50/40" : ""}`}
                  >
                    <td className="p-3.5 pl-5">
                      <div className="flex items-center gap-3 min-w-0">
                        {renderFileIcon(art.type)}
                        <div className="truncate">
                          <p className="font-bold text-slate-800 truncate pr-2">{art.name}</p>
                          <p className="text-[10px] text-slate-400 font-mono">Mã: {art.id} • {art.extension}</p>
                        </div>
                      </div>
                    </td>
                    <td className="p-3.5">
                      <Badge className="bg-slate-100 text-slate-600 hover:bg-slate-100 border-none font-bold text-[10.5px] px-2 py-0.5">{art.generatedBy}</Badge>
                    </td>
                    <td className="p-3.5 text-right font-mono text-[12px] text-slate-500">{art.size}</td>
                    <td className="p-3.5 pr-5 text-right" onClick={(e) => e.stopPropagation()}>
                      <div className="flex items-center justify-end gap-1.5">
                        <button title="Tải xuống trực tiếp" className="p-1.5 hover:bg-slate-200/60 rounded-md text-slate-500 hover:text-slate-700 transition-colors">
                          <Download size={14} />
                        </button>
                        <button title="Xóa tài sản" className="p-1.5 hover:bg-slate-200/60 rounded-md text-slate-400 hover:text-rose-600 transition-colors">
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </main>

      {/* ─── 3. INSPECTOR SIDEBAR PHẢI (Xem trước nội dung trực tiếp / Live File Preview) ─── */}
      <aside className="w-[340px] border-l bg-white hidden xl:flex flex-col shrink-0 overflow-hidden">
        {/* Header thanh bên phải */}
        <div className="h-14 border-b flex items-center justify-between px-4 shrink-0">
          <span className="text-[13px] font-bold text-slate-800">Cửa sổ xem trước (Preview)</span>
          <span className="text-[10px] font-mono font-bold text-slate-400 bg-slate-50 border px-1.5 py-0.5 rounded">{selectedArtifact.id}</span>
        </div>

        {/* Nội dung vùng Preview chi tiết */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 flex flex-col min-h-0">
          
          {/* Khối thông tin Metadata */}
          <div className="space-y-2 bg-slate-50 p-3 border rounded-xl shrink-0 text-[11.5px]">
            <div className="flex items-center gap-1.5 text-slate-400">
              <Calendar size={13}/>
              <span>Khởi tạo ngày: {new Date(selectedArtifact.createdAt).toLocaleDateString("vi-VN")}</span>
            </div>
            <div className="flex items-center gap-1.5 text-slate-400">
              <HardDrive size={13}/>
              <span>Tham chiếu nhiệm vụ: <strong className="text-indigo-600 font-mono font-bold">{selectedArtifact.jobRef}</strong></span>
            </div>
          </div>

          {/* Khối hiển thị nội dung động theo định dạng file */}
          <div className="flex-1 border rounded-xl overflow-hidden bg-slate-50 flex flex-col min-h-[260px] shadow-inner relative">
            
            {/* Trường hợp 1: Nếu là Hình ảnh */}
            {selectedArtifact.type === "image" && selectedArtifact.previewUrl && (
              <div className="w-full h-full flex items-center justify-center p-2 bg-slate-100">
                <img 
                  src={selectedArtifact.previewUrl} 
                  alt={selectedArtifact.name} 
                  className="max-w-full max-h-full object-contain rounded border bg-white shadow-xs"
                />
              </div>
            )}

            {/* Trường hợp 2: Nếu là Văn bản, Code hoặc Excel (Dùng khung mã code đơn giản) */}
            {selectedArtifact.type !== "image" && selectedArtifact.previewContent && (
              <pre className="w-full h-full p-4 font-mono text-[11px] text-slate-700 whitespace-pre-wrap overflow-y-auto leading-relaxed bg-white">
                {selectedArtifact.previewContent}
              </pre>
            )}

          </div>

          {/* Khối nút thao tác nhanh (Quick Action Buttons) ở đáy */}
          <div className="pt-2 border-t mt-auto grid grid-cols-2 gap-2 shrink-0">
            <button 
              onClick={() => {
                navigator.clipboard.writeText(selectedArtifact.previewContent || selectedArtifact.name);
                toast.success("Đã sao chép nội dung vào bộ nhớ tạm!");
              }}
              className="h-9 text-[11.5px] bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded-xl flex items-center justify-center gap-1 transition-colors"
            >
              <Copy size={13}/> Sao chép nội dung
            </button>
            <button className="h-9 text-[11.5px] bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-xl flex items-center justify-center gap-1 shadow-sm transition-all">
              <Share2 size={13}/> Đồng bộ Cloud/Drive
            </button>
          </div>

        </div>
      </aside>

    </div>
  );
}