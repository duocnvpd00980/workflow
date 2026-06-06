// ─── Config ───────────────────────────────────────────────────────────────────

import { API_BASE_URL } from "@/config";


// ─── Types ────────────────────────────────────────────────────────────────────

export interface Conv {
  id: string;
  title: string;
  last_message_at: string;
}

// ─── Query Keys ───────────────────────────────────────────────────────────────

export const queryKeys = {
  conversations: ["conversations"] as const,
};

// ─── API Functions ────────────────────────────────────────────────────────────

/** Lấy danh sách conversations — dùng cho useQuery */
export async function fetchConversations(): Promise<Conv[]> {
  const res = await fetch(`${API_BASE_URL}/chat/conversations`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/** Tạo conversation mới — dùng cho useMutation */
export async function createConversation(): Promise<string> {
  const res = await fetch(`${API_BASE_URL}/chat/conversations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title: "New chat" }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  return data.id ?? data.conversation_id;
}