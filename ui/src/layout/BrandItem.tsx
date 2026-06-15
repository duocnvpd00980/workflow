"use client";

import { MoreHorizontal, Edit2, Star, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuSeparator, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export type Brand = {
  id: string;
  name: string;
  website?: string;
  active: boolean;
  researching?: boolean; // task đang chạy nền
};

export function BrandItem({
  brand,
  onSetDefault,
  onEdit,
  onDelete,
}: {
  brand: Brand;
  onSetDefault: (id: string) => void;
  onEdit:       (id: string) => void;
  onDelete:     (id: string) => void;
}) {
  const { id, name, active, researching } = brand;

  return (
    <div className={cn(
      "group relative w-full flex items-center gap-2.5 h-9 px-3 rounded-md text-[13px]",
      "transition-colors duration-100 select-none",
      active
        ? "bg-zinc-100/80 text-zinc-900 font-semibold"
        : "text-zinc-500 font-medium hover:bg-zinc-200/50 hover:text-zinc-700"
    )}>
      {/* Left accent indicator - Linear style */}
      {active && (
        <div className="absolute left-0 top-1.5 bottom-1.5 w-[2.5px] rounded-r-full bg-zinc-900" />
      )}

      {/* Avatar */}
      <span className={cn(
        "h-5 w-5 rounded-[4px] flex items-center justify-center text-[10px] font-bold shrink-0 transition-colors",
        active 
          ? "bg-zinc-900 text-white" 
          : "bg-zinc-200 text-zinc-600 group-hover:bg-zinc-300"
      )}>
        {name.charAt(0).toUpperCase()}
      </span>

      {/* Name */}
      <span className="truncate flex-1 text-left">{name}</span>

      {/* Researching pulse indicator */}
      {researching && (
        <span className={cn(
          "h-1.5 w-1.5 rounded-full shrink-0 animate-pulse",
          active ? "bg-zinc-900/40" : "bg-amber-400"
        )} />
      )}

      {/* ⋮ Dropdown */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            onClick={(e) => e.stopPropagation()}
            className={cn(
              "h-5 w-5 flex items-center justify-center rounded",
              "opacity-0 group-hover:opacity-100 transition-opacity duration-100",
              active
                ? "hover:bg-zinc-200/60 text-zinc-500 hover:text-zinc-900 opacity-100"
                : "hover:bg-zinc-300/60 text-zinc-400 hover:text-zinc-700"
            )}
          >
            <MoreHorizontal className="h-3.5 w-3.5" />
          </button>
        </DropdownMenuTrigger>

        <DropdownMenuContent
          side="right"
          align="start"
          className="w-44 rounded-lg shadow-lg border-zinc-200/80 p-1 z-50"
          onClick={(e) => e.stopPropagation()}
        >
          <DropdownMenuItem
            className="flex items-center gap-2 text-[12.5px] rounded-md cursor-pointer"
            onClick={() => onEdit(id)}
          >
            <Edit2 className="h-3.5 w-3.5 text-zinc-400" />
            Chỉnh sửa
          </DropdownMenuItem>

          <DropdownMenuItem
            className="flex items-center gap-2 text-[12.5px] rounded-md cursor-pointer"
            onClick={() => onSetDefault(id)}
          >
            <Star className="h-3.5 w-3.5 text-zinc-400" />
            Đặt mặc định
          </DropdownMenuItem>

          <DropdownMenuSeparator />

          <DropdownMenuItem
            className="flex items-center gap-2 text-[12.5px] text-red-500 focus:text-red-500 rounded-md cursor-pointer"
            onClick={() => onDelete(id)}
          >
            <Trash2 className="h-3.5 w-3.5" />
            Xóa
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}

// ─────────────────────────────────────────────
// DELETE CONFIRM DIALOG
// ─────────────────────────────────────────────

export function DeleteConfirmDialog({
  open,
  brandName,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  brandName: string;
  onConfirm: () => void;
  onCancel:  () => void;
}) {
  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40 backdrop-blur-sm p-4"
      onClick={onCancel}
    >
      <div
        className="w-full max-w-xs bg-white rounded-2xl shadow-2xl border border-zinc-200/60 p-5"
        onClick={(e) => e.stopPropagation()}
      >
        <p className="text-[14px] font-semibold text-zinc-900">Xóa brand?</p>
        <p className="text-[12.5px] text-zinc-500 mt-1 mb-5">
          <span className="font-medium text-zinc-700">"{brandName}"</span>{" "}
          sẽ bị xóa vĩnh viễn và không thể khôi phục.
        </p>
        <div className="flex gap-2">
          <button
            onClick={onCancel}
            className="flex-1 h-9 rounded-lg border border-zinc-200 text-[13px] font-medium text-zinc-600 hover:bg-zinc-50 transition-colors"
          >
            Hủy
          </button>
          <button
            onClick={onConfirm}
            className="flex-1 h-9 rounded-lg bg-red-600 hover:bg-red-700 text-white text-[13px] font-semibold transition-colors"
          >
            Xóa
          </button>
        </div>
      </div>
    </div>
  );
}