"use client";

import { Plus, ChevronDown, CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuSeparator, DropdownMenuTrigger, DropdownMenuLabel,
} from "@/components/ui/dropdown-menu";
import { mockBrands } from "./mock";

export function BrandSwitcher() {
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
          <DropdownMenuItem
            key={b.id}
            className={cn("flex items-center gap-2 text-[13px] rounded-md cursor-pointer", b.active && "font-semibold")}
          >
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