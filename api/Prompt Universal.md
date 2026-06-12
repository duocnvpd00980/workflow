## NHIỆM VỤ
Refactor code React + Tailwind. Tách style ra file riêng, giữ logic trong component.

## QUY TẮC BẮT BUỘC

### 1. Tách file
- Tạo `styles.ts` cạnh component gốc
- Export object `S` chứa TẤT CẢ Tailwind classes
- Không để class string > 30 ký tự trong JSX

### 2. Cấu trúc `styles.ts`
```ts
export const S = {
  // Layout
  container: "...",
  // Component parts
  card: "...",
  cardHeader: "...",
  // Buttons
  btnPrimary: "...",
  btnDanger: "...",
  // Variants (gộp chung, không tách object riêng)
  statusActive: "...",
  statusInactive: "...",
} as const

// Helper nếu cần map động
export const getStatusClass = (status: string) => ({...}[status] || "")
export const STATUS_LABEL = {...}


import { S, getStatusClass } from "./styles"

<div className={S.card}>
  <span className={`${S.badge} ${getStatusClass(item.status)}`}>
    {STATUS_LABEL[item.status]}
  </span>
</div>


OUTPUT
styles.ts — đầy đủ
page.tsx (hoặc file gốc) — đã refactor
Comment // Refactored: style → S object ở đầu file