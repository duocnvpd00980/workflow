"use client";

import { Plus, ChevronDown, CheckCircle2, Loader2, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuSeparator, DropdownMenuTrigger, DropdownMenuLabel,
} from "@/components/ui/dropdown-menu";
import { useQuery } from "@tanstack/react-query";
import { useSearch, useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000/api/v1";

type BrandOptionResponse = {
  id: string;
  name: string;
  business_id: string;
  is_default: boolean;
};

type Brand = {
  id: string;
  name: string;
  active: boolean;
};

export function BrandSwitcher() {
  const search = useSearch({ strict: false });
  const navigate = useNavigate();

  const { data: brands = [], isLoading, isError } = useQuery<Brand[]>({
    queryKey: ["brand-voices", "options"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/brand-voices/options`, {
        headers: { accept: "application/json" },
      });
      if (!res.ok) throw new Error("Không thể tải danh sách brand");

      const rawData: BrandOptionResponse[] = await res.json();
      return rawData.map((item) => ({
        id: item.id,
        name: item.name,
        active: item.is_default,
      }));
    },
    placeholderData: (previousData) => previousData,
  });

  useEffect(() => {
  if (!brands.length) return;
  if ((search as Record<string, string>).brand) return;

  const defaultId = brands.find((b) => b.active)?.id ?? brands[0].id;
  navigate({
    search: (prev) => ({ ...prev, brand: defaultId }),
    replace: true,
  } as any);
}, [brands, search, navigate]);

  // Ưu tiên URL param ?brand=<id>, fallback về is_default, rồi phần tử đầu
  const activeBrandId: string | undefined =
    (search as Record<string, string>).brand ??
    brands.find((b) => b.active)?.id ??
    brands[0]?.id;

  const active = brands.find((b) => b.id === activeBrandId) ?? brands[0];

  function selectBrand(id: string) {
    navigate({
      search: (prev) => ({ ...prev, brand: id }),
      replace: true, // không đẩy vào history stack
    }  as any);
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          disabled={isLoading}
          className="flex items-center gap-1.5 h-8 px-2.5 rounded-md border border-zinc-200 bg-white hover:bg-zinc-50 transition-colors text-[12.5px] font-medium text-zinc-700 select-none disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {isLoading ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin text-zinc-400" />
          ) : isError ? (
            <AlertCircle className="h-3.5 w-3.5 text-red-400" />
          ) : (
            <span className="h-4 w-4 rounded-[3px] bg-zinc-900 flex items-center justify-center text-[9px] font-bold text-white shrink-0">
              {active?.name.charAt(0) ?? "?"}
            </span>
          )}

          <span>
            {isLoading
              ? "Đang tải..."
              : isError
                ? "Lỗi tải brand"
                : (active?.name ?? "Chọn brand")}
          </span>

          <ChevronDown className="h-3 w-3 text-zinc-400" />
        </button>
      </DropdownMenuTrigger>

      <DropdownMenuContent align="start" className="w-52 rounded-lg shadow-md border-zinc-200/80 p-1">
        <DropdownMenuLabel className="text-[11px] text-zinc-400 font-semibold uppercase tracking-wider px-2 pb-1">
          Brands
        </DropdownMenuLabel>

        {isError ? (
          <div className="px-2 py-2 text-[12px] text-red-500">
            Không thể tải danh sách brand.
          </div>
        ) : isLoading ? (
          <div className="px-2 py-2 text-[12px] text-zinc-400 flex items-center gap-1.5">
            <Loader2 className="h-3 w-3 animate-spin" /> Đang tải...
          </div>
        ) : brands.length === 0 ? (
          <div className="px-2 py-2 text-[12px] text-zinc-400">
            Chưa có brand nào.
          </div>
        ) : (
          brands.map((b) => {
            const isActive = b.id === activeBrandId;
            return (
              <DropdownMenuItem
                key={b.id}
                onSelect={() => selectBrand(b.id)}
                className={cn(
                  "flex items-center gap-2 text-[13px] rounded-md cursor-pointer",
                  isActive && "font-semibold"
                )}
              >
                <span
                  className={cn(
                    "h-1.5 w-1.5 rounded-full shrink-0",
                    isActive ? "bg-zinc-900" : "bg-zinc-300"
                  )}
                />
                {b.name}
                {isActive && (
                  <CheckCircle2 className="h-3.5 w-3.5 ml-auto text-zinc-500" />
                )}
              </DropdownMenuItem>
            );
          })
        )}

        <DropdownMenuSeparator />
        <DropdownMenuItem className="text-[13px] text-zinc-500 rounded-md cursor-pointer">
          <Plus className="h-3.5 w-3.5 mr-2" /> Thêm brand
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}