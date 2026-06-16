"use client";

import { useCallback, useState, useEffect } from "react";
import { Link, useRouterState } from "@tanstack/react-router";
import { Zap, Home, BrainCircuit, ListTodo, Settings, Plus, CalendarClock, Loader2, type LucideIcon } from "lucide-react";
import { useQuery, useQueryClient } from "@tanstack/react-query"; // Chèn thêm React Query
import { cn } from "@/lib/utils";
import { BrandItem, DeleteConfirmDialog, type Brand } from "./BrandItem";
import { CreateBrandModal } from "./CreateBrandModal";
import { API_BASE } from "@/config";

// ─────────────────────────────────────────────
// CONFIG
// ─────────────────────────────────────────────

type NavItem = { label: string; to: string; icon: LucideIcon };

const primaryNav: NavItem[] = [
    { label: "Home", to: "/", icon: Home },
    { label: "Knowledge", to: "/knowledge", icon: BrainCircuit },
    { label: "Tasks", to: "/tasks", icon: ListTodo },
    { label: "Planner", to: "/planner", icon: CalendarClock },
];

// Định nghĩa kiểu dữ liệu khớp chính xác với API Server trả về
type BrandOptionResponse = {
    id: string;
    name: string;
    business_id: string;
    is_default: boolean;
};

// ─────────────────────────────────────────────
// NAV LINK
// ─────────────────────────────────────────────

function NavLink({
    to, label, Icon, isActive, onClick,
}: {
    to: string; label: string; Icon: LucideIcon;
    isActive: boolean; onClick?: () => void;
}) {
    return (
        <Link
            to={to}
            onClick={onClick}
            search={true}
            aria-current={isActive ? "page" : undefined}
            className={cn(
                "group relative flex items-center gap-2.5 h-9 px-3 rounded-md text-[13px]",
                "transition-colors duration-100 select-none w-full",
                isActive
                    ? "bg-zinc-100/80 text-zinc-900 font-semibold"
                    : "text-zinc-500 font-medium hover:bg-zinc-200/50 hover:text-zinc-700"
            )}
        >
            {isActive && (
                <div className="absolute left-0 top-1.5 bottom-1.5 w-[2.5px] rounded-r-full bg-zinc-900" />
            )}
            
            <Icon className={cn(
                "h-4 w-4 shrink-0 transition-colors duration-100",
                isActive 
                    ? "text-zinc-900 stroke-[2.5px]" 
                    : "text-zinc-400 group-hover:text-zinc-600 stroke-[1.5px]"
            )} />
            <span className="truncate">{label}</span>
        </Link>
    );
}

// ─────────────────────────────────────────────
// SIDEBAR CONTENT
// ─────────────────────────────────────────────

export function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
    const currentPath = useRouterState().location.pathname;
    const queryClient = useQueryClient();
    
    const isActive = useCallback(
        (to: string) => to === "/" ? currentPath === "/" : currentPath.startsWith(to),
        [currentPath]
    );

    const [modalOpen, setModalOpen] = useState(false);
    const [deleteTarget, setDeleteTarget] = useState<Brand | null>(null);

    // ── FETCH BRAND OPTIONS VIA REACT QUERY ──
    const { data: brands = [], isLoading, isError } = useQuery<Brand[]>({
        queryKey: ["brand-voices", "options"],
        queryFn: async () => {
            const res = await fetch(`${API_BASE}/brand-voices/options`, {
                headers: { "accept": "application/json" },
            });
            if (!res.ok) throw new Error("Không thể tải danh sách brand");
            
            const rawData: BrandOptionResponse[] = await res.json();
            
            // Map trường `is_default` từ API sang `active` theo cấu trúc UI cũ của bạn
            return rawData.map((item) => ({
                id: item.id,
                name: item.name,
                active: item.is_default, // Đồng bộ trạng thái active của UI từ flag is_default
            }));
        },
        // Giữ data cũ khi đang fetch lại ngầm
        placeholderData: (previousData) => previousData,
    });

    // Lắng nghe event khi pipeline research kết thúc ngầm -> Invalidated để fetch lại data mới nhất
    useEffect(() => {
        const handler = () => {
            queryClient.invalidateQueries({ queryKey: ["brand-voices", "options"] });
        };
        window.addEventListener("brand:research-done", handler);
        return () => window.removeEventListener("brand:research-done", handler);
    }, [queryClient]);

    // ── Handlers ──

    const handleCreated = (_newBrand: Brand) => {
        // Sau khi tạo xong, thay vì tự push vào state local, ta invalidate query để React Query tự pull data chuẩn từ DB về
        queryClient.invalidateQueries({ queryKey: ["brand-voices", "options"] });
    };

    const handleSetDefault = async (id: string) => {
        // TODO: Viết mutation POST /brand-voices/{id}/set-default ở đây.
        // Tạm thời tối ưu UI ngay lập tức (Optimistic Update) bằng cách set query data cục bộ:
        queryClient.setQueryData<Brand[]>(["brand-voices", "options"], (prev) =>
            prev?.map((b) => ({ ...b, active: b.id === id }))
        );
        console.log("Set default brand:", id);
    };

    const handleEdit = (id: string) => {
        console.log("edit brand", id);
    };

    const handleDeleteConfirm = () => {
        if (!deleteTarget) return;
        // TODO: Viết mutation DELETE /brand-voices/{id} ở đây.
        // Tối ưu UI tạm thời sau khi xóa:
        queryClient.setQueryData<Brand[]>(["brand-voices", "options"], (prev) =>
            prev?.filter((b) => b.id !== deleteTarget.id)
        );
        setDeleteTarget(null);
    };

    return (
        <>
            <div className="flex flex-col h-full">
                {/* Logo */}
                <div className="h-14 px-4 flex items-center gap-2.5 border-b border-zinc-200/40 shrink-0 select-none">
                    <div className="h-6 w-6 rounded-[6px] bg-zinc-900 flex items-center justify-center shrink-0">
                        <Zap className="h-3.5 w-3.5 text-white fill-white" />
                    </div>
                    <span className="text-[13.5px] font-semibold text-zinc-800 tracking-tight truncate">
                        Agent Studio
                    </span>
                </div>

                {/* Scrollable body */}
                <div className="flex-1 overflow-y-auto py-3 px-2 space-y-6 scrollbar-none">
                    {/* Primary nav */}
                    <nav className="space-y-0.5">
                        {primaryNav.map((item) => (
                            <NavLink
                                key={item.to} to={item.to} label={item.label}
                                Icon={item.icon} isActive={isActive(item.to)} onClick={onNavigate}
                            />
                        ))}
                    </nav>

                    {/* Brands section */}
                    <div>
                        <div className="flex items-center justify-between px-3 pb-1.5">
                            <p className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider select-none">
                                Brands
                            </p>
                            <button
                                onClick={() => setModalOpen(true)}
                                className="h-5 w-5 flex items-center justify-center rounded text-zinc-400 hover:text-zinc-700 hover:bg-zinc-200/60 transition-colors"
                                title="Thêm brand"
                            >
                                <Plus className="h-3.5 w-3.5" strokeWidth={2.5} />
                            </button>
                        </div>

                        <div className="space-y-0.5">
                            {isLoading ? (
                                <div className="flex items-center gap-2 px-3 py-2 text-[12px] text-zinc-400 select-none">
                                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                    <span>Đang tải danh sách...</span>
                                </div>
                            ) : isError ? (
                                <div className="px-3 py-2 text-[12px] text-red-500 font-medium select-none">
                                    Lỗi tải dữ liệu.
                                </div>
                            ) : brands.length === 0 ? (
                                <div className="px-3 py-2 text-[12px] text-zinc-400 italic select-none">
                                    Chưa có brand voice nào
                                </div>
                            ) : (
                                brands.map((brand) => (
                                    <Link
                                        key={brand.id}
                                        to="/brand"
                                        search={{ contentId: brand.id } as any}
                                        className="block"
                                    >
                                        <BrandItem
                                            brand={brand}
                                            onSetDefault={handleSetDefault}
                                            onEdit={handleEdit}
                                            onDelete={(id) => setDeleteTarget(brands.find((b) => b.id === id) ?? null)}
                                        />
                                    </Link>
                                ))
                            )}
                        </div>
                    </div>
                </div>

                {/* Settings pinned bottom */}
                <div className="px-2 py-3 border-t border-zinc-200/40 shrink-0">
                    <NavLink
                        to="/settings" label="Settings" Icon={Settings}
                        isActive={isActive("/settings")} onClick={onNavigate}
                    />
                </div>
            </div>

            {/* Modals */}
            <CreateBrandModal
                open={modalOpen}
                onClose={() => setModalOpen(false)}
                onCreated={handleCreated}
            />
            <DeleteConfirmDialog
                open={!!deleteTarget}
                brandName={deleteTarget?.name ?? ""}
                onConfirm={handleDeleteConfirm}
                onCancel={() => setDeleteTarget(null)}
            />
        </>
    );
}

// ─────────────────────────────────────────────
// DESKTOP SIDEBAR
// ─────────────────────────────────────────────

export function Sidebar() {
    return (
        <aside className="hidden md:flex w-[240px] flex-col shrink-0 bg-zinc-100 border-r border-zinc-200/70 h-full">
            <SidebarContent />
        </aside>
    );
}