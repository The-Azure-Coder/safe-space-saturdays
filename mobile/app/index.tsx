import { Redirect } from 'expo-router'
import { ActivityIndicator, StyleSheet, View } from 'react-native'
import { useAuth } from '@/auth'
import { themes } from '@/theme'

export default function Index() {
  const { user, loading } = useAuth()
  if (loading) return <View style={styles.loading}><ActivityIndicator color={themes.sage.accent} size="large" /></View>
  return <Redirect href={user ? '/(tabs)' : '/login'} />
}

const styles = StyleSheet.create({ loading: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: themes.sage.background } })
