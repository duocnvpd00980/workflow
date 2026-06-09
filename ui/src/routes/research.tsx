import { createFileRoute } from '@tanstack/react-router'
import { useState, useRef, useEffect, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'

export const Route = createFileRoute('/research')({
  component: HotelResearchPage,
})

const BASE_API_URL = 'https://viable-superb-basilisk.ngrok-free.app/api/v1/hotel-research'

const NODE_META = [
  { node: 'screenshot_google',       label: '📸 Chụp Google Hotels',       pct: 7   },
  { node: 'screenshot_booking',      label: '📸 Chụp Booking.com',          pct: 14  },
  { node: 'ocr_images',              label: '🔍 OCR ảnh',                   pct: 21  },
  { node: 'llm_clean_hotels',        label: '🤖 Làm sạch tên hotel',        pct: 30  },
  { node: 'find_websites',           label: '🌐 Tìm website đối thủ',       pct: 40  },
  { node: 'crawl_websites',          label: '🕷️ Crawl website',             pct: 52  },
  { node: 'analyze_competitors',     label: '📊 Phân tích đối thủ',         pct: 63  },
  { node: 'collect_social_data',     label: '📈 Thu thập Google Trends',    pct: 70  },
  { node: 'scrape_tiktok_html',      label: '📱 Lấy HTML TikTok',           pct: 76  },
  { node: 'extract_tiktok_content',  label: '🔤 Extract nội dung TikTok',   pct: 82  },
  { node: 'scrape_tiktok_comments',  label: '💬 Scrape comments TikTok',    pct: 88  },
  { node: 'parse_tiktok_comments',   label: '🔎 Parse comments',            pct: 93  },
  { node: 'final_strategy_report',   label: '📝 Tạo báo cáo chiến lược',   pct: 100 },
]

interface StreamEvent {
  node: string
  label: string
  status: string
  progress: number
  message: string
  data: Record<string, unknown>
}

function HotelResearchPage() {
  const [businessName, setBusinessName] = useState('Sontras Sea Hotel')
  const [address, setAddress] = useState('41 Hoàng Sa Road, Son Tra District, Da Nang, Vietnam')
  const [industry, setIndustry] = useState('Hotel / Beachfront Resort / Hospitality')

  const [events, setEvents] = useState<StreamEvent[]>([])
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const reconnectAttempted = useRef(false)

  const connectToStream = useCallback(async (taskId: string) => {
    if (abortRef.current) {
      abortRef.current.abort()
    }
    
    setRunning(true)
    setError(null)
    abortRef.current = new AbortController()

    try {
      const res = await fetch(`${BASE_API_URL}/stream/${taskId}`, {
        method: 'GET',
        signal: abortRef.current.signal,
      })

      if (res.status === 404) {
        localStorage.removeItem('active_research_task_id')
        throw new Error('Tác vụ cũ đã hết hạn hoặc hệ thống backend đã khởi động lại.')
      }
      if (!res.ok) throw new Error(`HTTP Stream kết nối thất bại: ${res.status}`)
      if (!res.body) throw new Error('Cổng dữ liệu phản hồi trống')

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
          if (trimmed.startsWith('data: ')) {
            try {
              const parsed: StreamEvent = JSON.parse(trimmed.slice(5).trim())
              
              setEvents(prev => {
                const isDuplicate = prev.some(e => 
                  e.node === parsed.node && 
                  e.status === parsed.status &&
                  e.progress === parsed.progress
                )
                if (isDuplicate) return prev
                return [...prev, parsed]
              })
              
              if (parsed.node === 'FINISHED' || parsed.node === 'ERROR') {
                localStorage.removeItem('active_research_task_id')
                setTimeout(() => setRunning(false), 500)
              }
            } catch {
              // ignore malformed
            }
          }
        }
      }
    } catch (e: unknown) {
      if (e instanceof Error && e.name !== 'AbortError') {
        setError(e.message)
        localStorage.removeItem('active_research_task_id')
        setRunning(false)
      }
    }
  }, [])

  const startStream = async () => {
    setEvents([])
    setError(null)
    setRunning(true)
    abortRef.current = new AbortController()

    try {
      const triggerRes = await fetch(`${BASE_API_URL}/run/stream`, {
        method: 'POST',
        headers: { 
          'accept': 'application/json',
          'Content-Type': 'application/json' 
        },
        body: JSON.stringify({ business_name: businessName, address, industry }),
        signal: abortRef.current.signal,
      })

      if (!triggerRes.ok) throw new Error(`HTTP Trigger thất bại: ${triggerRes.status}`)
      const triggerData = await triggerRes.json()
      const taskId = triggerData.task_id

      if (!taskId) throw new Error('Không nhận được task_id từ backend.')

      localStorage.setItem('active_research_task_id', taskId)
      await connectToStream(taskId)

    } catch (e: unknown) {
      if (e instanceof Error && e.name !== 'AbortError') {
        setError(e.message)
      }
      setRunning(false)
    }
  }

  useEffect(() => {
    const savedTaskId = localStorage.getItem('active_research_task_id')
    if (savedTaskId && !reconnectAttempted.current) {
      reconnectAttempted.current = true
      console.log('Phát hiện tác vụ đang chạy dở, tiến hành khôi phục...')
      connectToStream(savedTaskId)
    }
  }, [connectToStream])

  const stop = () => {
    abortRef.current?.abort()
    setRunning(false)
    localStorage.removeItem('active_research_task_id')
  }

  const lastEvent = events.length > 0 ? events[events.length - 1] : null
  const activeNode = running && lastEvent ? lastEvent.node : null

  const doneNodes = new Set(
    events
      .filter(e => e.status === 'done' || e.status === 'finished' || e.status === 'success')
      .map(e => e.node)
  )

  const currentMeta = NODE_META.find(n => n.node === activeNode)
  const lastProgress = running 
    ? (currentMeta ? currentMeta.pct : (lastEvent?.progress ?? 0))
    : (events.some(e => e.node === 'FINISHED') ? 100 : (events.length > 0 ? lastEvent?.progress ?? 0 : 0))

  // Lấy dữ liệu final report từ event cuối
  const finalData = events.find(e => e.node === 'FINISHED')?.data as Record<string, unknown> | undefined
  const competitorAnalysis = finalData?.competitor_analysis as string || ''
  const finalReport = finalData?.final_report as string || ''

  const inputStyle = {
    width: '100%',
    padding: '8px 12px',
    background: '#ffffff',
    border: '1px solid #e2e8f0',
    borderRadius: 6,
    color: '#1e293b',
    fontFamily: 'inherit',
    fontSize: 13,
    marginTop: 4,
    boxSizing: 'border-box' as const,
    boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.02)',
    transition: 'border-color 0.2s',
  }

  const labelStyle = {
    display: 'block',
    fontSize: 12,
    fontWeight: 500,
    color: '#475569',
    marginBottom: 10
  }

  return (
    <div style={{ fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif', fontSize: 13, padding: 24, maxWidth: 900, margin: '20px auto', background: '#f8fafc', borderRadius: 12, border: '1px solid #e2e8f0', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.05)' }}>

      <div style={{ marginBottom: 16, borderBottom: '1px solid #e2e8f0', paddingBottom: 12 }}>
        <div style={{ fontWeight: 700, fontSize: 16, color: '#0f172a', display: 'flex', alignItems: 'center', gap: 6 }}>
          🏨 Hotel Research Monitor
        </div>
        <div style={{ color: '#94a3b8', fontSize: 11, fontFamily: 'monospace', marginTop: 4 }}>ENDPOINT: {BASE_API_URL}</div>
      </div>

      <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: 8, padding: 14, marginBottom: 16, boxShadow: '0 1px 3px rgba(0,0,0,0.02)' }}>
        <label style={labelStyle}>
          Business Name
          <input 
            type="text" 
            value={businessName} 
            onChange={(e) => setBusinessName(e.target.value)} 
            disabled={running}
            style={inputStyle}
          />
        </label>
        <label style={labelStyle}>
          Address
          <input 
            type="text" 
            value={address} 
            onChange={(e) => setAddress(e.target.value)} 
            disabled={running}
            style={inputStyle}
          />
        </label>
        <label style={labelStyle}>
          Industry
          <input 
            type="text" 
            value={industry} 
            onChange={(e) => setIndustry(e.target.value)} 
            disabled={running}
            style={inputStyle}
          />
        </label>
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <button
          onClick={startStream}
          disabled={running}
          style={{
            padding: '8px 20px',
            background: running ? '#cbd5e1' : '#2563eb',
            color: '#fff',
            border: 'none',
            borderRadius: 6,
            fontWeight: 600,
            cursor: running ? 'not-allowed' : 'pointer',
            fontSize: 13,
            boxShadow: running ? 'none' : '0 2px 4px rgba(37,99,235,0.2)',
          }}
        >
          {running ? '⏳ Running...' : '▶ Start Process'}
        </button>
        {running && (
          <button
            onClick={stop}
            style={{
              padding: '8px 14px',
              background: '#ef4444',
              color: '#fff',
              border: 'none',
              borderRadius: 6,
              fontWeight: 600,
              cursor: 'pointer',
              fontSize: 13,
            }}
          >
            ■ Stop
          </button>
        )}
      </div>

      {error && (
        <div style={{ background: '#fef2f2', border: '1px solid #fee2e2', color: '#ef4444', padding: '10px 12px', borderRadius: 6, marginBottom: 14, fontSize: 13, fontWeight: 500 }}>
          ❌ Error: {error}
        </div>
      )}

      <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: 8, padding: '12px 14px', marginBottom: 16, boxShadow: '0 1px 3px rgba(0,0,0,0.02)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, fontWeight: 600, color: '#334155', marginBottom: 6 }}>
          <span>Pipeline Progress</span>
          <span style={{ color: lastProgress === 100 ? '#16a34a' : lastProgress > 0 ? '#2563eb' : '#64748b' }}>
            {lastProgress}%
          </span>
        </div>
        <div style={{ background: '#f1f5f9', borderRadius: 4, height: 6, overflow: 'hidden', marginBottom: 12 }}>
          <div style={{
            height: '100%',
            width: `${lastProgress}%`,
            background: lastProgress === 100 ? '#16a34a' : '#2563eb',
            transition: 'width 0.4s ease',
          }} />
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, borderTop: '1px solid #f1f5f9', paddingTop: 10 }}>
          {NODE_META.map(({ node, label, pct }) => {
            const isDone = doneNodes.has(node)
            const isActive = activeNode === node
            
            const nodeIndex = NODE_META.findIndex(n => n.node === node)
            const activeIndex = NODE_META.findIndex(n => n.node === activeNode)
            const isPassed = isDone || (activeIndex !== -1 && nodeIndex < activeIndex)

            return (
              <div key={node} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '2px 0' }}>
                <span style={{
                  fontSize: 12,
                  width: 16,
                  textAlign: 'center',
                  flexShrink: 0,
                  color: isDone ? '#16a34a' : isActive ? '#d97706' : '#cbd5e1',
                  fontWeight: 'bold'
                }}>
                  {isDone ? '✓' : isActive ? '●' : '○'}
                </span>
                <span style={{
                  fontSize: 13,
                  flex: 1,
                  color: isActive ? '#0f172a' : isPassed ? '#64748b' : '#94a3b8',
                  fontWeight: isActive ? 600 : 400,
                }}>
                  {label}
                </span>
                <span style={{ fontSize: 11, fontWeight: 500, color: isPassed ? '#16a34a' : '#cbd5e1' }}>{pct}%</span>
              </div>
            )
          })}
        </div>
      </div>

      {/* ===== BÁO CÁO MARKDOWN ===== */}
      {(competitorAnalysis || finalReport) && (
        <div style={{ display: 'grid', gap: 16, marginBottom: 16 }}>
          {competitorAnalysis && (
            <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: 8, padding: 20, boxShadow: '0 1px 3px rgba(0,0,0,0.02)' }}>
              <h2 style={{ margin: '0 0 16px 0', fontSize: 16, color: '#0f172a', borderBottom: '2px solid #2563eb', paddingBottom: 8 }}>
                📊 Phân Tích Đối Thủ
              </h2>
              <div className="markdown-body" style={{ fontSize: 14, lineHeight: 1.7, color: '#334155' }}>
                <ReactMarkdown>{competitorAnalysis}</ReactMarkdown>
              </div>
            </div>
          )}
          
          {finalReport && (
            <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: 8, padding: 20, boxShadow: '0 1px 3px rgba(0,0,0,0.02)' }}>
              <h2 style={{ margin: '0 0 16px 0', fontSize: 16, color: '#0f172a', borderBottom: '2px solid #16a34a', paddingBottom: 8 }}>
                📝 Báo Cáo Chiến Lược
              </h2>
              <div className="markdown-body" style={{ fontSize: 14, lineHeight: 1.7, color: '#334155' }}>
                <ReactMarkdown>{finalReport}</ReactMarkdown>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ===== RAW EVENT LOG ===== */}
      <div
        style={{
          background: '#ffffff',
          border: '1px solid #e2e8f0',
          borderRadius: 8,
          padding: 12,
          maxHeight: '35vh',
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: 8,
          boxShadow: 'inset 0 1px 3px rgba(0,0,0,0.01)'
        }}
      >
        {events.length === 0 && !running && (
          <div style={{ color: '#94a3b8', textAlign: 'center', padding: '24px 0', fontSize: 12 }}>
            Sẵn sàng. Nhấn Start Process để bắt đầu nhận luồng dữ liệu.
          </div>
        )}

        {events.map((ev, i) => (
          <div key={i} style={{ borderBottom: '1px solid #f1f5f9', paddingBottom: 8 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 }}>
              <span style={{ color: '#2563eb', fontWeight: 600, fontSize: 12 }}>{ev.label || ev.node}</span>
              <span style={{ color: '#94a3b8', fontSize: 11, fontFamily: 'monospace' }}>{ev.progress}%</span>
            </div>
            <div style={{ color: ev.status === 'done' || ev.status === 'finished' ? '#16a34a' : '#64748b', fontSize: 11, marginBottom: 4, fontWeight: 500 }}>
              Status: {ev.status}
            </div>
            {ev.data && Object.keys(ev.data).length > 0 && (
              <pre style={{
                margin: 0,
                fontSize: 11,
                color: '#0f172a',
                background: '#f8fafc',
                border: '1px solid #e2e8f0',
                padding: '6px 8px',
                borderRadius: 4,
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-all',
                fontFamily: 'monospace'
              }}>
                {JSON.stringify(ev.data, null, 2)}
              </pre>
            )}
          </div>
        ))}

        {running && (
          <div style={{ color: '#2563eb', fontSize: 12, textAlign: 'center', padding: '6px 0', fontWeight: 500 }}>
            ● Đang tải luồng stream dữ liệu...
          </div>
        )}
      </div>

      {events.length > 0 && (
        <div style={{ color: '#94a3b8', fontSize: 11, marginTop: 8, textAlign: 'right', fontWeight: 500 }}>
          Đã nhận {events.length} gói tin
        </div>
      )}
    </div>
  )
}