import { createRouter } from '@tanstack/react-router'

import { routeTree } from './routeTree.gen'
import { queryClient } from './query-client'

export function getRouter() {
  const router = createRouter({
    routeTree,
    context: { queryClient },
    scrollRestoration: true,
    defaultPreload: 'intent',
    defaultPreloadStaleTime: 0,
  })

  return router
}

declare module '@tanstack/react-router' {
  interface Register {
    router: ReturnType<typeof getRouter>
  }
}
