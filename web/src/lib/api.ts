export const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers)
  if (!(init?.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    credentials: 'include',
    headers,
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
  avatar_url: string | null
  role: string
  xp: number
  streak: number
  level: number
}

export type Quote = { id: number; text: string; author: string; category: string; is_featured: boolean; saved: boolean }
export type Dashboard = { user: User; featured_quote: Quote | null; latest_check_in: CheckIn | null; rank: number; level_progress: number }
export type CheckIn = { id: number; mood: string; needs: Array<string>; energy: number; stress: number; thoughts: string | null; gratitude: string | null; completed: boolean; created_at: string }
export type Comment = { id: number; post_id: number; author: string; initials: string; text: string; created_at: string }
export type Post = { id: number; author: string; initials: string; text: string; image_url: string | null; created_at: string; likes: number; dislikes: number; loves: number; my_reaction: 'like' | 'dislike' | 'love' | null; comments: Array<Comment>; mine: boolean }
export type Game = { id: number; name: string; players: string; icon: string; color: string; is_featured: boolean }
export type Room = { id: number; name: string; game: string; players: number; max_players: number; status: string; joined: boolean }
export type Match = { match_id: string; room_id: number; game: string; board: Array<Array<number>>; current_player: 1 | 2; winner: 1 | 2 | null; draw: boolean; move_count: number }
export type GameSession = { match_id: string; room_id: number; game: string; state: Record<string, any> }
export type LeaderboardEntry = { rank: number; user: User }

export const api = {
  register: (body: { name: string; email: string; password: string; confirm_password: string }) => apiFetch<{ user: User }>('/api/auth/register', { method: 'POST', body: JSON.stringify(body) }),
  login: (body: { email: string; password: string; remember_me: boolean }) => apiFetch<{ user: User }>('/api/auth/login', { method: 'POST', body: JSON.stringify(body) }),
  me: () => apiFetch<User>('/api/auth/me'),
  updateProfile: (body: { name: string }) => apiFetch<User>('/api/auth/me', { method: 'PATCH', body: JSON.stringify(body) }),
  updateAvatar: (image: File) => { const body = new FormData(); body.append('image', image); return apiFetch<User>('/api/auth/me/avatar', { method: 'POST', body }) },
  logout: () => apiFetch<void>('/api/auth/logout', { method: 'POST' }),
  dashboard: () => apiFetch<Dashboard>('/api/dashboard'),
  checkIns: (page = 1, limit = 20) => apiFetch<Array<CheckIn>>(`/api/check-ins?page=${page}&limit=${limit}`),
  createCheckIn: (body: Omit<CheckIn, 'id' | 'created_at'>) => apiFetch<CheckIn>('/api/check-ins', { method: 'POST', body: JSON.stringify(body) }),
  quotes: (category?: string, page = 1, limit = 4) => apiFetch<Array<Quote>>(`/api/quotes?page=${page}&limit=${limit}${category ? `&category=${encodeURIComponent(category)}` : ''}`),
  saveQuote: (id: number) => apiFetch<Quote>(`/api/quotes/${id}/save`, { method: 'POST' }),
  posts: (page = 1, limit = 10) => apiFetch<Array<Post>>(`/api/community/posts?page=${page}&limit=${limit}`),
  createPost: (text: string, image?: File) => {
    if (image) {
      const body = new FormData()
      body.append('text', text)
      body.append('image', image)
      return apiFetch<Post>('/api/community/posts/with-image', { method: 'POST', body })
    }
    return apiFetch<Post>('/api/community/posts', { method: 'POST', body: JSON.stringify({ text }) })
  },
  react: (id: number, kind: 'like' | 'dislike') => apiFetch<Post>(`/api/community/posts/${id}/reactions`, { method: 'POST', body: JSON.stringify({ kind }) }),
  reply: (id: number, text: string) => apiFetch<Comment>(`/api/community/posts/${id}/comments`, { method: 'POST', body: JSON.stringify({ text }) }),
  likedPosts: (page = 1, limit = 5) => apiFetch<Array<Post>>(`/api/community/activity/liked?page=${page}&limit=${limit}`),
  repliedPosts: (page = 1, limit = 5) => apiFetch<Array<Post>>(`/api/community/activity/replied?page=${page}&limit=${limit}`),
  games: (page = 1, limit = 20) => apiFetch<Array<Game>>(`/api/games?page=${page}&limit=${limit}`),
  rooms: (page = 1, limit = 10) => apiFetch<Array<Room>>(`/api/games/rooms?page=${page}&limit=${limit}`),
  createRoom: (body: { game_id: number; name: string; max_players: number }) => apiFetch<Room>('/api/games/rooms', { method: 'POST', body: JSON.stringify(body) }),
  joinRoom: (id: number) => apiFetch<Room>(`/api/games/rooms/${id}/join`, { method: 'POST' }),
  createMatch: (body: { room_id: number; with_bot: boolean; bot_difficulty: 'friendly' | 'thoughtful' }) => apiFetch<Match>('/api/games/matches', { method: 'POST', body: JSON.stringify(body) }),
  match: (id: string) => apiFetch<Match>(`/api/games/matches/${id}`),
  move: (id: string, column: number) => apiFetch<Match>(`/api/games/matches/${id}/moves`, { method: 'POST', body: JSON.stringify({ column }) }),
  createGameSession: (room_id: number) => apiFetch<GameSession>('/api/games/sessions', { method: 'POST', body: JSON.stringify({ room_id }) }),
  gameSession: (id: string) => apiFetch<GameSession>(`/api/games/sessions/${id}`),
  gameAction: (id: string, action: Record<string, any>) => apiFetch<GameSession>(`/api/games/sessions/${id}/actions`, { method: 'POST', body: JSON.stringify({ action }) }),
  leaderboard: (period: string, page = 1, limit = 10) => apiFetch<Array<LeaderboardEntry>>(`/api/leaderboard?period=${period}&page=${page}&limit=${limit}`),
}
