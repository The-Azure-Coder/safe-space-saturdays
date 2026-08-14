import { StyleSheet, Text, View } from 'react-native'
import { themes } from '@/theme'

export default function Community() { return <View style={styles.page}><Text style={styles.eyebrow}>YOUR COMMUNITY</Text><Text style={styles.title}>A softer place to land.</Text><Text style={styles.copy}>Encouragement, reflections, and small wins from people making space for themselves.</Text><View style={styles.card}><Text style={styles.quote}>“You are allowed to grow at the pace that feels safe.”</Text><Text style={styles.author}>Safe Space Saturdays</Text></View></View> }

const styles = StyleSheet.create({ page: { backgroundColor: themes.sage.background, flex: 1, padding: 24, paddingTop: 62 }, eyebrow: { color: themes.sage.primary, fontSize: 12, fontWeight: '800', letterSpacing: 2 }, title: { color: themes.sage.text, fontSize: 34, fontWeight: '800', marginTop: 12 }, copy: { color: themes.sage.muted, fontSize: 16, lineHeight: 24, marginTop: 10 }, card: { backgroundColor: themes.sage.primary, borderRadius: 24, marginTop: 30, padding: 24 }, quote: { color: '#fffdf8', fontSize: 23, fontWeight: '700', lineHeight: 31 }, author: { color: '#dcebdc', fontSize: 13, marginTop: 18 } })
