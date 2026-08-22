import { useEffect } from 'react'
import {
  HeadContent,
  Scripts,
  createRootRouteWithContext,
} from '@tanstack/react-router'
import { QueryClientProvider } from '@tanstack/react-query'

import appCss from '../styles.css?url'
import type { RouterContext } from '../router-context'
import { queryClient } from '../query-client'
import { ApiWakeGate } from '../components/api-wake-gate'

export const Route = createRootRouteWithContext<RouterContext>()({
  head: () => ({
    meta: [
      { charSet: 'utf-8' },
      { name: 'viewport', content: 'width=device-width, initial-scale=1' },
      { title: 'Safe Space Saturdays' },
      {
        name: 'description',
        content:
          'A warm, welcoming space to reflect, connect, and grow together.',
      },
    ],
    links: [
      { rel: 'stylesheet', href: appCss },
      {
        rel: 'icon',
        type: 'image/png',
        href: '/assets/optimized/safe-space-favicon.png',
      },
    ],
  }),
  shellComponent: RootDocument,
})

function RootDocument({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    const theme = window.localStorage.getItem('safe-space-theme')
    if (
      theme === 'night' ||
      theme === 'purple' ||
      theme === 'crimson' ||
      theme === 'high-contrast' ||
      theme === 'sage'
    )
      document.documentElement.dataset.theme = theme
  }, [])
  return (
    <html lang="en">
      <head>
        <HeadContent />
        <script
          dangerouslySetInnerHTML={{
            __html: `try { const theme = localStorage.getItem('safe-space-theme'); if (theme === 'night' || theme === 'purple' || theme === 'crimson' || theme === 'high-contrast' || theme === 'sage') document.documentElement.dataset.theme = theme } catch {}`,
          }}
        />
      </head>
      <body>
        <QueryClientProvider client={queryClient}>
          <ApiWakeGate>{children}</ApiWakeGate>
        </QueryClientProvider>
        <Scripts />
      </body>
    </html>
  )
}
