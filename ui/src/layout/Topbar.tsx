"use client";

import { useState, useEffect } from "react";
import { Menu, Search, Plus, ChevronDown } from "lucide-react";
import { BrandSwitcher } from "./BrandSwitcher";
import { TaskBell } from "./TaskBell";
import { NotificationBell } from "./NotificationBell";
import { UserMenu } from "./UserMenu";
import { CommandPalette } from "./CommandPalette";
import { CreateModal } from "./CreateContentModal";

interface Props {
  onMenuClick?: () => void;
}

export function Topbar({ onMenuClick }: Props) {
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);

  // ⌘K / Ctrl+K global shortcut
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setPaletteOpen(true);
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, []);

  return (
    <>
      <header className="h-14 px-2 md:px-4 flex items-center justify-between shrink-0 border-b border-zinc-200/50 bg-white select-none gap-4">

       <div className="flex items-center gap-2.5">
         <div className="flex items-center gap-2.5 shrink-0">
          <button
            className="md:hidden h-8 w-8 rounded-md flex items-center justify-center text-zinc-500 hover:bg-zinc-100 transition-colors"
            onClick={onMenuClick}
          >
            <Menu className="h-4 w-4" />
          </button>
          <BrandSwitcher />
        </div>

        <div className="flex-1 flex justify-center">
          <button
            onClick={() => setPaletteOpen(true)}
            className="hidden md:flex w-full max-w-md items-center gap-2.5 h-8 px-3.5 rounded-lg border border-zinc-200 bg-zinc-50 hover:bg-zinc-100 hover:border-zinc-300 transition-all duration-150 text-left"
          >
            <Search className="h-3.5 w-3.5 text-zinc-400 shrink-0" />
            <span className="text-[12.5px] text-zinc-400 flex-1">Tìm kiếm content, brand, task...</span>
            <kbd className="hidden sm:inline-flex items-center text-[10px] text-zinc-300 font-mono border border-zinc-200 rounded px-1 py-0.5 bg-white leading-none">
              ⌘K
            </kbd>
          </button>
          <button
            onClick={() => setPaletteOpen(true)}
            className="md:hidden h-8 w-8 flex items-center justify-center rounded-lg text-zinc-500 hover:bg-zinc-100 transition-colors"
          >
            <Search className="h-4 w-4" />
          </button>
        </div>
       </div>

        {/* RIGHT: notifications + task + create + user */}
        <div className="flex items-center gap-1.5 shrink-0">
          <NotificationBell />
          <TaskBell />

          <div className="w-px h-4 bg-zinc-200 mx-0.5" />

          {/* + Tạo mới button — opens CreateModal */}
          <button
            onClick={() => setCreateOpen(true)}
            className="hidden md:flex items-center gap-1.5 h-8 px-3 rounded-lg bg-zinc-900 hover:bg-zinc-700 text-white text-[12px] font-medium transition-colors"
          >
            <Plus className="h-3.5 w-3.5" strokeWidth={2.5} />
            <span>Tạo mới</span>
            <ChevronDown className="h-3 w-3 opacity-60" />
          </button>

          {/* Mobile: icon-only create button */}
          <button
            onClick={() => setCreateOpen(true)}
            className="md:hidden h-8 w-8 flex items-center justify-center rounded-lg bg-zinc-900 hover:bg-zinc-700 text-white transition-colors"
          >
            <Plus className="h-4 w-4" strokeWidth={2.5} />
          </button>

          <div className="w-px h-4 bg-zinc-200 mx-0.5" />
          <UserMenu />
        </div>
      </header>

      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
      <CreateModal open={createOpen} onClose={() => setCreateOpen(false)} />
    </>
  );
}