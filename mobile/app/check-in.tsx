import { Link } from 'expo-router'
import { StyleSheet, Text, View } from 'react-native'
import { themes } from '@/theme'

export default function CheckIn() {
  return <View style={styles.page}><Text style={styles.eyebrow}>DAILY CHECK-IN</Text><Text style={styles.title}>Notice what you need.</Text><Text style={styles.copy}>The full check-in flow is coming next. Your mobile foundation is connected and ready for the same API-backed reflection experience as the website.</Text><Link href="/(tabs)" style={styles.link}>Back home</Link></View>
}

const styles = StyleSheet.create({ page: { backgroundColor: themes.sage.background, flex: 1, justifyContent: 'center', padding: 28 }, eyebrow: { color: themes.sage.primary, fontSize: 12, fontWeight: '800', letterSpacing: 2 }, title: { color: themes.sage.text, fontSize: 36, fontWeight: '800', marginTop: 14 }, copy: { color: themes.sage.muted, fontSize: 16, lineHeight: 25, marginTop: 14 }, link: { alignSelf: 'flex-start', backgroundColor: themes.sage.primary, borderRadius: 14, color: '#fffdf8', fontSize: 15, fontWeight: '800', marginTop: 25, overflow: 'hidden', paddingHorizontal: 17, paddingVertical: 13 } })
