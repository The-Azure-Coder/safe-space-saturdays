const CONFIGURED_API_URL =
  import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

// In production, route API traffic through the web origin. This keeps the
// httpOnly session cookie first-party on mobile browsers that block cookies
// from a separate API hostname.
export const API_URL =
  typeof window !== 'undefined' && import.meta.env.PROD
    ? window.location.origin
    : CONFIGURED_API_URL

export const API_HEALTH_URL = `${API_URL}/health/ready`

export const googleLoginUrl = `${API_URL}/api/auth/google/start`

export function assetUrl(value: string): string {
  return value.startsWith('http://') || value.startsWith('https://')
    ? value
    : `${API_URL}${value}`
}

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export const MAX_API_WAKE_RETRIES = 12
export const API_REQUEST_TIMEOUT_MS = 45_000

export function shouldRetryApiRequest(
  failureCount: number,
  error: unknown,
): boolean {
  if (failureCount >= MAX_API_WAKE_RETRIES || !(error instanceof ApiError))
    return false
  return error.status === 0 || error.status >= 500
}

export function apiRetryDelay(attemptIndex: number): number {
  return Math.min(1_200 * 2 ** attemptIndex, 8_000)
}

export async function apiFetch<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const headers = new Headers(init?.headers)
  if (!(init?.body instanceof FormData))
    headers.set('Content-Type', 'application/json')
  let response: Response
  const controller = new AbortController()
  const timeout = window.setTimeout(
    () => controller.abort(),
    API_REQUEST_TIMEOUT_MS,
  )
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      signal: controller.signal,
      credentials: 'include',
      headers,
    })
  } catch {
    const timedOut = controller.signal.aborted
    throw new ApiError(
      0,
      timedOut
        ? 'Safe Space is taking a little longer to wake up. We will keep trying for you.'
        : 'We could not reach Safe Space Saturdays. Please try again in a moment.',
    )
  } finally {
    window.clearTimeout(timeout)
  }
  if (!response.ok) {
    const contentType = response.headers.get('content-type') ?? ''
    const body = contentType.includes('application/json')
      ? ((await response.json().catch(() => null)) as {
          detail?: unknown
        } | null)
      : null
    const detail = Array.isArray(body?.detail)
      ? body.detail
          .map((item) =>
            typeof item === 'object' && item !== null && 'msg' in item
              ? String(item.msg)
              : String(item),
          )
          .join('. ')
      : body?.detail
    const transient = [502, 503, 504].includes(response.status)
    throw new ApiError(
      response.status,
      detail == null
        ? transient
          ? 'Safe Space is waking up. Please try again in a moment.'
          : 'Something went wrong'
        : String(detail),
    )
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export type User = {
  id: number
  name: string
  email: string
  avatar_url: string | null
  is_online: boolean
  role: string
  xp: number
  streak: number
  level: number
  is_approved: boolean
}

export type Quote = {
  id: number
  text: string
  author: string
  category: string
  is_featured: boolean
  saved: boolean
  approval_status?: 'pending' | 'approved' | 'rejected'
  submitted_by_user_id?: number | null
}
export type Dashboard = {
  user: User
  featured_quote: Quote | null
  latest_check_in: CheckIn | null
  rank: number
  level_progress: number
}
export type AdminDashboard = {
  total_members: number
  pending_members: number
  open_bug_reports: number
  pending_quotes: number
  active_rooms: number
  total_quotes: number
}
export type CheckIn = {
  id: number
  mood: string
  needs: Array<string>
  energy: number
  stress: number
  thoughts: string | null
  gratitude: string | null
  completed: boolean
  created_at: string
}
export type Challenge = {
  id: number
  slug: string
  title: string
  description: string
  category: string
  icon: string
  color: string
  xp: number
  week_start: string
  active_until: string
  completed: boolean
  completed_at: string | null
  reflection: string | null
}
export type Challenges = {
  week_start: string
  active_until: string
  completed_count: number
  total_count: number
  xp_earned: number
  challenges: Array<Challenge>
}
export type Comment = {
  id: number
  post_id: number
  author: string
  initials: string
  avatar_url: string | null
  is_online: boolean
  text: string
  created_at: string
}
export type Post = {
  id: number
  author: string
  initials: string
  avatar_url: string | null
  is_online: boolean
  text: string
  image_url: string | null
  created_at: string
  likes: number
  dislikes: number
  loves: number
  my_reaction: 'like' | 'dislike' | 'love' | null
  comments: Array<Comment>
  mine: boolean
  post_type?: 'original' | 'shared_quote'
  shared_quote_id?: number | null
}
export type Game = {
  id: number
  name: string
  players: string
  icon: string
  color: string
  is_featured: boolean
}
export type Room = {
  id: number
  name: string
  game: string
  players: number
  max_players: number
  status: string
  joined: boolean
  is_host: boolean
  match_id: string | null
  ready: boolean
  fill_with_bots: boolean
  invite_token?: string | null
}
export type RoomParticipant = {
  user_id: number
  name: string
  avatar_url: string | null
  seat_index: number | null
  ready: boolean
  is_host: boolean
}
export type LeaderboardPeriod = 'day' | 'week' | 'month' | 'all'
export type RoomInvite = Pick<
  Room,
  'id' | 'name' | 'game' | 'players' | 'max_players' | 'status'
> & { invite_token: string }
export type Match = {
  match_id: string
  room_id: number
  game: string
  board: Array<Array<number>>
  current_player: 1 | 2
  winner: 1 | 2 | null
  draw: boolean
  move_count: number
  last_move: [number, number] | null
  winning_cells: Array<[number, number]>
  player: 1 | 2 | null
  players: Array<{ name: string; is_bot: boolean }>
}
export type GameSession = {
  match_id: string
  room_id: number
  game: string
  state: Record<string, any>
}
export type Winner = {
  position: number
  name: string
  avatar_url: string | null
  points: number
  match_points: number
  wins: number
  game: string
  created_at: string
}
export type LeaderboardEntry = { rank: number; user: User }
export type BugReport = {
  id: number
  user_id: number | null
  reporter_name: string
  reporter_email: string
  title: string
  description: string
  severity: string
  status: string
  page_url: string | null
  admin_note: string | null
  created_at: string
  updated_at: string
}

export const api = {
  googleAuthStatus: () =>
    apiFetch<{ enabled: boolean }>('/api/auth/google/status'),
  register: (body: {
    name: string
    email: string
    password: string
    confirm_password: string
  }) =>
    apiFetch<{
      user: User
      pending_approval: boolean
      message?: string | null
    }>('/api/auth/register', { method: 'POST', body: JSON.stringify(body) }),
  login: (body: { email: string; password: string; remember_me: boolean }) =>
    apiFetch<{
      user: User
      pending_approval?: boolean
      message?: string | null
    }>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  me: () => apiFetch<User>('/api/auth/me'),
  updateProfile: (body: { name: string }) =>
    apiFetch<User>('/api/auth/me', {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),
  changePassword: (body: {
    current_password: string
    new_password: string
    confirm_password: string
  }) =>
    apiFetch<void>('/api/auth/me/password', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  updateAvatar: (image: File) => {
    const body = new FormData()
    body.append('image', image)
    return apiFetch<User>('/api/auth/me/avatar', { method: 'POST', body })
  },
  logout: () => apiFetch<void>('/api/auth/logout', { method: 'POST' }),
  dashboard: () => apiFetch<Dashboard>('/api/dashboard'),
  currentChallenges: () => apiFetch<Challenges>('/api/challenges/current'),
  challengeHistory: (page = 1, limit = 10) =>
    apiFetch<Array<Challenge>>(
      `/api/challenges/history?page=${page}&limit=${limit}`,
    ),
  completeChallenge: (id: number, reflection?: string) =>
    apiFetch<Challenge>(`/api/challenges/${id}/complete`, {
      method: 'POST',
      body: JSON.stringify({ reflection: reflection?.trim() || null }),
    }),
  checkIns: (page = 1, limit = 20) =>
    apiFetch<Array<CheckIn>>(`/api/check-ins?page=${page}&limit=${limit}`),
  createCheckIn: (body: Omit<CheckIn, 'id' | 'created_at'>) =>
    apiFetch<CheckIn>('/api/check-ins', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  quotes: (category?: string, page = 1, limit = 4, savedOnly = false) =>
    apiFetch<Array<Quote>>(
      `/api/quotes?page=${page}&limit=${limit}${category ? `&category=${encodeURIComponent(category)}` : ''}${savedOnly ? '&saved_only=true' : ''}`,
    ),
  submitQuote: (body: { text: string; author: string; category: string }) =>
    apiFetch<Quote>('/api/quotes/submissions', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  savedQuotes: (page = 1, limit = 5) =>
    apiFetch<Array<Quote>>(
      `/api/quotes?page=${page}&limit=${limit}&saved_only=true`,
    ),
  saveQuote: (id: number) =>
    apiFetch<Quote>(`/api/quotes/${id}/save`, { method: 'POST' }),
  posts: (page = 1, limit = 10) =>
    apiFetch<Array<Post>>(`/api/community/posts?page=${page}&limit=${limit}`),
  createPost: (text: string, image?: File) => {
    if (image) {
      const body = new FormData()
      body.append('text', text)
      body.append('image', image)
      return apiFetch<Post>('/api/community/posts/with-image', {
        method: 'POST',
        body,
      })
    }
    return apiFetch<Post>('/api/community/posts', {
      method: 'POST',
      body: JSON.stringify({ text }),
    })
  },
  shareQuote: (id: number) =>
    apiFetch<Post>(`/api/community/posts/from-quote/${id}`, { method: 'POST' }),
  react: (id: number, kind: 'like' | 'dislike') =>
    apiFetch<Post>(`/api/community/posts/${id}/reactions`, {
      method: 'POST',
      body: JSON.stringify({ kind }),
    }),
  reply: (id: number, text: string) =>
    apiFetch<Comment>(`/api/community/posts/${id}/comments`, {
      method: 'POST',
      body: JSON.stringify({ text }),
    }),
  likedPosts: (page = 1, limit = 5) =>
    apiFetch<Array<Post>>(
      `/api/community/activity/liked?page=${page}&limit=${limit}`,
    ),
  repliedPosts: (page = 1, limit = 5) =>
    apiFetch<Array<Post>>(
      `/api/community/activity/replied?page=${page}&limit=${limit}`,
    ),
  games: (page = 1, limit = 20) =>
    apiFetch<Array<Game>>(`/api/games?page=${page}&limit=${limit}`),
  winners: (page = 1, limit = 5) =>
    apiFetch<Array<Winner>>(`/api/games/winners?page=${page}&limit=${limit}`),
  rooms: (page = 1, limit = 10) =>
    apiFetch<Array<Room>>(`/api/games/rooms?page=${page}&limit=${limit}`),
  createRoom: (body: {
    game_id: number
    name: string
    max_players: number
    fill_with_bots?: boolean
    bot_difficulty?: 'friendly' | 'thoughtful'
  }) =>
    apiFetch<Room>('/api/games/rooms', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  joinRoom: (id: number) =>
    apiFetch<Room>(`/api/games/rooms/${id}/join`, { method: 'POST' }),
  room: (id: number) => apiFetch<Room>(`/api/games/rooms/${id}`),
  roomParticipants: (id: number) =>
    apiFetch<Array<RoomParticipant>>(`/api/games/rooms/${id}/participants`),
  roomInvite: (token: string) =>
    apiFetch<RoomInvite>(
      `/api/games/rooms/invite/${encodeURIComponent(token)}`,
    ),
  joinRoomInvite: (token: string) =>
    apiFetch<Room>(
      `/api/games/rooms/invite/${encodeURIComponent(token)}/join`,
      { method: 'POST' },
    ),
  joinGuestRoom: (token: string, name: string) =>
    apiFetch<{ room: Room; user: User }>(
      `/api/games/rooms/invite/${encodeURIComponent(token)}/guest`,
      {
        method: 'POST',
        body: JSON.stringify({ name }),
      },
    ),
  createMatch: (body: {
    room_id: number
    with_bot: boolean
    bot_difficulty: 'friendly' | 'thoughtful'
  }) =>
    apiFetch<Match>('/api/games/matches', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  match: (id: string) => apiFetch<Match>(`/api/games/matches/${id}`),
  move: (id: string, column: number) =>
    apiFetch<Match>(`/api/games/matches/${id}/moves`, {
      method: 'POST',
      body: JSON.stringify({ column }),
    }),
  createGameSession: (room_id: number, fill_with_bots = true) =>
    apiFetch<GameSession>('/api/games/sessions', {
      method: 'POST',
      body: JSON.stringify({ room_id, fill_with_bots }),
    }),
  setRoomReady: (id: number) =>
    apiFetch<Room>(`/api/games/rooms/${id}/ready`, { method: 'POST' }),
  changeRoomGame: (id: number, game_id: number) =>
    apiFetch<Room>(`/api/games/rooms/${id}/game`, {
      method: 'POST',
      body: JSON.stringify({ game_id }),
    }),
  endRoom: (id: number) =>
    apiFetch<void>(`/api/games/rooms/${id}`, { method: 'DELETE' }),
  cleanupBotRooms: () =>
    apiFetch<{ deleted: number }>('/api/games/rooms/cleanup-bot-rooms', {
      method: 'POST',
    }),
  gameSession: (id: string) =>
    apiFetch<GameSession>(`/api/games/sessions/${id}`),
  gameAction: (id: string, action: Record<string, any>) =>
    apiFetch<GameSession>(`/api/games/sessions/${id}/actions`, {
      method: 'POST',
      body: JSON.stringify({ action }),
    }),
  leaderboard: (period: LeaderboardPeriod, page = 1, limit = 10) =>
    apiFetch<Array<LeaderboardEntry>>(
      `/api/leaderboard?period=${period}&page=${page}&limit=${limit}`,
    ),
  leaderboardMe: (period: LeaderboardPeriod) =>
    apiFetch<LeaderboardEntry>(`/api/leaderboard/me?period=${period}`),
  createBugReport: (body: {
    title: string
    description: string
    severity: string
    page_url?: string
  }) =>
    apiFetch<BugReport>('/api/bug-reports', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  adminBugReports: (page = 1, limit = 20, status?: string) =>
    apiFetch<Array<BugReport>>(
      `/api/admin/bug-reports?page=${page}&limit=${limit}${status ? `&report_status=${encodeURIComponent(status)}` : ''}`,
    ),
  adminDashboard: () => apiFetch<AdminDashboard>('/api/admin/dashboard'),
  updateBugReport: (
    id: number,
    body: { status: string; admin_note?: string },
  ) =>
    apiFetch<BugReport>(`/api/admin/bug-reports/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),
  adminUsers: (page = 1, limit = 20, search = '') =>
    apiFetch<Array<User>>(
      `/api/admin/users?page=${page}&limit=${limit}${search ? `&search=${encodeURIComponent(search)}` : ''}`,
    ),
  updateAdminUser: (
    id: number,
    body: { role?: string; is_approved?: boolean },
  ) =>
    apiFetch<User>(`/api/admin/users/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),
  resetUserPassword: (id: number, password: string) =>
    apiFetch<void>(`/api/admin/users/${id}/password-reset`, {
      method: 'POST',
      body: JSON.stringify({ password }),
    }),
  adminQuotes: (page = 1, limit = 20, category = '') =>
    apiFetch<Array<Quote>>(
      `/api/admin/quotes?page=${page}&limit=${limit}${category ? `&category=${encodeURIComponent(category)}` : ''}`,
    ),
  createAdminQuote: (body: {
    text: string
    author: string
    category: string
    is_featured: boolean
  }) =>
    apiFetch<Quote>('/api/admin/quotes', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  updateAdminQuote: (
    id: number,
    body: {
      text: string
      author: string
      category: string
      is_featured: boolean
      approval_status?: string
    },
  ) =>
    apiFetch<Quote>(`/api/admin/quotes/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),
  deleteAdminQuote: (id: number) =>
    apiFetch<void>(`/api/admin/quotes/${id}`, { method: 'DELETE' }),
}
