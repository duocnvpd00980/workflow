-- BỎ HẾT ĐI, CODE MỚI LẠI THEO CÁCH BẠN ĐÃ LÀM MOCK API TÔI SẼ TẠO MỚI SAU : NGUYÊN TẮC CODE: ## NHIỆM VỤ
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
3. Cấu trúc JSX sau refactor
tsx
import { S, getStatusClass } from "./styles"

<div className={S.card}>
  <span className={`${S.badge} ${getStatusClass(item.status)}`}>
    {STATUS_LABEL[item.status]}
  </span>
</div>
4. Cấm
Không inline class string dài
Không giữ STATUS_META, CHANNEL_META riêng → gộp vào S
Không dùng cn() với string dài → dùng S.xxx
5. Giữ nguyên
Logic, state, handlers
shadcn components import
Icon imports
Types
OUTPUT
styles.ts — đầy đủ
page.tsx (hoặc file gốc) — đã refactor





📋 Nguyên tắc đã áp dụng:
- ✅ Tách styles.ts riêng, export S object
- ✅ Không class string > 30 ký tự trong JSX
- ✅ Giữ logic, state, handlers, types, icons
- ✅ Mock data, chưa có API
- ✅ 1 voice + templates (đơn giản, đủ là được)