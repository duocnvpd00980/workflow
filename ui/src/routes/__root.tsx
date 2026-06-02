// src/routes/__root.tsx
import { createRootRoute, Link, Outlet } from '@tanstack/react-router'
import { TanStackRouterDevtools } from '@tanstack/react-router-devtools'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'

const RootLayout = () => (
  <div>
    <main>
      <Outlet /> 
    </main>

    <TanStackRouterDevtools position="bottom-left" />
    <ReactQueryDevtools initialIsOpen={false}/>
  </div>
)

export const Route = createRootRoute({ component: RootLayout })