"use client";

import { useCallback, useState, useEffect } from "react";
import { Link, useRouterState } from "@tanstack/react-router";
import { Zap, Home, BrainCircuit, ListTodo, Settings, Plus, CalendarClock, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { BrandItem, DeleteConfirmDialog, type Brand } from "./BrandItem";
import { CreateBrandModal } from "./CreateBrandModal";


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

const INITIAL_BRANDS: Brand[] = [
    { id: "1", name: "Acme Corp", active: true },
    { id: "2", name: "StartupX", active: false },
    { id: "3", name: "Brand C", active: false },
];

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
            className={cn(
                "group flex items-center gap-2.5 h-9 px-3 rounded-md text-[13px] font-medium",
                "transition-all duration-150 select-none w-full",
                isActive
                    ? "bg-zinc-900 text-white"
                    : "text-zinc-500 hover:bg-zinc-200/60 hover:text-zinc-900"
            )}
        >
            <Icon className={cn(
                "h-4 w-4 shrink-0 transition-colors duration-150",
                isActive ? "text-white stroke-[2px]" : "text-zinc-400 group-hover:text-zinc-700 stroke-[1.5px]"
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
    const isActive = useCallback(
        (to: string) => to === "/" ? currentPath === "/" : currentPath.startsWith(to),
        [currentPath]
    );

    const [brands, setBrands] = useState<Brand[]>(INITIAL_BRANDS);
    const [modalOpen, setModalOpen] = useState(false);
    const [deleteTarget, setDeleteTarget] = useState<Brand | null>(null);

    // Lắng nghe event từ CreateBrandModal khi research xong
    // → tắt researching flag trên brand tương ứng
    useEffect(() => {
        const handler = (e: Event) => {
            const { id } = (e as CustomEvent<{ id: string }>).detail;
            setBrands((prev) =>
                prev.map((b) => b.id === id ? { ...b, researching: false } : b)
            );
        };
        window.addEventListener("brand:research-done", handler);
        return () => window.removeEventListener("brand:research-done", handler);
    }, []);

    // ── Handlers ──

    const handleCreated = (brand: Brand) => {
        setBrands((prev) => [
            ...prev.map((b) => ({ ...b, active: false })),
            brand,   // brand mới là active, researching: true
        ]);
    };

    const handleSetDefault = (id: string) =>
        setBrands((prev) => prev.map((b) => ({ ...b, active: b.id === id })));

    const handleEdit = (id: string) => {
        // TODO: mở Edit modal (reuse CreateBrandModal + initialData)
        console.log("edit brand", id);
    };

    const handleDeleteConfirm = () => {
        if (!deleteTarget) return;
        setBrands((prev) => {
            const next = prev.filter((b) => b.id !== deleteTarget.id);
            if (deleteTarget.active && next.length > 0) next[0].active = true;
            return next;
        });
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
                            {brands.map((brand) => (
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
                            ))}
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
        <aside className="hidden md:flex w-[240px] flex-col shrink-0 bg-[#f7f7f8] border-r border-zinc-200/70 h-full">
            <SidebarContent />
        </aside>
    );
}