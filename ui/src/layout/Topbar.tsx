"use client";

import { useState, useEffect, useCallback } from "react";
import {
    Bell, Zap, Plus, Search, ChevronDown, Menu,
    FileText, Mail, Share2, BookOpen, UserCircle,
    LogOut, Settings, CheckCircle2, X, Clock,
    type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
    DropdownMenu, DropdownMenuContent, DropdownMenuItem,
    DropdownMenuSeparator, DropdownMenuTrigger, DropdownMenuLabel,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";

// ─────────────────────────────────────────────
// MOCK DATA
// ─────────────────────────────────────────────

const mockBrands = [
    { id: "1", name: "Acme Corp", active: true },
    { id: "2", name: "StartupX", active: false },
    { id: "3", name: "Brand C", active: false },
];

const mockRunningTasks = [
    { id: "t1", label: 'Gen blog "AI Trends"', percent: 45, etaMin: 2 },
    { id: "t2", label: "Research thị trường VN", percent: 12, etaMin: 5 },
];

const mockDoneTasks = [
    { id: "t3", label: 'Gen email "Promo T6"', ago: "2 phút" },
    { id: "t4", label: "Research đối thủ A", ago: "1 giờ" },
    { id: "t5", label: "Gen social post T6", ago: "3 giờ" },
];

const mockNotifications = [
    { id: "n1", text: 'Brand "StartupX" đã được tạo', read: false, ago: "5p" },
    { id: "n2", text: 'Task "Gen blog" hoàn thành', read: false, ago: "2h" },
    { id: "n3", text: "Upload RAG thành công (3 files)", read: true, ago: "1 ngày" },
];

const recentSearches = [
    "AI Trends",
    "Blog post tháng 6",
    "Brand: StartupX",
];

const mockSearchResults = {
    content: [
        { id: "c1", label: "Blog: AI Trends 2024" },
        { id: "c2", label: "Email: Promo T6" },
    ],
    brands: [
        { id: "b1", label: "StartupX" },
    ],
    rag: [
        { id: "r1", label: "Brand Guidelines" },
    ],
    tasks: [
        { id: "t1", label: 'Gen blog "AI Trends" (đang chạy)' },
    ],
};

// ─────────────────────────────────────────────
// HELPERS
// ─────────────────────────────────────────────

function Badge({ count }: { count: number }) {
    if (count === 0) return null;
    return (
        <span className="absolute -top-1 -right-1 h-4 min-w-4 px-0.5 flex items-center justify-center rounded-full bg-zinc-900 text-white text-[9px] font-bold leading-none">
            {count}
        </span>
    );
}

function ProgressBar({ percent }: { percent: number }) {
    return (
        <div className="h-1.5 w-full bg-zinc-100 rounded-full overflow-hidden">
            <div
                className="h-full bg-zinc-800 rounded-full transition-all duration-500"
                style={{ width: `${percent}%` }}
            />
        </div>
    );
}

// ─────────────────────────────────────────────
// COMMAND PALETTE
// ─────────────────────────────────────────────

function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
    const [query, setQuery] = useState("");

    // Đóng bằng Escape
    useEffect(() => {
        if (!open) return;
        const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
        document.addEventListener("keydown", handler);
        return () => document.removeEventListener("keydown", handler);
    }, [open, onClose]);

    if (!open) return null;

    const hasQuery = query.trim().length > 0;

    return (
        <div
            className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh] bg-black/30 backdrop-blur-sm"
            onClick={onClose}
        >
            <div
                className="w-full max-w-xl mx-4 bg-white rounded-xl shadow-2xl border border-zinc-200/80 overflow-hidden"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Input */}
                <div className="flex items-center gap-3 px-4 py-3 border-b border-zinc-100">
                    <Search className="h-4 w-4 text-zinc-400 shrink-0" />
                    <input
                        autoFocus
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="Tìm kiếm..."
                        className="flex-1 text-[14px] text-zinc-800 placeholder:text-zinc-400 outline-none bg-transparent"
                    />
                    <button onClick={onClose} className="text-zinc-400 hover:text-zinc-600 transition-colors">
                        <X className="h-4 w-4" />
                    </button>
                </div>

                {/* Results */}
                <div className="max-h-[60vh] overflow-y-auto py-2">
                    {!hasQuery ? (
                        // Recent searches
                        <div className="px-3 pb-2">
                            <p className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider px-2 py-1.5">Gần đây</p>
                            {recentSearches.map((s) => (
                                <button key={s} className="w-full flex items-center gap-2.5 h-9 px-2 rounded-md hover:bg-zinc-50 transition-colors text-left">
                                    <Clock className="h-3.5 w-3.5 text-zinc-400 shrink-0" />
                                    <span className="text-[13px] text-zinc-600">{s}</span>
                                </button>
                            ))}
                        </div>
                    ) : (
                        // Search results by category
                        <div className="px-3 space-y-1">
                            {/* Content */}
                            <p className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider px-2 py-1.5 flex items-center gap-1.5">
                                <FileText className="h-3 w-3" /> Content
                            </p>
                            {mockSearchResults.content.map((r) => (
                                <button key={r.id} className="w-full flex items-center h-9 px-2 rounded-md hover:bg-zinc-50 transition-colors text-left">
                                    <span className="text-[13px] text-zinc-700">{r.label}</span>
                                </button>
                            ))}

                            {/* Brands */}
                            <p className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider px-2 py-1.5 flex items-center gap-1.5 mt-1">
                                🏢 Brands
                            </p>
                            {mockSearchResults.brands.map((r) => (
                                <button key={r.id} className="w-full flex items-center h-9 px-2 rounded-md hover:bg-zinc-50 transition-colors text-left">
                                    <span className="text-[13px] text-zinc-700">{r.label}</span>
                                </button>
                            ))}

                            {/* RAG */}
                            <p className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider px-2 py-1.5 flex items-center gap-1.5 mt-1">
                                <BookOpen className="h-3 w-3" /> RAG
                            </p>
                            {mockSearchResults.rag.map((r) => (
                                <button key={r.id} className="w-full flex items-center h-9 px-2 rounded-md hover:bg-zinc-50 transition-colors text-left">
                                    <span className="text-[13px] text-zinc-700">{r.label}</span>
                                </button>
                            ))}

                            {/* Tasks */}
                            <p className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider px-2 py-1.5 flex items-center gap-1.5 mt-1">
                                <Zap className="h-3 w-3" /> Tasks
                            </p>
                            {mockSearchResults.tasks.map((r) => (
                                <button key={r.id} className="w-full flex items-center h-9 px-2 rounded-md hover:bg-zinc-50 transition-colors text-left">
                                    <span className="text-[13px] text-zinc-700">{r.label}</span>
                                </button>
                            ))}
                        </div>
                    )}
                </div>

                {/* Footer hint */}
                <div className="border-t border-zinc-100 px-4 py-2 flex items-center gap-3">
                    <span className="text-[11px] text-zinc-400">
                        <kbd className="font-mono bg-zinc-100 px-1 rounded text-[10px]">↑↓</kbd> điều hướng
                    </span>
                    <span className="text-[11px] text-zinc-400">
                        <kbd className="font-mono bg-zinc-100 px-1 rounded text-[10px]">↵</kbd> chọn
                    </span>
                    <span className="text-[11px] text-zinc-400">
                        <kbd className="font-mono bg-zinc-100 px-1 rounded text-[10px]">Esc</kbd> đóng
                    </span>
                </div>
            </div>
        </div>
    );
}

// ─────────────────────────────────────────────
// BRAND SWITCHER
// ─────────────────────────────────────────────

function BrandSwitcher() {
    const active = mockBrands.find((b) => b.active) ?? mockBrands[0];
    return (
        <DropdownMenu>
            <DropdownMenuTrigger asChild>
                <button className="flex items-center gap-1.5 h-8 px-2.5 rounded-md border border-zinc-200 bg-white hover:bg-zinc-50 transition-colors text-[12.5px] font-medium text-zinc-700 select-none">
                    <span className="h-4 w-4 rounded-[3px] bg-zinc-900 flex items-center justify-center text-[9px] font-bold text-white shrink-0">
                        {active.name.charAt(0)}
                    </span>
                    <span>{active.name}</span>
                    <ChevronDown className="h-3 w-3 text-zinc-400" />
                </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="w-48 rounded-lg shadow-md border-zinc-200/80 p-1">
                <DropdownMenuLabel className="text-[11px] text-zinc-400 font-semibold uppercase tracking-wider px-2 pb-1">
                    Brands
                </DropdownMenuLabel>
                {mockBrands.map((b) => (
                    <DropdownMenuItem key={b.id} className={cn("flex items-center gap-2 text-[13px] rounded-md cursor-pointer", b.active && "font-semibold")}>
                        <span className={cn("h-1.5 w-1.5 rounded-full shrink-0", b.active ? "bg-zinc-900" : "bg-zinc-300")} />
                        {b.name}
                        {b.active && <CheckCircle2 className="h-3.5 w-3.5 ml-auto text-zinc-500" />}
                    </DropdownMenuItem>
                ))}
                <DropdownMenuSeparator />
                <DropdownMenuItem className="text-[13px] text-zinc-500 rounded-md cursor-pointer">
                    <Plus className="h-3.5 w-3.5 mr-2" /> Thêm brand
                </DropdownMenuItem>
            </DropdownMenuContent>
        </DropdownMenu>
    );
}

// ─────────────────────────────────────────────
// TASK BELL
// ─────────────────────────────────────────────

function TaskBell() {
    return (
        <DropdownMenu>
            <DropdownMenuTrigger asChild>
                <button className="relative h-8 w-8 flex items-center justify-center rounded-md text-zinc-500 hover:bg-zinc-100 transition-colors">
                    <Zap className="h-4 w-4" />
                    <Badge count={mockRunningTasks.length} />
                </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-80 rounded-xl shadow-lg border-zinc-200/80 p-0 overflow-hidden">
                {mockRunningTasks.length > 0 && (
                    <div className="p-3 border-b border-zinc-100">
                        <p className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider mb-2.5">
                            Đang chạy ({mockRunningTasks.length})
                        </p>
                        <div className="space-y-3.5">
                            {mockRunningTasks.map((task) => (
                                <div key={task.id} className="space-y-1.5">
                                    <div className="flex items-center justify-between">
                                        <span className="text-[12.5px] font-medium text-zinc-700 truncate flex-1 pr-2">{task.label}</span>
                                        <span className="text-[11px] text-zinc-400 shrink-0">{task.percent}%</span>
                                    </div>
                                    <ProgressBar percent={task.percent} />
                                    <div className="flex items-center justify-between">
                                        <span className="text-[11px] text-zinc-400">Còn ~{task.etaMin} phút</span>
                                        <button className="text-[11px] text-red-500 hover:text-red-600 font-medium">Hủy</button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
                <div className="p-3 border-b border-zinc-100">
                    <p className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider mb-2">
                        Hoàn thành ({mockDoneTasks.length})
                    </p>
                    <div className="space-y-0.5">
                        {mockDoneTasks.map((task) => (
                            <div key={task.id} className="flex items-center gap-2 h-8 px-1 rounded-md hover:bg-zinc-50 cursor-pointer transition-colors">
                                <CheckCircle2 className="h-3.5 w-3.5 text-zinc-400 shrink-0" />
                                <span className="text-[12.5px] text-zinc-600 truncate flex-1">{task.label}</span>
                                <span className="text-[11px] text-zinc-400 shrink-0">{task.ago}</span>
                            </div>
                        ))}
                    </div>
                </div>
                <div className="p-2">
                    <button className="w-full text-center text-[12px] text-zinc-500 hover:text-zinc-800 font-medium py-1.5 transition-colors">
                        Xem tất cả lịch sử →
                    </button>
                </div>
            </DropdownMenuContent>
        </DropdownMenu>
    );
}

// ─────────────────────────────────────────────
// NOTIFICATION BELL
// ─────────────────────────────────────────────

function NotificationBell() {
    const unread = mockNotifications.filter((n) => !n.read).length;
    return (
        <DropdownMenu>
            <DropdownMenuTrigger asChild>
                <button className="relative h-8 w-8 flex items-center justify-center rounded-md text-zinc-500 hover:bg-zinc-100 transition-colors">
                    <Bell className="h-4 w-4" />
                    <Badge count={unread} />
                </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-72 rounded-xl shadow-lg border-zinc-200/80 p-0 overflow-hidden">
                <div className="px-3 pt-3 pb-2 border-b border-zinc-100">
                    <p className="text-[13px] font-semibold text-zinc-800">Thông báo</p>
                </div>
                <div className="p-2 space-y-0.5 max-h-64 overflow-y-auto">
                    {mockNotifications.map((n) => (
                        <div key={n.id} className={cn(
                            "flex items-start gap-2.5 px-2 py-2 rounded-lg cursor-pointer transition-colors",
                            n.read ? "hover:bg-zinc-50" : "bg-zinc-50 hover:bg-zinc-100"
                        )}>
                            <span className={cn("h-1.5 w-1.5 rounded-full mt-1.5 shrink-0", n.read ? "bg-transparent" : "bg-zinc-900")} />
                            <div className="flex-1 min-w-0">
                                <p className={cn("text-[12.5px] leading-snug", n.read ? "text-zinc-500" : "text-zinc-800 font-medium")}>{n.text}</p>
                                <p className="text-[11px] text-zinc-400 mt-0.5">{n.ago}</p>
                            </div>
                        </div>
                    ))}
                </div>
                <div className="p-2 border-t border-zinc-100">
                    <button className="w-full text-center text-[12px] text-zinc-500 hover:text-zinc-800 font-medium py-1 transition-colors">
                        Đánh dấu tất cả đã đọc
                    </button>
                </div>
            </DropdownMenuContent>
        </DropdownMenu>
    );
}

// ─────────────────────────────────────────────
// QUICK CREATE
// ─────────────────────────────────────────────

function QuickCreate() {
    return (
        <DropdownMenu>
            <DropdownMenuTrigger asChild>
                <Button size="sm" className="gap-1.5 bg-zinc-900 hover:bg-zinc-800 text-white h-8 px-3 rounded-lg text-[12px] font-medium shadow-none">
                    <Plus className="h-3.5 w-3.5" strokeWidth={2.5} />
                    <span>Tạo mới</span>
                    <ChevronDown className="h-3 w-3 opacity-60" />
                </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48 rounded-lg shadow-md border-zinc-200/80 p-1">
                {[
                    { icon: FileText, label: "Blog Post" },
                    { icon: Mail, label: "Email Campaign" },
                    { icon: Share2, label: "Social Post" },
                    { icon: BookOpen, label: "Upload RAG" },
                ].map(({ icon: Icon, label }) => (
                    <DropdownMenuItem key={label} className="flex items-center gap-2.5 text-[13px] rounded-md cursor-pointer">
                        <Icon className="h-3.5 w-3.5 text-zinc-400" />
                        {label}
                    </DropdownMenuItem>
                ))}
            </DropdownMenuContent>
        </DropdownMenu>
    );
}

// ─────────────────────────────────────────────
// USER MENU
// ─────────────────────────────────────────────

function UserMenu() {
    return (
        <DropdownMenu>
            <DropdownMenuTrigger asChild>
                <button className="h-7 w-7 rounded-full bg-zinc-200 flex items-center justify-center hover:bg-zinc-300 transition-colors text-[12px] font-semibold text-zinc-700">
                    U
                </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48 rounded-lg shadow-md border-zinc-200/80 p-1">
                <DropdownMenuLabel className="text-[12px] text-zinc-500 font-normal px-2">user@example.com</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem className="flex items-center gap-2.5 text-[13px] rounded-md cursor-pointer">
                    <UserCircle className="h-3.5 w-3.5 text-zinc-400" /> Profile
                </DropdownMenuItem>
                <DropdownMenuItem className="flex items-center gap-2.5 text-[13px] rounded-md cursor-pointer">
                    <Settings className="h-3.5 w-3.5 text-zinc-400" /> Settings
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem className="flex items-center gap-2.5 text-[13px] text-red-500 focus:text-red-500 rounded-md cursor-pointer">
                    <LogOut className="h-3.5 w-3.5" /> Đăng xuất
                </DropdownMenuItem>
            </DropdownMenuContent>
        </DropdownMenu>
    );
}

// ─────────────────────────────────────────────
// TOPBAR
// ─────────────────────────────────────────────

export function Topbar({ onMenuClick }: { onMenuClick?: () => void }) {
    const [paletteOpen, setPaletteOpen] = useState(false);

    // Cmd+K global shortcut
    useEffect(() => {
        const handler = (e: KeyboardEvent) => {
            if ((e.metaKey || e.ctrlKey) && e.key === "k") {
                e.preventDefault();
                setPaletteOpen(true);
            }
        };
        document.addEventListener("keydown", handler);
        return () => document.removeEventListener("keydown", handler);
    }, []);

    return (
        <>
            <header className="h-14 px-4 flex items-center justify-between shrink-0 border-b border-zinc-200/50 bg-white select-none gap-4">

                {/* LEFT */}
                <div className="flex items-center gap-2.5 shrink-0">
                    <button
                        className="md:hidden h-8 w-8 rounded-md flex items-center justify-center text-zinc-500 hover:bg-zinc-100 transition-colors"
                        onClick={onMenuClick}
                    >
                        <Menu className="h-4 w-4" />
                    </button>
                    <BrandSwitcher />
                </div>

                {/* CENTER — Search: desktop full bar, mobile icon only */}
                <div className="flex-1 flex justify-center">

                    {/* Desktop: full search bar */}
                    <button
                        onClick={() => setPaletteOpen(true)}
                        className="hidden md:flex w-full max-w-md items-center gap-2.5 h-8 px-3.5 rounded-lg border border-zinc-200 bg-zinc-50 hover:bg-zinc-100 hover:border-zinc-300 transition-all duration-150 text-left"
                    >
                        <Search className="h-3.5 w-3.5 text-zinc-400 shrink-0" />
                        <span className="text-[12.5px] text-zinc-400 flex-1">Tìm kiếm...</span>
                        <kbd className="hidden sm:inline-flex items-center text-[10px] text-zinc-300 font-mono border border-zinc-200 rounded px-1 py-0.5 bg-white leading-none">
                            ⌘K
                        </kbd>
                    </button>

                    {/* Mobile: icon only */}
                    <button
                        onClick={() => setPaletteOpen(true)}
                        className="md:hidden h-8 w-8 flex items-center justify-center rounded-lg text-zinc-500 hover:bg-zinc-100 transition-colors"
                    >
                        <Search className="h-4 w-4" />
                    </button>

                </div>

                {/* RIGHT */}
                <div className="flex items-center gap-1.5 shrink-0">
                    <NotificationBell />
                    <TaskBell />
                    <div className="w-px h-4 bg-zinc-200 mx-0.5" />
                    <QuickCreate />
                    <div className="w-px h-4 bg-zinc-200 mx-0.5" />
                    <UserMenu />
                </div>
            </header>

            {/* Command Palette Modal */}
            <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
        </>
    );
}