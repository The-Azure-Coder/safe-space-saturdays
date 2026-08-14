import { useState } from 'react'
import { Link, router } from 'expo-router'
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View } from 'react-native'
import { useAuth } from '@/auth'
import { themes } from '@/theme'

export default function Login() {
  const { signIn, error } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const submit = async () => {
    setBusy(true)
    try { await signIn(email.trim(), password); router.replace('/(tabs)') } catch { /* message is rendered below */ } finally { setBusy(false) }
  }
  return <View style={styles.page}>
    <Text style={styles.eyebrow}>SAFE SPACE SATURDAYS</Text>
    <Text style={styles.title}>Welcome back{`\n`}to your safe space.</Text>
    <Text style={styles.copy}>Talk. Listen. Support. Heal. Grow.</Text>
    <View style={styles.card}>
      <Text style={styles.label}>Email</Text>
      <TextInput autoCapitalize="none" keyboardType="email-address" value={email} onChangeText={setEmail} style={styles.input} placeholder="you@example.com" placeholderTextColor={themes.sage.muted} />
      <Text style={styles.label}>Password</Text>
      <TextInput secureTextEntry value={password} onChangeText={setPassword} style={styles.input} placeholder="Your password" placeholderTextColor={themes.sage.muted} />
      {error ? <Text accessibilityRole="alert" style={styles.error}>{error}</Text> : null}
      <Pressable disabled={busy || !email || !password} onPress={submit} style={({ pressed }: { pressed: boolean }) => [styles.button, pressed && styles.pressed, (busy || !email || !password) && styles.disabled]}>
        {busy ? <ActivityIndicator color="#fffdf8" /> : <Text style={styles.buttonText}>Log in</Text>}
      </Pressable>
      <Text style={styles.signup}>New here? <Link href="/registration" style={styles.link}>Create an account</Link></Text>
    </View>
  </View>
}

const styles = StyleSheet.create({
  page: { flex: 1, padding: 28, justifyContent: 'center', backgroundColor: themes.sage.background },
  eyebrow: { color: themes.sage.primary, fontSize: 12, fontWeight: '800', letterSpacing: 2 },
  title: { color: themes.sage.text, fontSize: 38, fontWeight: '800', lineHeight: 43, marginTop: 14 },
  copy: { color: themes.sage.muted, fontSize: 16, marginTop: 12 },
  card: { backgroundColor: themes.sage.surface, borderColor: themes.sage.border, borderRadius: 24, borderWidth: 1, padding: 20, marginTop: 30 },
  label: { color: themes.sage.text, fontSize: 13, fontWeight: '700', marginBottom: 8, marginTop: 8 },
  input: { color: themes.sage.text, backgroundColor: themes.sage.background, borderColor: themes.sage.border, borderRadius: 13, borderWidth: 1, fontSize: 16, paddingHorizontal: 15, paddingVertical: 13 },
  button: { alignItems: 'center', backgroundColor: themes.sage.primary, borderRadius: 14, marginTop: 20, minHeight: 50, justifyContent: 'center' },
  buttonText: { color: '#fffdf8', fontSize: 16, fontWeight: '800' },
  pressed: { opacity: 0.82 }, disabled: { opacity: 0.5 }, error: { color: '#b24747', fontSize: 13, marginTop: 12 },
  signup: { color: themes.sage.muted, fontSize: 14, marginTop: 20, textAlign: 'center' }, link: { color: themes.sage.primary, fontWeight: '800' },
})
