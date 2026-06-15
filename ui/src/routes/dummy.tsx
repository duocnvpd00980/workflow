import { createFileRoute } from '@tanstack/react-router'
import React, { useState } from 'react';

export const Route = createFileRoute('/dummy')({
  component: SimpleChatTester,
})

export default function SimpleChatTester() {
  const [message, setMessage] = useState('chào');
  const [aiResponse, setAiResponse] = useState(''); // 🌟 Nơi hiển thị bài viết chạy từng chữ
  const [logs, setLogs] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);

  const handleSendStream = async () => {
    if (isStreaming) return;
    
    setIsStreaming(true);
    setAiResponse(''); // Xóa nội dung cũ
    setLogs('--- Bắt đầu kết nối API ---\n');

    try {
      const response = await fetch('http://localhost:8000/api/v1/chat/stream', {
        method: 'POST',
        headers: {
          'accept': 'application/json',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          conversation_id: "cc5b8de1-2517-46c8-b642-43cc4041d190",
          message: message,
          msg_id: crypto.randomUUID(), 
          brand_id: "7b0a96d6-4423-4979-ab2f-2b88845b0174",
          business_id: "string"
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP Error! Status: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) {
          setLogs((prev) => prev + "\n--- Luồng Stream Kết Thúc ---");
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        
        // 🌟 SỬA TẠI ĐÂY: Tách bằng \n đơn để xử lý chuẩn quy tắc dòng của SSE
        const lines = buffer.split("\n");
        buffer = lines.pop() || ""; 

        for (const line of lines) {
          const trimmedLine = line.trim();
          
          // Bỏ qua dòng trống hoặc dòng định nghĩa event tên hệ thống
          if (!trimmedLine || trimmedLine.startsWith("event:")) continue;

          if (trimmedLine.startsWith("data: ")) {
            const rawJson = trimmedLine.replace("data: ", "").trim();
            
            if (rawJson === "{}" || !rawJson) continue;

            try {
              const parsed = JSON.parse(rawJson);
              
              // Nếu backend trả về token (từng chữ)
              if (parsed.type === 'token') {
                setAiResponse((prev) => prev + parsed.text);
              } 
              // Nếu backend trả về log của node
              else if (parsed.type === 'node') {
                setLogs((prev) => prev + `[Node]: ${JSON.stringify(parsed.output)}\n`);
              } else {
                // Dự phòng nếu log thô chưa phân loại
                setLogs((prev) => prev + rawJson + "\n");
              }
            } catch (e) {
              // Nếu data không phải là JSON sạch (chuỗi thô)
              setLogs((prev) => prev + rawJson + "\n");
            }
          }
        }
      }

    } catch (error) {
      setLogs((prev) => prev + `\n❌ Lỗi hệ thống: ${error.message}`);
    } finally {
      setIsStreaming(false);
    }
  };

  return (
    <div style={{ padding: '24px', maxWidth: '650px', margin: '40px auto', fontFamily: 'sans-serif' }}>
      <h2 style={{ fontSize: '18px', marginBottom: '12px' }}>🚀 React Stream API Tester</h2>
      
      <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
        <input
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          disabled={isStreaming}
          style={{ flex: 1, padding: '8px 12px', borderRadius: '6px', border: '1px solid #ccc', fontSize: '14px' }}
        />
        <button
          onClick={handleSendStream}
          disabled={isStreaming}
          style={{ padding: '8px 16px', backgroundColor: isStreaming ? '#9ca3af' : '#6366f1', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '14px' }}
        >
          {isStreaming ? 'Đang chạy...' : 'Gửi API'}
        </button>
      </div>

      {/* 🌟 Ô HIỂN THỊ NỘI DUNG AI ĐANG GÕ */}
      <div style={{ marginBottom: '20px' }}>
        <label style={{ fontSize: '12px', fontWeight: 'bold', display: 'block', marginBottom: '6px' }}>🤖 Nội dung hiển thị thực tế (AI Response):</label>
        <div style={{ minHeight: '120px', padding: '16px', backgroundColor: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0', whiteSpace: 'pre-wrap', fontSize: '14px', lineHeight: '1.6', color: '#1e293b' }}>
          {aiResponse || <span style={{ color: '#94a3b8' }}>Chữ của AI sẽ chạy mượt mà ở đây...</span>}
        </div>
      </div>

      <div>
        <label style={{ fontSize: '12px', fontWeight: 'bold', display: 'block', marginBottom: '6px' }}>Technical Logs:</label>
        <pre style={{ backgroundColor: '#0f172a', color: '#38bdf8', padding: '16px', borderRadius: '8px', overflowX: 'auto', maxHeight: '150px', fontSize: '11px', margin: 0, fontFamily: 'monospace' }}>
          {logs || '// Chờ dữ liệu từ node...'}
        </pre>
      </div>
    </div>
  );
}