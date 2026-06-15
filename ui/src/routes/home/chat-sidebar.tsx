"use client"

import { useState, useCallback, useEffect, useRef } from "react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import {
  User, ChevronDown, Sparkles,
  RotateCcw, Bot, StopCircle, Clipboard, Check, X, Send,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { useChatStream } from "@/hooks/useChatStream"
import type { ChatMsg } from "@/hooks/useChatStream"
import { API_BASE, QUICK_PROMPTS } from "./types"

// ─── PROPS ───────────────────────────────────────────────────────────────────

interface ChatSidebarProps {
  /** UUID conversation — phải tạo trước qua POST {api}/conversations */
  conversationId: string
  brandId?: string
  businessId?: string
  isOpen: boolean
  onClose: () => void
  /** Gọi khi user bấm "Áp dụng vào bài" trên 1 kết quả hoàn thiện */
  onApply?: (content: string) => void
  onStreamingChange?: (isStreaming: boolean) => void
}

// ─── CHAT SIDEBAR: Copy Button ───────────────────────────────────────────────

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }
  return (
    <button
      onClick={copy}
      className="opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded hover:bg-muted text-muted-foreground hover:text-foreground"
      title="Copy"
    >
      {copied
        ? <Check className="h-3 w-3 text-emerald-500" />
        : <Clipboard className="h-3 w-3" />
      }
    </button>
  )
}

// ─── CHAT SIDEBAR: Blinking cursor ───────────────────────────────────────────

function StreamingCursor() {
  return (
    <span className="inline-block w-[2px] h-[1em] bg-foreground/70 ml-[1px] align-middle animate-[blink_0.9s_step-end_infinite]" />
  )
}

// ─── CHAT SIDEBAR: Apply button ──────────────────────────────────────────────

function ApplyButton({ content, onApply }: { content: string; onApply: (c: string) => void }) {
  const [applied, setApplied] = useState(false)
  const handleApply = () => {
    onApply(content)
    setApplied(true)
    setTimeout(() => setApplied(false), 2000)
  }
  return (
    <button
      onClick={handleApply}
      className={cn(
        "text-[11px] font-medium px-2.5 py-1 rounded-md transition-all duration-150",
        applied
          ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"
          : "bg-primary/10 text-primary hover:bg-primary/20"
      )}
    >
      {applied ? "✓ Đã áp dụng" : "Áp dụng vào bài"}
    </button>
  )
}

// ─── CHAT SIDEBAR: Chat bubble ────────────────────────────────────────────────

function ChatBubble({
  message,
  isStreaming,
  onApply,
}: {
  message: ChatMsg
  isStreaming: boolean
  onApply?: (content: string) => void
}) {
  const isUser  = message.role === "user"
  const isFinal = message.type === "final_result"
  const isError = message.type === "error"

  return (
    <div className={cn("flex gap-2.5", !isUser ? "items-start" : "items-start flex-row-reverse")}>
      <div className={cn(
        "shrink-0 w-6 h-6 rounded-full flex items-center justify-center mt-0.5",
        !isUser
          ? "bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-400"
          : "bg-muted text-muted-foreground"
      )}>
        {!isUser ? <Bot className="h-3.5 w-3.5" /> : <User className="h-3.5 w-3.5" />}
      </div>

      <div className={cn("group flex flex-col gap-1.5 max-w-[88%]", isUser && "items-end")}>
        <div className={cn(
          "relative rounded-2xl px-3.5 py-2.5 text-[13px] leading-relaxed whitespace-pre-wrap",
          isError
            ? "bg-destructive/10 text-destructive rounded-tl-sm"
            : !isUser
              ? "bg-muted/60 dark:bg-muted/40 text-foreground rounded-tl-sm"
              : "bg-primary text-primary-foreground rounded-tr-sm"
        )}>
          {message.text || (isStreaming && (
            <span className="text-muted-foreground/50 text-[12px]">Đang viết...</span>
          ))}
          {isStreaming && !isUser && <StreamingCursor />}

          {!isUser && message.text && !isStreaming && !isError && (
            <div className="absolute -top-2 right-2">
              <CopyButton text={message.text} />
            </div>
          )}
        </div>

        {isFinal && message.text && onApply && (
          <ApplyButton content={message.text} onApply={onApply} />
        )}
      </div>
    </div>
  )
}

// ─── CHAT SIDEBAR COMPONENT ───────────────────────────────────────────────────

export function ChatSidebar({
  conversationId,
  brandId,
  businessId,
  isOpen,
  onClose,
  onApply,
  onStreamingChange,
}: ChatSidebarProps) {
  const [input, setInput] = useState("")
  const [showScrollBtn, setShowScrollBtn] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const api = API_BASE

  const { messages, status, error, sendMessage, stop, reset } = useChatStream({
    api,
    conversationId,
    brandId,
    businessId,
  })

  const isStreaming = status === "streaming"

  // Chỉ hiển thị node_result cuối cùng + ẩn các node_result trung gian khi đang chạy,
  // để tránh spam UI với từng bước của graph — chỉ giữ message user + final/error.
  // Hook mới chỉ emit "user" | "final_result" | "error" — không còn node_result
  const visibleMessages = messages

  // Notify parent of streaming state
  useEffect(() => {
    onStreamingChange?.(isStreaming)
  }, [isStreaming, onStreamingChange])

  // Auto scroll khi có message mới hoặc đang stream
  useEffect(() => {
    setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 50)
  }, [messages.length, isStreaming])

  // Reset on close
  useEffect(() => {
    if (!isOpen) {
      stop()
      reset()
      setInput("")
    }
  }, [isOpen, stop, reset])

  const handleScroll = useCallback(() => {
    const el = scrollRef.current
    if (!el) return
    setShowScrollBtn(el.scrollHeight - el.scrollTop - el.clientHeight > 80)
  }, [])

  const handleSend = useCallback(async (text: string) => {
    if (!text.trim() || isStreaming) return
    setInput("")
    await sendMessage(text.trim())
  }, [isStreaming, sendMessage])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend(input)
    }
  }

  if (!isOpen) return null

  return (
    <div className="w-[320px] border-l border-border/60 bg-background flex flex-col h-full">
      {/* ── HEADER ── */}
      <div className="shrink-0 flex items-center justify-between px-4 h-12 border-b border-border/60">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-full bg-violet-100 dark:bg-violet-900/40 flex items-center justify-center">
            <Sparkles className="h-3.5 w-3.5 text-violet-600 dark:text-violet-400" />
          </div>
          <span className="text-sm font-semibold">AI Writer</span>
          {isStreaming && (
            <span className="flex items-center gap-1 text-[10px] text-violet-500 font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-violet-500 animate-pulse" />
              đang viết
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          {isStreaming && (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 text-[11px] gap-1 text-muted-foreground hover:text-destructive"
              onClick={stop}
            >
              <StopCircle className="h-3.5 w-3.5" />
              Dừng
            </Button>
          )}
          {visibleMessages.length > 0 && !isStreaming && (
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 text-muted-foreground"
              onClick={reset}
              title="Xóa cuộc trò chuyện"
            >
              <RotateCcw className="h-3.5 w-3.5" />
            </Button>
          )}
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-muted-foreground"
            onClick={onClose}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* ── MESSAGES ── */}
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto px-4 py-4 space-y-4"
      >
        {/* Empty state */}
        {visibleMessages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full gap-4 text-center pb-8">
            <div className="w-10 h-10 rounded-2xl bg-violet-50 dark:bg-violet-900/30 flex items-center justify-center">
              <Sparkles className="h-5 w-5 text-violet-500" />
            </div>
            <div>
              <p className="text-sm font-medium text-foreground">Chỉnh sửa với AI</p>
              <p className="text-[12px] text-muted-foreground mt-1">
                Nhập yêu cầu để AI sửa bài theo ý bạn
              </p>
            </div>
            <div className="w-full space-y-1.5 mt-2">
              {QUICK_PROMPTS.map((p) => (
                <button
                  key={p.label}
                  onClick={() => handleSend(p.label)}
                  disabled={isStreaming}
                  className="w-full text-left flex items-center gap-2.5 px-3 py-2 rounded-xl text-[12.5px] bg-muted/50 hover:bg-muted text-foreground/80 hover:text-foreground transition-colors"
                >
                  <span className="text-base leading-none">{p.icon}</span>
                  {p.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Message list */}
        {visibleMessages.map((msg, idx) => {
          const isLast = idx === visibleMessages.length - 1
          return (
            <ChatBubble
              key={msg.id}
              message={msg}
              isStreaming={isStreaming && isLast && msg.role === "assistant"}
              onApply={onApply}
            />
          )
        })}

        {/* Hook đã inject placeholder assistant message ngay khi bắt đầu stream */}

        {error && (
          <div className="text-[11px] text-destructive text-center">
            ⚠ {error}
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Scroll to bottom */}
      {showScrollBtn && (
        <div className="relative">
          <button
            onClick={() => bottomRef.current?.scrollIntoView({ behavior: "smooth" })}
            className="absolute bottom-2 left-1/2 -translate-x-1/2 flex items-center gap-1 text-[11px] font-medium text-muted-foreground bg-background border border-border/60 rounded-full px-3 py-1 shadow-sm hover:bg-muted transition-colors z-10"
          >
            <ChevronDown className="h-3 w-3" />
            Cuộn xuống
          </button>
        </div>
      )}

      {/* ── INPUT ── */}
      <div className="shrink-0 border-t border-border/60 p-3">
        {visibleMessages.length > 0 && !isStreaming && (
          <div className="flex gap-1.5 mb-2 overflow-x-auto scrollbar-none pb-1">
            {QUICK_PROMPTS.map((p) => (
              <button
                key={p.label}
                onClick={() => handleSend(p.label)}
                className="shrink-0 text-[11px] whitespace-nowrap px-2.5 py-1 rounded-full bg-muted hover:bg-muted/80 text-muted-foreground hover:text-foreground transition-colors"
              >
                {p.icon} {p.label}
              </button>
            ))}
          </div>
        )}

        <div className="flex items-end gap-2 bg-muted/40 border border-border/60 rounded-2xl px-3 py-2 focus-within:border-violet-400/60 focus-within:bg-background transition-all">
          <Textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => {
              setInput(e.target.value)
              e.target.style.height = "auto"
              e.target.style.height = Math.min(e.target.scrollHeight, 120) + "px"
            }}
            onKeyDown={handleKeyDown}
            placeholder="Nhập yêu cầu sửa bài..."
            disabled={isStreaming}
            rows={1}
            className="flex-1 resize-none border-0 bg-transparent p-0 text-[13px] placeholder:text-muted-foreground/60 focus-visible:ring-0 focus-visible:ring-offset-0 min-h-[20px] max-h-[120px] leading-relaxed"
          />
          <Button
            size="icon"
            disabled={!input.trim() || isStreaming}
            onClick={() => handleSend(input)}
            className={cn(
              "h-7 w-7 shrink-0 rounded-xl transition-all",
              input.trim() && !isStreaming
                ? "bg-violet-600 hover:bg-violet-700 text-white shadow-sm"
                : "bg-muted text-muted-foreground cursor-not-allowed"
            )}
          >
            <Send className="h-3.5 w-3.5" />
          </Button>
        </div>
        <p className="text-[10px] text-muted-foreground/60 mt-1.5 text-center">
          Enter để gửi · Shift+Enter xuống dòng
        </p>
      </div>
    </div>
  )
}