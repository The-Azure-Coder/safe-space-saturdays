import { Stack } from 'expo-router'
import { StatusBar } from 'expo-status-bar'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider } from '@/auth'
import { ThemeProvider } from '@/theme-context'
import { enableNotifications } from '@/notifications'
import { useEffect } from 'react'

const queryClient = new QueryClient()

export default function RootLayout() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider><AuthProvider>
        <NotificationBootstrap />
        <StatusBar style="light" />
        <Stack screenOptions={{ headerShown: false }}>
          <Stack.Screen name="challenges" />
          <Stack.Screen name="leaderboard" />
          <Stack.Screen name="check-in" />
          <Stack.Screen name="quotes" />
        </Stack>
      </AuthProvider></ThemeProvider>
    </QueryClientProvider>
  )
}

function NotificationBootstrap() { useEffect(() => { void enableNotifications() }, []); return null }
