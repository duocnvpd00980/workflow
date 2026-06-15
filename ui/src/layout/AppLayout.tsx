"use client";

import { useState, useEffect, useRef, Suspense, type ReactNode } from "react";
import { Link, useLocation, useRouterState } from "@tanstack/react-router";
import { TooltipProvider } from "@/components/ui/tooltip";
import {
    Sheet, SheetContent, SheetTitle, SheetDescription,
} from "@/components/ui/sheet";
import { MoreHorizontal, Home, BrainCircuit, ListTodo, type LucideIcon, Palette, Plus } from "lucide-react";
import { cn } from "@/lib/utils";
import { Sidebar, SidebarContent } from "./Sidebar";
import { Topbar } from "./Topbar";
import { Toaster } from "sonner";
import { CreateModal } from "./CreateContentModal";

// ─────────────────────────────────────────────
// HOOK
// ─────────────────────────────────────────────

function useScrollReset() {
    const location = useLocation();
    const ref = useRef<HTMLDivElement | null>(null);
    useEffect(() => {
        ref.current?.scrollTo(0, 0);
    }, [location.pathname]);
    return ref;
}

// ─────────────────────────────────────────────
// MOBILE BOTTOM NAV CONFIG
// ─────────────────────────────────────────────

type NavItem = { label: string; to: string; icon: LucideIcon };

const mobileNav: NavItem[] = [
    { label: "Home", to: "/", icon: Home },
    { label: "RAG", to: "/rag", icon: BrainCircuit },
    // [+] ở giữa — không phải NavItem
    { label: "Brands", to: "/brands", icon: Palette },
    { label: "Tasks", to: "/tasks", icon: ListTodo },
];

// ─────────────────────────────────────────────
// LAYOUT
// ─────────────────────────────────────────────

export default function AppLayout({ children }: { children: ReactNode }) {
    const [sheetOpen, setSheetOpen] = useState(false);
    const [createOpen, setCreateOpen] = useState(false);  // ← thêm
    const [runningCount, setRunningCount] = useState(0);    // ← thêm

    const scrollRef = useScrollReset();
    const currentPath = useRouterState().location.pathname;

    // Lắng nghe task running từ CreateBrandModal
    useEffect(() => {
        const onStart = () => setRunningCount((n) => n + 1);
        const onDone = () => setRunningCount((n) => Math.max(0, n - 1));
        window.addEventListener("brand:research-start", onStart);
        window.addEventListener("brand:research-done", onDone);
        return () => {
            window.removeEventListener("brand:research-start", onStart);
            window.removeEventListener("brand:research-done", onDone);
        };
    }, []);

    const isActive = (to: string) =>
        to === "/" ? currentPath === "/" : currentPath.startsWith(to);

    return (
        <TooltipProvider delayDuration={100}>
            <div className="h-dvh flex bg-zinc-100 font-sans text-zinc-900 antialiased overflow-hidden selection:bg-zinc-200">

                {/* ── Desktop Sidebar ── */}
                <Sidebar />

                {/* ── Main workspace ── */}
                <div className="flex-1 flex flex-col min-w-0 bg-white">

                    {/* Top bar */}
                    <Topbar onMenuClick={() => setSheetOpen(true)} />

                    {/* Page content */}
                    <main ref={scrollRef} className="flex-1 overflow-auto min-h-0 bg-white">
                        <Suspense fallback={
                            <div className="p-4 space-y-2 animate-pulse">
                                {[1, 2, 3].map((i) => (
                                    <div key={i} className="h-12 bg-zinc-100 rounded-lg" />
                                ))}
                            </div>
                        }>
                            {children}
                        </Suspense>
                    </main>

                    {/* ── Mobile Bottom Nav ── */}
                    <nav
                        className="md:hidden fixed bottom-0 left-0 right-0 border-t border-zinc-200 bg-white/95 backdrop-blur-md z-40 select-none"
                        style={{
                            height: "calc(56px + env(safe-area-inset-bottom, 0px))",
                            paddingBottom: "env(safe-area-inset-bottom, 0px)",
                        }}
                    >
                        <div className="h-14 grid grid-cols-5 items-center">

                            {/* Tab 1: Home */}
                            {/* Tab 2: RAG */}
                            {mobileNav.slice(0, 2).map((item) => {
                                const active = isActive(item.to);
                                return (
                                    <Link
                                        key={item.to}
                                        to={item.to}
                                        className={cn(
                                            "flex flex-col items-center justify-center gap-0.5 h-full transition-colors duration-150",
                                            active ? "text-zinc-950" : "text-zinc-400"
                                        )}
                                    >
                                        <item.icon className="h-[18px] w-[18px]" strokeWidth={active ? 2.2 : 1.6} />
                                        <span className={cn("text-[10px] font-medium tracking-tight", active && "font-semibold")}>
                                            {item.label}
                                        </span>
                                    </Link>
                                );
                            })}

                            {/* Tab 3: CENTER [+] FAB */}
                            <button
                                onClick={() => setCreateOpen(true)}
                                className="flex flex-col items-center justify-center h-full"
                            >
                                <div className="h-10 w-10 rounded-full bg-zinc-900 flex items-center justify-center shadow-lg shadow-zinc-900/20 active:scale-95 transition-transform duration-150">
                                    <Plus className="h-5 w-5 text-white" strokeWidth={2.5} />
                                </div>
                            </button>

                            {/* Tab 4: Brands */}
                            {/* Tab 5: Tasks — với badge ⚡ khi có task chạy */}
                            {mobileNav.slice(2).map((item) => {
                                const active = isActive(item.to);
                                const isTask = item.to === "/tasks";

                                return (
                                    <Link
                                        key={item.to}
                                        to={item.to}
                                        className={cn(
                                            "relative flex flex-col items-center justify-center gap-0.5 h-full transition-colors duration-150",
                                            active ? "text-zinc-950" : "text-zinc-400"
                                        )}
                                    >
                                        {/* Task tab: icon + badge running */}
                                        {isTask ? (
                                            <div className="relative">
                                                <item.icon
                                                    className="h-[18px] w-[18px]"
                                                    strokeWidth={active ? 2.2 : 1.6}
                                                />
                                                {/* Badge: chỉ hiện khi có task đang chạy */}
                                                {runningCount > 0 && (
                                                    <span className="absolute -top-1.5 -right-2 h-4 min-w-4 px-1 flex items-center justify-center rounded-full bg-orange-500 text-white text-[9px] font-bold leading-none">
                                                        {runningCount}
                                                    </span>
                                                )}
                                            </div>
                                        ) : (
                                            <item.icon
                                                className="h-[18px] w-[18px]"
                                                strokeWidth={active ? 2.2 : 1.6}
                                            />
                                        )}
                                        <span className={cn(
                                            "text-[10px] font-medium tracking-tight",
                                            active && "font-semibold",
                                            // Task tab: label đổi màu cam khi đang chạy
                                            isTask && runningCount > 0 && !active && "text-orange-500"
                                        )}>
                                            {isTask && runningCount > 0 ? `⚡ ${runningCount} đang chạy` : item.label}
                                        </span>
                                    </Link>
                                );
                            })}
                        </div>
                    </nav>

                    {/* Spacer cho bottom nav mobile */}
                    <div className="md:hidden shrink-0" style={{ height: "calc(49px + env(safe-area-inset-bottom, 0px))" }} />
                </div>
            </div>

            {/* ── Mobile Drawer (slide từ dưới lên) ── */}
            <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
                <SheetContent
                    side="bottom"
                    className="rounded-t-xl p-0 max-h-[80vh] border-0 bg-[#f7f7f8]"
                >
                    <SheetTitle className="sr-only">Menu</SheetTitle>
                    <SheetDescription className="sr-only">Navigation</SheetDescription>
                    <div className="p-4 pb-6 h-full overflow-y-auto">
                        {/* Drag handle */}
                        <div className="w-9 h-1 bg-zinc-200 rounded-full mx-auto mb-5" />
                        <SidebarContent onNavigate={() => setSheetOpen(false)} />
                    </div>
                </SheetContent>
            </Sheet>
            <Toaster
                position="bottom-right"
                richColors
                expand={false}
                toastOptions={{
                    classNames: {
                        toast: "rounded-xl border border-zinc-200/80 shadow-lg text-[13px]",
                        title: "font-semibold text-zinc-900",
                        description: "text-zinc-500 text-[12px]",
                        actionButton: "bg-zinc-900 text-white text-[12px] rounded-lg px-3 h-7 font-medium",
                    },
                }}
            />
            <CreateModal open={createOpen} onClose={() => setCreateOpen(false)} />
        </TooltipProvider>
    );
}