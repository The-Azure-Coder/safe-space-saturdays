import { createFileRoute } from '@tanstack/react-router'

import { SafeSpaceApp } from '../components/safe-space-app'

export const Route = createFileRoute('/contact')({
  component: () => <SafeSpaceApp screen="contact" />,
})
