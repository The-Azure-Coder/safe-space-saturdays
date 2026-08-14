declare module 'expo-router' {
  import type { ComponentType } from 'react'
  export const Stack: ComponentType<any> & { Screen: ComponentType<any> }
  export const Tabs: ComponentType<any> & { Screen: ComponentType<any> }
  export const Link: ComponentType<any>
  export const Redirect: ComponentType<any>
  export function useLocalSearchParams<T extends Record<string, string | string[] | undefined> = Record<string, string | string[] | undefined>>(): T
  export const router: { replace: (href: string) => void; push: (href: string) => void }
}
