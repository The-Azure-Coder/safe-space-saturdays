import * as SecureStore from 'expo-secure-store'

export type User = {
  id: number
  name: string
  email: string
  avatar_url: string | null
  is_online: boolean
  role: string
  is_approved: boolean
  xp: number
  streak: number
  level: number
}

type AuthResponse = {
  user: User
  access_token?: string | null
  pending_approval?: boolean
  message?: string | null
}

const tokenKey = 'safe-space-access-token'
const apiUrl = (process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000').replace(/\/$/, '')

export class MobileApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
  }
}

async function readToken() {
  return SecureStore.getItemAsync(tokenKey)
}

async function saveToken(token: string | null | undefined) {
  if (token) await SecureStore.setItemAsync(tokenKey, token)
}

export async function clearToken() {
  await SecureStore.deleteItemAsync(tokenKey)
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = await readToken()
  const headers = new Headers(init?.headers)
  headers.set('Content-Type', 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)
  let response: Response
  try {
    response = await fetch(`${apiUrl}${path}`, { ...init, headers })
  } catch {
    throw new MobileApiError(0, 'We could not reach Safe Space Saturdays yet.')
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null) as { detail?: unknown } | null
    throw new MobileApiError(response.status, typeof body?.detail === 'string' ? body.detail : 'Something went wrong')
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export async function login(email: string, password: string) {
  const result = await request<AuthResponse>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password, remember_me: true }),
  })
  await saveToken(result.access_token)
  return result.user
}

export async function register(name: string, email: string, password: string) {
  const result = await request<AuthResponse>('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify({ name, email, password, confirm_password: password }),
  })
  if (!result.access_token) {
    throw new MobileApiError(403, result.message ?? 'Your account is awaiting approval before you can sign in.')
  }
  await saveToken(result.access_token)
  return result.user
}

export async function restoreSession() {
  const user = await request<User>('/api/auth/me')
  return user
}

export async function logout() {
  try {
    await request<void>('/api/auth/logout', { method: 'POST' })
  } finally {
    await clearToken()
  }
}
