import { createRoot } from 'react-dom/client'
import { RouterProvider } from '@tanstack/react-router'
import { getRouter } from './router'

const router = getRouter()

createRoot(document).render(
  
  <RouterProvider router={router} />,
)

requestAnimationFrame(() => {
  document.documentElement.dataset.clientReady = 'true'
})
