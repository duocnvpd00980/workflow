// src/config/env.ts

// 1. Log kiểm tra biến môi trường cốt lõi để mày dễ debug trên console browser
console.log("Biến môi trường gốc từ file .env:", import.meta.env.VITE_API_BASE_URL);
console.log("Chế độ chạy hiện tại của Vite (dev hay build):", import.meta.env.MODE);

// 2. Tự động check môi trường thông qua biến ngầm import.meta.env.DEV của Vite
// - Nếu ĐANG DEV (npm run dev) -> Ép nhận localhost luôn, bất chấp các file .env khác.
// - Nếu ĐANG BUILD (npm run build) -> Ưu tiên lấy biến trong file .env cấu hình deploy, nếu không có mới fallback.
const API = import.meta.env.DEV 
  ? "http://localhost:8000/api/v1" 
  : (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1");

// 3. Sử dụng biến gốc để phân tách các đường dẫn, dẹp sạch lặp code VITE_
export const API_BASE_URL = `${API}/rag`;
export const BASE = `${API}/rag`;
export const API_BASE = API;

// Các đường dẫn liên quan đến marketing
export const MARKETING_BASE_URL = `${API}/marketing`;
export const BASE_URL = `${API}/marketing`;
export const GROQ_API_KEY = import.meta.env.GROQ_API_KEY;