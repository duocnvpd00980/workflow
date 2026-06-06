"use client";

import { createFileRoute } from '@tanstack/react-router';
import { 
  Search,
  Filter,
  FileText,
  Image as ImageIcon,
  FileSpreadsheet,
  Code,
  Download,
  Copy,
  Share2,
  Calendar,
  HardDrive,
  ChevronRight
} from "lucide-react";
import { useState, useMemo } from "react";
import { Badge } from "@/components/ui/badge";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

// ─────────────────────────────────────────────
// MOCK DATA SẢN PHẨM ĐẦU RA (ARTIFACTS)
// ─────────────────────────────────────────────
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
    previewUrl: "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=500&auto=format&fit=crop&q=60",
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
});

export default function ArtifactsPage() {
  const [searchTerm, setSearchTerm] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");

  // Bộ lọc tìm kiếm & loại tệp tin
  const filteredArtifacts = useMemo(() => {
    return MOCK_ARTIFACTS.filter(art => {
      const matchesSearch = art.name.toLowerCase().includes(searchTerm.toLowerCase()) || art.id.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesType = typeFilter === "all" || art.type === typeFilter;
      return matchesSearch && matchesType;
    });
  }, [searchTerm, typeFilter]);

  // Hệ thống icon tinh gọn cho bảng dữ liệu chính
  const renderFileIcon = (type: string) => {
    switch (type) {
      case "document": return <FileText size={16} className="text-blue-500" />;
      case "image": return <ImageIcon size={16} className="text-purple-500" />;
      case "spreadsheet": return <FileSpreadsheet size={16} className="text-emerald-500" />;
      case "code": return <Code size={16} className="text-amber-500" />;
      default: return <FileText size={16} className="text-muted-foreground" />;
    }
  };

  return (
    <div className="space-y-4 max-w-[1000px] mx-auto w-full">
      
      {/* ─── THANH CÔNG CỤ: TÌM KIẾM & BỘ LỌC TÁC VỤ ─── */}
      <div className="bg-background border rounded-xl p-4 flex flex-col md:flex-row gap-3 items-center justify-between">
        <div className="relative w-full md:w-64">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Tìm tên file hoặc mã tài sản..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-4 py-1.5 text-xs bg-muted/50 border rounded-lg focus:outline-none focus:ring-2 focus:ring-ring transition-all"
          />
        </div>

        <div className="flex items-center gap-1 overflow-x-auto w-full md:w-auto pb-1 md:pb-0">
          <Filter size={13} className="text-muted-foreground mr-1.5 shrink-0 hidden lg:inline" />
          {[
            { id: "all", label: "Tất cả" },
            { id: "document", label: "Văn bản (.md)" },
            { id: "image", label: "Hình ảnh (.png)" },
            { id: "spreadsheet", label: "Bảng tính (.xlsx)" },
            { id: "code", label: "Mã nguồn (.py)" },
          ].map((t) => (
            <button
              key={t.id}
              onClick={() => setTypeFilter(t.id)}
              className={cn(
                "px-3 py-1.5 text-[11px] font-semibold rounded-lg whitespace-nowrap transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring",
                typeFilter === t.id 
                  ? "bg-foreground text-background shadow-sm" 
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* ─── BẢNG QUẢN LÝ TÀI NGUYÊN ĐẦU RA ─── */}
      <div className="border bg-background rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left text-xs">
            <thead>
              <tr className="bg-muted/40 border-b text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
                <th className="p-3 pl-4">Tên sản phẩm đầu ra</th>
                <th className="p-3">Được tạo bởi</th>
                <th className="p-3 text-right">Kích thước</th>
                <th className="p-3 pr-4 text-center w-12">Xem</th>
              </tr>
            </thead>
            <tbody className="divide-y text-muted-foreground font-medium">
              {filteredArtifacts.map((art) => (
                <Sheet key={art.id}>
                  {/* Bọc toàn bộ hàng (Row) bằng Trigger giúp mở xem nhanh từ bất cứ đâu */}
                  <SheetTrigger asChild>
                    <tr className="hover:bg-muted/40 cursor-pointer transition-colors group">
                      <td className="p-3 pl-4">
                        <div className="flex items-center gap-3 min-w-0">
                          {renderFileIcon(art.type)}
                          <div className="min-w-0 truncate">
                            <p className="font-semibold text-foreground group-hover:text-primary transition-colors truncate pr-2 text-sm">{art.name}</p>
                            <p className="text-[10px] text-muted-foreground font-mono">Mã: {art.id} • {art.extension}</p>
                          </div>
                        </div>
                      </td>
                      <td className="p-3">
                        <Badge variant="secondary" className="bg-muted text-muted-foreground font-semibold text-[10px] px-2 py-0">
                          {art.generatedBy}
                        </Badge>
                      </td>
                      <td className="p-3 text-right font-mono text-muted-foreground">{art.size}</td>
                      <td className="p-3 pr-4 text-center">
                        <div className="flex justify-center items-center">
                          <ChevronRight size={15} className="text-muted-foreground/60 group-hover:text-primary group-hover:translate-x-0.5 transition-all" />
                        </div>
                      </td>
                    </tr>
                  </SheetTrigger>

                  {/* ─── DRAWER XEM TRƯỚC ĐỘC LẬP TỪNG FILE ─── */}
                  <SheetContent className="w-full sm:max-w-[420px] rounded-l-[20px] md:rounded-l-xl p-6 flex flex-col h-full gap-4">
                    <SheetHeader className="border-b pb-3 shrink-0">
                      <div className="flex items-center justify-between w-full pr-6">
                        <span className="text-[10px] font-mono font-bold text-muted-foreground bg-muted border px-1.5 py-0.5 rounded">{art.id}</span>
                        <span className="text-[11px] font-mono text-muted-foreground">{art.size}</span>
                      </div>
                      <SheetTitle className="text-sm font-bold text-foreground tracking-tight line-clamp-2 text-left pt-1">
                        {art.name}
                      </SheetTitle>
                    </SheetHeader>

                    {/* Vùng Metadata và Nội dung tệp tin */}
                    <div className="flex-1 overflow-y-auto space-y-4 min-h-0 flex flex-col">
                      <div className="space-y-1.5 bg-muted/30 p-3 border rounded-xl shrink-0 text-[11px] text-muted-foreground font-medium">
                        <div className="flex items-center gap-1.5">
                          <Calendar size={12}/>
                          <span>Ngày tạo: {new Date(art.createdAt).toLocaleDateString("vi-VN")}</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <HardDrive size={12}/>
                          <span>Tham chiếu nhiệm vụ: <strong className="text-primary font-mono font-bold">{art.jobRef}</strong></span>
                        </div>
                      </div>

                      {/* Khung render nội dung động */}
                      <div className="flex-1 border bg-muted/10 rounded-xl overflow-hidden flex flex-col min-h-[240px] relative">
                        {art.type === "image" && art.previewUrl ? (
                          <div className="w-full h-full flex items-center justify-center p-2 bg-muted/30">
                            <img 
                              src={art.previewUrl} 
                              alt={art.name} 
                              className="max-w-full max-h-full object-contain rounded border bg-background shadow-xs"
                            />
                          </div>
                        ) : (
                          <pre className="w-full h-full p-4 font-mono text-[10.5px] text-foreground bg-background whitespace-pre-wrap overflow-y-auto leading-relaxed shadow-inner">
                            {art.previewContent}
                          </pre>
                        )}
                      </div>
                    </div>

                    {/* Cụm Action điều khiển dưới đáy ngăn kéo */}
                    <div className="pt-3 border-t mt-auto grid grid-cols-3 gap-2 shrink-0">
                      <button 
                        onClick={() => {
                          navigator.clipboard.writeText(art.previewContent || art.name);
                          toast.success("Đã sao chép vào bộ nhớ tạm!");
                        }}
                        className="h-8 text-[11px] bg-muted hover:bg-muted/80 text-foreground font-semibold rounded-lg flex items-center justify-center gap-1 transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      >
                        <Copy size={13}/> Sao chép
                      </button>
                      <a 
                        href={art.previewUrl || "#"} 
                        download={art.name}
                        onClick={(e) => {
                          if(!art.previewUrl) {
                            e.preventDefault();
                            toast.info("Đang tải dữ liệu tệp văn bản...");
                          }
                        }}
                        className="h-8 text-[11px] bg-muted hover:bg-muted/80 text-foreground font-semibold rounded-lg flex items-center justify-center gap-1 transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      >
                        <Download size={13}/> Tải về
                      </a>
                      <button className="h-8 text-[11px] bg-primary hover:bg-primary/90 text-primary-foreground font-semibold rounded-lg flex items-center justify-center gap-1 transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring shadow-xs">
                        <Share2 size={13}/> Cloud
                      </button>
                    </div>
                  </SheetContent>
                </Sheet>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}