"use client"

import { useState, useCallback, useEffect } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { Button } from "@/components/ui/button"
import {
  User, Sparkles, RotateCcw, Bot, X, Send,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { useChatStream } from "@/hooks/useChatStream"
import type { ChatMsg } from "@/hooks/useChatStream"
import { QUICK_PROMPTS } from "./types"

// ─── AI ELEMENTS IMPORTS ─────────────────────────────────────────────────────
import {
  Conversation,
  ConversationContent,
  ConversationEmptyState,
  ConversationScrollButton,
} from "@/components/ai-elements/conversation"
import {
  PromptInput,
  PromptInputTextarea,
  PromptInputSubmit,
  type PromptInputMessage,
} from "@/components/ai-elements/prompt-input"
import { Shimmer } from "@/components/ai-elements/shimmer"
import { Suggestion, Suggestions } from "@/components/ai-elements/suggestion"
import {
  CodeBlock,
  CodeBlockHeader,
  CodeBlockTitle,
  CodeBlockFilename,
  CodeBlockActions,
  CodeBlockCopyButton,
} from "@/components/ai-elements/code-block"

// ─── MARKDOWN RENDERER ─────────────────────────────────────────────────────────
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { API_BASE } from "@/config"

/** Component render markdown với style đẹp cho chat bubble */
function MarkdownContent({ content, className }: { content: string; className?: string }) {
  return (
    <div className={cn("prose prose-sm dark:prose-invert max-w-none text-left", className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // Override để style phù hợp với chat bubble nhỏ
          h1: ({ children }) => <h1 className="text-base font-bold mt-3 mb-2">{children}</h1>,
          h2: ({ children }) => <h2 className="text-sm font-bold mt-2 mb-1.5">{children}</h2>,
          h3: ({ children }) => <h3 className="text-[13px] font-bold mt-2 mb-1">{children}</h3>,
          p: ({ children }) => <p className="mb-1.5 last:mb-0 leading-relaxed">{children}</p>,
          ul: ({ children }) => <ul className="list-disc pl-4 mb-1.5 space-y-0.5">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal pl-4 mb-1.5 space-y-0.5">{children}</ol>,
          li: ({ children }) => <li className="leading-relaxed">{children}</li>,
          code: ({ children, className }) => {
            const isInline = !className
            if (isInline) {
              return <code className="bg-muted px-1 py-0.5 rounded text-[11px] font-mono">{children}</code>
            }
            // Code block sẽ được xử lý riêng bởi ChatMessage
            return <>{children}</>
          },
          strong: ({ children }) => <strong className="font-semibold text-foreground">{children}</strong>,
          em: ({ children }) => <em className="italic">{children}</em>,
          a: ({ children, href }) => (
            <a href={href} className="text-violet-600 underline hover:text-violet-700" target="_blank" rel="noopener noreferrer">
              {children}
            </a>
          ),
          blockquote: ({ children }) => (
            <blockquote className="border-l-2 border-violet-300 pl-3 italic text-muted-foreground my-1.5">
              {children}
            </blockquote>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}

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

// ─── CHAT SIDEBAR: Streaming Indicator ───────────────────────────────────────

function StreamingIndicator() {
  return (
    <div className="flex items-center gap-2 text-muted-foreground/70">
      <Shimmer as="span" className="text-[12px]">
        Đang viết
      </Shimmer>
    </div>
  )
}

// ─── CHAT SIDEBAR: Message Renderer ──────────────────────────────────────────

function ChatMessage({
  message,
  isStreaming,
  isLast,
  onApply,
}: {
  message: ChatMsg
  isStreaming: boolean
  isLast: boolean
  onApply?: (content: string) => void
}) {
  const isUser = message.role === "user"
  const isFinal = message.type === "final_result"
  const isError = message.type === "error"

  // Detect code block trong markdown
  const codeBlockRegex = /```(\w+)?\n([\s\S]*?)```/
  const hasCodeBlock = !isUser && codeBlockRegex.test(message.text || "")

  // Extract code blocks nếu có
  const renderContent = () => {
    if (!message.text) return null

    // Nếu là user hoặc error → hiển thị plain text
    if (isUser || isError) {
      return <div className="whitespace-pre-wrap text-left">{message.text}</div>
    }

    // Nếu có code block → tách riêng
    if (hasCodeBlock) {
      const parts = message.text.split(/(```(?:\w+)?\n[\s\S]*?```)/)
      return (
        <div className="space-y-2">
          {parts.map((part, i) => {
            const match = part.match(/```(\w+)?\n([\s\S]*?)```/)
            if (match) {
              const lang = match[1] || "typescript"
              const code = match[2].trim()
              return (
                <div key={i} className="-mx-1">
                  <CodeBlock code={code} language="typescript">
                    <CodeBlockHeader>
                      <CodeBlockTitle>
                        <CodeBlockFilename>generated.{lang}</CodeBlockFilename>
                      </CodeBlockTitle>
                      <CodeBlockActions>
                        <CodeBlockCopyButton />
                      </CodeBlockActions>
                    </CodeBlockHeader>
                  </CodeBlock>
                </div>
              )
            }
            // Render phần text còn lại bằng Markdown
            if (part.trim()) {
              return <MarkdownContent key={i} content={part} />
            }
            return null
          })}
        </div>
      )
    }

    // Mặc định: render Markdown
    return <MarkdownContent content={message.text} />
  }

  return (
    <div className={cn("flex gap-2.5", !isUser ? "items-start" : "items-start flex-row-reverse")}>
      {/* Avatar */}
      <div className={cn(
        "shrink-0 w-6 h-6 rounded-full flex items-center justify-center mt-0.5",
        !isUser
          ? "bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-400"
          : "bg-muted text-muted-foreground"
      )}>
        {!isUser ? <Bot className="h-3.5 w-3.5" /> : <User className="h-3.5 w-3.5" />}
      </div>

      {/* Content */}
      <div className={cn("group flex flex-col gap-1.5 max-w-[88%]", isUser && "items-end")}>
        {/* Bubble */}
        <div className={cn(
          "relative rounded-2xl px-3.5 py-2.5 text-[13px] leading-relaxed",
          isError
            ? "bg-destructive/10 text-destructive rounded-tl-sm"
            : !isUser
              ? "bg-muted/60 dark:bg-muted/40 text-foreground rounded-tl-sm"
              : "bg-primary text-primary-foreground rounded-tr-sm"
        )}>
          {renderContent()}

          {/* Streaming indicator */}
          {isStreaming && isLast && !isUser && !message.text && (
            <StreamingIndicator />
          )}
          {isStreaming && isLast && !isUser && message.text && (
            <span className="inline-block w-[2px] h-[1em] bg-foreground/60 ml-[1px] align-middle animate-[blink_0.9s_step-end_infinite]" />
          )}
        </div>

        {/* Apply button cho final result */}
        {isFinal && message.text && onApply && (
          <ApplyButton content={message.text} onApply={onApply} />
        )}
      </div>
    </div>
  )
}

// ─── CHAT SIDEBAR COMPONENT ─────────────────────────────────────────────────

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
  const [hasHydrated, setHasHydrated] = useState(false)
  const api = API_BASE
  const queryClient = useQueryClient()

  const { messages, status, error, sendMessage, stop, reset, hydrate } = useChatStream({
    api,
    conversationId,
    brandId,
    businessId,
  })

  const isStreaming = status === "streaming"

  // Load history
  const { data: historyData } = useQuery({
    queryKey: ["chat-history", conversationId],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/chat/conversations/${conversationId}`)
      if (!res.ok) throw new Error("Không load được lịch sử chat")
      return res.json() as Promise<{ 
        messages: { id: string; role: string; content: string }[] 
      }>
    },
    staleTime: 0,
    enabled: !!conversationId && isOpen,
    refetchOnMount: "always",
    refetchOnWindowFocus: true,
  })

  // HYDRATE: Chạy khi có dữ liệu từ BE
  useEffect(() => {
    if (!isOpen || !conversationId) return
    
    if (historyData?.messages && historyData.messages.length > 0) {
      hydrate(historyData.messages)
      setHasHydrated(true)
    }
  }, [historyData?.messages, conversationId, isOpen, hydrate])

  // Invalidate query khi conversationId thay đổi - KHÔNG reset
  useEffect(() => {
    if (isOpen && conversationId) {
      queryClient.invalidateQueries({ queryKey: ["chat-history", conversationId] })
    }
  }, [conversationId, isOpen, queryClient])

  // Reset CHỈ khi đóng sidebar
  useEffect(() => {
    if (!isOpen) {
      stop()
      reset()
      setInput("")
    }
  }, [isOpen, stop, reset])

  useEffect(() => {
    onStreamingChange?.(isStreaming)
  }, [isStreaming, onStreamingChange])

  // Handle submit qua PromptInput
  const handleSubmit = useCallback((message: PromptInputMessage) => {
    if (!message.text?.trim() || isStreaming) return
    setInput("")
    sendMessage(message.text.trim())
  }, [isStreaming, sendMessage])

  // Handle suggestion click
  const handleSuggestionClick = useCallback((suggestion: string) => {
    if (isStreaming) return
    sendMessage(suggestion)
  }, [isStreaming, sendMessage])

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
              <span className="w-3.5 h-3.5 flex items-center justify-center">⏹</span>
              Dừng
            </Button>
          )}
          {messages.length > 0 && !isStreaming && (
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

      {/* ── CONVERSATION ── */}
      <Conversation className="flex-1 min-h-0">
        <ConversationContent className="px-4 py-4 space-y-4">
          {messages.length === 0 && (
            <ConversationEmptyState
              icon={
                <div className="w-10 h-10 rounded-2xl bg-violet-50 dark:bg-violet-900/30 flex items-center justify-center">
                  <Sparkles className="h-5 w-5 text-violet-500" />
                </div>
              }
              title="Chỉnh sửa với AI"
              description="Nhập yêu cầu để AI sửa bài theo ý bạn"
            />
          )}

          {messages.map((msg, idx) => {
            const isLast = idx === messages.length - 1
            return (
              <ChatMessage
                key={msg.id}
                message={msg}
                isStreaming={isStreaming}
                isLast={isLast}
                onApply={onApply}
              />
            )
          })}

          {error && (
            <div className="text-[11px] text-destructive text-left">
              ⚠ {error}
            </div>
          )}
        </ConversationContent>
        
        <ConversationScrollButton />
      </Conversation>

      {/* ── PROMPT INPUT ── */}
      <div className="shrink-0 border-t border-border/60 p-3">
        {messages.length === 0 && !isStreaming && (
          <Suggestions className="mb-2">
            {QUICK_PROMPTS.map((p) => (
              <Suggestion
                key={p.label}
                suggestion={p.label}
                onClick={handleSuggestionClick}
                className="text-[11px]"
              >
                <span className="mr-1">{p.icon}</span>
                {p.label}
              </Suggestion>
            ))}
          </Suggestions>
        )}

        <PromptInput
          onSubmit={handleSubmit}
          className="w-full"
        >
          <div className="flex items-end gap-2 bg-muted/40 border border-border/60 rounded-2xl px-3 py-2 focus-within:border-violet-400/60 focus-within:bg-background transition-all">
            <PromptInputTextarea
              value={input}
              onChange={(e) => setInput(e.currentTarget.value)}
              placeholder="Nhập yêu cầu sửa bài..."
              disabled={isStreaming}
              rows={1}
              className="flex-1 resize-none border-0 bg-transparent p-0 text-[13px] placeholder:text-muted-foreground/60 focus-visible:ring-0 focus-visible:ring-offset-0 min-h-[20px] max-h-[120px] leading-relaxed"
            />
            <PromptInputSubmit
              disabled={!input.trim() || isStreaming}
              status={isStreaming ? "streaming" : "ready"}
              className={cn(
                "h-7 w-7 shrink-0 rounded-xl transition-all flex items-center justify-center",
                input.trim() && !isStreaming
                  ? "bg-violet-600 hover:bg-violet-700 text-white shadow-sm"
                  : "bg-muted text-muted-foreground cursor-not-allowed"
              )}
            >
              <Send className="h-3.5 w-3.5" />
            </PromptInputSubmit>
          </div>
        </PromptInput>
        
        <p className="text-[10px] text-muted-foreground/60 mt-1.5 text-center">
          Enter để gửi · Shift+Enter xuống dòng
        </p>
      </div>
    </div>
  )
}