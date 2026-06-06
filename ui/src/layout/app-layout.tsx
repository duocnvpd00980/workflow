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
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    ref.current?.scrollTo(0, 0);
  }, [location.pathname]);
  return ref;
}

// ─────────────────────────────────────────────
// COMPONENTS
// ─────────────────────────────────────────────

/** Left-border weight indicator + color for active state */
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
      {/* Active indicator bar */}
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

/** Sidebar nav item */
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

/** Mobile bottom nav item */
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

// ─────────────────────────────────────────────
// SIDEBAR SHELL (shared desktop+tablet)
// ─────────────────────────────────────────────

function SidebarContent({
  isActive,
  onNavClick,
}: {
  isActive: (to: string) => boolean;
  onNavClick?: () => void;
}) {
  return (
    <>
      {/* Logo */}
      <div className="h-16 px-4 flex items-center gap-3 shrink-0">
        <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center shrink-0">
          <Zap size={18} className="text-primary-foreground" aria-hidden="true" />
        </div>
        <span className="text-base font-semibold tracking-tight">Agent</span>
      </div>

      {/* Primary group */}
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

      {/* Secondary group */}
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

// ─────────────────────────────────────────────
// LOADING SKELETON
// ─────────────────────────────────────────────

function ContentSkeleton() {
  return (
    <div className="flex-1 p-6 space-y-4 animate-pulse">
      <div className="h-7 w-1/3 rounded-lg bg-muted" />
      <div className="h-4 w-2/3 rounded bg-muted" />
      <div className="h-4 w-1/2 rounded bg-muted" />
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-8">
        <div className="h-32 rounded-xl bg-muted" />
        <div className="h-32 rounded-xl bg-muted" />
        <div className="h-32 rounded-xl bg-muted" />
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// MAIN LAYOUT
// ─────────────────────────────────────────────

export default function AppLayout({ children }: Props) {
  const [sheetOpen, setSheetOpen] = useState(false);
  const routerState = useRouterState();
  const currentPath = routerState.location.pathname;
  const scrollRef = useScrollReset();

  // Get page title from current route
  const pageTitle =
    primaryNav.find((item) => item.to === currentPath)?.label ||
    secondaryNav.find((item) => item.to === currentPath)?.label ||
    "Agent";

  const isActive = useCallback(
    (to: string) => (to === "/" ? currentPath === "/" : currentPath.startsWith(to)),
    [currentPath]
  );

  const closeSheet = useCallback(() => setSheetOpen(false), []);

  return (
    <TooltipProvider delayDuration={300}>
      <div className="h-dvh flex bg-background overflow-hidden">

        {/* ══════════════════════════════════════
            DESKTOP SIDEBAR  ≥1280px
        ══════════════════════════════════════ */}
        <aside
          className="hidden xl:flex w-[240px] border-r flex-col shrink-0"
          role="navigation"
          aria-label="Điều hướng chính"
        >
          <SidebarContent isActive={isActive} />
        </aside>

        {/* ══════════════════════════════════════
            TABLET SIDEBAR  768–1279px
            Full labels, grouped — no icon-only
        ══════════════════════════════════════ */}
        <aside
          className="hidden md:flex xl:hidden w-[200px] border-r flex-col shrink-0"
          role="navigation"
          aria-label="Điều hướng chính"
        >
          <SidebarContent isActive={isActive} />
        </aside>

        {/* ══════════════════════════════════════
            CONTENT AREA
        ══════════════════════════════════════ */}
        <div className="flex-1 flex flex-col min-w-0">

          {/* Header */}
          <header className="h-14 border-b px-3 md:px-4 flex items-center justify-between shrink-0 gap-3">
            {/* Left: Mobile menu + route title */}
            <div className="flex items-center gap-3 min-w-0">
              {/* Mobile hamburger */}
              <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
                <SheetTrigger asChild>
                  <button
                    className="md:hidden h-11 w-11 rounded-lg flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-muted transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    aria-label="Mở menu"
                  >
                    <Menu size={20} aria-hidden="true" />
                  </button>
                </SheetTrigger>
                <SheetContent
                  side="bottom"
                  className="rounded-t-[20px] h-auto"
                  style={{ paddingBottom: "env(safe-area-inset-bottom, 0px)" }}
                >
                  <SheetTitle className="sr-only">Menu điều hướng</SheetTitle>
                  <SheetDescription className="sr-only">
                    Truy cập tất cả các mục trong ứng dụng
                  </SheetDescription>

                  {/* Drag handle */}
                  <div className="pt-3 pb-2 flex justify-center">
                    <div className="w-10 h-1 bg-muted rounded-full" aria-hidden="true" />
                  </div>

                  {/* Nav groups */}
                  <nav className="px-4 space-y-0.5" aria-label="Mobile navigation">
                    <p className="px-2 py-1 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                      Chính
                    </p>
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
                    <p className="px-2 py-1 mt-3 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
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

                  {/* Safe area spacer */}
                  <div className="h-6" />
                </SheetContent>
              </Sheet>

              {/* Route-aware title */}
              <h1 className="font-semibold text-base truncate">{pageTitle}</h1>
            </div>

            {/* Right: empty for now */}
            <div className="shrink-0" />
          </header>

          {/* Scrollable content */}
          <main
            ref={scrollRef}
            role="main"
            aria-label="Nội dung trang"
            className="flex-1 overflow-auto min-h-0"
          >
            {/* Max-width container, centered */}
            <div className="mx-auto w-full max-w-[1200px] px-4 py-6">
              <Suspense fallback={<ContentSkeleton />}>
                {children}
              </Suspense>
            </div>
          </main>

          {/* ══════════════════════════════════════
              MOBILE BOTTOM NAV  <768px
          ══════════════════════════════════════ */}
          <nav
            className="md:hidden fixed bottom-0 left-0 right-0 border-t bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 z-50 grid grid-cols-5"
            style={{
              height: "calc(56px + env(safe-area-inset-bottom, 0px))",
              paddingBottom: "env(safe-area-inset-bottom, 0px)",
            }}
            role="navigation"
            aria-label="Tab bar"
          >
            {primaryNav.map((item) => (
              <MobileNavItem key={item.to} item={item} isActive={isActive(item.to)} />
            ))}

            {/* More */}
            <button
              onClick={() => setSheetOpen(true)}
              aria-label="Xem thêm"
              aria-expanded={sheetOpen}
              className={cn(
                "flex flex-col items-center justify-center gap-0.5 min-h-[44px] transition-colors",
                "outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-lg",
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

          {/* Mobile bottom nav spacer so content doesn't hide behind nav */}
          <div
            className="md:hidden shrink-0"
            style={{ height: "calc(56px + env(safe-area-inset-bottom, 0px))" }}
            aria-hidden="true"
          />
        </div>
      </div>
    </TooltipProvider>
  );
}