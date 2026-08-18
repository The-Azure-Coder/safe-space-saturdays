import { tanstackStart } from '@tanstack/react-start/plugin/vite'
import viteReact from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [tanstackStart({ client: { entry: 'client.tsx' } }), viteReact()],
  server: {
    headers: { 'Cache-Control': 'no-store' },
    watch: {
      usePolling: true,
      interval: 250,
      // graphify writes its generated report into this mounted workspace;
      // it is documentation output, not application source. Watching it
      // repeatedly tears down SSR while a browser request is in flight.
      ignored: ['**/graphify-out/**'],
    },
  },
})
