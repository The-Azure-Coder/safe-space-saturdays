import { Tabs } from 'expo-router'
import { Ionicons } from '@expo/vector-icons'
import { themes } from '@/theme'

export default function TabsLayout() {
  return <Tabs screenOptions={{ headerShown: false, tabBarActiveTintColor: themes.sage.primary, tabBarInactiveTintColor: themes.sage.muted, tabBarStyle: { backgroundColor: themes.sage.surface, borderTopColor: themes.sage.border, height: 86, paddingBottom: 12, paddingTop: 8 } }}>
    <Tabs.Screen name="index" options={{ title: 'Home', tabBarIcon: ({ color, size }: { color: string; size: number }) => <Ionicons name="home-outline" color={color} size={size} /> }} />
    <Tabs.Screen name="games" options={{ title: 'Games', tabBarIcon: ({ color, size }: { color: string; size: number }) => <Ionicons name="game-controller-outline" color={color} size={size} /> }} />
    <Tabs.Screen name="community" options={{ title: 'Community', tabBarIcon: ({ color, size }: { color: string; size: number }) => <Ionicons name="people-outline" color={color} size={size} /> }} />
    <Tabs.Screen name="profile" options={{ title: 'Profile', tabBarIcon: ({ color, size }: { color: string; size: number }) => <Ionicons name="person-circle-outline" color={color} size={size} /> }} />
  </Tabs>
}
