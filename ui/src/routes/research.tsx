import { createFileRoute, useSearch, useNavigate } from '@tanstack/react-router'
import React from 'react'
import { useState, useRef, useEffect, useCallback, useReducer } from 'react'
import ReactMarkdown from 'react-markdown'

export const Route = createFileRoute('/research')({
  component: HotelResearchPage,
  validateSearch: (search: Record<string, unknown>) => ({
    task_id: (search.task_id as string) || undefined,
  }),
})

const BASE_API_URL = 'http://localhost:8000/api/v1/hotel-research'

// ── Types ─────────────────────────────────────────────────────────
interface ProgressEvent {
  node: string
  label: string
  status: string
  message: string
  progress: number
  data: Record<string, unknown>
}

interface TaskStatus {
  task_id: string
  status: 'running' | 'completed' | 'failed' | 'queued'
  total_events: number
}

interface ResultItem {
  id: number
  task_id: string
  business_name: string
  created_at: string
  competitors_count: number
  has_analysis: boolean
  has_report: boolean
}

interface FinalResult {
  task_id: string
  status: string
  result: {
    business_name?: string
    address?: string
    competitor_analysis?: string
    final_report?: string
    competitors_clean?: string[]
    errors?: string[]
    [key: string]: unknown
  }
}

// ── Pipeline Steps (Marketing-friendly) ───────────────────────────
const PIPELINE_STEPS = [
  { node: 'screenshots',       label: 'Tìm kiếm đối thủ trên Google & Booking',  icon: '🔍', pct: 10  },
  { node: 'vision_extract',    label: 'Phân tích hình ảnh & trích xuất dữ liệu', icon: '👁️', pct: 25  },
  { node: 'competitor_branch', label: 'Phân tích chiến lược đối thủ',          icon: '🏆', pct: 50  },
  { node: 'social_branch',     label: 'Thu thập dữ liệu mạng xã hội',           icon: '📱', pct: 65  },
  { node: 'merge_data',        label: 'Tổng hợp & làm sạch dữ liệu',           icon: '🔄', pct: 75  },
  { node: 'final_report',      label: 'Tạo báo cáo chiến lược marketing',      icon: '📝', pct: 85  },
  { node: 'cleanup',           label: 'Hoàn tất & lưu trữ kết quả',            icon: '✅', pct: 100 },
]

// ── Theme ───────────────────────────────────────────────────────
const theme = {
  bg: '#f8fafc',
  surface: '#ffffff',
  surfaceHover: '#f1f5f9',
  border: '#e2e8f0',
  text: '#0f172a',
  textMuted: '#475569',
  textDim: '#94a3b8',
  primary: '#3b82f6',
  primaryLight: '#eff6ff',
  primaryDark: '#1d4ed8',
  success: '#10b981',
  successLight: '#ecfdf5',
  warning: '#f59e0b',
  danger: '#ef4444',
  purple: '#8b5cf6',
  orange: '#f97316',
  gradient: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  font: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  mono: '"SF Mono", "Fira Code", monospace',
}

// ── Event Buffer (Performance) ──────────────────────────────────
interface EventBuffer {
  events: ProgressEvent[]
  lastUpdate: number
}

function useEventBuffer(throttleMs = 100) {
  const bufferRef = useRef<EventBuffer>({ events: [], lastUpdate: 0 })
  const [events, setEvents] = useState<ProgressEvent[]>([])
  const rafRef = useRef<number | null>(null)

  const flush = useCallback(() => {
    const now = Date.now()
    if (now - bufferRef.current.lastUpdate >= throttleMs) {
      setEvents([...bufferRef.current.events])
      bufferRef.current.lastUpdate = now
      rafRef.current = null
    } else {
      rafRef.current = requestAnimationFrame(flush)
    }
  }, [throttleMs])

  const append = useCallback((event: ProgressEvent) => {
    const isDup = bufferRef.current.events.some(
      e => e.node === event.node && e.status === event.status && e.progress === event.progress && e.message === event.message
    )
    if (!isDup) {
      bufferRef.current.events = [...bufferRef.current.events, event]
      if (!rafRef.current) {
        rafRef.current = requestAnimationFrame(flush)
      }
    }
  }, [flush])

  const clear = useCallback(() => {
    bufferRef.current = { events: [], lastUpdate: 0 }
    setEvents([])
    if (rafRef.current) cancelAnimationFrame(rafRef.current)
  }, [])

  useEffect(() => () => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current)
  }, [])

  return { events, append, clear, raw: bufferRef.current.events }
}

// ── Retry Fetch ─────────────────────────────────────────────────
async function fetchWithRetry(url: string, options: RequestInit, retries = 3, delay = 1000): Promise<Response> {
  let lastError: Error | null = null
  for (let i = 0; i < retries; i++) {
    try {
      const res = await fetch(url, options)
      if (res.ok || res.status === 404) return res
      if (res.status >= 500) throw new Error(`Server error ${res.status}`)
      return res
    } catch (e) {
      lastError = e instanceof Error ? e : new Error(String(e))
      if (i < retries - 1) await new Promise(r => setTimeout(r, delay * Math.pow(2, i)))
    }
  }
  throw lastError || new Error('Fetch failed after retries')
}

// ── Components ──────────────────────────────────────────────────

function Card({ children, style, className }: { children: React.ReactNode; style?: React.CSSProperties; className?: string }) {
  return (
    <div className={className} style={{
      background: theme.surface, borderRadius: 16, border: `1px solid ${theme.border}`,
      boxShadow: '0 1px 3px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.02)', overflow: 'hidden', ...style,
    }}>
      {children}
    </div>
  )
}

function Button({ children, onClick, variant = 'primary', size = 'md', disabled, icon, style, ariaLabel }: {
  children: React.ReactNode; onClick?: () => void; variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg'; disabled?: boolean; icon?: string; style?: React.CSSProperties; ariaLabel?: string
}) {
  const variants = {
    primary: { bg: theme.primary, color: '#fff', hover: theme.primaryDark, shadow: '0 4px 14px rgba(59,130,246,0.35)' },
    secondary: { bg: theme.surface, color: theme.text, hover: theme.surfaceHover, shadow: '0 1px 3px rgba(0,0,0,0.08)' },
    ghost: { bg: 'transparent', color: theme.textMuted, hover: '#f1f5f9', shadow: 'none' },
    danger: { bg: theme.danger, color: '#fff', hover: '#dc2626', shadow: '0 4px 14px rgba(239,68,68,0.35)' },
  }
  const sizes = { sm: '8px 14px', md: '12px 24px', lg: '14px 32px' }
  const v = variants[variant]
  const [hovered, setHovered] = useState(false)
  return (
    <button
      onClick={onClick} disabled={disabled} aria-label={ariaLabel}
      onMouseEnter={() => setHovered(true)} onMouseLeave={() => setHovered(false)}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 8, padding: sizes[size], borderRadius: 12,
        border: variant === 'secondary' ? `1px solid ${theme.border}` : 'none',
        background: disabled ? '#e2e8f0' : hovered ? v.hover : v.bg,
        color: disabled ? theme.textDim : v.color, fontWeight: 600, fontSize: size === 'sm' ? 13 : 14,
        cursor: disabled ? 'not-allowed' : 'pointer', transition: 'all 0.2s ease', fontFamily: theme.font,
        boxShadow: disabled ? 'none' : v.shadow, ...style,
      }}
    >
      {icon && <span style={{ fontSize: size === 'sm' ? 14 : 16 }}>{icon}</span>}
      {children}
    </button>
  )
}

function Input({ label, value, onChange, disabled, placeholder, type = 'text' }: {
  label: string; value: string; onChange: (v: string) => void; disabled?: boolean; placeholder?: string; type?: string
}) {
  return (
    <label style={{ display: 'block' }}>
      <span style={{ display: 'block', fontSize: 12, fontWeight: 600, color: theme.textMuted, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>
        {label}
      </span>
      <input
        type={type} value={value} placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)} disabled={disabled}
        style={{
          width: '100%', padding: '12px 16px', background: theme.surface, border: `1px solid ${theme.border}`,
          borderRadius: 12, color: theme.text, fontFamily: theme.font, fontSize: 14, outline: 'none',
          transition: 'all 0.2s', boxSizing: 'border-box',
        }}
        onFocus={(e) => { e.currentTarget.style.borderColor = theme.primary; e.currentTarget.style.boxShadow = '0 0 0 3px rgba(59,130,246,0.1)' }}
        onBlur={(e) => { e.currentTarget.style.borderColor = theme.border; e.currentTarget.style.boxShadow = 'none' }}
      />
    </label>
  )
}

function Badge({ children, color = 'blue' }: { children: React.ReactNode; color?: 'blue' | 'green' | 'orange' | 'purple' | 'red' | 'gray' }) {
  const colors = {
    blue: { bg: '#eff6ff', text: '#2563eb', border: '#bfdbfe' },
    green: { bg: '#ecfdf5', text: '#059669', border: '#a7f3d0' },
    orange: { bg: '#fff7ed', text: '#ea580c', border: '#fed7aa' },
    purple: { bg: '#f5f3ff', text: '#7c3aed', border: '#ddd6fe' },
    red: { bg: '#fef2f2', text: '#dc2626', border: '#fecaca' },
    gray: { bg: '#f8fafc', text: '#64748b', border: '#e2e8f0' },
  }
  const c = colors[color]
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', padding: '4px 12px', borderRadius: 20,
      fontSize: 12, fontWeight: 600, background: c.bg, color: c.text, border: `1px solid ${c.border}`,
    }}>
      {children}
    </span>
  )
}

function ProgressRing({ value, size = 120, stroke = 8 }: { value: number; size?: number; stroke?: number }) {
  const radius = (size - stroke) / 2
  const circumference = radius * 2 * Math.PI
  const offset = circumference - (value / 100) * circumference
  return (
    <div style={{ position: 'relative', width: size, height: size }} role="progressbar" aria-valuenow={value} aria-valuemin={0} aria-valuemax={100}>
      <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
        <circle cx={size/2} cy={size/2} r={radius} fill="none" stroke={theme.border} strokeWidth={stroke} />
        <circle cx={size/2} cy={size/2} r={radius} fill="none"
          stroke={value === 100 ? theme.success : theme.primary}
          strokeWidth={stroke} strokeLinecap="round"
          strokeDasharray={circumference} strokeDashoffset={offset}
          style={{ transition: 'stroke-dashoffset 0.5s ease, stroke 0.3s ease' }}
        />
      </svg>
      <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }}>
        <span style={{ fontSize: 28, fontWeight: 800, color: value === 100 ? theme.success : theme.text }}>{value}%</span>
        <span style={{ fontSize: 11, color: theme.textDim, fontWeight: 500 }}>{value === 100 ? 'Hoàn tất' : 'Đang chạy'}</span>
      </div>
    </div>
  )
}

function StepTimeline({ events, running }: { events: ProgressEvent[]; running: boolean }) {
  const doneNodes = new Set(events.filter(e => e.status === 'done' || e.status === 'finished' || e.status === 'success').map(e => e.node))
  const lastNode = events.length > 0 ? events[events.length - 1].node : null

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }} role="list" aria-label="Pipeline steps">
      {PIPELINE_STEPS.map((step, idx) => {
        const isDone = doneNodes.has(step.node)
        const isActive = lastNode === step.node && running
        const isPassed = isDone || (PIPELINE_STEPS.findIndex(s => s.node === lastNode) > idx && running)

        return (
          <div key={step.node} style={{ display: 'flex', gap: 16, position: 'relative' }} role="listitem">
            {idx < PIPELINE_STEPS.length - 1 && (
              <div style={{
                position: 'absolute', left: 19, top: 40, bottom: -8, width: 2,
                background: isPassed ? (isDone ? theme.success : theme.primary) : theme.border,
                transition: 'background 0.3s',
              }} aria-hidden="true" />
            )}
            <div style={{
              width: 40, height: 40, borderRadius: '50%', flexShrink: 0,
              display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18,
              background: isDone ? theme.successLight : isActive ? theme.primaryLight : theme.bg,
              border: `2px solid ${isDone ? theme.success : isActive ? theme.primary : theme.border}`,
              transition: 'all 0.3s', zIndex: 1,
            }} aria-label={isDone ? 'Completed' : isActive ? 'In progress' : 'Pending'}>
              {isDone ? '✓' : isActive ? (
                <span style={{ animation: 'spin 1s linear infinite', display: 'inline-block' }}>⟳</span>
              ) : step.icon}
            </div>
            <div style={{ paddingBottom: 20, flex: 1 }}>
              <div style={{
                fontWeight: isActive ? 700 : isPassed ? 600 : 500, fontSize: 14,
                color: isActive ? theme.primary : isPassed ? theme.text : theme.textDim,
                transition: 'color 0.3s',
              }}>
                {step.label}
              </div>
              <div style={{ fontSize: 12, color: theme.textDim, marginTop: 2 }}>
                {isDone ? 'Hoàn thành' : isActive ? 'Đang xử lý...' : 'Chờ'}
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

function ReportCard({ title, icon, color, children }: { title: string; icon: string; color: string; children: React.ReactNode }) {
  return (
    <Card style={{ borderTop: `4px solid ${color}` }}>
      <div style={{ padding: '24px 28px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
          <span style={{ fontSize: 24 }}>{icon}</span>
          <span style={{ fontWeight: 700, fontSize: 18, color: theme.text }}>{title}</span>
        </div>
        <div style={{ fontSize: 15, lineHeight: 1.8, color: '#334155' }}>
          {children}
        </div>
      </div>
    </Card>
  )
}

function Toast({ message, type = 'info', onClose }: { message: string; type?: 'info' | 'success' | 'warning'; onClose: () => void }) {
  const colors = {
    info: { bg: '#eff6ff', border: '#bfdbfe', text: '#1e40af' },
    success: { bg: '#ecfdf5', border: '#a7f3d0', text: '#065f46' },
    warning: { bg: '#fffbeb', border: '#fcd34d', text: '#92400e' },
  }
  const c = colors[type]
  useEffect(() => {
    const t = setTimeout(onClose, 5000)
    return () => clearTimeout(t)
  }, [onClose])
  return (
    <div style={{
      position: 'fixed', top: 80, right: 24, zIndex: 100,
      background: c.bg, border: `1px solid ${c.border}`, borderRadius: 12,
      padding: '14px 20px', color: c.text, fontSize: 14, fontWeight: 500,
      boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)', maxWidth: 400,
      display: 'flex', alignItems: 'center', gap: 10,
    }} role="alert" aria-live="polite">
      <span>{type === 'info' ? 'ℹ️' : type === 'success' ? '✅' : '⚠️'}</span>
      {message}
      <button onClick={onClose} style={{ marginLeft: 8, background: 'none', border: 'none', cursor: 'pointer', fontSize: 16, color: c.text }} aria-label="Close notification">✕</button>
    </div>
  )
}

function Skeleton({ width, height = 16 }: { width?: string | number; height?: number }) {
  return (
    <div style={{
      width: width ?? '100%', height,
      background: 'linear-gradient(90deg, #e2e8f0 25%, #f1f5f9 50%, #e2e8f0 75%)',
      backgroundSize: '200% 100%', borderRadius: 8,
      animation: 'shimmer 1.5s infinite',
    }} aria-hidden="true" />
  )
}

// ── Error Boundary ──────────────────────────────────────────────

class ErrorBoundary extends React.Component<{ children: React.ReactNode }, { hasError: boolean; error: string }> {
  constructor(props: { children: React.ReactNode }) {
    super(props)
    this.state = { hasError: false, error: '' }
  }
  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error: error.message }
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: theme.bg, padding: 24 }}>
          <Card style={{ maxWidth: 500, padding: 40, textAlign: 'center' }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>💥</div>
            <h2 style={{ fontSize: 20, fontWeight: 700, color: theme.text, margin: '0 0 12px' }}>Đã xảy ra lỗi</h2>
            <p style={{ color: theme.textMuted, fontSize: 14, marginBottom: 20 }}>{this.state.error}</p>
            <Button onClick={() => window.location.reload()} icon="🔄">Tải lại trang</Button>
          </Card>
        </div>
      )
    }
    return this.props.children
  }
}

// ── Main Component ──────────────────────────────────────────────

function HotelResearchPage() {
  const search = useSearch({ from: '/research' })
  const navigate = useNavigate({ from: '/research' })
  const urlTaskId = search.task_id

  // ── Form State ─────────────────────────────────────────────
  const [form, setForm] = useState({
    business_name: 'Sontras Sea Hotel',
    address: '41 Hoàng Sa Road, Son Tra District, Da Nang, Vietnam',
    industry: 'Hotel / Beachfront Resort / Hospitality',
  })

  // ── Event Buffer (Performance fix) ──────────────────────────
  const { events, append: appendEvent, clear: clearEvents, raw: rawEvents } = useEventBuffer(100)

  // ── Stream State ───────────────────────────────────────────
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null)
  const isResumingRef = useRef(false)

  // ── Resume State ────────────────────────────────────────────
  const [resuming, setResuming] = useState(false)
  const [resumeMessage, setResumeMessage] = useState<string | null>(null)

  // ── View State ─────────────────────────────────────────────
  const [view, setView] = useState<'home' | 'running' | 'report' | 'history'>('home')

  // ── Results State ──────────────────────────────────────────
  const [results, setResults] = useState<ResultItem[]>([])
  const [resultsLoading, setResultsLoading] = useState(false)

  // ── Report State ───────────────────────────────────────────
  const [selectedReport, setSelectedReport] = useState<FinalResult['result'] | null>(null)
  const [reportLoading, setReportLoading] = useState(false)
  const [reportError, setReportError] = useState<string | null>(null)

  // ── Toast ───────────────────────────────────────────────────
  const [toast, setToast] = useState<{ message: string; type: 'info' | 'success' | 'warning' } | null>(null)

  // ════════════════════════════════════════════════════════════
  //  CORE API FUNCTIONS
  // ════════════════════════════════════════════════════════════

  // ── Check Status ────────────────────────────────────────────
  const checkStatus = useCallback(async (taskId: string): Promise<TaskStatus | null> => {
    try {
      const res = await fetchWithRetry(`${BASE_API_URL}/status/${taskId}`, {}, 3, 500)
      if (!res.ok) return null
      return await res.json()
    } catch { return null }
  }, [])

  // ── Fetch Result ────────────────────────────────────────────
  const fetchResult = useCallback(async (taskId: string): Promise<FinalResult | null> => {
    try {
      const res = await fetchWithRetry(`${BASE_API_URL}/result/${taskId}`, {}, 3, 500)
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || `Lỗi ${res.status}`)
      }
      return await res.json()
    } catch (e) {
      if (e instanceof Error) throw e
      return null
    }
  }, [])

  // ── SSE Stream ──────────────────────────────────────────────
  const connectToStream = useCallback(async (taskId: string) => {
    if (abortRef.current) abortRef.current.abort()
    setRunning(true)
    setError(null)
    setView('running')
    setCurrentTaskId(taskId)
    setResumeMessage(null)
    abortRef.current = new AbortController()

    // Save to localStorage + URL (via TanStack Router)
    localStorage.setItem('active_research_task_id', taskId)
    navigate({ search: { task_id: taskId } as any})

    try {
      const res = await fetchWithRetry(`${BASE_API_URL}/stream/${taskId}`, {
        method: 'GET', signal: abortRef.current.signal,
        headers: { Accept: 'text/event-stream' },
      }, 2, 500)

      if (res.status === 404) {
        localStorage.removeItem('active_research_task_id')
        throw new Error('Phiên làm việc đã hết hạn. Vui lòng bắt đầu lại.')
      }
      if (!res.ok) throw new Error('Không thể kết nối đến server.')
      if (!res.body) throw new Error('Lỗi kết nối stream.')

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''

        for (const line of lines) {
          const trimmed = line.trim()
          if (!trimmed.startsWith('data: ')) continue
          try {
            const parsed: ProgressEvent = JSON.parse(trimmed.slice(5).trim())
            const meta = PIPELINE_STEPS.find(s => s.node === parsed.node)
            const enriched = { ...parsed, label: meta?.label || parsed.node, progress: meta?.pct || parsed.progress }
            appendEvent(enriched)

            if (parsed.node === 'FINISHED') {
              localStorage.removeItem('active_research_task_id')
              setTimeout(async () => {
                setRunning(false)
                try {
                  const result = await fetchResult(taskId)
                  if (result) {
                    setSelectedReport(result.result)
                    setView('report')
                    setToast({ message: 'Nghiên cứu hoàn tất! Báo cáo đã sẵn sàng.', type: 'success' })
                  }
                } catch (e) {
                  if (e instanceof Error) setError(e.message)
                }
              }, 600)
            }
            if (parsed.node === 'ERROR') {
              localStorage.removeItem('active_research_task_id')
              setTimeout(() => { setRunning(false); setError(parsed.message); setView('home') }, 600)
            }
          } catch { /* ignore malformed */ }
        }
      }
    } catch (e: unknown) {
      if (e instanceof Error && e.name !== 'AbortError') {
        setError(e.message)
        localStorage.removeItem('active_research_task_id')
        setRunning(false)
        setView('home')
      }
    }
  }, [navigate, appendEvent, fetchResult])

  // ── Start Research ──────────────────────────────────────────
  const startResearch = async () => {
    clearEvents()
    setError(null)
    setSelectedReport(null)
    setReportError(null)
    setRunning(true)
    abortRef.current = new AbortController()

    try {
      const res = await fetchWithRetry(`${BASE_API_URL}/run/stream`, {
        method: 'POST',
        headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
        signal: abortRef.current.signal,
      }, 2, 500)
      if (!res.ok) throw new Error('Không thể khởi động nghiên cứu.')
      const data = await res.json()
      if (!data.task_id) throw new Error('Lỗi hệ thống.')
      await connectToStream(data.task_id)
    } catch (e: unknown) {
      if (e instanceof Error && e.name !== 'AbortError') {
        setError(e.message)
        setRunning(false)
        setView('home')
      }
    }
  }

  // ── Stop Research ───────────────────────────────────────────
  const stopResearch = () => {
    abortRef.current?.abort()
    setRunning(false)
    localStorage.removeItem('active_research_task_id')
    navigate({ search: {} as any})
    setView('home')
  }

  // ── Resume Logic (F5 / URL / LocalStorage) ──────────────────
  const resumeTask = useCallback(async (taskId: string) => {
    if (isResumingRef.current) return
    isResumingRef.current = true
    setResuming(true)
    setResumeMessage('Đang kiểm tra trạng thái tác vụ...')

    try {
      const status = await checkStatus(taskId)
      if (!status) {
        localStorage.removeItem('active_research_task_id')
        setToast({ message: 'Không tìm thấy tác vụ. Có thể server đã khởi động lại.', type: 'warning' })
        setView('home')
        return
      }

      if (status.status === 'running' || status.status === 'queued') {
        setResumeMessage('Tác vụ đang chạy. Đang kết nối lại stream...')
        setToast({ message: 'Phát hiện tác vụ đang chạy. Đang kết nối lại...', type: 'info' })
        await connectToStream(taskId)
      } else if (status.status === 'completed') {
        setResumeMessage('Tác vụ đã hoàn tất. Đang tải báo cáo...')
        try {
          const result = await fetchResult(taskId)
          if (result) {
            setSelectedReport(result.result)
            setView('report')
            setToast({ message: 'Đã tải báo cáo từ tác vụ trước.', type: 'success' })
          }
        } catch (e) {
          if (e instanceof Error) {
            setError(e.message)
            setToast({ message: e.message, type: 'warning' })
          }
        }
      } else {
        localStorage.removeItem('active_research_task_id')
        setToast({ message: `Tác vụ thất bại: ${status.status}`, type: 'warning' })
        setView('home')
      }
    } finally {
      setResuming(false)
      setResumeMessage(null)
      isResumingRef.current = false
    }
  }, [checkStatus, fetchResult, connectToStream, navigate])

  // ── Mount: Check URL param or localStorage ──────────────────
  useEffect(() => {
    const saved = urlTaskId || localStorage.getItem('active_research_task_id')
    if (saved && !running && !isResumingRef.current) {
      resumeTask(saved)
    }
    return () => { abortRef.current?.abort() }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // ── Fetch History ───────────────────────────────────────────
  const fetchHistory = useCallback(async () => {
    setResultsLoading(true)
    try {
      const res = await fetchWithRetry(`${BASE_API_URL}/results?limit=20&offset=0`, {}, 3, 500)
      if (!res.ok) throw new Error('Lỗi tải lịch sử')
      const data = await res.json()
      setResults(data.items || [])
    } catch {
      setResults([])
    } finally {
      setResultsLoading(false)
    }
  }, [])

  useEffect(() => {
    if (view === 'history') fetchHistory()
  }, [view, fetchHistory])

  // ── View Report from History ────────────────────────────────
  const viewReport = async (taskId: string) => {
    setReportLoading(true)
    setSelectedReport(null)
    setReportError(null)
    try {
      const result = await fetchResult(taskId)
      if (result) {
        setSelectedReport(result.result)
        setView('report')
      }
    } catch (e) {
      if (e instanceof Error) {
        setReportError(e.message)
        setToast({ message: e.message, type: 'warning' })
      }
    } finally {
      setReportLoading(false)
    }
  }

  // ── Derived ─────────────────────────────────────────────────
  const lastEvent = events[events.length - 1]
  const lastProgress = lastEvent?.progress ?? 0
  const finalData = events.find(e => e.node === 'FINISHED')?.data
  const competitorAnalysis = selectedReport?.competitor_analysis || (finalData?.competitor_analysis as string) || ''
  const finalReport = selectedReport?.final_report || (finalData?.final_report as string) || ''
  const reportBusinessName = selectedReport?.business_name || form.business_name
  const reportAddress = selectedReport?.address || form.address

  // ── Render ────────────────────────────────────────────────
  return (
    <div style={{
      minHeight: '100vh', background: theme.bg, fontFamily: theme.font,
      color: theme.text, fontSize: 14, lineHeight: 1.6,
    }}>
      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        @keyframes slideUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        @keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
        .animate-slide-up { animation: slideUp 0.5s ease forwards; }
        .animate-fade-in { animation: fadeIn 0.3s ease forwards; }
        .markdown-body h1 { font-size: 22px; font-weight: 700; margin: 24px 0 12px; color: #0f172a; }
        .markdown-body h2 { font-size: 18px; font-weight: 700; margin: 20px 0 10px; color: #0f172a; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px; }
        .markdown-body h3 { font-size: 16px; font-weight: 600; margin: 16px 0 8px; color: #334155; }
        .markdown-body p { margin: 10px 0; }
        .markdown-body ul { margin: 10px 0; padding-left: 24px; }
        .markdown-body li { margin: 6px 0; }
        .markdown-body strong { color: #0f172a; }
        .markdown-body blockquote { border-left: 4px solid #3b82f6; padding-left: 16px; margin: 16px 0; color: #475569; font-style: italic; }
        .markdown-body table { width: 100%; border-collapse: collapse; margin: 16px 0; }
        .markdown-body th, .markdown-body td { padding: 10px 12px; border: 1px solid #e2e8f0; text-align: left; }
        .markdown-body th { background: #f8fafc; font-weight: 600; }
        .markdown-body tr:nth-child(even) { background: #fafbfc; }
      `}</style>

      {/* Toast */}
      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}

      {/* ═══ HEADER ═══ */}
      <header style={{
        background: theme.surface, borderBottom: `1px solid ${theme.border}`,
        position: 'sticky', top: 0, zIndex: 50,
      }}>
        <div style={{ maxWidth: 1200, margin: '0 auto', padding: '0 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 64 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{
              width: 40, height: 40, borderRadius: 12, background: theme.gradient,
              display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 20,
            }}>
              🏨
            </div>
            <div>
              <div style={{ fontWeight: 800, fontSize: 18, letterSpacing: '-0.02em' }}>Hotel Research</div>
              <div style={{ fontSize: 11, color: theme.textDim, fontWeight: 500 }}>AI Marketing Intelligence</div>
            </div>
          </div>
          <nav style={{ display: 'flex', gap: 4 }}>
            {[
              { key: 'home' as const, label: 'Nghiên cứu mới', icon: '🔍' },
              { key: 'history' as const, label: 'Lịch sử', icon: '📋' },
            ].map(tab => (
              <button
                key={tab.key}
                onClick={() => setView(tab.key)}
                style={{
                  padding: '8px 16px', borderRadius: 10, border: 'none', background: 'transparent',
                  color: view === tab.key ? theme.primary : theme.textMuted, fontWeight: view === tab.key ? 700 : 500,
                  fontSize: 14, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6,
                  transition: 'all 0.2s',
                }}
              >
                <span>{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      {/* ═══ RESUME BANNER ═══ */}
      {resuming && (
        <div style={{
          background: theme.primaryLight, borderBottom: `1px solid ${theme.border}`,
          padding: '12px 24px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
        }}>
          <span style={{ animation: 'spin 1s linear infinite', display: 'inline-block', fontSize: 16 }}>⟳</span>
          <span style={{ fontSize: 14, fontWeight: 500, color: theme.primaryDark }}>
            {resumeMessage || 'Đang khôi phục tác vụ...'}
          </span>
        </div>
      )}

      {/* ═══ ACTIVE TASK BANNER ═══ */}
      {running && currentTaskId && (
        <div style={{
          background: 'linear-gradient(135deg, #667eea15, #764ba215)', borderBottom: `1px solid ${theme.border}`,
          padding: '10px 24px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12,
        }}>
          <span style={{ fontSize: 14 }}>⚡</span>
          <span style={{ fontSize: 13, fontWeight: 500, color: theme.primaryDark }}>
            Tác vụ đang chạy: <code style={{ fontFamily: theme.mono, background: '#fff', padding: '2px 6px', borderRadius: 4 }}>{currentTaskId}</code>
          </span>
          <span style={{ fontSize: 12, color: theme.textDim }}>
            ({events.length} events • {lastProgress}%)
          </span>
          <button
            onClick={() => { navigator.clipboard.writeText(`${window.location.origin}/research?task_id=${currentTaskId}`); setToast({ message: 'Đã sao chép link!', type: 'success' }) }}
            style={{ fontSize: 12, color: theme.primary, background: 'none', border: 'none', cursor: 'pointer', fontWeight: 600 }}
          >
            Copy link
          </button>
        </div>
      )}

      <main style={{ maxWidth: 1200, margin: '0 auto', padding: '32px 24px' }}>

        {/* ════════════════════════════════════════════════════════
            VIEW: HOME — Form
        ════════════════════════════════════════════════════════ */}
        {view === 'home' && (
          <div className="animate-slide-up" style={{ maxWidth: 640, margin: '0 auto' }}>
            <div style={{ textAlign: 'center', marginBottom: 40 }}>
              <h1 style={{ fontSize: 36, fontWeight: 800, margin: '0 0 12px', letterSpacing: '-0.03em' }}>
                Nghiên cứu đối thủ <span style={{ background: theme.gradient, WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>thông minh</span>
              </h1>
              <p style={{ fontSize: 16, color: theme.textMuted, maxWidth: 480, margin: '0 auto', lineHeight: 1.6 }}>
                AI tự động phân tích đối thủ, xu hướng thị trường và đề xuất chiến lược marketing cho khách sạn của bạn.
              </p>
            </div>

            <Card>
              <div style={{ padding: '32px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 24 }}>
                  <span style={{ fontSize: 20 }}>🎯</span>
                  <span style={{ fontWeight: 700, fontSize: 18 }}>Thông tin khách sạn</span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                  <Input
                    label="Tên khách sạn"
                    value={form.business_name}
                    onChange={v => setForm(p => ({ ...p, business_name: v }))}
                    placeholder="VD: Sontras Sea Hotel"
                  />
                  <Input
                    label="Địa chỉ"
                    value={form.address}
                    onChange={v => setForm(p => ({ ...p, address: v }))}
                    placeholder="VD: 41 Hoàng Sa Road, Đà Nẵng"
                  />
                  <Input
                    label="Phân khúc / Ngành"
                    value={form.industry}
                    onChange={v => setForm(p => ({ ...p, industry: v }))}
                    placeholder="VD: Hotel / Beachfront Resort"
                  />
                </div>

                {error && (
                  <div style={{
                    marginTop: 20, padding: '12px 16px', background: '#fef2f2', border: '1px solid #fecaca',
                    borderRadius: 12, color: '#dc2626', fontSize: 13, fontWeight: 500,
                  }}>
                    ❌ {error}
                  </div>
                )}

                <div style={{ marginTop: 28, display: 'flex', gap: 12 }}>
                  <Button onClick={startResearch} size="lg" icon="🚀" style={{ flex: 1, justifyContent: 'center' }} ariaLabel="Bắt đầu nghiên cứu">
                    Bắt đầu nghiên cứu
                  </Button>
                </div>

                <div style={{ marginTop: 20, display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                  {[
                    { icon: '🔍', text: 'Tìm đối thủ' },
                    { icon: '📊', text: 'Phân tích website' },
                    { icon: '📱', text: 'TikTok trends' },
                    { icon: '📝', text: 'Báo cáo chiến lược' },
                  ].map((tag, i) => (
                    <span key={i} style={{
                      display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 14px',
                      background: theme.bg, borderRadius: 20, fontSize: 12, color: theme.textMuted, fontWeight: 500,
                      border: `1px solid ${theme.border}`,
                    }}>
                      <span>{tag.icon}</span>
                      {tag.text}
                    </span>
                  ))}
                </div>
              </div>
            </Card>
          </div>
        )}

        {/* ════════════════════════════════════════════════════════
            VIEW: RUNNING — Progress
        ════════════════════════════════════════════════════════ */}
        {view === 'running' && (
          <div className="animate-fade-in" style={{ maxWidth: 800, margin: '0 auto' }}>
            <Card>
              <div style={{ padding: '40px', textAlign: 'center' }}>
                <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 32 }}>
                  <ProgressRing value={lastProgress} size={160} stroke={10} />
                </div>

                <h2 style={{ fontSize: 24, fontWeight: 700, margin: '0 0 8px' }}>
                  Đang nghiên cứu đối thủ...
                </h2>
                <p style={{ color: theme.textMuted, fontSize: 15, marginBottom: 32 }}>
                  {lastEvent?.label || lastEvent?.message || 'Khởi động...'}
                </p>

                <div style={{ textAlign: 'left', maxWidth: 520, margin: '0 auto' }}>
                  <StepTimeline events={events} running={running} />
                </div>

                <div style={{ marginTop: 32, display: 'flex', justifyContent: 'center', gap: 12 }}>
                  <Button variant="ghost" onClick={stopResearch} icon="✕" ariaLabel="Hủy nghiên cứu">
                    Hủy bỏ
                  </Button>
                </div>
              </div>
            </Card>
          </div>
        )}

        {/* ════════════════════════════════════════════════════════
            VIEW: REPORT — Results
        ════════════════════════════════════════════════════════ */}
        {view === 'report' && (
          <div className="animate-slide-up">
            {/* Success Header */}
            <div style={{
              background: theme.gradient, borderRadius: 20, padding: '40px 48px', color: '#fff',
              marginBottom: 32, display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 20,
            }}>
              <div>
                <div style={{ fontSize: 14, fontWeight: 600, opacity: 0.9, marginBottom: 8 }}>✅ Nghiên cứu hoàn tất</div>
                <h2 style={{ fontSize: 28, fontWeight: 800, margin: 0, letterSpacing: '-0.02em' }}>
                  {reportBusinessName}
                </h2>
                <p style={{ margin: '8px 0 0', opacity: 0.85, fontSize: 15 }}>{reportAddress}</p>
              </div>
              <div style={{ display: 'flex', gap: 10 }}>
                <Button variant="secondary" onClick={() => setView('home')} icon="🔍" style={{ background: 'rgba(255,255,255,0.15)', color: '#fff', border: '1px solid rgba(255,255,255,0.3)' }}>
                  Nghiên cứu mới
                </Button>
                <Button variant="secondary" onClick={() => setView('history')} icon="📋" style={{ background: 'rgba(255,255,255,0.15)', color: '#fff', border: '1px solid rgba(255,255,255,0.3)' }}>
                  Lịch sử
                </Button>
              </div>
            </div>

            {/* Stats Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16, marginBottom: 32 }}>
              {[
                { label: 'Đối thủ phân tích', value: `${selectedReport?.competitors_clean?.length || 0}`, icon: '🏨', color: theme.primary },
                { label: 'Nguồn dữ liệu', value: 'Google + Booking + TikTok', icon: '📡', color: theme.purple },
                { label: 'Thời gian', value: '3-5 phút', icon: '⏱️', color: theme.orange },
                { label: 'Độ tin cậy', value: 'AI-Powered', icon: '🤖', color: theme.success },
              ].map((stat, i) => (
                <Card key={i} style={{ padding: '24px', display: 'flex', alignItems: 'center', gap: 16 }}>
                  <div style={{
                    width: 48, height: 48, borderRadius: 14, background: `${stat.color}15`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 24,
                  }}>
                    {stat.icon}
                  </div>
                  <div>
                    <div style={{ fontSize: 11, color: theme.textDim, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                      {stat.label}
                    </div>
                    <div style={{ fontSize: 18, fontWeight: 700, color: theme.text, marginTop: 2 }}>
                      {stat.value}
                    </div>
                  </div>
                </Card>
              ))}
            </div>

            {/* Reports */}
            <div style={{ display: 'grid', gap: 24 }}>
              {reportError && (
                <div style={{ padding: '16px 20px', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 12, color: '#dc2626' }}>
                  ❌ {reportError}
                </div>
              )}
              {competitorAnalysis && (
                <ReportCard title="Phân Tích Đối Thủ" icon="📊" color={theme.primary}>
                  <div className="markdown-body">
                    <ReactMarkdown>{competitorAnalysis}</ReactMarkdown>
                  </div>
                </ReportCard>
              )}
              {finalReport && (
                <ReportCard title="Báo Cáo Chiến Lược Marketing" icon="📝" color={theme.success}>
                  <div className="markdown-body">
                    <ReactMarkdown>{finalReport}</ReactMarkdown>
                  </div>
                </ReportCard>
              )}
              {!competitorAnalysis && !finalReport && !reportError && (
                <Card style={{ padding: 60, textAlign: 'center' }}>
                  <div style={{ fontSize: 48, marginBottom: 16 }}>📭</div>
                  <div style={{ fontWeight: 600, fontSize: 16, color: theme.textMuted }}>
                    Chưa có báo cáo. Vui lòng chạy nghiên cứu trước.
                  </div>
                </Card>
              )}
            </div>
          </div>
        )}

        {/* ════════════════════════════════════════════════════════
            VIEW: HISTORY — Past Reports
        ════════════════════════════════════════════════════════ */}
        {view === 'history' && (
          <div className="animate-fade-in">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
              <h2 style={{ fontSize: 24, fontWeight: 700, margin: 0 }}>📋 Lịch sử nghiên cứu</h2>
              <Button onClick={fetchHistory} icon="🔄" variant="secondary" size="sm">Làm mới</Button>
            </div>

            {resultsLoading && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {[1, 2, 3].map(i => (
                  <Card key={i} style={{ padding: 24 }}>
                    <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
                      <Skeleton width={56} height={56} />
                      <div style={{ flex: 1 }}>
                        <Skeleton width="40%" height={18} />
                        <div style={{ marginTop: 8 }}><Skeleton width="60%" height={14} /></div>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            )}

            {!resultsLoading && results.length === 0 && (
              <Card style={{ padding: 60, textAlign: 'center' }}>
                <div style={{ fontSize: 48, marginBottom: 16 }}>📭</div>
                <div style={{ fontWeight: 600, fontSize: 16, color: theme.textMuted }}>
                  Chưa có nghiên cứu nào. Hãy bắt đầu nghiên cứu đầu tiên!
                </div>
                <Button onClick={() => setView('home')} icon="🔍" style={{ marginTop: 20 }}>
                  Nghiên cứu mới
                </Button>
              </Card>
            )}

            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {results.map(item => (
                <HistoryItem
                  key={item.id}
                  item={item}
                  onViewReport={() => viewReport(item.task_id)}
                  onResume={() => resumeTask(item.task_id)}
                  checkStatus={checkStatus}
                />
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

// ── History Item Component (with live status) ───────────────────

function HistoryItem({
  item, onViewReport, onResume, checkStatus
}: {
  item: ResultItem
  onViewReport: () => void
  onResume: () => void
  checkStatus: (taskId: string) => Promise<TaskStatus | null>
}) {
  const [status, setStatus] = useState<string | null>(null)
  const [checking, setChecking] = useState(false)
  const checkedRef = useRef(false)

  const check = async () => {
    if (checkedRef.current) return
    checkedRef.current = true
    setChecking(true)
    const s = await checkStatus(item.task_id)
    setStatus(s?.status || 'unknown')
    setChecking(false)
  }

  useEffect(() => { check() }, [])

  const statusConfig: Record<string, { color: 'blue' | 'green' | 'orange' | 'red' | 'gray'; text: string }> = {
    running: { color: 'blue', text: 'Đang chạy' },
    queued: { color: 'orange', text: 'Đang chờ' },
    completed: { color: 'green', text: 'Hoàn tất' },
    failed: { color: 'red', text: 'Thất bại' },
    unknown: { color: 'gray', text: 'Không rõ' },
  }
  const sc = status ? statusConfig[status] || { color: 'gray', text: status } : { color: 'gray', text: '...' }

  return (
    <Card style={{ padding: 0 }}>
      <div style={{ padding: '24px 28px', display: 'flex', alignItems: 'center', gap: 20, flexWrap: 'wrap' }}>
        <div style={{
          width: 56, height: 56, borderRadius: 16, background: theme.gradient,
          display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 24, flexShrink: 0,
        }}>
          🏨
        </div>
        <div style={{ flex: 1, minWidth: 200 }}>
          <div style={{ fontWeight: 700, fontSize: 16, color: theme.text, marginBottom: 4 }}>
            {item.business_name || 'Không tên'}
          </div>
          <div style={{ fontSize: 13, color: theme.textDim, display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'center' }}>
            <span>{new Date(item.created_at).toLocaleString('vi-VN')}</span>
            <span>🏨 {item.competitors_count} đối thủ</span>
            {item.has_analysis && <Badge color="blue">Phân tích</Badge>}
            {item.has_report && <Badge color="green">Báo cáo</Badge>}
            {checking ? (
              <span style={{ fontSize: 12, color: theme.textDim }}>⏳</span>
            ) : (
              <Badge color={sc.color as any}>{sc.text}</Badge>
            )}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          {status === 'running' || status === 'queued' ? (
            <Button size="sm" variant="primary" onClick={onResume} icon="▶" ariaLabel="Theo dõi tiến trình">
              Theo dõi
            </Button>
          ) : (
            <Button size="sm" variant="secondary" onClick={onViewReport} ariaLabel="Xem báo cáo">
              Xem báo cáo
            </Button>
          )}
        </div>
      </div>
    </Card>
  )
}

// ── Export with Error Boundary ──────────────────────────────────

export default function HotelResearchPageWithBoundary() {
  return (
    <ErrorBoundary>
      <HotelResearchPage />
    </ErrorBoundary>
  )
}