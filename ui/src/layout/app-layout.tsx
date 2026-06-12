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
  SheetTrigger,
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

import {
  TooltipProvider,
} from "@/components/ui/tooltip";

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
  Filter,
  type LucideIcon,
} from "lucide-react";

// ─────────────────────────────────────────────
// TYPES
// ─────────────────────────────────────────────

type NavItem = {
  label: string;
  to: string;
  icon: LucideIcon;
};

type Props = {
  children: ReactNode;
};

// ─────────────────────────────────────────────
// NAV CONFIG
// ─────────────────────────────────────────────

const primaryNav: NavItem[] = [
  { label: "Tạo", to: "/", icon: Zap },
  { label: "Tri thức", to: "/knowledge", icon: BrainCircuit },
  { label: "Brand", to: "/brand", icon: Palette },
  { label: "Kế hoạch", to: "/planner", icon: Zap },
  { label: "Tra cứu", to: "/research", icon: Zap },
];

const secondaryNav: NavItem[] = [
  { label: "Kho", to: "/artifacts", icon: Package },
  { label: "Lịch sử", to: "/history", icon: History },
  { label: "Thống kê", to: "/analytics", icon: BarChart3 },
  { label: "Tích hợp", to: "/integrations", icon: Zap },
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
// COMPONENTS
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
      aria-current={isActive ? "page" : undefined}
      className={cn(
        "group relative flex items-center gap-3 min-h-[44px] px-3 rounded-xl text-sm font-medium transition-colors duration-150",
        "outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1",
        isActive
          ? "bg-primary/10 text-primary"
          : "text-muted-foreground hover:bg-muted hover:text-foreground"
      )}
    >
      {isActive && (
        <span
          className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-r-full bg-primary"
          aria-hidden="true"
        />
      )}

      <Icon
        size={18}
        aria-hidden="true"
        strokeWidth={isActive ? 2.5 : 2}
        className={cn(
          "shrink-0 transition-none",
          isActive ? "text-primary" : "text-muted-foreground"
        )}
      />

      <span className="truncate">{label}</span>
    </Link>
  );
}

// Giữ nguyên component Sidebar Item
function SidebarNavItem({
  item,
  isActive,
}: {
  item: NavItem;
  isActive: boolean;
}) {
  return (
    <NavLink
      to={item.to}
      label={item.label}
      Icon={item.icon}
      isActive={isActive}
    />
  );
}

// Giữ nguyên component Mobile Item bên ngoài
function MobileNavItem({
  item,
  isActive,
}: {
  item: NavItem;
  isActive: boolean;
}) {
  return (
    <Link
      to={item.to}
      aria-current={isActive ? "page" : undefined}
      aria-label={item.label}
      className={cn(
        "flex flex-col items-center justify-center gap-0.5 min-h-[44px] transition-colors duration-150",
        "outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-lg",
        isActive ? "text-primary" : "text-muted-foreground"
      )}
    >
      <item.icon
        size={20}
        aria-hidden="true"
        strokeWidth={isActive ? 2.5 : 2}
        className={isActive ? "text-primary" : "text-muted-foreground"}
      />
      <span className="text-[11px] font-medium leading-none">{item.label}</span>
    </Link>
  );
}

// Giữ nguyên component Sidebar Content cho Desktop
function SidebarContent({
  isActive,
  onNavClick,
}: {
  isActive: (to: string) => boolean;
  onNavClick?: () => void;
}) {
  return (
    <>
      <div className="h-16 px-4 flex items-center gap-3 shrink-0">
        <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center shrink-0">
          <Zap size={18} className="text-primary-foreground" aria-hidden="true" />
        </div>
        <span className="text-base font-semibold tracking-tight">Agent</span>
      </div>

      <nav className="px-2 space-y-0.5" aria-label="Chính">
        <p className="px-2 pb-1 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
          Chính
        </p>
        {primaryNav.map((item) => (
          <SidebarNavItem
            key={item.to}
            item={item}
            isActive={isActive(item.to)}
          />
        ))}
      </nav>

      <div className="mx-4 my-2 h-px bg-border" aria-hidden="true" />

      <nav className="px-2 space-y-0.5" aria-label="Phụ">
        <p className="px-2 pb-1 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
          Quản lý
        </p>
        {secondaryNav.map((item) => (
          <SidebarNavItem
            key={item.to}
            item={item}
            isActive={isActive(item.to)}
          />
        ))}
      </nav>

      <div className="flex-1" />
    </>
  );
}

function ContentSkeleton() {
  return (
    <div className="animate-pulse">
      {[1, 2, 3, 4, 5].map((i) => (
        <div key={i} className="border-b px-4 py-3 flex items-start gap-3">
          <div className="h-5 w-5 rounded bg-muted shrink-0" />
          <div className="flex-1 space-y-2">
            <div className="h-4 w-3/4 rounded bg-muted" />
            <div className="h-3 w-1/2 rounded bg-muted" />
          </div>
        </div>
      ))}
    </div>
  );
}

// ─────────────────────────────────────────────
// MAIN LAYOUT
// ─────────────────────────────────────────────

export default function AppLayout({ children }: Props) {
  const [sheetOpen, setSheetOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");
  const routerState = useRouterState();
  const currentPath = routerState.location.pathname;
  const scrollRef = useScrollReset();

  const isActive = useCallback(
    (to: string) => (to === "/" ? currentPath === "/" : currentPath.startsWith(to)),
    [currentPath]
  );

  const closeSheet = useCallback(() => setSheetOpen(false), []);

  // ─── PHÂN TÁCH ITEM CHO MOBILE BOTTOM NAV (CHỐNG TRÀN VỠ GRID) ───
  // Lấy chính xác 4 phần tử đầu tiên hiển thị ngoài thanh Tabbar bottom
  const mobileVisibleNav = primaryNav.slice(0, 4);
  // Đẩy phần tử thứ 5 ("Tra cứu") vào nhóm danh sách ẩn trong Sheet "Khác"
  const mobileHiddenPrimaryNav = primaryNav.slice(4);

  return (
    <TooltipProvider delayDuration={300}>
      <div className="h-dvh flex bg-gray-50 overflow-hidden">

        {/* DESKTOP SIDEBAR ≥1280px (GIỮ NGUYÊN THAY ĐỔI) */}
        <aside
          className="hidden xl:flex w-[240px] flex-col shrink-0"
          role="navigation"
          aria-label="Điều hướng chính"
        >
          <SidebarContent isActive={isActive} />
        </aside>

        {/* TABLET SIDEBAR 768–1279px (GIỮ NGUYÊN THAY ĐỔI) */}
        <aside
          className="hidden md:flex xl:hidden w-[200px] flex-col shrink-0"
          role="navigation"
          aria-label="Điều hướng chính"
        >
          <SidebarContent isActive={isActive} />
        </aside>

        {/* CONTENT AREA */}
        <div className="flex-1 flex flex-col min-w-0">

          {/* HEADER — TOOLBAR (ĐÃ SỬA ĐỂ RESPONSIVE TRÊN MOBILE) */}
          <header className="h-14 px-3 md:px-4 flex items-center gap-2 sm:gap-3 shrink-0 bg-background md:bg-gray-50 border-b md:border-0">
            {/* Mobile hamburger menu */}
            <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
              <SheetTrigger asChild>
                <button
                  className="md:hidden h-9 w-9 rounded-lg flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-muted transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  aria-label="Mở menu"
                >
                  <Menu size={20} aria-hidden="true" />
                </button>
              </SheetTrigger>
              <SheetContent
                side="bottom"
                className="rounded-t-[20px] h-auto max-h-[82vh] overflow-y-auto"
                style={{ paddingBottom: "env(safe-area-inset-bottom, 0px)" }}
              >
                <SheetTitle className="sr-only">Menu điều hướng</SheetTitle>
                <SheetDescription className="sr-only">
                  Truy cập tất cả các mục trong ứng dụng
                </SheetDescription>

                <div className="pt-2 pb-3 flex justify-center">
                  <div className="w-10 h-1 bg-muted rounded-full" aria-hidden="true" />
                </div>

                <nav className="px-2 space-y-0.5" aria-label="Mobile navigation">
                  <p className="px-2 py-1 text-[11px] font-bold text-muted-foreground uppercase tracking-wider">
                    Chính
                  </p>
                  {/* Render đầy đủ mảng primaryNav trong menu vuốt lên */}
                  {primaryNav.map((item) => (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      label={item.label}
                      Icon={item.icon}
                      isActive={isActive(item.to)}
                      onClick={closeSheet}
                    />
                  ))}
                  <p className="px-2 py-1 mt-4 text-[11px] font-bold text-muted-foreground uppercase tracking-wider">
                    Quản lý
                  </p>
                  {secondaryNav.map((item) => (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      label={item.label}
                      Icon={item.icon}
                      isActive={isActive(item.to)}
                      onClick={closeSheet}
                    />
                  ))}
                </nav>

                <div className="h-4" />
              </SheetContent>
            </Sheet>

            {/* Ô Search: Co dãn chiếm khoảng trống còn lại */}
            <div className="relative flex-1 min-w-0">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Tìm nội dung..."
                className="pl-9 h-9 bg-muted/50 border-0 w-full text-sm"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>

            {/* Select Filter: Thu nhỏ hoặc ẩn bớt text trên mobile để tránh chèn ép */}
            <Select value={filter} onValueChange={setFilter}>
              <SelectTrigger className="h-9 w-[95px] sm:w-[130px] bg-muted/50 border-0 text-xs sm:text-sm shrink-0 px-2">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tất cả</SelectItem>
                <SelectItem value="draft">Draft</SelectItem>
                <SelectItem value="published">Published</SelectItem>
                <SelectItem value="scheduled">Scheduled</SelectItem>
              </SelectContent>
            </Select>

            {/* Button New CTA: Ẩn chữ trên mobile chỉ giữ dấu cộng để tối giản diện tích */}
            <Button size="sm" className="gap-1 bg-indigo-600 hover:bg-indigo-700 h-9 shrink-0 px-2.5 sm:px-3">
              <Plus className="h-4 w-4 stroke-[2.5]" />
              <span className="hidden sm:inline">New</span>
            </Button>

            {/* Nút More: Ẩn hẳn trên Mobile để nhường chỗ cho Input */}
            <Button variant="ghost" size="icon" className="h-9 w-9 shrink-0 hidden sm:flex">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </header>

          {/* MAIN CONTAINER — GIỮ NGUYÊN CSS GỐC CỦA BẠN */}
          <main
            ref={scrollRef}
            role="main"
            aria-label="Nội dung trang"
            className="flex-1 overflow-auto min-h-0 bg-background md:rounded-lg md:m-4 border-6 border-white"
          >
            <div className="w-full min-h-0 rounded-lg overflow-auto">
              <Suspense fallback={<ContentSkeleton />}>
                {children}
              </Suspense>
            </div>
          </main>

          {/* SỬA ĐỔI TOÀN DIỆN: MOBILE BOTTOM NAV CHUẨN 5 CỘT GRID KHÔNG VỠ */}
          <nav
            className="md:hidden fixed bottom-0 left-0 right-0 border-t bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 z-50 grid grid-cols-5"
            style={{
              height: "calc(52px + env(safe-area-inset-bottom, 0px))",
              paddingBottom: "env(safe-area-inset-bottom, 0px)",
            }}
            role="navigation"
            aria-label="Tab bar mobile"
          >
            {/* Chỉ render 4 items đầu ngoài thanh bottom */}
            {mobileVisibleNav.map((item) => (
              <MobileNavItem key={item.to} item={item} isActive={isActive(item.to)} />
            ))}

            {/* Item cột số 5: Kích hoạt menu mở rộng vuốt đáy lên */}
            <button
              onClick={() => setSheetOpen(true)}
              aria-label="Xem thêm"
              aria-expanded={sheetOpen}
              className={cn(
                "flex flex-col items-center justify-center gap-0.5 min-h-[44px] transition-colors outline-none select-none",
                sheetOpen ? "text-primary" : "text-muted-foreground"
              )}
            >
              <MoreHorizontal
                size={20}
                aria-hidden="true"
                strokeWidth={sheetOpen ? 2.5 : 2}
              />
              <span className="text-[11px] font-medium leading-none">Khác</span>
            </button>
          </nav>

          <div
            className="md:hidden shrink-0"
            style={{ height: "calc(52px + env(safe-area-inset-bottom, 0px))" }}
            aria-hidden="true"
          />
        </div>
      </div>
    </TooltipProvider>
  );
}