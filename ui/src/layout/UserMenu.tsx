"use client";

import { UserCircle, Settings, LogOut } from "lucide-react";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuSeparator, DropdownMenuTrigger, DropdownMenuLabel,
} from "@/components/ui/dropdown-menu";

export function UserMenu() {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button className="h-7 w-7 rounded-full bg-zinc-200 flex items-center justify-center hover:bg-zinc-300 transition-colors text-[12px] font-semibold text-zinc-700">
          U
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48 rounded-lg shadow-md border-zinc-200/80 p-1">
        <DropdownMenuLabel className="text-[12px] text-zinc-500 font-normal px-2">
          user@example.com
        </DropdownMenuLabel>
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