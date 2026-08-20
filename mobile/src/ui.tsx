import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native'
import type { PropsWithChildren } from 'react'
import { themes } from './theme'

export function Page({ children }: PropsWithChildren) { return <View style={styles.page}>{children}</View> }
export function Header({ eyebrow, title, copy }: { eyebrow: string; title: string; copy?: string }) { return <><Text style={styles.eyebrow}>{eyebrow}</Text><Text style={styles.title}>{title}</Text>{copy ? <Text style={styles.copy}>{copy}</Text> : null}</> }
export function Loading() { return <View style={styles.center}><ActivityIndicator size="large" color={themes.sage.primary} /><Text style={styles.muted}>Keeping your safe space ready…</Text></View> }
export function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) { return <View style={styles.card}><Text style={styles.error}>{message}</Text><Pressable onPress={onRetry} style={styles.button}><Text style={styles.buttonText}>Try again</Text></Pressable></View> }
export const styles = StyleSheet.create({
  page: { backgroundColor: themes.sage.background, flex: 1, padding: 24, paddingTop: 62 },
  eyebrow: { color: themes.sage.primary, fontSize: 12, fontWeight: '800', letterSpacing: 2 },
  title: { color: themes.sage.text, fontSize: 34, fontWeight: '800', marginTop: 12 },
  copy: { color: themes.sage.muted, fontSize: 16, lineHeight: 24, marginTop: 10 },
  muted: { color: themes.sage.muted, fontSize: 14, marginTop: 12 },
  center: { alignItems: 'center', flex: 1, justifyContent: 'center' },
  card: { backgroundColor: themes.sage.surface, borderColor: themes.sage.border, borderRadius: 22, borderWidth: 1, marginTop: 24, padding: 20 },
  button: { alignItems: 'center', backgroundColor: themes.sage.primary, borderRadius: 14, justifyContent: 'center', marginTop: 16, minHeight: 48, paddingHorizontal: 18 },
  buttonText: { color: '#fffdf8', fontSize: 15, fontWeight: '800' },
  error: { color: '#b24747', fontSize: 14, lineHeight: 21 },
})
