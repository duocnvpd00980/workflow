import React, { useState } from 'react';
import { createFileRoute } from '@tanstack/react-router';


export const Route = createFileRoute('/templates')({
  component: PageTemplates,
});

function PageTemplates() {
  const [filter, setFilter] = useState("Tất cả");
  const categories = ["Tất cả", "Social", "Blog", "Ads", "Campaign"];
  
  const templates = [
    { title: "Facebook Caption", desc: "Tạo caption hấp dẫn cho bài đăng Facebook kèm hashtag tự động.", type: "Social", time: "~ 30s" },
    { title: "SEO Blog Post", desc: "Bài viết cấu trúc SEO gồm các bước Research, Outline và sinh nội dung bài viết.", type: "Blog", time: "~ 2-3 phút" },
    { title: "Product Launch Campaign", desc: "Chiến dịch ra mắt sản phẩm đồng bộ đa kênh (Social, Ads, Landing Page).", type: "Campaign", time: "~ 5 phút" },
  ];

  return (
    <div className="flex">
      <div className="space-y-4 animate-fadeIn">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-bold text-slate-900">Templates hệ thống</h2>
            <p className="text-xs text-slate-500 mt-0.5">Chọn template mẫu phù hợp với kế hoạch marketing của bạn.</p>
          </div>
          <input type="text" placeholder="Tìm kiếm template..." className="text-xs bg-white border px-3 py-1.5 rounded-lg outline-none focus:border-indigo-500 w-full sm:w-64" />
        </div>

        <div className="flex flex-wrap gap-1 bg-slate-200/60 p-1 rounded-lg w-fit text-[11px] font-semibold">
          {categories.map((cat) => (
            <button key={cat} onClick={() => setFilter(cat)} className={`px-3 py-1 rounded-md transition-all ${filter === cat ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-900"}`}>
              {cat}
            </button>
          ))}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {templates.filter(t => filter === "Tất cả" || t.type === filter).map((t, i) => (
            <div key={i} className="bg-white p-5 rounded-xl border border-slate-200 flex flex-col justify-between shadow-sm group hover:border-indigo-500 transition-all">
              <div className="space-y-2">
                <div className="flex justify-between items-center text-[10px]">
                  <span className="bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded font-bold">{t.type}</span>
                  <span className="text-slate-400 font-mono">{t.time}</span>
                </div>
                <h3 className="text-xs font-bold text-slate-900 group-hover:text-indigo-600 transition-colors">{t.title}</h3>
                <p className="text-[11px] text-slate-500 line-clamp-2 leading-relaxed">{t.desc}</p>
              </div>
              <button className="text-[11px] mt-4 bg-slate-50 hover:bg-indigo-600 hover:text-white px-3 py-1.5 rounded-md font-bold transition-all w-full text-center">
                Khai triển quy trình
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}