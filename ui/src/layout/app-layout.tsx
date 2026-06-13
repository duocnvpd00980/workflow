"use client";

import {
  useState,
  useCallback,
  useEffect,
  useRef,
  Suspense,
  type ReactNode,
} from "react";

import { Link, useRouterState, useLocation } from "@tanstack/react-router";

import {
  Sheet,
  SheetContent,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";

import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import { TooltipProvider } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

import {
  Zap,
  BrainCircuit,
  Palette,
  History,
  BarChart3,
  Package,
  Menu,
  MoreHorizontal,
  Search,
  Plus,
  Compass,
  SlidersHorizontal,
  ChevronDown,
  type LucideIcon,
} from "lucide-react";

// ─────────────────────────────────────────────
// CONFIG
// ─────────────────────────────────────────────

type NavItem = {
  label: string;
  to: string;
  icon: LucideIcon;
};

type Props = {
  children: ReactNode;
};

const primaryNav: NavItem[] = [
  { label: "Home", to: "/", icon: Zap },
  { label: "Tri thức", to: "/knowledge", icon: BrainCircuit },
  { label: "Brand", to: "/brand", icon: Palette },
  { label: "Kế hoạch", to: "/planner", icon: SlidersHorizontal },
  { label: "Tra cứu", to: "/research", icon: Compass },
];

const secondaryNav: NavItem[] = [
  { label: "Brands", to: "/brand", icon: Zap },
];

// ─────────────────────────────────────────────
// HOOKS
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
// RE-DESIGNED COMPONENTS (High-density, Flat)
// ─────────────────────────────────────────────

function NavLink({
  to,
  label,
  Icon,
  isActive,
  onClick,
}: {
  to: string;
  label: string;
  Icon: LucideIcon;
  isActive: boolean;
  onClick?: () => void;
}) {
  return (
    <Link
      to={to}
      onClick={onClick}
      className={cn(
        "group relative flex items-center gap-2.5 h-8 px-2.5 rounded-md text-[13px] font-medium transition-all duration-150 select-none",
        isActive
          ? "bg-zinc-200/60 text-zinc-900 font-semibold"
          : "text-zinc-500 hover:bg-zinc-200/30 hover:text-zinc-900"
      )}
    >
      <Icon
        className={cn(
          "h-3.5 w-3.5 transition-colors duration-150 shrink-0", 
          isActive ? "text-zinc-900 stroke-[2px]" : "text-zinc-400 group-hover:text-zinc-600 stroke-[1.5px]"
        )}
      />
      <span className="truncate">{label}</span>
    </Link>
  );
}

// ─────────────────────────────────────────────
// MAIN LAYOUT
// ─────────────────────────────────────────────

export default function AppLayout({ children }: Props) {
  const [sheetOpen, setSheetOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");
  const currentPath = useRouterState().location.pathname;
  const scrollRef = useScrollReset();

  const isActive = useCallback(
    (to: string) => (to === "/" ? currentPath === "/" : currentPath.startsWith(to)),
    [currentPath]
  );

  const mobileVisibleNav = primaryNav.slice(0, 4);

  return (
    <TooltipProvider delayDuration={100}>
      {/* Nền xám cực nhẹ chuẩn app Linear/Vercel */}
      <div className="h-dvh flex bg-[#fafafa] font-sans text-zinc-900 antialiased overflow-hidden selection:bg-zinc-200">
        
        {/* DESKTOP SIDEBAR: Không bóng đổ, chia ranh giới bằng 1px border sắc lẹm */}
        <aside className="hidden md:flex w-[220px] flex-col shrink-0 bg-[#f7f7f8] border-r border-zinc-200/70">
          
          {/* Workspace Switcher tối giản */}
          <div className="h-12 px-3.5 flex items-center justify-between hover:bg-zinc-200/40 cursor-pointer transition-colors duration-150 border-b border-zinc-200/40 select-none">
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="h-5 w-5 rounded-[5px] bg-zinc-900 flex items-center justify-center shrink-0 shadow-xs">
                <Zap className="h-3 w-3 text-white fill-white" />
              </div>
              <span className="text-[13px] font-semibold text-zinc-800 truncate tracking-tight">Agent Studio</span>
            </div>
            <ChevronDown className="h-3.5 w-3.5 text-zinc-400/80" />
          </div>

          {/* Nội dung thanh điều hướng mật độ cao */}
          <div className="flex-1 overflow-y-auto p-2.5 space-y-5 scrollbar-none">
            <nav className="space-y-0.5">
              {primaryNav.map((item) => (
                <NavLink key={item.to} to={item.to} label={item.label} Icon={item.icon} isActive={isActive(item.to)} />
              ))}
            </nav>

            <nav className="space-y-0.5">
              <p className="px-2.5 pb-1.5 text-[11px] font-semibold text-zinc-400/90 uppercase tracking-wider select-none">Quản lý</p>
              {secondaryNav.map((item) => (
                <NavLink key={item.to} to={item.to} label={item.label} Icon={item.icon} isActive={isActive(item.to)} />
              ))}
            </nav>
          </div>
        </aside>

        {/* WORKSPACE AREA: Tràn viền (Full-bleed), không bo góc bọc ngoài */}
        <div className="flex-1 flex flex-col min-w-0 bg-white">
          
          {/* TOP ACTION BAR: Phẳng dẹt, hòa làm một với nội dung */}
          <header className="h-12 px-4 flex items-center justify-between shrink-0 border-b border-zinc-200/50 bg-white select-none">
            <div className="flex items-center gap-3 min-w-0 flex-1">
              <button
                className="md:hidden h-8 w-8 rounded-lg flex items-center justify-center text-zinc-500 hover:bg-zinc-100 transition-colors"
                onClick={() => setSheetOpen(true)}
              >
                <Menu className="h-4 w-4" />
              </button>
              
              {/* Thanh tìm kiếm nhúng chìm vào dòng chảy hệ thống */}
              <div className="relative w-full max-w-xs hidden md:block">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-zinc-400/90" />
                <Input
                  placeholder="Tìm kiếm nhanh... (⌘K)"
                  className="pl-8 h-8 bg-transparent border-0 focus-visible:ring-0 text-[13px] w-full placeholder:text-zinc-400/80 shadow-none"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </div>
            </div>

            {/* Các nút chức năng viền mảnh */}
            <div className="flex items-center gap-2 shrink-0">
              <Select value={filter} onValueChange={setFilter}>
                <SelectTrigger className="h-8 bg-white border border-zinc-200 hover:bg-zinc-50 text-[12px] font-medium px-2.5 rounded-lg shadow-none transition-colors">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="rounded-lg shadow-md border-zinc-200/80">
                  <SelectItem value="all" className="text-[12.5px]">Tất cả</SelectItem>
                  <SelectItem value="draft" className="text-[12.5px]">Bản nháp</SelectItem>
                  <SelectItem value="published" className="text-[12.5px]">Đã đăng</SelectItem>
                </SelectContent>
              </Select>

              <Button size="sm" className="gap-1 bg-zinc-900 hover:bg-zinc-800 text-white h-8 px-3 rounded-lg text-[12px] font-medium shadow-none transition-colors">
                <Plus className="h-3.5 w-3.5" strokeWidth={2.5} />
                <span>Tạo mới</span>
              </Button>
            </div>
          </header>

          {/* TRONG SUỐT VÀ TRÀN KHUNG: Nội dung render tại đây không bị ép biên */}
          <main ref={scrollRef} className="flex-1 overflow-auto min-h-0 bg-white">
            <Suspense fallback={
              <div className="p-4 space-y-2 animate-pulse">
                {[1, 2, 3].map((i) => <div key={i} className="h-12 bg-zinc-100 rounded-lg" />)}
              </div>
            }>
              {children}
            </Suspense>
          </main>

          {/* MOBILE NAVIGATION */}
          <nav
            className="md:hidden fixed bottom-0 left-0 right-0 border-t border-zinc-200 bg-white/95 backdrop-blur-md z-40 grid grid-cols-5 select-none"
            style={{
              height: "calc(49px + env(safe-area-inset-bottom, 0px))",
              paddingBottom: "env(safe-area-inset-bottom, 0px)",
            }}
          >
            {mobileVisibleNav.map((item) => {
              const active = isActive(item.to)
              return (
                <Link
                  key={item.to}
                  to={item.to}
                  className={cn("flex flex-col items-center justify-center text-zinc-400 transition-colors duration-150", active && "text-zinc-950")}
                >
                  <item.icon className="h-4 w-4" strokeWidth={active ? 2.2 : 1.6} />
                  <span className={cn("text-[10px] mt-1 font-medium tracking-tight", active && "font-semibold")}>{item.label}</span>
                </Link>
              )
            })}
            <button onClick={() => setSheetOpen(true)} className="flex flex-col items-center justify-center text-zinc-400 hover:text-zinc-600 transition-colors">
              <MoreHorizontal className="h-4 w-4" />
              <span className="text-[10px] mt-1 font-medium tracking-tight">Thêm</span>
            </button>
          </nav>

          <div className="md:hidden shrink-0" style={{ height: "calc(49px + env(safe-area-inset-bottom, 0px))" }} />
        </div>
      </div>

      {/* MOBILE DRAWER */}
      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetContent side="bottom" className="rounded-t-xl p-0 max-h-[80vh] border-0 bg-[#f7f7f8]">
          <SheetTitle className="sr-only">Menu</SheetTitle>
          <SheetDescription className="sr-only">Navigation</SheetDescription>
          <div className="p-4 pb-6 h-full overflow-y-auto">
            <div className="w-9 h-1 bg-zinc-200 rounded-full mx-auto mb-5" />
            <nav className="space-y-1">
              {primaryNav.map((item) => (
                <NavLink key={item.to} to={item.to} label={item.label} Icon={item.icon} isActive={isActive(item.to)} onClick={() => setSheetOpen(false)} />
              ))}
              <div className="pt-4 mt-2 border-t border-zinc-200/60 space-y-1">
                {secondaryNav.map((item) => (
                  <NavLink key={item.to} to={item.to} label={item.label} Icon={item.icon} isActive={isActive(item.to)} onClick={() => setSheetOpen(false)} />
                ))}
              </div>
            </nav>
          </div>
        </SheetContent>
      </Sheet>
    </TooltipProvider>
  );
}