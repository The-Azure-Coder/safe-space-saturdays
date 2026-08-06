import { HeadContent, Scripts, createRootRouteWithContext } from '@tanstack/react-router'
import { QueryClientProvider } from '@tanstack/react-query'

import appCss from '../styles.css?url'
import type { RouterContext } from '../router-context'
import { queryClient } from '../query-client'

export const Route = createRootRouteWithContext<RouterContext>()({
  head: () => ({
    meta: [
      { charSet: 'utf-8' },
      { name: 'viewport', content: 'width=device-width, initial-scale=1' },
      { title: 'Safe Space Saturdays' },
      { name: 'description', content: 'A warm, welcoming space to reflect, connect, and grow together.' },
    ],
    links: [{ rel: 'stylesheet', href: appCss }],
  }),
  shellComponent: RootDocument,
})

function RootDocument({ children }: { children: React.ReactNode }) {
  return <html lang="en"><head><HeadContent /></head><body><QueryClientProvider client={queryClient}>{children}</QueryClientProvider><Scripts /></body></html>
}
