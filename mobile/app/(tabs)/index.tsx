import { Link } from 'expo-router'
import { useQuery } from '@tanstack/react-query'
import { StyleSheet, Text, View } from 'react-native'
import { useAuth } from '@/auth'
import { mobileApi } from '@/api'
import { Page, Header, Loading, ErrorState, styles as ui } from '@/ui'
import { themes } from '@/theme'

export default function Home() {
  const { user } = useAuth()
  const dashboard = useQuery({ queryKey: ['mobile-dashboard'], queryFn: mobileApi.dashboard, retry: 2 })
  if (dashboard.isPending) return <Page><Loading /></Page>
  if (dashboard.isError) return <Page><ErrorState message={dashboard.error.message} onRetry={() => void dashboard.refetch()} /></Page>
  const current = dashboard.data.user ?? user
  return <Page><Header eyebrow="SAFE SPACE SATURDAYS" title={`Welcome back, ${current?.name.split(' ')[0] ?? 'friend'}.`} copy="A small check-in can change the shape of a day." /><View style={styles.hero}><Text style={styles.heroTitle}>How are you arriving today?</Text><Text style={styles.heroCopy}>Take a quiet moment to notice what you need.</Text><Link href="/check-in" style={styles.button}>Open daily check-in</Link></View><View style={styles.row}><View style={styles.stat}><Text style={styles.number}>{current?.streak ?? 0}</Text><Text style={styles.label}>day streak</Text></View><View style={styles.stat}><Text style={styles.number}>{current?.level ?? 1}</Text><Text style={styles.label}>level</Text></View><View style={styles.stat}><Text style={styles.number}>{current?.xp ?? 0}</Text><Text style={styles.label}>XP earned</Text></View></View>{dashboard.data.featured_quote ? <View style={styles.quote}><Text style={styles.quoteText}>“{dashboard.data.featured_quote.text}”</Text><Text style={styles.quoteAuthor}>{dashboard.data.featured_quote.author}</Text></View> : null}</Page>
}

const styles = StyleSheet.create({ hero: { backgroundColor: themes.sage.primary, borderRadius: 24, marginTop: 32, padding: 24 }, heroTitle: { color: '#fffdf8', fontSize: 24, fontWeight: '800' }, heroCopy: { color: '#e6f0e6', fontSize: 15, lineHeight: 22, marginTop: 8 }, button: { alignSelf: 'flex-start', backgroundColor: themes.sage.accent, borderRadius: 13, color: '#fffdf8', fontSize: 14, fontWeight: '800', marginTop: 20, overflow: 'hidden', paddingHorizontal: 16, paddingVertical: 12 }, row: { flexDirection: 'row', gap: 10, marginTop: 18 }, stat: { backgroundColor: themes.sage.surface, borderColor: themes.sage.border, borderRadius: 18, borderWidth: 1, flex: 1, padding: 15 }, number: { color: themes.sage.text, fontSize: 23, fontWeight: '800' }, label: { color: themes.sage.muted, fontSize: 12, marginTop: 4 }, quote: { backgroundColor: themes.sage.surface, borderColor: themes.sage.border, borderRadius: 20, borderWidth: 1, marginTop: 18, padding: 20 }, quoteText: { color: themes.sage.text, fontSize: 19, fontWeight: '700', lineHeight: 27 }, quoteAuthor: { color: themes.sage.muted, fontSize: 13, marginTop: 12 } })
