"use client";

import { Bell } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { mockNotifications } from "./mock";

function Badge({ count }: { count: number }) {
  if (count === 0) return null;
  return (
    <span className="absolute -top-1 -right-1 h-4 min-w-4 px-0.5 flex items-center justify-center rounded-full bg-zinc-900 text-white text-[9px] font-bold leading-none">
      {count}
    </span>
  );
}

export function NotificationBell() {
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
            <div
              key={n.id}
              className={cn(
                "flex items-start gap-2.5 px-2 py-2 rounded-lg cursor-pointer transition-colors",
                n.read ? "hover:bg-zinc-50" : "bg-zinc-50 hover:bg-zinc-100"
              )}
            >
              <span className={cn("h-1.5 w-1.5 rounded-full mt-1.5 shrink-0", n.read ? "bg-transparent" : "bg-zinc-900")} />
              <div className="flex-1 min-w-0">
                <p className={cn("text-[12.5px] leading-snug", n.read ? "text-zinc-500" : "text-zinc-800 font-medium")}>
                  {n.text}
                </p>
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