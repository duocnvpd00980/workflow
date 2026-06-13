import {
  createRootRoute,
  Outlet,
} from "@tanstack/react-router";

import {
  TanStackRouterDevtools,
} from "@tanstack/react-router-devtools";

import {
  ReactQueryDevtools,
} from "@tanstack/react-query-devtools";
import AppLayout from "@/layout/AppLayout";



function RootLayout() {
  return (
    <>
      <AppLayout>

        <Outlet />

      </AppLayout>

      <TanStackRouterDevtools
        position="bottom-left"
      />

      <ReactQueryDevtools
        initialIsOpen={false}
      />
    </>
  );
}

export const Route =
  createRootRoute({
    component:
      RootLayout,
  });