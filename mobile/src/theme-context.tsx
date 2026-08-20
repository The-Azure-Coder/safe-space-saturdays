import { createContext, useContext, useEffect, useMemo, useState, type PropsWithChildren } from 'react'
import * as SecureStore from 'expo-secure-store'
import { themes, type ThemeColors, type ThemeName } from './theme'

type ThemeContextValue = { name: ThemeName; colors: ThemeColors; setTheme: (name: ThemeName) => Promise<void> }
const ThemeContext = createContext<ThemeContextValue | null>(null)
const key = 'safe-space-mobile-theme'

export function ThemeProvider({ children }: PropsWithChildren) {
  const [name, setName] = useState<ThemeName>('sage')
  useEffect(() => { SecureStore.getItemAsync(key).then((value) => { if (value && value in themes) setName(value as ThemeName) }).catch(() => undefined) }, [])
  const value = useMemo(() => ({ name, colors: themes[name], async setTheme(next: ThemeName) { setName(next); await SecureStore.setItemAsync(key, next) } }), [name])
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme() { const value = useContext(ThemeContext); if (!value) throw new Error('useTheme must be used inside ThemeProvider'); return value }
