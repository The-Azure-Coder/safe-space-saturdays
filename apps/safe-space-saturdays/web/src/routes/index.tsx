import { createFileRoute } from '@tanstack/react-router'

import { SafeSpaceApp } from '../components/safe-space-app'

export const Route = createFileRoute('/')({
  component: () => <SafeSpaceApp screen="home" />,
})
