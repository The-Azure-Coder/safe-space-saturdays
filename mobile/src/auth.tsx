import { createContext, useContext, useEffect, useMemo, useState, type PropsWithChildren } from 'react'
import { login, logout, register, restoreSession, type User } from './api'

type AuthContextValue = {
  user: User | null
  loading: boolean
  error: string | null
  signIn: (email: string, password: string) => Promise<void>
  signUp: (name: string, email: string, password: string) => Promise<void>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: PropsWithChildren) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    restoreSession()
      .then(setUser)
      .catch(() => undefined)
      .finally(() => setLoading(false))
  }, [])

  const value = useMemo<AuthContextValue>(() => ({
    user,
    loading,
    error,
    async signIn(email, password) {
      setError(null)
      try { setUser(await login(email, password)) } catch (reason) {
        const message = reason instanceof Error ? reason.message : 'Unable to sign in'
        setError(message)
        throw reason
      }
    },
    async signUp(name, email, password) {
      setError(null)
      try { setUser(await register(name, email, password)) } catch (reason) {
        const message = reason instanceof Error ? reason.message : 'Unable to create your account'
        setError(message)
        throw reason
      }
    },
    async signOut() { await logout(); setUser(null) },
  }), [error, loading, user])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth must be used inside AuthProvider')
  return value
}
