import { Stack } from 'expo-router'
import { StatusBar } from 'expo-status-bar'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider } from '@/auth'

const queryClient = new QueryClient()

export default function RootLayout() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <StatusBar style="light" />
        <Stack screenOptions={{ headerShown: false }}>
          <Stack.Screen name="challenges" />
          <Stack.Screen name="leaderboard" />
          <Stack.Screen name="check-in" />
          <Stack.Screen name="quotes" />
        </Stack>
      </AuthProvider>
    </QueryClientProvider>
  )
}
