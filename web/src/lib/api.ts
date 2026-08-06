const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: unknown } | null
    const detail = Array.isArray(body?.detail)
      ? body.detail.map((item) => typeof item === 'object' && item !== null && 'msg' in item ? String(item.msg) : String(item)).join('. ')
      : body?.detail
    throw new ApiError(response.status, detail == null ? 'Something went wrong' : String(detail))
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export type User = {
  id: number
  name: string
  email: string
  role: string
  xp: number
  streak: number
  level: number
}

export type Quote = { id: number; text: string; author: string; category: string; is_featured: boolean; saved: boolean }
export type Dashboard = { user: User; featured_quote: Quote | null; latest_check_in: CheckIn | null; rank: number; level_progress: number }
export type CheckIn = { id: number; mood: string; needs: Array<string>; energy: number; stress: number; thoughts: string | null; gratitude: string | null; completed: boolean; created_at: string }
export type Post = { id: number; author: string; initials: string; text: string; created_at: string; likes: number; support: number; replies: number; mine: boolean }
export type Game = { id: number; name: string; players: string; icon: string; color: string; is_featured: boolean }
export type Room = { id: number; name: string; game: string; players: number; max_players: number; status: string; joined: boolean }
export type LeaderboardEntry = { rank: number; user: User }

export const api = {
  register: (body: { name: string; email: string; password: string; confirm_password: string }) => apiFetch<{ user: User }>('/api/auth/register', { method: 'POST', body: JSON.stringify(body) }),
  login: (body: { email: string; password: string; remember_me: boolean }) => apiFetch<{ user: User }>('/api/auth/login', { method: 'POST', body: JSON.stringify(body) }),
  me: () => apiFetch<User>('/api/auth/me'),
  updateProfile: (body: { name: string }) => apiFetch<User>('/api/auth/me', { method: 'PATCH', body: JSON.stringify(body) }),
  logout: () => apiFetch<void>('/api/auth/logout', { method: 'POST' }),
  dashboard: () => apiFetch<Dashboard>('/api/dashboard'),
  checkIns: () => apiFetch<Array<CheckIn>>('/api/check-ins'),
  createCheckIn: (body: Omit<CheckIn, 'id' | 'created_at'>) => apiFetch<CheckIn>('/api/check-ins', { method: 'POST', body: JSON.stringify(body) }),
  quotes: (category?: string) => apiFetch<Array<Quote>>(`/api/quotes${category ? `?category=${encodeURIComponent(category)}` : ''}`),
  saveQuote: (id: number) => apiFetch<Quote>(`/api/quotes/${id}/save`, { method: 'POST' }),
  posts: () => apiFetch<Array<Post>>('/api/community/posts'),
  createPost: (text: string) => apiFetch<Post>('/api/community/posts', { method: 'POST', body: JSON.stringify({ text }) }),
  react: (id: number, kind: 'like' | 'support' | 'love') => apiFetch<Post>(`/api/community/posts/${id}/reactions`, { method: 'POST', body: JSON.stringify({ kind }) }),
  games: () => apiFetch<Array<Game>>('/api/games'),
  rooms: () => apiFetch<Array<Room>>('/api/games/rooms'),
  createRoom: (body: { game_id: number; name: string; max_players: number }) => apiFetch<Room>('/api/games/rooms', { method: 'POST', body: JSON.stringify(body) }),
  joinRoom: (id: number) => apiFetch<Room>(`/api/games/rooms/${id}/join`, { method: 'POST' }),
  leaderboard: (period: string) => apiFetch<Array<LeaderboardEntry>>(`/api/leaderboard?period=${period}`),
}
