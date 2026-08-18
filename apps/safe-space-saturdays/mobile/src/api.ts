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

export type Quote = { id: number; text: string; author: string; category: string; is_featured: boolean; saved: boolean }
export type CheckIn = { id: number; mood: string; needs: string[]; energy: number; stress: number; thoughts: string | null; gratitude: string | null; completed: boolean; created_at: string }
export type Dashboard = { user: User; featured_quote: Quote | null; latest_check_in: CheckIn | null; rank: number; level_progress: number; daily_checkin_question: string }
export type Challenge = { id: number; slug: string; title: string; description: string; category: string; icon: string; color: string; xp: number; week_start: string; active_until: string; completed: boolean; completed_at: string | null; reflection: string | null }
export type Challenges = { week_start: string; active_until: string; completed_count: number; total_count: number; xp_earned: number; challenges: Challenge[] }
export type Post = { id: number; user_id: number; author_name: string; author_avatar_url: string | null; author_is_online: boolean; text: string; image_url: string | null; post_type: string; quote_id: number | null; like_count: number; dislike_count: number; user_reaction: string | null; comments: Comment[]; comment_count: number; created_at: string }
export type Comment = { id: number; user_id: number; author_name: string; author_avatar_url: string | null; text: string; created_at: string }
export type LeaderboardEntry = { rank: number; user: User }
export type Game = { id: number; name: string; description: string; color: string; min_players: number; max_players: number; is_featured: boolean }
export type Room = { id: number; name: string; game_id: number; game_name: string; host_id: number; host_name: string; status: string; max_players: number; participant_count: number; bot_difficulty: string; invite_token: string }
export type GameSession = { match_id: string; game: string; state: Record<string, any> }

type AuthResponse = {
  user: User
  access_token?: string | null
  pending_approval?: boolean
  message?: string | null
}

const tokenKey = 'safe-space-access-token'
const apiUrl = (process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000').replace(/\/$/, '')
const requestTimeoutMs = 45_000
export const googleLoginUrl = `${apiUrl}/api/auth/google/start?mobile=true`
export const assetUrl = (path: string | null) => path && path.startsWith('/') ? `${apiUrl}${path}` : path

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

async function fetchWithTimeout(input: RequestInfo | URL, init?: RequestInit) {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), requestTimeoutMs)
  try {
    return await fetch(input, { ...init, signal: controller.signal })
  } finally {
    clearTimeout(timeout)
  }
}

export async function clearToken() {
  await SecureStore.deleteItemAsync(tokenKey)
}

async function request<T>(path: string, init?: RequestInit, canRefresh = true): Promise<T> {
  const token = await readToken()
  const headers = new Headers(init?.headers)
  headers.set('Content-Type', 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)
  let response: Response
  try {
    response = await fetchWithTimeout(`${apiUrl}${path}`, { ...init, headers })
  } catch {
    throw new MobileApiError(0, 'Safe Space is taking a little longer to wake up. Please try again shortly.')
  }
  if (!response.ok) {
    if (response.status === 401 && token && canRefresh && path !== '/api/auth/refresh') {
      try {
        const refreshed = await request<AuthResponse>('/api/auth/refresh', { method: 'POST' }, false)
        await saveToken(refreshed.access_token)
        return request<T>(path, init, false)
      } catch {
        await clearToken()
      }
    }
    const body = await response.json().catch(() => null) as { detail?: unknown } | null
    throw new MobileApiError(response.status, typeof body?.detail === 'string' ? body.detail : 'Something went wrong')
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

async function upload(path: string, uri: string, name = 'profile.jpg') {
  const token = await readToken()
  const body = new FormData()
  body.append('image', { uri, name, type: 'image/jpeg' } as unknown as Blob)
  const headers = token ? { Authorization: `Bearer ${token}` } : undefined
  const response = await fetchWithTimeout(`${apiUrl}${path}`, { method: 'POST', headers, body })
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: string } | null
    throw new MobileApiError(response.status, payload?.detail ?? 'The image could not be uploaded')
  }
  return response.json() as Promise<User>
}

async function uploadPost(text: string, uri: string) {
  const token = await readToken()
  const body = new FormData()
  body.append('text', text)
  body.append('image', { uri, name: 'community.jpg', type: 'image/jpeg' } as unknown as Blob)
  const response = await fetchWithTimeout(`${apiUrl}/api/community/posts/with-image`, { method: 'POST', headers: token ? { Authorization: `Bearer ${token}` } : undefined, body })
  if (!response.ok) throw new MobileApiError(response.status, 'The post image could not be uploaded')
  return response.json() as Promise<Post>
}

export async function login(email: string, password: string) {
  const result = await request<AuthResponse>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password, remember_me: true }),
  })
  await saveToken(result.access_token)
  return result.user
}

export async function loginWithGoogleToken(token: string) {
  await saveToken(token)
  return restoreSession()
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

export const mobileApi = {
  dashboard: () => request<Dashboard>('/api/dashboard'),
  checkIns: (page = 1) => request<CheckIn[]>(`/api/check-ins?page=${page}&limit=20`),
  createCheckIn: (body: Omit<CheckIn, 'id' | 'created_at'>) => request<CheckIn>('/api/check-ins', { method: 'POST', body: JSON.stringify(body) }),
  challenges: () => request<Challenges>('/api/challenges/current'),
  completeChallenge: (id: number, reflection?: string) => request<Challenge>(`/api/challenges/${id}/complete`, { method: 'POST', body: JSON.stringify({ reflection: reflection?.trim() || null }) }),
  posts: (page = 1) => request<Post[]>(`/api/community/posts?page=${page}&limit=10`),
  createPost: (text: string) => request<Post>('/api/community/posts', { method: 'POST', body: JSON.stringify({ text }) }),
  react: (id: number, kind: 'like' | 'dislike') => request<Post>(`/api/community/posts/${id}/reactions`, { method: 'POST', body: JSON.stringify({ kind }) }),
  reply: (id: number, text: string) => request<Comment>(`/api/community/posts/${id}/comments`, { method: 'POST', body: JSON.stringify({ text }) }),
  quotes: (savedOnly = false) => request<Quote[]>(`/api/quotes?page=1&limit=20${savedOnly ? '&saved_only=true' : ''}`),
  saveQuote: (id: number) => request<Quote>(`/api/quotes/${id}/save`, { method: 'POST' }),
  submitQuote: (body: { text: string; author: string; category: 'Encouragement' | 'Rest' | 'Growth' | 'Connection' }) => request<Quote>('/api/quotes/submissions', { method: 'POST', body: JSON.stringify(body) }),
  updateAvatar: (uri: string) => upload('/api/auth/me/avatar', uri),
  createPostWithImage: (text: string, uri: string) => uploadPost(text, uri),
  leaderboard: (period: 'day' | 'week' | 'month' | 'all') => request<LeaderboardEntry[]>(`/api/leaderboard?period=${period}&page=1&limit=20`),
  leaderboardMe: (period: 'day' | 'week' | 'month' | 'all') => request<LeaderboardEntry>(`/api/leaderboard/me?period=${period}`),
  games: () => request<Game[]>('/api/games?page=1&limit=20'),
  rooms: () => request<Room[]>('/api/games/rooms?page=1&limit=20'),
  room: (id: number) => request<Room>(`/api/games/rooms/${id}`),
  roomParticipants: (id: number) => request<Array<{ user_id: number; display_name: string; ready: boolean; player_type: string }>>(`/api/games/rooms/${id}/participants`),
  createRoom: (body: { game_id: number; name: string; max_players: number; fill_with_bots?: boolean }) => request<Room>('/api/games/rooms', { method: 'POST', body: JSON.stringify(body) }),
  joinRoom: (id: number) => request<Room>(`/api/games/rooms/${id}/join`, { method: 'POST' }),
  setRoomReady: (id: number) => request<Room>(`/api/games/rooms/${id}/ready`, { method: 'POST' }),
  createSession: (roomId: number, fillWithBots = true) => request<GameSession>('/api/games/sessions', { method: 'POST', body: JSON.stringify({ room_id: roomId, fill_with_bots: fillWithBots }) }),
  gameSession: (id: string) => request<GameSession>(`/api/games/sessions/${id}`),
  gameAction: (id: string, action: Record<string, unknown>) => request<GameSession>(`/api/games/sessions/${id}/actions`, { method: 'POST', body: JSON.stringify({ action }) }),
}
