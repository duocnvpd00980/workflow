import { StrictMode } from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider, createRouter } from '@tanstack/react-router'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { routeTree } from './routeTree.gen'
import './index.css'

// 1. Khởi tạo React Query Client
const queryClient = new QueryClient()

// 2. Khởi tạo TanStack Router 
// (Bổ sung truyền queryClient vào context để các file routes sau này lấy ra dùng chung)
const router = createRouter({ 
  routeTree,
  context: {
    queryClient,
  }
})

// 3. Đăng ký Typescript bảo vệ Route (Bắt buộc để có Type-safe)
declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}

// 4. Render app (Giữ nguyên ID 'root' của bạn, không cần sửa index.html)
const rootElement = document.getElementById('root')!

if (!rootElement.innerHTML) {
  const root = ReactDOM.createRoot(rootElement)
  root.render(
    <StrictMode>
      {/* PHẢI BỌC QueryClientProvider ở ngoài cùng để kích hoạt React Query */}
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
        <ReactQueryDevtools initialIsOpen={false} />
      </QueryClientProvider>
    </StrictMode>,
  )
}