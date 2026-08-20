import { tanstackStart } from '@tanstack/react-start/plugin/vite'
import viteReact from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [tanstackStart({ client: { entry: 'client.tsx' } }), viteReact()],
  optimizeDeps: {
    // The complete Phosphor catalog produces a multi-megabyte optimized chunk
    // and can leave a fresh container's Vite optimizer hanging before hydration.
    exclude: ['@phosphor-icons/react'],
  },
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
