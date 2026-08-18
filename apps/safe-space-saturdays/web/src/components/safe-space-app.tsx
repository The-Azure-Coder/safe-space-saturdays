import { useEffect, useRef, useState } from 'react'
import type { ChangeEvent, ComponentType, FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate } from '@tanstack/react-router'
import {
  ArrowRight,
  Bug,
  BookmarkSimple,
  CaretLeft,
  CaretRight,
  CaretDown,
  Check,
  CheckCircle,
  CheckSquare,
  ChatCircleDots,
  DotsThreeVertical,
  EnvelopeSimple,
  Eye,
  EyeSlash,
  Flame,
  GameController,
  Heart,
  House,
  Leaf,
  LockKey,
  List,
  PencilSimple,
  Palette,
  Quotes,
  ShieldCheck,
  Smiley,
  Sparkle,
  Star,
  Trophy,
  ThumbsUp,
  UserCircle,
  UsersThree,
  X,
} from '@phosphor-icons/react'

import { ApiError, api, apiRetryDelay, assetUrl, googleLoginUrl, shouldRetryApiRequest } from '../lib/api'
import type { CheckIn, CommunityApplication, LeaderboardPeriod, Post, Quote } from '../lib/api'
import { GeneralLoader } from './general-loader'

type Screen =
  | 'home'
  | 'check-in'
  | 'challenges'
  | 'games'
  | 'leaderboard'
  | 'community'
  | 'quotes'
  | 'login'
  | 'registration'
  | 'profile'
  | 'admin'
  | 'contact'

type Icon = ComponentType<{
  size?: number
  weight?: 'regular' | 'fill' | 'duotone'
  color?: string
}>

const staffRoles = new Set(['admin', 'super_admin', 'manager', 'moderator'])

const navItems: Array<{ href: string; label: string; icon: Icon }> = [
  { href: '/', label: 'Home', icon: House },
  { href: '/check-in', label: 'Daily Check-In', icon: Heart },
  { href: '/games', label: 'Games', icon: GameController },
  { href: '/leaderboard', label: 'Leaderboard', icon: Trophy },
  { href: '/community', label: 'Community', icon: UsersThree },
  { href: '/quotes', label: 'Quotes', icon: Quotes },
  { href: '/contact', label: 'Contact', icon: EnvelopeSimple },
]

const moods = [
  { label: 'Great', icon: '😄' },
  { label: 'Good', icon: '🙂' },
  { label: 'Okay', icon: '😐' },
  { label: 'Not Great', icon: '🙁' },
  { label: 'Struggling', icon: '😔' },
]

const MAX_SOURCE_IMAGE_BYTES = 40_000_000

type GameDefinition = {
  id?: number
  name: string
  players: string
  description: string
  icon: Icon | string
  color: string
}

function gameRoomCapacity(name: string | undefined): number {
  const normalized = name?.trim().toLowerCase() ?? ''
  if (normalized === 'connect four' || normalized === 'connect-four' || normalized === 'trivia' || normalized === 'trivia battle') return 2
  return 4
}

const games: Array<GameDefinition> = [
  {
    name: 'Ludo',
    players: '2–4 players',
    description: 'Roll, race, and make a little room for friendly competition.',
    icon: '/assets/game-ludo.png',
    color: 'sage',
  },
  {
    name: 'Dominoes',
    players: '2–4 players',
    description: 'Match the ends, play your hand, and keep the table flowing.',
    icon: '/assets/game-dominoes.png',
    color: 'peach',
  },
  {
    name: 'Trivia Battle',
    players: '2+ players',
    description: 'Put your curious mind to work across bright, playful categories.',
    icon: '/assets/game-trivia.png',
    color: 'lilac',
  },
  {
    name: 'Connect Four',
    players: '2 players',
    description: 'Think one move ahead and connect four before your rival does.',
    icon: '/assets/game-connect-four.png',
    color: 'blue',
  },
  {
    name: 'Scribble',
    players: '2–4 players',
    description: 'Draw something wonderfully imperfect and see who can guess it.',
    icon: '/assets/game-scribble.png',
    color: 'coral',
  },
  {
    name: 'ABC Fast or Slow',
    players: '2–6 players',
    description: 'Race the clock, think creatively, and find one-of-a-kind answers.',
    icon: '/assets/game-abc-fast-slow.png',
    color: 'sage',
  },
]

function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <Link
      className={`brand-mark ${compact ? 'brand-mark--compact' : ''}`}
      to="/"
      aria-label="Safe Space Saturdays home"
    >
      <img
        className="brand-mark__image"
        src="/assets/safe-space-saturdays-logo.jpeg"
        alt="Safe Space Saturdays — you are not alone"
      />
    </Link>
  )
}

function ProfileLevelBadge({ level }: { level: number }) {
  return (
    <span
      className="profile-level-badge"
      aria-label={`Level ${level}`}
      title={`Level ${level}`}
    >
      <Star size={12} weight="fill" aria-hidden="true" />
      <span>LV {level}</span>
    </span>
  )
}

function PageHeader({ screen }: { screen: Screen }) {
  const currentUser = useQuery({
    queryKey: ['me'],
    queryFn: api.me,
    retry: false,
    refetchInterval: 60_000,
  })
  const queryClient = useQueryClient()
  const [menuOpen, setMenuOpen] = useState(false)
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const profileMenuRef = useRef<HTMLDivElement>(null)
  const logout = useMutation({
    mutationFn: api.logout,
    onSuccess: () => {
      queryClient.clear()
      window.location.href = '/login'
    },
  })
  const displayName = currentUser.data?.name
  useEffect(() => {
    setMenuOpen(false)
    setMobileNavOpen(false)
  }, [screen])
  useEffect(() => {
    const closeOnOutsideClick = (event: PointerEvent) => {
      if (
        profileMenuRef.current &&
        !profileMenuRef.current.contains(event.target as Node)
      )
        setMenuOpen(false)
    }
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setMenuOpen(false)
    }
    document.addEventListener('pointerdown', closeOnOutsideClick)
    document.addEventListener('keydown', closeOnEscape)
    return () => {
      document.removeEventListener('pointerdown', closeOnOutsideClick)
      document.removeEventListener('keydown', closeOnEscape)
    }
  }, [])
  return (
    <header className="app-header">
      <Logo compact />
      <nav
        id="main-navigation"
        className={mobileNavOpen ? 'app-nav app-nav--mobile-open' : 'app-nav'}
        aria-label="Main navigation"
      >
        {navItems.map(({ href, label, icon: NavIcon }) => (
          <Link
            onClick={() => {
              setMobileNavOpen(false)
              setMenuOpen(false)
            }}
            className={
              isActive(screen, href)
                ? 'app-nav__link app-nav__link--active'
                : 'app-nav__link'
            }
            to={href}
            key={href}
          >
            <NavIcon
              size={22}
              weight={isActive(screen, href) ? 'fill' : 'regular'}
              aria-hidden="true"
            />
            <span>{label}</span>
          </Link>
        ))}
        {displayName && (
          <div className="app-nav__mobile-account">
            <Link
              onClick={() => setMobileNavOpen(false)}
              className={
                screen === 'profile'
                  ? 'app-nav__link app-nav__link--active'
                  : 'app-nav__link'
              }
              to="/profile"
            >
              <UserCircle
                size={22}
                weight={screen === 'profile' ? 'fill' : 'regular'}
                aria-hidden="true"
              />
              <span>Profile &amp; settings</span>
              {currentUser.data && (
                <ProfileLevelBadge level={currentUser.data.level} />
              )}
            </Link>
            {currentUser.data && staffRoles.has(currentUser.data.role) && (
              <Link
                onClick={() => setMobileNavOpen(false)}
                className={
                  screen === 'admin'
                    ? 'app-nav__link app-nav__link--active'
                    : 'app-nav__link'
                }
                to="/admin"
              >
                <ShieldCheck
                  size={22}
                  weight={screen === 'admin' ? 'fill' : 'regular'}
                  aria-hidden="true"
                />
                <span>Admin portal</span>
              </Link>
            )}
            <button
              className="app-nav__link app-nav__link--button"
              type="button"
              onClick={() => {
                setMobileNavOpen(false)
                logout.mutate()
              }}
              disabled={logout.isPending}
            >
              <X size={22} aria-hidden="true" />
              <span>{logout.isPending ? 'Signing out…' : 'Log out'}</span>
            </button>
          </div>
        )}
      </nav>
      <button
        className="mobile-nav-toggle"
        type="button"
        aria-label={
          mobileNavOpen ? 'Close navigation menu' : 'Open navigation menu'
        }
        aria-expanded={mobileNavOpen}
        aria-controls="main-navigation"
        onClick={() => setMobileNavOpen((open) => !open)}
      >
        {mobileNavOpen ? (
          <X size={22} aria-hidden="true" />
        ) : (
          <List size={22} aria-hidden="true" />
        )}
      </button>
      {displayName ? (
        <div className="profile-menu-wrap" ref={profileMenuRef}>
          <button
            className="profile-menu"
            type="button"
            aria-label={`Open ${displayName} profile menu, level ${currentUser.data?.level ?? 1}, ${currentUser.data?.is_online ? 'online' : 'offline'}`}
            aria-expanded={menuOpen}
            aria-haspopup="menu"
            onClick={() => setMenuOpen((open) => !open)}
          >
            <Avatar
              initials={displayName[0].toUpperCase()}
              color="gold"
              imageUrl={currentUser.data?.avatar_url}
              online={currentUser.data?.is_online}
            />
            <span className="profile-menu__name">{displayName}</span>
            {currentUser.data && (
              <ProfileLevelBadge level={currentUser.data.level} />
            )}
            <CaretDown size={16} aria-hidden="true" />
          </button>
          {menuOpen && (
            <div className="profile-dropdown" role="menu">
              <Link
                to="/profile"
                role="menuitem"
                onClick={() => setMenuOpen(false)}
              >
                Profile & settings
              </Link>
              {currentUser.data && staffRoles.has(currentUser.data.role) && (
                <Link
                  to="/admin"
                  role="menuitem"
                  onClick={() => setMenuOpen(false)}
                >
                  Admin portal
                </Link>
              )}
              <button
                type="button"
                role="menuitem"
                onClick={() => logout.mutate()}
                disabled={logout.isPending}
              >
                {logout.isPending ? 'Signing out…' : 'Log out'}
              </button>
            </div>
          )}
        </div>
      ) : (
        <div className="auth-actions" aria-label="Account actions">
          <Link className="auth-actions__login" to="/login">
            Log in
          </Link>
          <Link
            className="button button--primary button--small"
            to="/registration"
          >
            Sign up
          </Link>
        </div>
      )}
    </header>
  )
}

function isActive(screen: Screen, href: string) {
  if (href === '/') return screen === 'home'
  return href.slice(1) === screen
}

function PageFooter() {
  return (
    <footer className="page-footer">
      <span className="footer-leaf">❧</span>
      <span className="footer-heart">♡</span>
      <span>You are not alone. You belong here.</span>
      <Link className="page-footer__link" to="/contact">Join the community</Link>
      <span className="footer-leaf footer-leaf--right">❧</span>
    </footer>
  )
}

function SectionHeading({
  eyebrow,
  title,
  description,
}: {
  eyebrow?: string
  title: string
  description?: string
}) {
  return (
    <div className="section-heading">
      {eyebrow && <span className="eyebrow">{eyebrow}</span>}
      <h1>
        {title}{' '}
        <span className="heart-doodle" aria-hidden="true">
          ♡
        </span>
      </h1>
      {description && <p>{description}</p>}
    </div>
  )
}

function ContentSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="content-skeleton" aria-label="Loading content">
      {Array.from({ length: rows }, (_, index) => (
        <div className="content-skeleton__row" key={index}>
          <span className="content-skeleton__avatar" />
          <span className="content-skeleton__copy">
            <i />
            <i />
            <i />
          </span>
        </div>
      ))}
    </div>
  )
}

function EmptyState({ title, message }: { title: string; message: string }) {
  return (
    <div className="empty-state" role="status">
      <Sparkle size={28} weight="fill" aria-hidden="true" />
      <div>
        <strong>{title}</strong>
        <p>{message}</p>
      </div>
    </div>
  )
}

function StatCard({
  icon: StatIcon,
  label,
  value,
  detail,
  tone = 'sage',
  progress,
}: {
  icon: Icon
  label: string
  value: string
  detail: string
  tone?: string
  progress?: number
}) {
  return (
    <article className={`stat-card stat-card--${tone}`}>
      <div className="stat-card__label">
        <StatIcon size={22} weight="fill" aria-hidden="true" />{' '}
        <span>{label}</span>
      </div>
      <div className="stat-card__value">
        {value} <small>{detail}</small>
      </div>
      {progress !== undefined ? (
        <div className="progress-track" aria-label={`${progress}% complete`}>
          <span style={{ width: `${progress}%` }} />
        </div>
      ) : (
        <p>Keep it going!</p>
      )}
    </article>
  )
}

function PaginationControls({
  page,
  itemCount,
  pageSize,
  onPageChange,
  label = 'Results',
}: {
  page: number
  itemCount: number
  pageSize: number
  onPageChange: (page: number) => void
  label?: string
}) {
  const hasNext = itemCount === pageSize
  if (page === 1 && !hasNext) return null
  return (
    <nav className="pagination-controls" aria-label={`${label} pagination`}>
      <button
        className="button button--secondary button--small"
        type="button"
        disabled={page === 1}
        onClick={() => onPageChange(page - 1)}
      >
        Previous
      </button>
      <span aria-live="polite">Page {page}</span>
      <button
        className="button button--secondary button--small"
        type="button"
        disabled={!hasNext}
        onClick={() => onPageChange(page + 1)}
      >
        Next
      </button>
    </nav>
  )
}

function Avatar({
  initials,
  color = 'sage',
  imageUrl,
  online = false,
}: {
  initials: string
  color?: string
  imageUrl?: string | null
  online?: boolean
}) {
  return (
    <span className={`avatar avatar--${color}`}>
      {imageUrl ? <img src={assetUrl(imageUrl)} alt="" /> : initials}
      <span
        className={`avatar__presence${online ? ' avatar__presence--online' : ''}`}
        role="img"
        aria-label={online ? 'Online now' : 'Offline'}
        title={online ? 'Online now' : 'Offline'}
      />
    </span>
  )
}

function AuthLayout({ mode }: { mode: 'login' | 'registration' }) {
  const [showPassword, setShowPassword] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [formError, setFormError] = useState('')
  const [resetMessage, setResetMessage] = useState('')
  const [passwordValue, setPasswordValue] = useState('')
  const [confirmPasswordValue, setConfirmPasswordValue] = useState('')
  const [rememberMe, setRememberMe] = useState(true)
  const isLogin = mode === 'login'
  const googleAuth = useQuery({
    queryKey: ['google-auth-status'],
    queryFn: api.googleAuthStatus,
    retry: 4,
    retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 8000),
    staleTime: 5 * 60 * 1000,
  })
  useEffect(() => {
    const error = new URLSearchParams(window.location.search).get('oauth_error')
    if (!error) return
    const messages: Record<string, string> = {
      cancelled: 'Google sign-in was cancelled. You can try again whenever you are ready.',
      pending_approval: 'Your account is awaiting approval before you can sign in.',
      account_conflict: 'This email is already linked to another Google account. Please use your original sign-in method.',
      unavailable: 'Google sign-in is temporarily unavailable. Please use your email and password.',
      failed: 'Google sign-in could not be completed. Please try again.',
    }
    setFormError(messages[error] ?? 'Google sign-in could not be completed. Please try again.')
    window.history.replaceState({}, '', window.location.pathname)
  }, [])
  const mutation = useMutation({
    mutationFn: (body: {
      name?: string
      email: string
      password: string
      confirm_password?: string
      remember_me?: boolean
    }) =>
      isLogin
        ? api.login({
            email: body.email,
            password: body.password,
            remember_me: body.remember_me ?? false,
          })
        : api.register({
            name: body.name ?? '',
            email: body.email,
            password: body.password,
            confirm_password: body.confirm_password ?? '',
          }),
    retry: shouldRetryApiRequest,
    retryDelay: apiRetryDelay,
    onSuccess: (result) => {
      setSubmitted(true)
      if (isLogin || !result.pending_approval) window.location.href = '/'
      else
        setFormError(
          result.message ??
            'Your account is awaiting approval before you can sign in.',
        )
    },
  })
  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    const name = String(data.get('name') ?? '').trim()
    const email = String(data.get('email') ?? '').trim()
    const password = String(data.get('password') ?? '')
    const confirmPassword = String(data.get('confirm-password') ?? '')
    if (!isLogin && name.length < 2)
      return setFormError('Please enter your full name.')
    if (!isLogin && password.length < 10)
      return setFormError('Your password must be at least 10 characters.')
    if (!isLogin && password !== confirmPassword)
      return setFormError('Passwords do not match.')
    setFormError('')
    mutation.mutate({
      name,
      email,
      password,
      confirm_password: confirmPassword,
      remember_me: rememberMe,
    })
  }
  return (
    <main className="auth-page">
      <section className="auth-intro">
        <Logo />
        <h1>
          {isLogin ? 'You are not alone.' : 'Come as you are.'}{' '}
          <span className="heart-doodle">♡</span>
        </h1>
        <p>
          {isLogin
            ? 'A gentle place to reconnect, reflect, and find your people.'
            : 'This is a space to breathe, be seen, and belong. We’re here to listen, support, and walk alongside you.'}
        </p>
        <img
          src="/assets/community-circle.png"
          alt="A group of people gathered together in a supportive circle"
        />
      </section>
      <section className="auth-panel" aria-labelledby="auth-title">
        <span className="auth-panel__leaf" aria-hidden="true">
          ❧
        </span>
        <h2 id="auth-title">
          {isLogin ? 'Welcome back' : 'Create your safe space'}
        </h2>
        <p className="auth-panel__intro">
          {isLogin
            ? 'It’s good to have you here.'
            : 'Join a community that cares. You are not alone.'}
        </p>
        {submitted && (
          <div className="form-success" role="status">
            <CheckCircle size={20} weight="fill" />{' '}
            {isLogin ? 'Welcome back.' : 'Your account is ready to begin.'}
          </div>
        )}
        {(formError || mutation.isError) && (
          <div className="form-error" role="alert">
            {formError ||
              (mutation.error instanceof Error ? mutation.error.message : '') ||
              'We could not complete that request.'}
            </div>
        )}
        {mutation.isPending && <GeneralLoader label="Signing you in…" />}
        {googleAuth.data?.enabled !== false && (
          <>
            <a className="google-auth-button" href={googleLoginUrl}>
              <svg aria-hidden="true" className="google-mark" viewBox="0 0 24 24" width="20" height="20">
                <path fill="#4285f4" d="M21.6 12.23c0-.71-.06-1.4-.18-2.07H12v3.92h5.38a4.6 4.6 0 0 1-2 3.02v2.55h3.24c1.9-1.75 2.98-4.33 2.98-7.42Z" />
                <path fill="#34a853" d="M12 22c2.7 0 4.98-.9 6.64-2.43l-3.24-2.54c-.9.6-2.05.96-3.4.96-2.61 0-4.82-1.76-5.61-4.13H3.04v2.62A10 10 0 0 0 12 22Z" />
                <path fill="#fbbc05" d="M6.39 13.86A6.02 6.02 0 0 1 6.08 12c0-.65.11-1.28.31-1.86V7.52H3.04A10 10 0 0 0 2 12c0 1.61.38 3.14 1.04 4.48l3.35-2.62Z" />
                <path fill="#ea4335" d="M12 6.01c1.47 0 2.78.5 3.82 1.49l2.88-2.88A9.67 9.67 0 0 0 12 2a10 10 0 0 0-8.96 5.52l3.35 2.62C7.18 7.77 9.39 6.01 12 6.01Z" />
              </svg>
              <span>{isLogin ? 'Continue with Google' : 'Sign up with Google'}</span>
            </a>
            <div className="auth-divider" aria-hidden="true">
              <span>or continue with email</span>
            </div>
          </>
        )}
        <form onSubmit={onSubmit} noValidate>
          {!isLogin && (
            <label>
              Full name
              <input
                name="name"
                type="text"
                autoComplete="name"
                placeholder="Your full name"
                required
              />
            </label>
          )}
          <label>
            Email {isLogin && <span className="sr-only">address</span>}
            <span className="input-wrap">
              <EnvelopeSimple size={20} aria-hidden="true" />
              <input
                name="email"
                type="email"
                autoComplete="email"
                inputMode="email"
                autoCapitalize="none"
                spellCheck="false"
                placeholder="you@example.com"
                required
              />
            </span>
          </label>
          <label>
            Password
            <span className="input-wrap">
              <LockKey size={20} aria-hidden="true" />
              <input
                name="password"
                type={showPassword ? 'text' : 'password'}
                autoComplete={isLogin ? 'current-password' : 'new-password'}
                placeholder={
                  isLogin ? '••••••••••' : 'Create a strong password'
                }
                minLength={!isLogin ? 10 : undefined}
                required
                value={passwordValue}
                onChange={(event) => setPasswordValue(event.target.value)}
              />
              <button
                className="input-action"
                type="button"
                onClick={() => setShowPassword((value) => !value)}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <EyeSlash size={20} /> : <Eye size={20} />}
              </button>
            </span>
            {!isLogin && (
              <small className="field-help">Use at least 10 characters.</small>
            )}
          </label>
          {!isLogin && (
            <label>
              Confirm password
              <span className="input-wrap">
                <LockKey size={20} aria-hidden="true" />
                <input
                  name="confirm-password"
                  type="password"
                  autoComplete="new-password"
                  placeholder="Confirm your password"
                  minLength={10}
                  required
                  value={confirmPasswordValue}
                  onChange={(event) =>
                    setConfirmPasswordValue(event.target.value)
                  }
                  aria-invalid={
                    confirmPasswordValue.length > 0 &&
                    passwordValue !== confirmPasswordValue
                  }
                />
                {confirmPasswordValue.length > 0 &&
                  passwordValue === confirmPasswordValue &&
                  passwordValue.length >= 10 && (
                    <Check
                      size={20}
                      className="input-valid"
                      aria-label="Passwords match"
                    />
                  )}
              </span>
            </label>
          )}
          {isLogin ? (
            <div className="form-row">
              <label className="checkbox-label checkbox-label--remember">
                <input
                  name="remember_me"
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(event) => setRememberMe(event.target.checked)}
                />{' '}
                <span>Remember me</span>
              </label>
              <button
                className="text-link"
                type="button"
                onClick={() =>
                  setResetMessage(
                    'Password reset is not enabled in this pre-launch build. Please contact the project administrator.',
                  )
                }
              >
                Forgot password?
              </button>
            </div>
          ) : (
            <label className="checkbox-label">
              <input type="checkbox" required />{' '}
              <span>
                I agree to the Safe Space Saturdays Privacy Policy and Terms of
                Service.
              </span>
            </label>
          )}
          {resetMessage && (
            <p className="form-help" role="status">
              {resetMessage}
            </p>
          )}
          <button
            className="button button--primary button--wide"
            type="submit"
            disabled={mutation.isPending}
          >
            {mutation.isPending
              ? 'Please wait…'
              : isLogin
                ? 'Log in'
                : 'Create account'}
          </button>
        </form>
        <p className="auth-switch">
          {isLogin ? 'New here?' : 'Already have an account?'}{' '}
          <Link to={isLogin ? '/registration' : '/login'}>
            {isLogin ? 'Create an account' : 'Log in'}
          </Link>
        </p>
      </section>
    </main>
  )
}

function HomeScreen() {
  const dashboard = useQuery({
    queryKey: ['dashboard'],
    queryFn: api.dashboard,
  })
  const data = dashboard.data
  return (
    <>
      <PageHeader screen="home" />
      <main className="page-content home-page">
        <WelcomeCarousel />
        {dashboard.isLoading && (
          <GeneralLoader label="Gathering your safe-space details…" />
        )}
        <section className="stats-grid">
          <StatCard
            icon={Flame}
            label="Login Streak"
            value={data ? String(data.user.streak) : '—'}
            detail="days"
          />
          <StatCard
            icon={Star}
            label="Total XP"
            value={data ? data.user.xp.toLocaleString() : '—'}
            detail="XP"
            tone="peach"
            progress={data?.level_progress}
          />
          <StatCard
            icon={Leaf}
            label="Level"
            value={data ? String(data.user.level) : '—'}
            detail="Rooted"
            tone="sage"
          />
        </section>
        <section className="dashboard-grid">
          <article className="quote-card">
            <div className="card-title">
              <Quotes size={22} weight="fill" /> <span>Daily Quote</span>
            </div>
            <blockquote>
              “
              {data?.featured_quote?.text ??
                'Take a moment for yourself today.'}
              ”
            </blockquote>
            <cite>
              — {data?.featured_quote?.author ?? 'Safe Space Saturdays'}
            </cite>
          </article>
          <article className="check-card">
            <div className="card-title">
              <Smiley size={22} weight="fill" />{' '}
              <span>How are you feeling today?</span>
            </div>
            <p>Your check-in helps us support you better.</p>
            <div className="mood-row">
              {moods.map((mood) => (
                <Link className="mood-option" key={mood.label} to="/check-in">
                  <span>{mood.icon}</span>
                  <small>{mood.label}</small>
                </Link>
              ))}
            </div>
            <Link className="button button--primary" to="/check-in">
              Check In
            </Link>
          </article>
          <article className="community-card">
            <div className="card-title">
              <UsersThree size={22} weight="fill" />{' '}
              <span>Community Corner</span>
            </div>
            <h3>You are not alone.</h3>
            <p>Join a space that listens, encourages, and grows together.</p>
            <Link className="button button--lilac" to="/community">
              Explore Community <ArrowRight size={16} />
            </Link>
          </article>
      </section>
        <GameStrip />
        {/* <ComingSoonBanner /> */}
      </main>
      <PageFooter />
    </>
  )
}

const welcomeSlides = [
  {
    eyebrow: 'Welcome back',
    title: 'Welcome back to your safe space.',
    body: 'Here, we talk. We listen. We support. We heal. We grow. You are not alone.',
    cta: 'Start a check-in',
    to: '/check-in',
    tone: 'sage',
    icon: Heart,
  },
  {
    eyebrow: 'Small steps count',
    title: 'Progress can be soft.',
    body: 'Celebrate the tiny wins too. They are how a steadier, kinder rhythm begins.',
    cta: 'Visit the community',
    to: '/community',
    tone: 'peach',
    icon: Sparkle,
  },
  {
    eyebrow: 'Make room to breathe',
    title: 'You do not have to rush healing.',
    body: 'Find a quote, settle your shoulders, and give yourself permission to move gently.',
    cta: 'Find a little calm',
    to: '/quotes',
    tone: 'lilac',
    icon: Leaf,
  },
] as const

function WelcomeCarousel() {
  const [activeSlide, setActiveSlide] = useState(0)
  useEffect(() => {
    const timer = window.setInterval(
      () => setActiveSlide((slide) => (slide + 1) % welcomeSlides.length),
      6500,
    )
    return () => window.clearInterval(timer)
  }, [])
  const slide = welcomeSlides[activeSlide]
  const SlideIcon = slide.icon
  const move = (direction: -1 | 1) =>
    setActiveSlide(
      (current) =>
        (current + direction + welcomeSlides.length) % welcomeSlides.length,
    )
  return (
    <section
      className={`welcome-carousel welcome-carousel--${slide.tone}`}
      aria-roledescription="carousel"
      aria-label="A little encouragement"
    >
      <div
        key={`copy-${activeSlide}`}
        className="welcome-carousel__copy"
        aria-live="polite"
      >
        <span className="welcome-carousel__eyebrow">{slide.eyebrow}</span>
        <h2>{slide.title}</h2>
        <p>{slide.body}</p>
        <Link className="button button--primary button--small" to={slide.to}>
          {slide.cta} <ArrowRight size={16} />
        </Link>
      </div>
      <div key={`art-${activeSlide}`} className="welcome-carousel__art">
        <img
          className="welcome-carousel__image"
          src="/assets/community-circle.png"
          alt="Friends supporting one another in a safe space"
        />
        <span className="welcome-carousel__sun" aria-hidden="true" />
        <span
          className="welcome-carousel__flower welcome-carousel__flower--one"
          aria-hidden="true"
        >
          ✦
        </span>
        <span
          className="welcome-carousel__flower welcome-carousel__flower--two"
          aria-hidden="true"
        >
          ✿
        </span>
        <span className="welcome-carousel__icon" aria-hidden="true">
          <SlideIcon size={36} weight="fill" />
        </span>
      </div>
      <div className="welcome-carousel__controls">
        <button
          type="button"
          aria-label="Previous encouragement"
          onClick={() => move(-1)}
        >
          <CaretLeft size={20} />
        </button>
        <div className="welcome-carousel__dots">
          {welcomeSlides.map((item, index) => (
            <button
              type="button"
              key={item.title}
              className={
                index === activeSlide
                  ? 'welcome-carousel__dot welcome-carousel__dot--active'
                  : 'welcome-carousel__dot'
              }
              aria-label={`Show encouragement ${index + 1}`}
              aria-current={index === activeSlide ? 'true' : undefined}
              onClick={() => setActiveSlide(index)}
            />
          ))}
        </div>
        <button
          type="button"
          aria-label="Next encouragement"
          onClick={() => move(1)}
        >
          <CaretRight size={20} />
        </button>
      </div>
    </section>
  )
}

function ComingSoonBanner() {
  return (
    <section className="coming-soon-banner" aria-labelledby="coming-soon-title">
      <div className="coming-soon-banner__mark" aria-hidden="true">
        ✦
      </div>
      <div>
        <span className="eyebrow">Game night is on its way</span>
        <h2 id="coming-soon-title">
          A little more play is coming soon{' '}
          <span className="heart-doodle">♡</span>
        </h2>
        <p>
          We’re thoughtfully building the rooms, rules, and friendly bot
          experience. Until then, there is always space to check in, connect,
          and grow together.
        </p>
      </div>
      <Link className="button button--small button--primary" to="/community">
        Stay connected <ArrowRight size={16} />
      </Link>
    </section>
  )
}

void ComingSoonBanner

function GameStrip() {
  const navigate = useNavigate()
  const [activeIndex, setActiveIndex] = useState(0)
  const catalog = useQuery({
    queryKey: ['games', 'home'],
    queryFn: () => api.games(1, 20),
    retry: false,
  })
  const launch = useMutation({
    mutationFn: async (game: GameDefinition) => {
      const catalogGame = catalog.data?.find(
        (item) =>
          item.name.toLowerCase() === game.name.toLowerCase() ||
          item.name
            .toLowerCase()
            .includes(game.name.toLowerCase().split(' ')[0]),
      )
      if (!catalogGame) throw new Error('Open Games to load this game')
      const room = await api.createRoom({
        game_id: catalogGame.id,
        name: `${catalogGame.name} · Friendly bot`,
        max_players: 2,
      })
      if (catalogGame.name === 'Connect Four') {
        const match = await api.createMatch({
          room_id: room.id,
          with_bot: true,
          bot_difficulty: 'friendly',
        })
        return { kind: 'connect-four' as const, id: match.match_id }
      }
      const match = await api.createGameSession(room.id)
      return { kind: 'session' as const, id: match.match_id }
    },
    onSuccess: (match) => {
      if (match.kind === 'connect-four')
        navigate({ to: '/games/play/$matchId', params: { matchId: match.id } })
      else
        navigate({
          to: '/games/session/$matchId',
          params: { matchId: match.id },
        })
    },
    onError: () => navigate({ to: '/games' }),
  })
  useEffect(() => {
    const timer = window.setInterval(
      () => setActiveIndex((index) => (index + 1) % games.length),
      6000,
    )
    return () => window.clearInterval(timer)
  }, [])
  const activeGame = games[activeIndex]
  const move = (direction: -1 | 1) =>
    setActiveIndex(
      (index) => (index + direction + games.length) % games.length,
    )
  return (
    <section
      className={`game-strip game-strip--${activeGame.color}`}
      aria-roledescription="carousel"
      aria-label="Featured games"
    >
      <div className="section-row">
        <div className="card-title">
          <GameController size={22} weight="fill" /> <span>Featured Games</span>
        </div>
        <Link to="/games">
          View all games <ArrowRight size={16} />
        </Link>
      </div>
      <div className="game-feature" key={activeGame.name}>
        <div className="game-feature__copy" aria-live="polite">
          <span className="eyebrow">A little game night</span>
          <h2>{activeGame.name}</h2>
          <p>{activeGame.description}</p>
          <div className="game-feature__meta">
            <span>{activeGame.players}</span>
            <button
              className="button button--primary button--small"
              type="button"
              onClick={() => launch.mutate(activeGame)}
              disabled={catalog.isLoading || launch.isPending}
            >
              {launch.isPending ? 'Setting up…' : 'Play now'} <ArrowRight size={16} />
            </button>
          </div>
        </div>
        <div className="game-feature__art" aria-hidden="true">
          <img src={activeGame.icon as string} alt="" />
          <span className="game-feature__spark game-feature__spark--one">✦</span>
          <span className="game-feature__spark game-feature__spark--two">✿</span>
        </div>
      </div>
      <div className="game-strip__controls">
        <button type="button" aria-label="Previous featured game" onClick={() => move(-1)}>
          <CaretLeft size={18} />
        </button>
        <div className="game-strip__dots">
          {games.map((game, index) => (
            <button
              type="button"
              key={game.name}
              className={index === activeIndex ? 'is-active' : ''}
              aria-label={`Show ${game.name}`}
              aria-current={index === activeIndex ? 'true' : undefined}
              onClick={() => setActiveIndex(index)}
            />
          ))}
        </div>
        <button type="button" aria-label="Next featured game" onClick={() => move(1)}>
          <CaretRight size={18} />
        </button>
      </div>
    </section>
  )
}

function formatCooldown(milliseconds: number) {
  const totalSeconds = Math.max(0, Math.ceil(milliseconds / 1000))
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60
  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
}

function AdminScreen() {
  const profile = useQuery({ queryKey: ['me'], queryFn: api.me, retry: false })
  const [tab, setTab] = useState<'reports' | 'users' | 'quotes' | 'applications'>('reports')
  const [reportStatus, setReportStatus] = useState('')
  const [applicationStatus, setApplicationStatus] = useState('pending')
  const [search, setSearch] = useState('')
  const [quoteText, setQuoteText] = useState('')
  const [quoteAuthor, setQuoteAuthor] = useState('Safe Space Saturdays')
  const [quoteCategory, setQuoteCategory] = useState('Encouragement')
  const adminDashboard = useQuery({
    queryKey: ['admin-dashboard'],
    queryFn: api.adminDashboard,
    enabled: Boolean(profile.data && staffRoles.has(profile.data.role)),
  })
  const reports = useQuery({
    queryKey: ['admin-reports', reportStatus],
    queryFn: () => api.adminBugReports(1, 50, reportStatus || undefined),
    enabled: Boolean(profile.data && staffRoles.has(profile.data.role)),
  })
  const users = useQuery({
    queryKey: ['admin-users', search],
    queryFn: () => api.adminUsers(1, 50, search),
    enabled: Boolean(profile.data && staffRoles.has(profile.data.role)),
  })
  const quotes = useQuery({
    queryKey: ['admin-quotes'],
    queryFn: () => api.adminQuotes(1, 100),
    enabled: Boolean(profile.data && staffRoles.has(profile.data.role)),
  })
  const applications = useQuery({
    queryKey: ['admin-community-applications', applicationStatus],
    queryFn: () => api.adminCommunityApplications(1, 50, applicationStatus),
    enabled: Boolean(profile.data && staffRoles.has(profile.data.role)),
  })
  const reportUpdate = useMutation({
    mutationFn: ({
      id,
      status,
      admin_note,
    }: {
      id: number
      status: string
      admin_note?: string
    }) => api.updateBugReport(id, { status, admin_note }),
    onSuccess: () => reports.refetch(),
  })
  const roleUpdate = useMutation({
    mutationFn: ({ id, role, is_approved, email_notifications_enabled }: { id: number; role?: string; is_approved?: boolean; email_notifications_enabled?: boolean }) =>
      api.updateAdminUser(id, { role, is_approved, email_notifications_enabled }),
    onSuccess: () => users.refetch(),
  })
  const reset = useMutation({
    mutationFn: ({ id, password }: { id: number; password: string }) =>
      api.resetUserPassword(id, password),
  })
  const createQuote = useMutation({
    mutationFn: api.createAdminQuote,
    onSuccess: () => {
      setQuoteText('')
      quotes.refetch()
    },
  })
  const quoteUpdate = useMutation({
    mutationFn: ({ id, quote, approval_status }: { id: number; quote: { text: string; author: string; category: string; is_featured: boolean }; approval_status: string }) =>
      api.updateAdminQuote(id, { text: quote.text, author: quote.author, category: quote.category, is_featured: quote.is_featured, approval_status }),
    onSuccess: () => quotes.refetch(),
  })
  const applicationUpdate = useMutation({
    mutationFn: ({ id, status, admin_note }: { id: number; status: CommunityApplication['status']; admin_note?: string }) =>
      api.updateCommunityApplication(id, { status, admin_note }),
    onSuccess: () => applications.refetch(),
  })
  const applicationResend = useMutation({
    mutationFn: api.resendCommunityApplication,
    onSuccess: () => applications.refetch(),
  })
  const weeklyNotification = useMutation({
    mutationFn: api.sendWeeklyPerformerNotification,
  })
  const dailyNotification = useMutation({
    mutationFn: api.sendDailyCheckinNotification,
  })
  if (profile.isLoading)
    return (
      <>
        <PageHeader screen="admin" />
        <main className="page-content">
          <GeneralLoader label="Loading admin workspace…" />
        </main>
      </>
    )
  if (profile.isError || !profile.data || !staffRoles.has(profile.data.role))
    return (
      <>
        <PageHeader screen="admin" />
        <main className="page-content">
          <section className="empty-state-card">
            <ShieldCheck size={34} />
            <h1>Admin access required</h1>
            <p>This workspace is restricted to approved administrators.</p>
            <Link className="button button--secondary" to="/">
              Return home
            </Link>
          </section>
        </main>
        <PageFooter />
      </>
    )
  return (
    <>
      <PageHeader screen="admin" />
      <main className="page-content admin-page">
        <SectionHeading
          eyebrow="Steward workspace"
          title="Admin portal"
          description="Review member feedback, protect accounts, and keep the community content thoughtful."
        />
        <section className="admin-overview" aria-label="Admin overview">
          <div className="admin-overview__heading">
            <div>
              <span className="eyebrow">Overview</span>
              <h2>Admin dashboard</h2>
            </div>
            <div className="admin-overview__actions">
              <button
                className="button button--secondary button--small"
                type="button"
                onClick={() => dailyNotification.mutate()}
                disabled={dailyNotification.isPending}
              >
                <Heart size={17} weight="duotone" />
                {dailyNotification.isPending ? 'Sending kind reminder…' : 'Send today’s kind reminder'}
              </button>
              {adminDashboard.isFetching && <GeneralLoader label="Updating…" />}
            </div>
          </div>
          {dailyNotification.data && <p className="admin-notification-result">Sent to {dailyNotification.data.sent} of {dailyNotification.data.recipients} opted-in members.</p>}
          {adminDashboard.isLoading ? (
            <ContentSkeleton rows={1} />
          ) : adminDashboard.data ? (
            <div className="admin-overview__grid">
              <AdminMetric icon={UsersThree} label="Members" value={adminDashboard.data.total_members} detail={adminDashboard.data.pending_members ? `${adminDashboard.data.pending_members} awaiting approval` : 'All approved'} />
              <AdminMetric icon={Bug} label="Open reports" value={adminDashboard.data.open_bug_reports} detail="Needs attention" />
              <AdminMetric icon={Quotes} label="Pending quotes" value={adminDashboard.data.pending_quotes} detail={`${adminDashboard.data.total_quotes} total quotes`} />
              <AdminMetric icon={GameController} label="Live rooms" value={adminDashboard.data.active_rooms} detail="Open or in play" />
              <AdminMetric icon={EnvelopeSimple} label="Applications" value={adminDashboard.data.pending_community_applications} detail="Awaiting review" />
            </div>
          ) : adminDashboard.isError ? (
            <p className="admin-overview__error">Overview data is temporarily unavailable.</p>
          ) : null}
        </section>
        <div className="admin-tabs" role="tablist" aria-label="Admin sections">
          <button
            className={tab === 'applications' ? 'admin-tab admin-tab--active' : 'admin-tab'}
            role="tab"
            aria-selected={tab === 'applications'}
            onClick={() => setTab('applications')}
            type="button"
          >
            <EnvelopeSimple size={18} /> Applications
          </button>
          <button
            className={
              tab === 'reports' ? 'admin-tab admin-tab--active' : 'admin-tab'
            }
            role="tab"
            aria-selected={tab === 'reports'}
            onClick={() => setTab('reports')}
            type="button"
          >
            <Bug size={18} /> Bug reports
          </button>
          <button
            className={
              tab === 'users' ? 'admin-tab admin-tab--active' : 'admin-tab'
            }
            role="tab"
            aria-selected={tab === 'users'}
            onClick={() => setTab('users')}
            type="button"
          >
            <UsersThree size={18} /> Users
          </button>
          <button
            className={
              tab === 'quotes' ? 'admin-tab admin-tab--active' : 'admin-tab'
            }
            role="tab"
            aria-selected={tab === 'quotes'}
            onClick={() => setTab('quotes')}
            type="button"
          >
            <Quotes size={18} /> Quotes
          </button>
        </div>
        {tab === 'applications' && (
          <section className="admin-panel">
            <div className="admin-panel__toolbar">
              <div>
                <h2>Community applications</h2>
                <p>Review requests to join the private WhatsApp community.</p>
              </div>
              <select aria-label="Filter community applications" value={applicationStatus} onChange={(event) => setApplicationStatus(event.target.value)}>
                <option value="pending">Pending</option>
                <option value="approved">Approved</option>
                <option value="rejected">Rejected</option>
                <option value="">All applications</option>
              </select>
            </div>
            {applications.isLoading && <ContentSkeleton rows={3} />}
            {applications.data?.length ? (
              <div className="admin-list">
                {applications.data.map((application) => (
                  <article className="admin-list-item application-list-item" key={application.id}>
                    <div className="admin-list-item__top">
                      <div>
                        <span className={`status-badge status-badge--${application.status}`}>{application.status}</span>
                        <h3>{application.name}</h3>
                        <small>{application.email}{application.phone ? ` · ${application.phone}` : ''} · {new Date(application.created_at).toLocaleString()}</small>
                      </div>
                      <select aria-label={`Update application for ${application.email}`} value={application.status} onChange={(event) => applicationUpdate.mutate({ id: application.id, status: event.target.value as CommunityApplication['status'], admin_note: application.admin_note ?? undefined })}>
                        <option value="pending">Pending</option>
                        <option value="approved">Approve</option>
                        <option value="rejected">Reject</option>
                      </select>
                    </div>
                    <p>{application.message}</p>
                    {application.status === 'approved' && <button className="button button--secondary button--small" type="button" onClick={() => applicationResend.mutate(application.id)} disabled={applicationResend.isPending}>{applicationResend.isPending ? 'Sending…' : application.email_sent_at ? 'Resend invite email' : 'Send invite email'}</button>}
                    {application.status === 'approved' && <small className="admin-list-item__meta">{application.email_sent_at ? `Invite email sent ${new Date(application.email_sent_at).toLocaleString()}.` : 'Email not sent yet — check Brevo settings and resend.'}</small>}
                  </article>
                ))}
              </div>
            ) : (!applications.isLoading && <div className="admin-empty"><EnvelopeSimple size={28} /><p>No applications in this view.</p></div>)}
          </section>
        )}
        {tab === 'reports' && (
          <section className="admin-panel">
            <div className="admin-panel__toolbar">
              <div>
                <h2>Bug reports</h2>
                <p>Keep a clear trail from report to resolution.</p>
              </div>
              <select
                aria-label="Filter bug reports"
                value={reportStatus}
                onChange={(event) => setReportStatus(event.target.value)}
              >
                <option value="">All statuses</option>
                <option value="open">Open</option>
                <option value="in_progress">In progress</option>
                <option value="resolved">Resolved</option>
                <option value="closed">Closed</option>
              </select>
            </div>
            {reports.isLoading && <ContentSkeleton rows={4} />}
            {reports.data?.length ? (
              <div className="admin-list">
                {reports.data.map((report) => (
                  <article className="admin-list-item" key={report.id}>
                    <div className="admin-list-item__top">
                      <div>
                        <span
                          className={`severity-badge severity-badge--${report.severity}`}
                        >
                          {report.severity}
                        </span>
                        <h3>{report.title}</h3>
                        <small>
                          {report.reporter_name} · {report.reporter_email} ·{' '}
                          {new Date(report.created_at).toLocaleString()}
                        </small>
                      </div>
                      <select
                        aria-label={`Update status for ${report.title}`}
                        value={report.status}
                        onChange={(event) =>
                          reportUpdate.mutate({
                            id: report.id,
                            status: event.target.value,
                            admin_note: report.admin_note ?? undefined,
                          })
                        }
                      >
                        <option value="open">Open</option>
                        <option value="in_progress">In progress</option>
                        <option value="resolved">Resolved</option>
                        <option value="closed">Closed</option>
                      </select>
                    </div>
                    <p>{report.description}</p>
                    <small className="admin-list-item__meta">
                      Reported from {report.page_url || 'unknown page'}
                    </small>
                  </article>
                ))}
              </div>
            ) : (
              !reports.isLoading && (
                <div className="admin-empty">
                  <Bug size={28} />
                  <p>No bug reports in this view.</p>
                </div>
              )
            )}
          </section>
        )}
        {tab === 'users' && (
          <section className="admin-panel">
            <div className="admin-user-toolbar">
              <div>
                <span className="eyebrow">Community care</span>
                <h2>User management</h2>
                <p>Shape access, support accounts, and choose who receives community emails.</p>
              </div>
              <div className="admin-user-toolbar__actions">
                <button
                  className="button button--secondary button--small"
                  type="button"
                  onClick={() => weeklyNotification.mutate()}
                  disabled={weeklyNotification.isPending}
                >
                  <Trophy size={17} weight="duotone" />
                  {weeklyNotification.isPending ? 'Sending podium…' : 'Email weekly podium'}
                </button>
                <input
                  aria-label="Search users"
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Search name or email"
                />
                {weeklyNotification.data && (
                  <small className="admin-user-toolbar__result">
                    Sent to {weeklyNotification.data.sent} of {weeklyNotification.data.recipients} opted-in members.
                  </small>
                )}
              </div>
            </div>
            {users.data?.length ? (
              <div className="admin-list">
                {users.data.map((member) => (
                  <article
                    className="admin-list-item admin-user-row"
                    key={member.id}
                  >
                    <div className="admin-user-identity">
                      <span className="admin-user-avatar"><UserCircle size={28} weight="duotone" /></span>
                      <div>
                        <h3>{member.name}</h3>
                        <small>{member.email}</small>
                        <div className="admin-user-badges">
                          <span>{member.role.replace('_', ' ')}</span>
                          <span className={member.is_approved ? 'is-positive' : 'is-pending'}>{member.is_approved ? 'Approved' : 'Awaiting approval'}</span>
                        </div>
                      </div>
                    </div>
                    <div className="admin-user-actions">
                      <select
                        aria-label={`Role for ${member.email}`}
                        value={member.role}
                        onChange={(event) =>
                          roleUpdate.mutate({
                            id: member.id,
                            role: event.target.value,
                          })
                        }
                      >
                        <option value="member">Member</option>
                        <option value="moderator">Moderator</option>
                        <option value="manager">Manager</option>
                        <option value="admin">Admin</option>
                        <option value="super_admin">Super admin</option>
                      </select>
                      <label className="admin-email-toggle" title="Allow this user to receive community emails">
                        <input
                          type="checkbox"
                          checked={member.email_notifications_enabled}
                          onChange={(event) =>
                            roleUpdate.mutate({
                              id: member.id,
                              email_notifications_enabled: event.target.checked,
                            })
                          }
                        />
                        <span className="admin-email-toggle__track" aria-hidden="true"><span /></span>
                        <span>{member.email_notifications_enabled ? 'Emails on' : 'Emails off'}</span>
                      </label>
                      {!member.is_approved && <button className="button button--secondary button--small" type="button" onClick={() => roleUpdate.mutate({ id: member.id, is_approved: true })}>Approve account</button>}
                      <button
                        className="button button--secondary button--small"
                        type="button"
                        onClick={() => {
                          const password = window.prompt(
                            `New password for ${member.email} (10+ characters)`,
                          )
                          if (password)
                            reset.mutate({ id: member.id, password })
                        }}
                      >
                        Reset password
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <div className="admin-empty">
                <UsersThree size={28} />
                <p>No users match this search.</p>
              </div>
            )}
          </section>
        )}
        {tab === 'quotes' && (
          <section className="admin-panel">
            <div className="admin-panel__toolbar">
              <div>
                <h2>Quote library</h2>
                <p>Add and curate the words members see across the app.</p>
              </div>
            </div>
            <form
              className="admin-quote-form"
              onSubmit={(event) => {
                event.preventDefault()
                createQuote.mutate({
                  text: quoteText.trim(),
                  author: quoteAuthor.trim(),
                  category: quoteCategory,
                  is_featured: false,
                })
              }}
            >
              <label>
                Quote
                <textarea
                  value={quoteText}
                  onChange={(event) => setQuoteText(event.target.value)}
                  minLength={3}
                  maxLength={2000}
                  required
                  placeholder="Write something encouraging…"
                />
              </label>
              <label>
                Author
                <input
                  value={quoteAuthor}
                  onChange={(event) => setQuoteAuthor(event.target.value)}
                  maxLength={120}
                  required
                />
              </label>
              <label>
                Category
                <select
                  value={quoteCategory}
                  onChange={(event) => setQuoteCategory(event.target.value)}
                >
                  <option>Encouragement</option>
                  <option>Rest</option>
                  <option>Growth</option>
                  <option>Connection</option>
                </select>
              </label>
              <button
                className="button button--primary"
                type="submit"
                disabled={createQuote.isPending}
              >
                {createQuote.isPending ? 'Adding…' : 'Add quote'}
              </button>
            </form>
            <div className="admin-list">
              {quotes.data?.map((quote) => (
                <article className="admin-list-item" key={quote.id}>
                  <div>
                    <h3>{quote.text}</h3>
                    <small>
                      — {quote.author} · {quote.category}
                      {quote.is_featured ? ' · Featured' : ''} · {quote.approval_status ?? 'approved'}
                    </small>
                  </div>
                  {quote.approval_status === 'pending' && <div className="admin-user-actions"><button className="button button--primary button--small" type="button" onClick={() => quoteUpdate.mutate({ id: quote.id, quote, approval_status: 'approved' })}>Approve</button><button className="button button--secondary button--small" type="button" onClick={() => quoteUpdate.mutate({ id: quote.id, quote, approval_status: 'rejected' })}>Reject</button></div>}
                </article>
              ))}
            </div>
          </section>
        )}
      </main>
      <PageFooter />
    </>
  )
}

function AdminMetric({
  icon: MetricIcon,
  label,
  value,
  detail,
}: {
  icon: Icon
  label: string
  value: number
  detail: string
}) {
  return (
    <article className="admin-metric">
      <div className="admin-metric__icon" aria-hidden="true">
        <MetricIcon size={22} weight="fill" />
      </div>
      <div>
        <span>{label}</span>
        <strong>{value.toLocaleString()}</strong>
        <small>{detail}</small>
      </div>
    </article>
  )
}

function GameTile({
  game,
  compact = false,
  onPlay,
}: {
  game: GameDefinition
  compact?: boolean
  onPlay?: () => void
}) {
  const GameIcon = typeof game.icon === 'string' ? null : game.icon
  const generatedAssets: Record<string, string> = {
    Ludo: '/assets/game-ludo.png',
    Dominoes: '/assets/game-dominoes.png',
    'Trivia Battle': '/assets/game-trivia.png',
    'Connect Four': '/assets/game-connect-four.png',
    Scribble: '/assets/game-scribble.png',
    'ABC Fast or Slow': '/assets/game-abc-fast-slow.png',
  }
  const generatedIcon =
    typeof game.icon === 'string' && game.icon.startsWith('/')
      ? game.icon
      : generatedAssets[game.name.trim()] ?? null
  return (
    <article
      className={`game-tile game-tile--${game.color} ${compact ? 'game-tile--compact' : ''}`}
    >
      <span className="game-tile__icon" aria-hidden="true">
        {generatedIcon ? (
          <img src={generatedIcon} alt="" />
        ) : GameIcon ? (
          <GameIcon size={compact ? 34 : 48} weight="duotone" />
        ) : null}
      </span>
      <h3>{game.name}</h3>
      {onPlay ? (
        <button
          className="button button--small button--primary"
          type="button"
          onClick={onPlay}
        >
          Play
        </button>
      ) : (
        <Link className="button button--small button--primary" to="/games">
          Play
        </Link>
      )}
      {!compact && <small>{game.players}</small>}
    </article>
  )
}

function CheckInScreen() {
  const [selectedMood, setSelectedMood] = useState('')
  const [needs, setNeeds] = useState<Array<string>>([])
  const [energy, setEnergy] = useState(3)
  const [stress, setStress] = useState(3)
  const [thoughts, setThoughts] = useState('')
  const [gratitude, setGratitude] = useState('')
  const [completedCheckIn, setCompletedCheckIn] = useState<CheckIn | null>(null)
  const [draftSaved, setDraftSaved] = useState(false)
  const queryClient = useQueryClient()
  const currentUser = useQuery({
    queryKey: ['me'],
    queryFn: api.me,
    retry: false,
  })
  const dashboard = useQuery({
    queryKey: ['dashboard'],
    queryFn: api.dashboard,
    retry: false,
  })
  const [now, setNow] = useState(() => Date.now())
  const latestCheckIn =
    completedCheckIn ?? dashboard.data?.latest_check_in ?? null
  const nextCheckInAt = latestCheckIn?.completed
    ? new Date(latestCheckIn.created_at).getTime() + 12 * 60 * 60 * 1000
    : 0
  const remainingCooldown = Math.max(0, nextCheckInAt - now)
  const cooldownActive = Boolean(
    latestCheckIn?.completed && remainingCooldown > 0,
  )
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(timer)
  }, [])
  const mutation = useMutation({
    mutationFn: api.createCheckIn,
    onSuccess: (checkIn) => {
      setCompletedCheckIn(checkIn)
      queryClient.invalidateQueries({ queryKey: ['me'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
  const submit = () => {
    if (!selectedMood) return
    mutation.mutate({
      mood: selectedMood,
      needs,
      energy,
      stress,
      thoughts: thoughts || null,
      gratitude: gratitude || null,
      completed: true,
    })
  }
  const saveDraft = () => {
    window.localStorage.setItem(
      'safe-space-checkin-draft',
      JSON.stringify({
        selectedMood,
        needs,
        energy,
        stress,
        thoughts,
        gratitude,
      }),
    )
    setDraftSaved(true)
  }
  if (cooldownActive && latestCheckIn)
    return (
      <>
        <PageHeader screen="check-in" />
        <main className="page-content checkin-complete-page">
          <section
            className="checkin-complete-card checkin-cooldown-card"
            aria-labelledby="checkin-complete-title"
          >
            <div className="checkin-cooldown-card__visual">
              <img
                src="/assets/community-circle.png"
                alt="Friends reflecting together in a supportive circle"
              />
              <span className="checkin-complete-card__icon">
                <CheckCircle size={34} weight="fill" />
              </span>
            </div>
            <span className="eyebrow">A moment kept for you</span>
            <h1 id="checkin-complete-title">Your check-in is complete.</h1>
            <p className="checkin-complete-card__intro">
              You made space to notice what is happening inside you. Take this
              time to let your reflection settle.
            </p>
            <div className="checkin-cooldown" role="timer" aria-live="polite">
              <small>Your next check-in opens in</small>
              <strong>{formatCooldown(remainingCooldown)}</strong>
              <span>Come back when you are ready to check in again.</span>
            </div>
            <CheckInReflection checkIn={latestCheckIn} />
            <div className="checkin-complete-actions">
              <Link className="button button--primary" to="/profile">
                Review your reflections
              </Link>
              <Link className="button button--secondary" to="/">
                Return home
              </Link>
            </div>
          </section>
        </main>
        <PageFooter />
      </>
    )
  return (
    <>
      <PageHeader screen="check-in" />
      <main className="page-content checkin-page">
        <div className="checkin-main">
          <SectionHeading
            title="Daily Check-In"
            description="Take a moment to check in with yourself. Your responses help us support you better."
          />
          <section className="form-card">
            <h2>
              <Smiley size={24} weight="fill" /> 1. How are you feeling today?
            </h2>
            <div className="mood-row mood-row--large">
              {moods.map((mood) => (
                <button
                  className={
                    selectedMood === mood.label
                      ? 'mood-option mood-option--selected'
                      : 'mood-option'
                  }
                  key={mood.label}
                  type="button"
                  onClick={() => setSelectedMood(mood.label)}
                >
                  <span>{mood.icon}</span>
                  <small>{mood.label}</small>
                </button>
              ))}
            </div>
          </section>
          <div className="two-column">
            <section className="form-card">
              <h2>
                <Leaf size={24} weight="fill" /> 2. What do you need today?
              </h2>
              <div className="choice-list">
                {[
                  'Rest',
                  'Encouragement',
                  'Space',
                  'Someone to Talk To',
                  'Motivation',
                  'Fun',
                  'Prayer / Positive Words',
                ].map((choice) => (
                  <button
                    type="button"
                    key={choice}
                    className={
                      needs.includes(choice)
                        ? 'choice-chip choice-chip--selected'
                        : 'choice-chip'
                    }
                    onClick={() =>
                      setNeeds((current) =>
                        current.includes(choice)
                          ? current.filter((item) => item !== choice)
                          : [...current, choice],
                      )
                    }
                  >
                    <span aria-hidden="true">
                      {choice === 'Rest'
                        ? '🛏️'
                        : choice === 'Encouragement'
                          ? '🧡'
                          : choice === 'Space'
                            ? '☁️'
                            : choice === 'Motivation'
                              ? '⭐'
                              : '🌿'}
                    </span>
                    {choice}
                  </button>
                ))}
              </div>
            </section>
            <section className="form-card">
              <h2>
                <Sparkle size={24} weight="fill" /> 3. Energy & Stress Check
              </h2>
              <RangeRow
                label="Energy Level"
                left="Low"
                right="High"
                value={energy}
                onChange={setEnergy}
              />
              <RangeRow
                label="Stress Level"
                left="Calm"
                right="Overwhelmed"
                value={stress}
                onChange={setStress}
                accent
              />
            </section>
          </div>
          <div className="two-column">
            <section className="form-card">
              <h2>
                <PencilSimple size={24} /> 4. What’s on your mind?
              </h2>
              <label className="field-label" htmlFor="checkin-thoughts">
                Your thoughts
                <textarea
                  id="checkin-thoughts"
                  placeholder="Write a few thoughts about your day..."
                  value={thoughts}
                  onChange={(event) => setThoughts(event.target.value)}
                />
              </label>
            </section>
            <section className="form-card">
              <h2>
                <Heart size={24} weight="fill" /> 5. What are you grateful for
                today?
              </h2>
              <label className="field-label" htmlFor="checkin-gratitude">
                A small gratitude
                <textarea
                  id="checkin-gratitude"
                  placeholder="Write about something you are grateful for..."
                  value={gratitude}
                  onChange={(event) => setGratitude(event.target.value)}
                />
              </label>
            </section>
          </div>
          <div className="privacy-note">
            <ShieldCheck size={24} weight="fill" />
            <span>
              <strong>Your privacy matters.</strong>
              <small>
                Your check-in is private and only you can see your responses.
              </small>
            </span>
          </div>
          {mutation.isError && (
            <div className="form-error" role="alert">
              {mutation.error.message}
            </div>
          )}
          {draftSaved && (
            <div className="form-success" role="status">
              Your check-in draft is saved on this device.
            </div>
          )}
          <div className="checkin-actions">
            <button
              className="button button--primary button--wide"
              type="button"
              onClick={submit}
              disabled={mutation.isPending || !selectedMood}
            >
              <CheckSquare size={22} />{' '}
              {mutation.isPending ? 'Saving…' : 'Complete Check-In'}
            </button>
            <button
              className="button button--secondary button--wide"
              type="button"
              onClick={saveDraft}
            >
              <BookmarkSimple size={22} />{' '}
              {draftSaved ? 'Saved for Later' : 'Save for Later'}
            </button>
          </div>
        </div>
        <aside className="checkin-sidebar">
          <StatCard
            icon={Flame}
            label="Current Streak"
            value={currentUser.data ? String(currentUser.data.streak) : '—'}
            detail="days"
          />
          <article className="quote-card">
            <div className="card-title">
              <Quotes size={22} weight="fill" /> <span>Quote of the Day</span>
            </div>
            <blockquote>
              “You don’t have to have it all figured out to move forward.”
            </blockquote>
            <cite>— Unknown</cite>
          </article>
          <article className="support-card">
            <div className="card-title">
              <UsersThree size={22} weight="fill" />{' '}
              <span>Need Extra Support?</span>
            </div>
            <p>
              You are not alone. Reach out to a trusted club leader or join the{' '}
              <em>Wellness Circle.</em>
            </p>
            <Link className="button button--lilac" to="/community">
              Join Wellness Circle
            </Link>
          </article>
        </aside>
      </main>
      <PageFooter />
    </>
  )
}

function RangeRow({
  label,
  left,
  right,
  accent = false,
  value,
  onChange,
}: {
  label: string
  left: string
  right: string
  accent?: boolean
  value?: number
  onChange?: (value: number) => void
}) {
  const inputId = `range-${label.toLowerCase().replaceAll(' ', '-')}`
  return (
    <div className={`range-row ${accent ? 'range-row--accent' : ''}`}>
      <div className="range-row__heading">
        <label htmlFor={inputId}>{label}</label>
        <output htmlFor={inputId}>{value ?? 3} / 5</output>
      </div>
      <input
        id={inputId}
        aria-label={label}
        type="range"
        min="1"
        max="5"
        value={value ?? 3}
        onInput={(event) => onChange?.(Number(event.currentTarget.value))}
        onChange={(event) => onChange?.(Number(event.currentTarget.value))}
      />
      <div className="range-labels">
        <span>{left}</span>
        <span>{right}</span>
      </div>
    </div>
  )
}

function CheckInReflection({ checkIn }: { checkIn: CheckIn }) {
  const date = new Date(checkIn.created_at)
  const moodMessage: Record<string, string> = {
    Great: 'You had some brightness to hold onto.',
    Good: 'There was some steadiness available to you.',
    Okay: 'You gave yourself permission to be honest.',
    'Not Great': 'You noticed a harder moment instead of hiding it.',
    Struggling: 'You reached for support while things felt heavy.',
  }
  return (
    <article className="checkin-reflection">
      <div className="checkin-reflection__header">
        <div>
          <span className="eyebrow">
            {date.toLocaleDateString(undefined, {
              month: 'long',
              day: 'numeric',
              year: 'numeric',
            })}
          </span>
          <h3>{checkIn.mood}</h3>
          <p>
            {moodMessage[checkIn.mood] ??
              'You made time to check in with yourself.'}
          </p>
        </div>
        <span className="checkin-reflection__badge">
          <CheckCircle size={18} weight="fill" /> Complete
        </span>
      </div>
      <div className="checkin-reflection__metrics">
        <span>
          <small>Energy</small>
          <strong>{checkIn.energy} / 5</strong>
        </span>
        <span>
          <small>Stress</small>
          <strong>{checkIn.stress} / 5</strong>
        </span>
        <span>
          <small>Needed</small>
          <strong>{checkIn.needs.length || '—'}</strong>
        </span>
      </div>
      <div className="checkin-reflection__body">
        <div>
          <small>What you needed</small>
          <p>
            {checkIn.needs.length
              ? checkIn.needs.join(' · ')
              : 'You did not name a specific need.'}
          </p>
        </div>
        <div>
          <small>Your reflection</small>
          <p>{checkIn.thoughts || 'You kept this reflection private.'}</p>
        </div>
        <div>
          <small>Gratitude</small>
          <p>{checkIn.gratitude || 'Nothing added this time.'}</p>
        </div>
      </div>
    </article>
  )
}

function QuotesScreen() {
  const [category, setCategory] = useState('All')
  const [activeQuoteIndex, setActiveQuoteIndex] = useState(0)
  const [quoteDraft, setQuoteDraft] = useState('')
  const [quoteAuthor, setQuoteAuthor] = useState('')
  const [shareStatus, setShareStatus] = useState('')
  const queryClient = useQueryClient()
  const quotes = useQuery({
    queryKey: ['quotes', category, 'slider'],
    queryFn: () => api.quotes(category, 1, 100),
  })
  const save = useMutation({
    mutationFn: api.saveQuote,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['quotes'] }),
  })
  const share = useMutation({
    mutationFn: (quoteId: number) => api.shareQuote(quoteId),
    onSuccess: () => {
      setShareStatus('Shared with the community.')
      queryClient.invalidateQueries({ queryKey: ['posts'] })
    },
  })
  const submitQuote = useMutation({
    mutationFn: api.submitQuote,
    onSuccess: () => {
      setQuoteDraft('')
      setQuoteAuthor('')
      setShareStatus(
        'Submitted for approval. It will appear in the quote library once reviewed.',
      )
    },
  })
  const allQuotes = quotes.data ?? []
  const activeQuote: Quote | undefined = allQuotes.length
    ? allQuotes[activeQuoteIndex] ?? allQuotes[0]
    : undefined
  const moveQuote = (direction: number) => {
    if (!allQuotes.length) return
    setActiveQuoteIndex(
      (current) => (current + direction + allQuotes.length) % allQuotes.length,
    )
  }
  useEffect(() => setActiveQuoteIndex(0), [category])
  useEffect(() => {
    if (activeQuoteIndex >= allQuotes.length && allQuotes.length)
      setActiveQuoteIndex(0)
  }, [activeQuoteIndex, allQuotes.length])
  useEffect(() => {
    if (allQuotes.length < 2) return
    const timer = window.setInterval(() => {
      setActiveQuoteIndex((current) => (current + 1) % allQuotes.length)
    }, 8000)
    return () => window.clearInterval(timer)
  }, [allQuotes.length])
  return (
    <>
      <PageHeader screen="quotes" />
      <main className="page-content quotes-page">
        {quotes.isLoading && <ContentSkeleton rows={3} />}
        <SectionHeading
          title="A little something for today"
          description="Words can uplift, comfort, and remind us we’re not alone. Take what you need, and come back anytime."
        />
        <article
          className="featured-quote"
          aria-roledescription="carousel"
          aria-label="Quote slider"
        >
          <span className="quote-mark">
            <Quotes size={28} weight="fill" />
          </span>
          <div
            key={activeQuote?.id ?? 'empty'}
            className="featured-quote__content"
          >
            <blockquote>
              “{activeQuote?.text ?? 'Take a moment for yourself today.'}”
            </blockquote>
            <cite>— {activeQuote?.author ?? 'Safe Space Saturdays'}</cite>
          </div>
          <div className="quote-slider-controls">
            <button
              type="button"
              className="quote-slider-arrow"
              aria-label="Previous quote"
              onClick={() => moveQuote(-1)}
              disabled={!allQuotes.length}
            >
              <CaretLeft size={20} />
            </button>
            <div className="carousel-dots" aria-label="Choose a quote">
              {allQuotes.map((quote, index) => (
                <button
                  type="button"
                  className={
                    index === activeQuoteIndex
                      ? 'carousel-dot carousel-dot--active'
                      : 'carousel-dot'
                  }
                  aria-label={`Show quote ${index + 1}`}
                  aria-current={index === activeQuoteIndex ? 'true' : undefined}
                  onClick={() => setActiveQuoteIndex(index)}
                  key={quote.id}
                />
              ))}
            </div>
            <button
              type="button"
              className="quote-slider-arrow"
              aria-label="Next quote"
              onClick={() => moveQuote(1)}
              disabled={!allQuotes.length}
            >
              <CaretRight size={20} />
            </button>
          </div>
        </article>
        <div className="quote-actions">
          <button
            className="button button--primary"
            type="button"
            disabled={!activeQuote}
            onClick={() => activeQuote && save.mutate(activeQuote.id)}
          >
            <BookmarkSimple size={20} />{' '}
            {activeQuote?.saved ? 'Saved' : 'Save this quote'}
          </button>
          <button
            className="button button--secondary"
            type="button"
            disabled={!activeQuote || share.isPending}
            onClick={() => activeQuote && share.mutate(activeQuote.id)}
          >
            <UsersThree size={20} />{' '}
            {share.isPending ? 'Sharing…' : 'Share with community'}
          </button>
        </div>
        <section
          className="quote-share-card"
          aria-labelledby="write-quote-title"
        >
          <div className="card-title">
            <PencilSimple size={22} />
            <span id="write-quote-title">Suggest a quote</span>
          </div>
          <p>
            Share a few words that might give someone else a little hope.
            Suggestions are reviewed before joining the quote library.
          </p>
          <form
            onSubmit={(event) => {
              event.preventDefault()
              const text = quoteDraft.trim()
              if (text)
                submitQuote.mutate({
                  text,
                  author: quoteAuthor.trim() || 'A Safe Space member',
                  category: category === 'All' ? 'Encouragement' : category,
                })
            }}
          >
            <label className="quote-author-field">
              Author <span>(optional)</span>
              <input
                value={quoteAuthor}
                onChange={(event) => setQuoteAuthor(event.target.value)}
                placeholder="Your name or source"
                maxLength={120}
                aria-label="Quote author"
              />
            </label>
            <textarea
              value={quoteDraft}
              onChange={(event) => {
                setQuoteDraft(event.target.value)
                setShareStatus('')
              }}
              placeholder="Write an encouraging thought or personal quote…"
              maxLength={1000}
              aria-label="Write your own quote"
            />
            <div className="quote-share-card__footer">
              <small>{quoteDraft.length}/1000</small>
              <button
                className="button button--primary button--small"
                type="submit"
                disabled={!quoteDraft.trim() || submitQuote.isPending}
              >
                {submitQuote.isPending ? 'Submitting…' : 'Submit quote'}
              </button>
            </div>
          </form>
          {shareStatus && (
            <p className="form-success" role="status">
              {shareStatus}
            </p>
          )}
          {submitQuote.isError && (
            <p className="form-error" role="alert">
              {submitQuote.error.message}
            </p>
          )}
        </section>
        <div className="filter-row">
          {['All', 'Encouragement', 'Rest', 'Growth', 'Connection'].map(
            (filter, index) => (
              <button
                className={
                  category === filter
                    ? 'filter-chip filter-chip--active'
                    : 'filter-chip'
                }
                type="button"
                onClick={() => setCategory(filter)}
                key={filter}
              >
                {index === 0 ? (
                  <Leaf size={18} />
                ) : index === 1 ? (
                  <Sparkle size={18} />
                ) : index === 2 ? (
                  <span>☾</span>
                ) : (
                  <Leaf size={18} />
                )}
                {filter}
              </button>
            ),
          )}
        </div>
      </main>
      <PageFooter />
    </>
  )
}

function CommunityScreen() {
  const [draft, setDraft] = useState('')
  const [page, setPage] = useState(1)
  const [sort, setSort] = useState('latest')
  const [communityTab, setCommunityTab] = useState<'feed' | 'announcements'>('feed')
  const [replyDrafts, setReplyDrafts] = useState<Record<number, string>>({})
  const [expandedReplies, setExpandedReplies] = useState<
    Record<number, boolean>
  >({})
  const [openReplyPostId, setOpenReplyPostId] = useState<number | null>(null)
  const [editingCommentId, setEditingCommentId] = useState<number | null>(null)
  const [editingCommentDraft, setEditingCommentDraft] = useState('')
  const [removedPostIds, setRemovedPostIds] = useState<number[]>([])
  const [moderatingPostId, setModeratingPostId] = useState<number | null>(null)
  const [announcementTitle, setAnnouncementTitle] = useState('')
  const [announcementBody, setAnnouncementBody] = useState('')
  const [announcementCtaLabel, setAnnouncementCtaLabel] = useState('')
  const [announcementCtaPath, setAnnouncementCtaPath] = useState('')
  const [imageFile, setImageFile] = useState<File | undefined>()
  const [imageError, setImageError] = useState('')
  const imageInput = useRef<HTMLInputElement>(null)
  const queryClient = useQueryClient()
  const profile = useQuery({ queryKey: ['me'], queryFn: api.me, retry: false })
  const canSeeAnnouncements = ['admin', 'super_admin'].includes(
    profile.data?.role ?? '',
  )
  const canModerateCommunity = staffRoles.has(profile.data?.role ?? '')
  const announcementsQuery = useQuery({
    queryKey: ['community-announcements'],
    queryFn: api.announcements,
  })
  const postsQuery = useQuery({
    queryKey: ['posts', page, sort],
    queryFn: () => api.posts(page, 10, sort),
    refetchInterval: 60_000,
  })
  const create = useMutation({
    mutationFn: () => api.createPost(draft.trim(), imageFile),
    onSuccess: (newPost) => {
      setDraft('')
      setImageFile(undefined)
      if (imageInput.current) imageInput.current.value = ''
      if (page === 1) {
        queryClient.setQueryData<Array<Post>>(['posts', page, sort], (current = []) => [
          newPost,
          ...current.filter((post) => post.id !== newPost.id),
        ].slice(0, 10))
      }
      void queryClient.invalidateQueries({ queryKey: ['posts'], refetchType: 'active' })
    },
  })
  const react = useMutation({
    mutationFn: ({ id, kind }: { id: number; kind: 'like' | 'dislike' }) =>
      api.react(id, kind),
    onSuccess: (updatedPost) => {
      queryClient.setQueryData<Array<Post>>(['posts', page, sort], (current = []) =>
        current.map((post) => post.id === updatedPost.id ? updatedPost : post),
      )
      void queryClient.invalidateQueries({ queryKey: ['posts'], refetchType: 'active' })
    },
  })
  const reply = useMutation({
    mutationFn: ({ id, text }: { id: number; text: string }) =>
      api.reply(id, text),
    onSuccess: async (_, variables) => {
      setReplyDrafts((drafts) => ({ ...drafts, [variables.id]: '' }))
      await queryClient.refetchQueries({ queryKey: ['posts', page, sort], type: 'active' })
      void queryClient.invalidateQueries({ queryKey: ['replied-posts'], refetchType: 'active' })
      setOpenReplyPostId(null)
    },
  })
  const editReply = useMutation({
    mutationFn: ({ id, text }: { id: number; text: string }) => api.editReply(id, text),
    onSuccess: async () => {
      setEditingCommentId(null)
      setEditingCommentDraft('')
      await queryClient.refetchQueries({ queryKey: ['posts', page, sort], type: 'active' })
    },
  })
  const moderatePost = useMutation({
    mutationFn: ({ id, action }: { id: number; action: 'flag' | 'unflag' | 'timeout' }) => api.moderatePost(id, action),
    onSuccess: (updatedPost) => {
      setModeratingPostId(null)
      queryClient.setQueryData<Array<Post>>(['posts', page, sort], (current = []) =>
        current.map((post) => post.id === updatedPost.id ? updatedPost : post),
      )
    },
    onError: () => setModeratingPostId(null),
  })
  const deletePost = useMutation({
    mutationFn: (id: number) => api.deletePost(id),
    onSuccess: (_, id) => {
      setModeratingPostId(null)
      setRemovedPostIds((current) => [...current, id])
    },
    onError: () => setModeratingPostId(null),
  })
  const createAnnouncement = useMutation({
    mutationFn: () => api.createAnnouncement({
      title: announcementTitle.trim(),
      body: announcementBody.trim(),
      cta_label: announcementCtaLabel.trim() || undefined,
      cta_path: announcementCtaPath.trim() || undefined,
    }),
    onSuccess: () => {
      setAnnouncementTitle('')
      setAnnouncementBody('')
      setAnnouncementCtaLabel('')
      setAnnouncementCtaPath('')
      void queryClient.invalidateQueries({ queryKey: ['community-announcements'] })
    },
  })
  const chooseImage = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return
    if (
      !['image/jpeg', 'image/png', 'image/webp'].includes(file.type) ||
      file.size > MAX_SOURCE_IMAGE_BYTES
    ) {
      setImageError('Choose a JPEG, PNG, or WebP image under 40 MB. Larger images are resized automatically.')
      setImageFile(undefined)
      event.currentTarget.value = ''
      return
    }
    setImageError('')
    setImageFile(file)
  }
  useEffect(() => {
    if (!canSeeAnnouncements && communityTab === 'announcements') setCommunityTab('feed')
  }, [canSeeAnnouncements, communityTab])
  return (
    <>
      <PageHeader screen="community" />
      <main className="page-content community-page">
        <section className="community-hero">
          <img
            src="/assets/community-circle.png"
            alt="A group of friends supporting each other"
          />
          <SectionHeading
            title="Community"
            description="A place to talk, listen, and feel less alone."
          />
        </section>
        <div className="community-promos">
          <PromoCard
            title="Wellness Circle"
            body="Open talks and guided conversations in a judgement-free space."
            cta="Join Circle"
            to="/community"
            tone="sage"
            icon="🌿"
          />
          <PromoCard
            title="Game Night"
            body="Play fun games, connect, and unwind with friends."
            cta="See Upcoming"
            to="/games"
            tone="peach"
            icon="🎮"
          />
          <PromoCard
            title="Small Wins"
            body="Celebrate progress, share wins, and uplift each other."
            cta="Share a Win"
            to="/community"
            tone="lilac"
            icon="🪴"
          />
        </div>
        <div className="community-tabs" role="tablist" aria-label="Community sections">
          <button className={communityTab === 'feed' ? 'community-tab community-tab--active' : 'community-tab'} type="button" role="tab" aria-selected={communityTab === 'feed'} onClick={() => setCommunityTab('feed')}><ChatCircleDots size={17} /> Community feed</button>
          {canSeeAnnouncements && <button className={communityTab === 'announcements' ? 'community-tab community-tab--active' : 'community-tab'} type="button" role="tab" aria-selected={communityTab === 'announcements'} onClick={() => setCommunityTab('announcements')}><Sparkle size={17} /> Announcements · admin</button>}
        </div>
        {communityTab === 'announcements' && canSeeAnnouncements ? <section className="announcement-admin-panel" role="tabpanel">
          <div className="card-title"><Sparkle size={24} weight="fill" /><span>Post an announcement</span></div>
          <p className="announcement-card__intro">Share a warm update with the whole community. It will appear in the public announcements card.</p>
          <form className="announcement-compose-form" onSubmit={(event) => { event.preventDefault(); if (announcementTitle.trim() && announcementBody.trim()) createAnnouncement.mutate() }}>
            <label>Title<input value={announcementTitle} onChange={(event) => setAnnouncementTitle(event.target.value)} maxLength={160} required placeholder="A little good news…" /></label>
            <label>Message<textarea value={announcementBody} onChange={(event) => setAnnouncementBody(event.target.value)} maxLength={1000} required placeholder="Tell the community what is happening." /></label>
            <div className="announcement-compose-form__grid"><label>Button label <input value={announcementCtaLabel} onChange={(event) => setAnnouncementCtaLabel(event.target.value)} maxLength={80} placeholder="Explore" /></label><label>Button link <input value={announcementCtaPath} onChange={(event) => setAnnouncementCtaPath(event.target.value)} maxLength={200} placeholder="/games" /></label></div>
            <button className="button button--primary" type="submit" disabled={!announcementTitle.trim() || !announcementBody.trim() || createAnnouncement.isPending}>{createAnnouncement.isPending ? 'Posting…' : 'Post announcement'}</button>
          </form>
        </section> : <div className="community-layout">
          <section className="conversation-card">
            <div className="section-row">
              <div className="card-title">
                <ChatCircleDots size={24} weight="fill" />
                <span>Community Conversations</span>
                <small>Share, support, and grow together.</small>
              </div>
              <button
                className="button button--primary"
                type="button"
                onClick={() =>
                  document.getElementById('post-composer')?.focus()
                }
              >
                <PencilSimple size={18} /> Start a Post
              </button>
            </div>
            <div className="post-composer">
              <label className="sr-only" htmlFor="post-composer">
                Share something with the community
              </label>
              <textarea
                id="post-composer"
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                placeholder="Share a small win or a kind thought…"
              />
              <div className="post-composer__controls">
                <label className="button button--secondary button--small post-image-picker">
                  <span>Attach image</span>
                  <input
                    ref={imageInput}
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    onChange={chooseImage}
                  />
                </label>
                {imageFile && <small>{imageFile.name}</small>}
                {imageError && (
                  <p className="form-error" role="alert">
                    {imageError}
                  </p>
                )}
                <button
                  className="button button--small button--primary"
                  type="button"
                  disabled={
                    !draft.trim() || create.isPending || Boolean(imageError)
                  }
                  onClick={() => create.mutate()}
                >
                  {create.isPending ? 'Posting…' : 'Post'}
                </button>
              </div>
            </div>
            <div className="community-feed-toolbar">
              <div><span className="eyebrow">The feed</span><strong>What’s being shared</strong></div>
              <label>Sort by<select aria-label="Sort community posts" value={sort} onChange={(event) => { setSort(event.target.value); setPage(1) }}><option value="latest">Latest</option><option value="earliest">Earliest</option><option value="most_liked">Most liked</option><option value="most_replied">Most replies</option></select></label>
            </div>
            {postsQuery.isLoading && <ContentSkeleton rows={4} />}
            {(postsQuery.data?.length ?? 0) === 0 && !postsQuery.isLoading ? (
              <EmptyState
                title="No conversations yet"
                message="Be the first to share a kind thought with the community."
              />
            ) : (
              (postsQuery.data ?? []).map((post) => (
                <article className="post-row" key={post.id}>
                  <Avatar
                    initials={post.initials}
                    color="sage"
                    imageUrl={post.avatar_url}
                    online={post.is_online}
                  />
                  <div className="post-row__body">
                    {removedPostIds.includes(post.id) ? <div className="moderation-placeholder" role="status"><ShieldCheck size={22} /><div><strong>This post was removed by a moderator.</strong><p>The conversation has been kept calm and safe for everyone.</p></div></div> : <>
                    <div className="post-row__meta">
                      <strong>{post.author}</strong>
                      <span>
                        • {new Date(post.created_at).toLocaleString()}
                      </span>
                    </div>
                    <p>{post.text}</p>
                    {post.post_type === 'shared_quote' && <span className="shared-quote-badge"><Quotes size={15} weight="fill" /> Shared quote</span>}
                    {post.image_url && (
                      <img
                        className="post-row__image"
                        src={assetUrl(post.image_url)}
                        alt={`Image shared by ${post.author}`}
                      />
                    )}
                    <div className="post-row__actions">
                      <button
                        className={
                          post.my_reaction === 'like'
                            ? 'reaction-button reaction-button--active'
                            : 'reaction-button'
                        }
                        type="button"
                        aria-label={`Like ${post.author}'s post`}
                        aria-pressed={post.my_reaction === 'like'}
                        onClick={() =>
                          react.mutate({ id: post.id, kind: 'like' })
                        }
                      >
                        <ThumbsUp size={17} weight="fill" /> <span>Like</span>{' '}
                        {post.likes}
                      </button>
                      <button
                        className="reaction-button"
                        type="button"
                        aria-expanded={openReplyPostId === post.id}
                        onClick={() =>
                          setOpenReplyPostId((current) =>
                            current === post.id ? null : post.id,
                          )
                        }
                      >
                        <ChatCircleDots size={17} /> <span>Reply</span>
                      </button>
                    </div>
                    {post.likes > 0 && <p className="post-liked-by"><ThumbsUp size={15} weight="fill" /> Liked by {post.liked_by.slice(0, 3).join(', ')}{post.likes > 3 ? ` and ${post.likes - 3} more` : ''}</p>}
                    {post.comments.length > 0 && (
                      <div
                        className="post-replies"
                        aria-label={`Replies to ${post.author}'s post`}
                      >
                        <button className="view-replies-button" type="button" aria-expanded={Boolean(expandedReplies[post.id])} onClick={() => setExpandedReplies((current) => ({ ...current, [post.id]: !current[post.id] }))}>
                          {expandedReplies[post.id] ? 'Hide replies' : `View ${post.comments.length} repl${post.comments.length === 1 ? 'y' : 'ies'}`}
                        </button>
                        {expandedReplies[post.id] && post.comments.map((comment) => (
                            <div className="post-reply" key={comment.id}>
                              <Avatar
                                initials={comment.initials}
                                color="lilac"
                                imageUrl={comment.avatar_url}
                                online={comment.is_online}
                              />
                              <div className="post-reply__content">
                                <strong>{comment.author}</strong>
                                {editingCommentId === comment.id ? (
                                  <form className="post-reply__edit" onSubmit={(event) => { event.preventDefault(); const text = editingCommentDraft.trim(); if (text) editReply.mutate({ id: comment.id, text }) }}>
                                    <input value={editingCommentDraft} onChange={(event) => setEditingCommentDraft(event.target.value)} maxLength={1000} autoFocus />
                                    <button className="button button--secondary button--small" type="submit" disabled={!editingCommentDraft.trim() || editReply.isPending}>Save</button>
                                    <button className="button button--secondary button--small" type="button" onClick={() => setEditingCommentId(null)}>Cancel</button>
                                  </form>
                                ) : <p>{comment.text}</p>}
                                {(comment.mine || comment.author === profile.data?.name) && editingCommentId !== comment.id && <button className="edit-reply-button" type="button" onClick={() => { setEditingCommentId(comment.id); setEditingCommentDraft(comment.text) }}>Edit</button>}
                              </div>
                            </div>
                          ))}
                      </div>
                    )}
                    {post.is_flagged && <p className="moderation-notice" role="status"><ShieldCheck size={15} /> This post is flagged for moderator review.</p>}
                    {canModerateCommunity && (
                      <div className="post-moderation-actions" aria-label={`Moderation actions for ${post.author}`}>
                        <button type="button" disabled={moderatingPostId === post.id} onClick={() => { setModeratingPostId(post.id); moderatePost.mutate({ id: post.id, action: post.is_flagged ? 'unflag' : 'flag' }) }}>{moderatingPostId === post.id ? 'Working…' : post.is_flagged ? 'Unflag' : 'Flag'}</button>
                        <button type="button" disabled={moderatingPostId === post.id} onClick={() => { setModeratingPostId(post.id); moderatePost.mutate({ id: post.id, action: 'timeout' }) }}>Timeout 2h</button>
                        <button type="button" disabled={moderatingPostId === post.id} onClick={() => { setModeratingPostId(post.id); deletePost.mutate(post.id) }}>{moderatingPostId === post.id ? 'Removing…' : 'Remove'}</button>
                      </div>
                    )}
                    </>}
                    {openReplyPostId === post.id && (
                      <form
                        className="reply-form"
                        onSubmit={(event) => {
                          event.preventDefault()
                          const text = (replyDrafts[post.id] ?? '').trim()
                          if (text) reply.mutate({ id: post.id, text })
                        }}
                      >
                        <label className="sr-only" htmlFor={`reply-${post.id}`}>
                          Reply to {post.author}'s post
                        </label>
                        <input
                          id={`reply-${post.id}`}
                          autoFocus
                          value={replyDrafts[post.id] ?? ''}
                          onChange={(event) =>
                            setReplyDrafts((drafts) => ({
                              ...drafts,
                              [post.id]: event.target.value,
                            }))
                          }
                          placeholder="Write a thoughtful reply…"
                          maxLength={1000}
                        />
                        <button
                          className="button button--secondary button--small"
                          type="submit"
                          disabled={
                            !(replyDrafts[post.id] ?? '').trim() ||
                            reply.isPending
                          }
                        >
                          Reply
                        </button>
                      </form>
                    )}
                  </div>
                  <button
                    className="more-button"
                    aria-label={`More actions for ${post.author}`}
                    type="button"
                  >
                    •••
                  </button>
                </article>
              ))
            )}
            <PaginationControls
              page={page}
              itemCount={postsQuery.data?.length ?? 0}
              pageSize={10}
              onPageChange={setPage}
              label="Community posts"
            />
          </section>
          <aside className="community-sidebar">
            <section className="announcement-card" aria-labelledby="community-announcements-title">
              <div className="card-title"><Sparkle size={24} weight="fill" /><span id="community-announcements-title">Community announcements</span></div>
              <p className="announcement-card__intro">The latest little updates from your Safe Space.</p>
              <div className="announcement-item"><span className="announcement-item__badge">New</span><div><strong>Game night is here</strong><p>Friendly rooms, bot play, and game-night rules are ready whenever you are.</p><Link to="/games">Explore the games <ArrowRight size={15} /></Link></div></div>
              <div className="announcement-item"><span className="announcement-item__badge">New</span><div><strong>ABC Fast or Slow is now available</strong><p>Spin the letter wheel, choose your pace, and race to find creative answers.</p><Link to="/games">Play ABC Fast or Slow <ArrowRight size={15} /></Link></div></div>
              {(announcementsQuery.data ?? []).map((announcement) => <div className="announcement-item" key={announcement.id}><span className="announcement-item__badge announcement-item__badge--sage">New</span><div><strong>{announcement.title}</strong><p>{announcement.body}</p>{announcement.cta_label && announcement.cta_path && <a href={announcement.cta_path}>{announcement.cta_label} <ArrowRight size={15} /></a>}</div></div>)}
            </section>
            <section className="guidelines-card">
              <div className="card-title">
                <Leaf size={24} weight="fill" />
                <span>Community guidelines</span>
              </div>
              <p>We care for each other.</p>
              {[
                [
                  '🧡',
                  'Be Kind',
                  'Choose compassion and respect in every interaction.',
                ],
                [
                  '🔒',
                  'Respect Privacy',
                  'What’s shared here stays here. Protect each other’s stories.',
                ],
                [
                  '🌱',
                  'Encourage & Uplift',
                  'Cheer each other on and celebrate every step forward.',
                ],
              ].map(([icon, title, text]) => (
                <div className="guideline" key={title}>
                  <span>{icon}</span>
                  <div>
                    <strong>{title}</strong>
                    <p>{text}</p>
                  </div>
                </div>
              ))}
            </section>
          </aside>
        </div>}
      </main>
      <PageFooter />
    </>
  )
}

function PromoCard({
  title,
  body,
  cta,
  tone,
  icon,
  to,
}: {
  title: string
  body: string
  cta: string
  tone: string
  icon: string
  to: string
}) {
  return (
    <article className={`promo-card promo-card--${tone}`}>
      <span className="promo-card__icon" aria-hidden="true">
        {icon}
      </span>
      <div>
        <h2>{title}</h2>
        <p>{body}</p>
        <Link className="button button--small button--primary" to={to}>
          {cta}
        </Link>
      </div>
    </article>
  )
}

function ChallengesScreen() {
  const queryClient = useQueryClient()
  const challengesQuery = useQuery({
    queryKey: ['current-challenges'],
    queryFn: api.currentChallenges,
  })
  const [activeId, setActiveId] = useState<number | null>(null)
  const [reflection, setReflection] = useState('')
  const complete = useMutation({
    mutationFn: ({ id, note }: { id: number; note?: string }) =>
      api.completeChallenge(id, note),
    onSuccess: () => {
      setActiveId(null)
      setReflection('')
      void queryClient.invalidateQueries({ queryKey: ['current-challenges'] })
      void queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      void queryClient.invalidateQueries({ queryKey: ['me'] })
      void queryClient.invalidateQueries({ queryKey: ['leaderboard'] })
    },
  })
  const data = challengesQuery.data
  const incompleteChallenge = data?.challenges.find((challenge) => !challenge.completed)
  const focusChallenge = data?.challenges.find((challenge) => challenge.id === activeId) ?? incompleteChallenge
  const weekEnd = data
    ? new Date(`${data.active_until}T12:00:00`).toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
      })
    : ''

  return (
    <>
      <PageHeader screen="challenges" />
      <main className="page-content challenges-page">
        <section className="challenges-hero">
          <SectionHeading
            eyebrow="Small steps, real care"
            title="Your weekly challenges"
            description="Gentle prompts to help you notice, connect, and care for yourself this week. There is no perfect way to complete them."
          />
          {data && (
            <aside className="challenge-progress-card" aria-label="Weekly challenge progress">
              <div className="challenge-progress-card__topline">
                <span className="eyebrow">This week</span>
                <Sparkle size={22} weight="fill" aria-hidden="true" />
              </div>
              <strong>{data.completed_count} of {data.total_count}</strong>
              <span>challenges completed</span>
              <div className="progress-track" aria-label={`${data.completed_count} of ${data.total_count} challenges completed`}>
                <span style={{ width: `${data.total_count ? (data.completed_count / data.total_count) * 100 : 0}%` }} />
              </div>
              <div className="challenge-progress-card__meta">
                <span><Trophy size={16} weight="fill" aria-hidden="true" /> {data.xp_earned} XP earned</span>
                <span>Resets {weekEnd}</span>
              </div>
            </aside>
          )}
        </section>

        {challengesQuery.isLoading && <ContentSkeleton rows={5} />}
        {challengesQuery.isError && (
          <div className="form-error challenge-error" role="alert">
            <span>We could not load this week’s challenges.</span>
            <button className="button button--secondary button--small" type="button" onClick={() => void challengesQuery.refetch()}>
              Try again
            </button>
          </div>
        )}
        {challengesQuery.data?.challenges.length === 0 && !challengesQuery.isLoading && (
          <EmptyState title="New prompts arrive next week" message="For now, take a gentle pause in Daily Check-In and come back when a new set is ready." />
        )}
        {data && data.challenges.length > 0 && (
          <>
            {focusChallenge && (
              <section className={`challenge-feature challenge-feature--${focusChallenge.color}`} aria-labelledby="today-challenge-title">
                <div className="challenge-feature__icon" aria-hidden="true">{focusChallenge.icon}</div>
                <div className="challenge-feature__content">
                  <span className="eyebrow">A gentle place to start</span>
                  <h2 id="today-challenge-title">{focusChallenge.title}</h2>
                  <p>{focusChallenge.description}</p>
                  <button className="button button--primary" type="button" onClick={() => setActiveId(activeId === focusChallenge.id ? null : focusChallenge.id)} aria-expanded={activeId === focusChallenge.id}>
                    {activeId === focusChallenge.id ? 'Close reflection' : 'I’m ready'} <ArrowRight size={17} aria-hidden="true" />
                  </button>
                  {activeId === focusChallenge.id && (
                    <form className="challenge-reflection" onSubmit={(event) => { event.preventDefault(); complete.mutate({ id: focusChallenge.id, note: reflection }) }}>
                      <label className="field-label" htmlFor="challenge-reflection">Add a note <span>(optional)</span></label>
                      <textarea id="challenge-reflection" value={reflection} onChange={(event) => setReflection(event.target.value)} maxLength={500} placeholder="What did you notice?" />
                      <div className="challenge-reflection__actions">
                        <small>{reflection.length}/500 · A private note for you</small>
                        <button className="button button--orange" type="submit" disabled={complete.isPending}>{complete.isPending ? 'Saving…' : `Complete · +${focusChallenge.xp} XP`}</button>
                      </div>
                    </form>
                  )}
                </div>
              </section>
            )}
            {complete.isError && <p className="form-error" role="alert">{complete.error.message}</p>}
            {complete.isSuccess && (
              <section className="challenge-celebration" role="status" aria-label="Challenge completed">
                <span className="challenge-celebration__icon" aria-hidden="true"><Sparkle size={23} weight="fill" /></span>
                <div>
                  <span className="eyebrow">A little win to keep</span>
                  <strong>Challenge complete · +{complete.data.xp} XP</strong>
                  <p>That was worth celebrating. Your progress is waiting for you on your profile.</p>
                </div>
                <Link className="button button--secondary button--small" to="/profile">View progress</Link>
              </section>
            )}
            <section className="challenges-section" aria-labelledby="all-challenges-title">
              <div className="section-row">
                <div>
                  <span className="eyebrow">Choose your pace</span>
                  <h2 id="all-challenges-title">This week’s prompts</h2>
                </div>
                <span className="challenge-count">{data.completed_count}/{data.total_count} complete</span>
              </div>
              <div className="challenge-grid">
                {data.challenges.map((challenge) => (
                  <article className={`challenge-card challenge-card--${challenge.color}${challenge.completed ? ' challenge-card--completed' : ''}`} key={challenge.id}>
                    <div className="challenge-card__header">
                      <span className="challenge-card__icon" aria-hidden="true">{challenge.icon}</span>
                      <span className="challenge-card__category">{challenge.category}</span>
                      <span className="challenge-card__xp">+{challenge.xp} XP</span>
                    </div>
                    <h3>{challenge.title}</h3>
                    <p>{challenge.description}</p>
                    {challenge.completed ? (
                      <div className="challenge-card__complete" role="status"><CheckCircle size={19} weight="fill" aria-hidden="true" /> Completed</div>
                    ) : (
                      <button className="button button--secondary button--small" type="button" onClick={() => { setActiveId(challenge.id); setReflection('') }}>
                        Choose this challenge <ArrowRight size={15} aria-hidden="true" />
                      </button>
                    )}
                  </article>
                ))}
              </div>
            </section>
          </>
        )}
        <section className="challenge-guide" aria-labelledby="challenge-guide-title">
          <Sparkle size={23} weight="fill" aria-hidden="true" />
          <div>
            <h2 id="challenge-guide-title">How this works</h2>
            <p>Pick the prompts that feel right, complete them in your own way, and collect a little XP for showing up. You never need to share a photo, location, or private details.</p>
          </div>
        </section>
      </main>
      <PageFooter />
    </>
  )
}

function GamesScreen() {
  const navigate = useNavigate()
  const [showAllGames, setShowAllGames] = useState(false)
  const [roomsPage, setRoomsPage] = useState(1)
  const [showCreateRoom, setShowCreateRoom] = useState(false)
  const [roomName, setRoomName] = useState('A gentle game night')
  const [roomGameId, setRoomGameId] = useState<number | null>(null)
  const [roomPlayers, setRoomPlayers] = useState(4)
  const [roomFillBots, setRoomFillBots] = useState(true)
  const [copiedRoomId, setCopiedRoomId] = useState<number | null>(null)
  const [shareRoomId, setShareRoomId] = useState<number | null>(null)
  useEffect(() => {
    if (shareRoomId === null) return
    const closeMenu = () => setShareRoomId(null)
    document.addEventListener('click', closeMenu)
    return () => document.removeEventListener('click', closeMenu)
  }, [shareRoomId])
  const profile = useQuery({ queryKey: ['me'], queryFn: api.me, retry: false })
  const gamesQuery = useQuery({
    queryKey: ['games', 'featured'],
    queryFn: () => api.games(1, 50),
  })
  const roomsQuery = useQuery({
    queryKey: ['rooms', roomsPage],
    queryFn: () => api.rooms(roomsPage, 5),
    refetchInterval: 2500,
  })
  const winnersQuery = useQuery({
    queryKey: ['game-winners'],
    queryFn: () => api.winners(1, 5),
    refetchInterval: 10000,
  })
  const queryClient = useQueryClient()
  const join = useMutation({
    mutationFn: api.joinRoom,
    onSuccess: (room) => {
      queryClient.invalidateQueries({ queryKey: ['rooms'] })
      navigate({ to: '/games/rooms/$roomId', params: { roomId: String(room.id) } })
    },
  })
  const cleanupBotRooms = useMutation({
    mutationFn: api.cleanupBotRooms,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['rooms'] }),
  })
  const playGame = useMutation({
    mutationFn: async (game: GameDefinition) => {
      if (!game.id) throw new Error('This game is not available yet')
      const room = await api.createRoom({
        game_id: game.id,
        name: `${game.name} · Friendly bot`,
        max_players: 2,
      })
      if (game.name === 'Connect Four') {
        const match = await api.createMatch({
          room_id: room.id,
          with_bot: true,
          bot_difficulty: 'friendly',
        })
        return { kind: 'connect-four' as const, id: match.match_id }
      }
      const match = await api.createGameSession(room.id)
      return { kind: 'session' as const, id: match.match_id }
    },
    onSuccess: (match) => {
      if (match.kind === 'connect-four')
        navigate({ to: '/games/play/$matchId', params: { matchId: match.id } })
      else
        navigate({
          to: '/games/session/$matchId',
          params: { matchId: match.id },
        })
    },
  })
  const createRoom = useMutation({
    mutationFn: api.createRoom,
    onSuccess: (room) => {
      setShowCreateRoom(false)
      setRoomName('A gentle game night')
      queryClient.invalidateQueries({ queryKey: ['rooms'] })
      navigate({ to: '/games/rooms/$roomId', params: { roomId: String(room.id) } })
    },
  })
  const availableGames: Array<GameDefinition> = gamesQuery.data?.length
    ? gamesQuery.data.map((game) => ({
        ...game,
        color: game.color,
        description: games.find((fallback) => fallback.name === game.name)?.description ?? 'A friendly game to enjoy together.',
      }))
    : games.map((game, index) => ({ ...game, id: index + 1 }))
  const selectedGame = availableGames.find((game) => game.id === roomGameId)
  const maxRoomPlayers = gameRoomCapacity(selectedGame?.name)
  useEffect(() => {
    if (roomPlayers > maxRoomPlayers) setRoomPlayers(maxRoomPlayers)
  }, [maxRoomPlayers, roomPlayers])
  const rooms = roomsQuery.data ?? []
  const firstGameId = availableGames[0]?.id ?? null
  return (
    <>
      <PageHeader screen="games" />
      <main className="page-content games-page">
        <section className="games-hero">
          <SectionHeading
            title="Games"
            description="Play, connect, and unwind with the community. Jump in for fun, friendly competition, and good vibes!"
          />
          <img
            src="/assets/community-circle.png"
            alt="Friends playing games together"
          />
        </section>
        <section className="game-night-banner">
          <div>
            <h2>
              Game Night Starts at 7:00 PM!{' '}
              <span className="heart-doodle">♡</span>
            </h2>
            <p>Join friends for fun, connection, and friendly competition.</p>
          </div>
          <button
            className="button button--orange"
            type="button"
            onClick={() =>
              document
                .getElementById('live-rooms')
                ?.scrollIntoView({ behavior: 'smooth' })
            }
          >
            Join Game Night
          </button>
          <button
            className="button button--ghost"
            type="button"
            onClick={() => {
              setRoomGameId((current) => current ?? firstGameId)
              setShowCreateRoom(true)
            }}
          >
            Create Room
          </button>
        </section>
        {showCreateRoom && (
          <form
            className="room-create-card"
            onSubmit={(event) => {
              event.preventDefault()
              if (roomGameId && roomName.trim())
                createRoom.mutate({
                  game_id: roomGameId,
                  name: roomName.trim(),
                  max_players: roomPlayers,
                  fill_with_bots: roomFillBots,
                })
            }}
          >
            <div>
              <span className="eyebrow">Make space for play</span>
              <h2>Create a room</h2>
              <p>Choose a game, invite friends, and keep it friendly.</p>
            </div>
            <label className="field-label">
              Room name
              <input
                value={roomName}
                onChange={(event) => setRoomName(event.target.value)}
                maxLength={100}
                required
              />
            </label>
            <label className="field-label">
              Game
              <select
                value={roomGameId ?? ''}
                onChange={(event) => setRoomGameId(Number(event.target.value))}
                required
              >
                {availableGames.map((game) => (
                  <option value={game.id} key={game.id}>
                    {game.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="field-label">
              Players
              <select
                value={roomPlayers}
                onChange={(event) => setRoomPlayers(Number(event.target.value))}
              >
                {[2, 3, 4, 5, 6, 7, 8].filter((count) => count <= maxRoomPlayers).map((count) => (
                  <option value={count} key={count}>{count} players</option>
                ))}
              </select>
            </label>
            <label className="field-label">
              Open seats
              <select
                value={roomFillBots ? 'bots' : 'humans'}
                onChange={(event) =>
                  setRoomFillBots(event.target.value === 'bots')
                }
              >
                <option value="bots">Fill remaining seats with bots</option>
                <option value="humans">Humans only</option>
              </select>
            </label>
            <div className="room-create-actions">
              <button
                className="button button--primary"
                type="submit"
                disabled={createRoom.isPending || !roomGameId}
              >
                {createRoom.isPending ? 'Creating…' : 'Create room'}
              </button>
              <button
                className="button button--secondary"
                type="button"
                onClick={() => setShowCreateRoom(false)}
              >
                Cancel
              </button>
            </div>
          </form>
        )}
        {playGame.error && (
          <p className="form-error" role="alert">
            {playGame.error.message}
          </p>
        )}
        {(join.error ||
          cleanupBotRooms.error) && (
          <p className="form-error" role="alert">
            {
              (
                join.error ||
                cleanupBotRooms.error
              )?.message
            }
          </p>
        )}
        <div className="games-layout">
          <section className="games-panel">
            <div className="card-title">
              <GameController size={24} weight="fill" />
              <span>Featured Games</span>
            </div>
            <div
              className={
                showAllGames
                  ? 'game-grid game-grid--games-expanded'
                  : 'game-grid game-grid--games-list'
              }
            >
              {(showAllGames ? availableGames : availableGames.slice(0, 7)).map(
                (game) => (
                  <GameTile
                    game={game}
                    key={game.id}
                    onPlay={() => playGame.mutate(game)}
                  />
                ),
              )}
            </div>
            {availableGames.length > 7 && (
              <button
                className="button button--secondary button--small games-view-more"
                type="button"
                onClick={() => setShowAllGames((visible) => !visible)}
              >
                {showAllGames ? 'Show featured' : 'View more games'}
              </button>
            )}
          </section>
          <section className="rooms-panel" id="live-rooms">
            <div className="section-row">
              <div className="card-title">
                <UsersThree size={24} weight="fill" />
                <span>Live Rooms</span>
              </div>
              {profile.data && staffRoles.has(profile.data.role) && (
                <button
                  className="button button--small room-cleanup-button"
                  type="button"
                  disabled={cleanupBotRooms.isPending}
                  aria-label="Clean up stale bot rooms"
                  onClick={() => {
                    if (window.confirm('Delete active rooms containing only the host and generated bots?'))
                      cleanupBotRooms.mutate()
                  }}
                >
                  <span aria-hidden="true">✦</span>
                  {cleanupBotRooms.isPending ? 'Cleaning…' : 'Clean bot rooms'}
                </button>
              )}
            </div>
            {cleanupBotRooms.data && <p className="form-success" role="status">Deleted {cleanupBotRooms.data.deleted} stale bot {cleanupBotRooms.data.deleted === 1 ? 'room' : 'rooms'}.</p>}
            {rooms.length === 0 && !roomsQuery.isLoading ? (
              <EmptyState
                title="No live rooms yet"
                message="Create a room when you are ready to play with the community."
              />
            ) : (
              rooms.map((room) => (
                <div className="room-row" key={room.id}>
                  <span className="room-icon" aria-hidden="true">
                    🎲
                  </span>
                  <div className="room-row__details">
                    <strong className="room-row__name" title={room.name}>
                      {room.name}
                    </strong>
                    <small>
                      {room.status === 'active' && room.fill_with_bots
                        ? `${room.max_players} / ${room.max_players} players · bot match`
                        : `${room.players} / ${room.max_players} players`}
                    </small>
                  </div>
                  {room.invite_token && (
                    <div className="room-share-menu">
                      <button
                        className="room-share-trigger"
                        type="button"
                        aria-label="Room options"
                        aria-expanded={shareRoomId === room.id}
                        onClick={(event) => { event.stopPropagation(); setShareRoomId((current) => current === room.id ? null : room.id) }}
                      >
                        <DotsThreeVertical size={20} weight="bold" />
                      </button>
                      {shareRoomId === room.id && <div className="room-share-popover" role="menu">
                        <button type="button" role="menuitem" onClick={() => {
                          const inviteUrl = `${window.location.origin}/games/rooms/invite/${room.invite_token}`
                          void navigator.clipboard.writeText(inviteUrl).then(() => {
                            setCopiedRoomId(room.id)
                            setShareRoomId(null)
                            window.setTimeout(() => setCopiedRoomId((current) => current === room.id ? null : current), 1800)
                          })
                        }}>{copiedRoomId === room.id ? 'Copied ✓' : 'Copy invite link'}</button>
                      </div>}
                    </div>
                  )}
                  {room.joined ? (
                    <span
                      className="room-status-pill room-status-pill--joined"
                      aria-label="You joined this room"
                    >
                      Joined ✓
                    </span>
                  ) : (
                    <button
                      className="button button--small button--primary room-action-button"
                      type="button"
                      disabled={join.isPending}
                      onClick={() => join.mutate(room.id)}
                    >
                      Join
                    </button>
                  )}
                  {room.joined && room.status === 'open' && (
                    <button
                      className="button button--small button--secondary room-action-button"
                      type="button"
                      onClick={() => navigate({ to: '/games/rooms/$roomId', params: { roomId: String(room.id) } })}
                    >
                      Open lobby
                    </button>
                  )}
                  {room.joined && room.status === 'active' && room.match_id && (
                    <button
                      className="button button--small button--secondary"
                      type="button"
                      onClick={() =>
                        room.game === 'Connect Four'
                          ? navigate({
                              to: '/games/play/$matchId',
                              params: { matchId: room.match_id! },
                            })
                          : navigate({
                              to: '/games/session/$matchId',
                              params: { matchId: room.match_id! },
                            })
                      }
                    >
                      Enter game
                    </button>
                  )}
                </div>
              ))
            )}
            <PaginationControls
              page={roomsPage}
              itemCount={roomsQuery.data?.length ?? 0}
              pageSize={5}
              onPageChange={setRoomsPage}
              label="Game rooms"
            />
          </section>
          <section className="winner-panel">
            <div className="section-row">
              <div className="card-title">
                <Trophy size={24} weight="fill" />
                <span>Recent Winners</span>
              </div>
              <button className="text-link" type="button">
                See all <ArrowRight size={16} />
              </button>
            </div>
            {winnersQuery.data?.length ? winnersQuery.data.map((winner) => (
              <div className="winner-row" key={`${winner.position}-${winner.name}`}>
                <span className="winner-rank" aria-label={`Position ${winner.position}`}>{winner.position}</span>
                <Avatar initials={winner.name.slice(0, 1).toUpperCase()} color={winner.position === 1 ? 'gold' : 'sage'} imageUrl={winner.avatar_url} />
                <div>
                  <strong>{winner.name}</strong>
                  <small>+{winner.match_points} XP · {winner.game} · Recent win</small>
                </div>
              </div>
            )) : !winnersQuery.isLoading && (
              <div className="winner-row winner-row--empty">
                <Avatar initials="★" color="gold" />
                <div>
                  <strong>Community winners</strong>
                  <small>Results will appear after the first match.</small>
                </div>
              </div>
            )}
          </section>
        </div>
      </main>
      <PageFooter />
    </>
  )
}

function BugReportWidget() {
  const currentUser = useQuery({
    queryKey: ['me'],
    queryFn: api.me,
    retry: false,
  })
  const [open, setOpen] = useState(false)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [severity, setSeverity] = useState('normal')
  const report = useMutation({
    mutationFn: api.createBugReport,
    onSuccess: () => {
      setTitle('')
      setDescription('')
      setSeverity('normal')
    },
  })
  if (currentUser.isError || !currentUser.data) return null
  return (
    <div className="bug-report-widget">
      {open && (
        <section
          className="bug-report-popover"
          aria-labelledby="bug-report-title"
        >
          <div className="bug-report-popover__header">
            <div>
              <span className="eyebrow">Help us improve</span>
              <h2 id="bug-report-title">Report a bug</h2>
            </div>
            <button
              className="icon-button"
              type="button"
              aria-label="Close bug report form"
              onClick={() => setOpen(false)}
            >
              <X size={18} />
            </button>
          </div>
          <p>
            Tell us what went wrong and where you noticed it. Please do not
            include private journal details.
          </p>
          {report.isSuccess ? (
            <div className="form-success" role="status">
              Thanks — your report is with the team.
            </div>
          ) : (
            <form
              onSubmit={(event) => {
                event.preventDefault()
                report.mutate({
                  title: title.trim(),
                  description: description.trim(),
                  severity,
                  page_url: window.location.pathname,
                })
              }}
            >
              <label>
                Short title
                <input
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                  minLength={3}
                  maxLength={160}
                  required
                  placeholder="What went wrong?"
                />
              </label>
              <label>
                Details
                <textarea
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                  minLength={10}
                  maxLength={5000}
                  required
                  placeholder="What did you expect, and what happened instead?"
                />
              </label>
              <label>
                Severity
                <select
                  value={severity}
                  onChange={(event) => setSeverity(event.target.value)}
                >
                  <option value="low">Low</option>
                  <option value="normal">Normal</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </select>
              </label>
              {report.isError && (
                <p className="form-error" role="alert">
                  {report.error.message}
                </p>
              )}
              <button
                className="button button--primary button--wide"
                type="submit"
                disabled={report.isPending}
              >
                {report.isPending ? 'Sending…' : 'Send bug report'}
              </button>
            </form>
          )}
        </section>
      )}
      <button
        className="bug-report-launcher"
        type="button"
        aria-label={open ? 'Close bug report form' : 'Report a bug'}
        aria-expanded={open}
        onClick={() => {
          setOpen((value) => !value)
          report.reset()
        }}
      >
        <Bug size={23} weight="duotone" />
        <span>{open ? 'Close' : 'Report a bug'}</span>
      </button>
    </div>
  )
}

function LeaderboardScreen() {
  const [period, setPeriod] = useState<LeaderboardPeriod>('week')
  const [page, setPage] = useState(1)
  const leaderboard = useQuery({
    queryKey: ['leaderboard', period, page],
    queryFn: () => api.leaderboard(period, page, 10),
    refetchInterval: 60_000,
    refetchOnMount: 'always',
    refetchOnWindowFocus: true,
  })
  const progress = useQuery({
    queryKey: ['leaderboard-me', period],
    queryFn: () => api.leaderboardMe(period),
    refetchOnMount: 'always',
    refetchOnWindowFocus: true,
  })
  const entries = leaderboard.data ?? []
  const isRefreshing = leaderboard.isFetching || progress.isFetching
  const filters: Array<[LeaderboardPeriod, string]> = [
    ['day', 'Today'],
    ['week', 'This Week'],
    ['month', 'This Month'],
    ['all', 'All Time'],
  ]
  return (
    <>
      <PageHeader screen="leaderboard" />
      <main className="page-content leaderboard-page">
        <section className="leaderboard-hero">
          <div>
            <SectionHeading
              title="Community Leaderboard"
              description="Celebrate progress. Inspire each other. Together, we grow stronger."
            />
          </div>
          <div className="podium">
            {page === 1 && !isRefreshing &&
              entries.slice(0, 3).map((entry, index) => (
                <div
                  className={`podium-member podium-member--${index + 1}`}
                  key={entry.user.id}
                >
                  <span
                    className="podium-rank"
                    aria-label={`Rank ${index + 1}`}
                    title={`Rank ${index + 1}`}
                  >
                    {index + 1}
                  </span>
                  <Avatar
                    initials={entry.user.name[0]}
                    color="sage"
                    imageUrl={entry.user.avatar_url}
                    online={entry.user.is_online}
                  />
                  <strong>{entry.user.name}</strong>
                  <ProfileLevelBadge level={entry.user.level} />
                  <span>{entry.user.xp.toLocaleString()} XP</span>
                  <div className="podium-block" />
                </div>
              ))}
          </div>
          <aside className="progress-card">
            <div className="card-title">
              <Leaf size={22} weight="fill" />
              <span>Your progress</span>
            </div>
            <div className="progress-card__stats">
              <span>
                Rank
                <strong>#{progress.data?.rank ?? '—'}</strong>
              </span>
              <span>
                {period === 'all' ? 'Total XP' : 'XP Earned'}
                <strong>
                  {progress.isFetching ? '—' : progress.data?.user.xp.toLocaleString() ?? '—'}{' '}
                  <small>{period === 'all' ? 'XP' : 'this period'}</small>
                </strong>
              </span>
            </div>
            <p>Keep it going!</p>
          </aside>
        </section>
        <div className="leaderboard-filter">
          {filters.map(([value, label]) => (
            <button
              className={
                period === value
                  ? 'filter-chip filter-chip--active'
                  : 'filter-chip'
              }
              type="button"
              onClick={() => {
                setPeriod(value)
                setPage(1)
              }}
              key={value}
            >
              {label}
            </button>
          ))}
        </div>
        <section className="leaderboard-table">
          <div className="leaderboard-table__head">
            <span>Rank</span>
            <span>Member</span>
            <span>{period === 'all' ? 'Total XP' : 'XP Earned'}</span>
            <span>Current Streak</span>
          </div>
          {isRefreshing ? (
            <div className="leaderboard-loading" role="status" aria-live="polite">
              <span className="leaderboard-loading__spark" aria-hidden="true">✦</span>
              <strong>Gathering the kindest wins…</strong>
              <span>One moment while we refresh the rankings.</span>
            </div>
          ) : leaderboard.isError ? (
            <div className="leaderboard-error" role="alert">
              <strong>We couldn’t load the rankings.</strong>
              <span>{leaderboard.error.message}</span>
              <button className="button button--small button--secondary" type="button" onClick={() => void leaderboard.refetch()}>Try again</button>
            </div>
          ) : !leaderboard.isLoading && entries.length === 0 ? (
            <EmptyState
              title="No rankings yet"
              message="Complete a check-in or encourage the community to start earning points."
            />
          ) : (
            entries.map((entry) => (
              <div className="leaderboard-row" key={entry.user.id}>
                <strong>{entry.rank}</strong>
                <div className="leaderboard-member">
                  <Avatar
                    initials={entry.user.name[0]}
                    color="sage"
                    imageUrl={entry.user.avatar_url}
                    online={entry.user.is_online}
                  />
                  <span className="leaderboard-member__name">
                    {entry.user.name} <Leaf size={16} weight="fill" />
                  </span>
                  <ProfileLevelBadge level={entry.user.level} />
                </div>
                <span className="xp xp--sage">
                  {entry.user.xp.toLocaleString()} <small>XP</small>
                </span>
                <span>
                  {entry.user.streak} <small>days</small>
                </span>
              </div>
            ))
          )}
        </section>
        <PaginationControls
          page={page}
          itemCount={entries.length}
          pageSize={10}
          onPageChange={setPage}
          label="Leaderboard"
        />
      </main>
      <PageFooter />
    </>
  )
}

function ProfileScreen() {
  const queryClient = useQueryClient()
  const profile = useQuery({ queryKey: ['me'], queryFn: api.me, retry: false })
  const [name, setName] = useState('')
  const [saved, setSaved] = useState(false)
  const [activeTab, setActiveTab] = useState<
    'profile' | 'activity' | 'appearance' | 'privacy' | 'security'
  >('profile')
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmNewPassword, setConfirmNewPassword] = useState('')
  const [showCurrentPassword, setShowCurrentPassword] = useState(false)
  const [showNewPassword, setShowNewPassword] = useState(false)
  const [showConfirmNewPassword, setShowConfirmNewPassword] = useState(false)
  const [avatarPreview, setAvatarPreview] = useState<string | null>(null)
  const [avatarFile, setAvatarFile] = useState<File | undefined>()
  const [likedPage, setLikedPage] = useState(1)
  const [repliedPage, setRepliedPage] = useState(1)
  const [savedQuotesPage, setSavedQuotesPage] = useState(1)
  const [checkInsPage, setCheckInsPage] = useState(1)
  const [challengeHistoryPage, setChallengeHistoryPage] = useState(1)
  const [avatarError, setAvatarError] = useState('')
  const [theme, setTheme] = useState<
    'sage' | 'night' | 'purple' | 'crimson' | 'high-contrast'
  >(() => {
    if (typeof window === 'undefined') return 'sage'
    return (
      (window.localStorage.getItem('safe-space-theme') as
        'sage' | 'night' | 'purple' | 'crimson' | 'high-contrast' | null) ?? 'sage'
    )
  })
  const update = useMutation({
    mutationFn: api.updateProfile,
    onSuccess: (user) => {
      queryClient.setQueryData(['me'], user)
      queryClient.setQueryData(
        ['dashboard'],
        (current: { user: typeof user } | undefined) =>
          current ? { ...current, user } : current,
      )
      setName(user.name)
      setSaved(true)
    },
  })
  const logout = useMutation({
    mutationFn: api.logout,
    onSuccess: () => {
      queryClient.clear()
      window.location.href = '/login'
    },
  })
  const changePassword = useMutation({
    mutationFn: api.changePassword,
    onSuccess: () => {
      setCurrentPassword('')
      setNewPassword('')
      setConfirmNewPassword('')
      logout.mutate()
    },
  })
  const likedPosts = useQuery({
    queryKey: ['liked-posts', likedPage],
    queryFn: () => api.likedPosts(likedPage),
    enabled: activeTab === 'activity',
  })
  const repliedPosts = useQuery({
    queryKey: ['replied-posts', repliedPage],
    queryFn: () => api.repliedPosts(repliedPage),
    enabled: activeTab === 'activity',
  })
  const savedQuotes = useQuery({
    queryKey: ['saved-quotes', savedQuotesPage],
    queryFn: () => api.savedQuotes(savedQuotesPage),
    enabled: activeTab === 'activity',
  })
  const checkIns = useQuery({
    queryKey: ['check-ins', checkInsPage],
    queryFn: () => api.checkIns(checkInsPage, 5),
    enabled: activeTab === 'activity',
  })
  const challengeHistory = useQuery({
    queryKey: ['challenge-history', challengeHistoryPage],
    queryFn: () => api.challengeHistory(challengeHistoryPage, 10),
    enabled: activeTab === 'activity',
  })
  const saveAvatar = useMutation({
    mutationFn: api.updateAvatar,
    onSuccess: (user) => {
      queryClient.setQueryData(['me'], user)
      setAvatarPreview(null)
      setAvatarFile(undefined)
    },
  })
  useEffect(() => {
    document.documentElement.dataset.theme = theme
    window.localStorage.setItem('safe-space-theme', theme)
  }, [theme])
  const user = profile.data
  if (profile.isError)
    return (
      <>
        <PageHeader screen="profile" />
        <main className="page-content profile-page">
          <SectionHeading
            eyebrow="Your space"
            title="Profile & settings"
            description="Sign in to manage your profile, privacy, and progress."
          />
          <section className="profile-card profile-auth-required">
            <ShieldCheck size={32} weight="fill" />
            <h2>Your profile is private</h2>
            <p>Log in to view and update your account details.</p>
            <Link className="button button--primary" to="/login">
              Log in
            </Link>
          </section>
        </main>
        <PageFooter />
      </>
    )
  const displayName = name || user?.name || ''
  const passwordErrors = [
    ...(currentPassword.length === 0 ? ['Enter your current password.'] : []),
    ...(newPassword.length === 0
      ? ['Enter a new password.']
      : newPassword.length < 10
        ? ['Your new password must be at least 10 characters.']
        : []),
    ...(confirmNewPassword.length === 0
      ? ['Confirm your new password.']
      : newPassword !== confirmNewPassword
        ? ['Your passwords do not match.']
        : []),
  ]
  const handleAvatarChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type) || file.size > MAX_SOURCE_IMAGE_BYTES) {
      setAvatarError('Choose a JPEG, PNG, or WebP image under 40 MB. Larger images are resized automatically.')
      return
    }
    setAvatarError('')
    setAvatarFile(file)
    const reader = new FileReader()
    reader.onload = () => setAvatarPreview(String(reader.result))
    reader.readAsDataURL(file)
  }
  const tabs = [
    { id: 'profile' as const, label: 'Profile', icon: UserCircle },
    { id: 'activity' as const, label: 'Activity', icon: Heart },
    { id: 'appearance' as const, label: 'Appearance', icon: Palette },
    { id: 'privacy' as const, label: 'Privacy', icon: ShieldCheck },
    { id: 'security' as const, label: 'Security', icon: LockKey },
  ]
  return (
    <>
      <PageHeader screen="profile" />
      <main className="page-content profile-page">
        <SectionHeading
          eyebrow="Your space"
          title="Profile & settings"
          description="Keep your details close, your boundaries clear, and your progress in view."
        />
        <section className="profile-card profile-card--identity">
          <div className="profile-identity">
            <span className="avatar avatar--gold avatar--large">
              {avatarPreview ? (
                <img
                  className="profile-avatar-image"
                  src={avatarPreview}
                  alt="Your selected profile picture"
                />
              ) : user?.avatar_url ? (
                <img
                  className="profile-avatar-image"
                  src={assetUrl(user.avatar_url)}
                  alt="Your profile picture"
                />
              ) : (
                (displayName[0] || 'J').toUpperCase()
              )}
            </span>
            <div>
              <h2>{displayName || 'Loading your profile…'}</h2>
              <p>{user?.email || 'Your private account details'}</p>
            </div>
          </div>
          <div className="profile-stats">
            <span>
              <strong>{user?.xp ?? '—'}</strong>
              <small>Total XP</small>
            </span>
            <span>
              <strong>{user?.streak ?? '—'}</strong>
              <small>Day streak</small>
            </span>
            <span>
              <strong>{user?.level ?? '—'}</strong>
              <small>Level</small>
            </span>
          </div>
        </section>
        <div
          className="profile-tabs"
          role="tablist"
          aria-label="Profile settings sections"
        >
          {tabs.map(({ id, label, icon: TabIcon }) => (
            <button
              id={`profile-tab-${id}`}
              className={
                activeTab === id
                  ? 'profile-tab profile-tab--active'
                  : 'profile-tab'
              }
              type="button"
              role="tab"
              aria-selected={activeTab === id}
              aria-controls={`profile-panel-${id}`}
              onClick={() => setActiveTab(id)}
              key={id}
            >
              <TabIcon
                size={19}
                weight={activeTab === id ? 'fill' : 'regular'}
              />
              {label}
            </button>
          ))}
        </div>
        <section
          className="profile-tab-panel"
          id={`profile-panel-${activeTab}`}
          role="tabpanel"
          aria-labelledby={`profile-tab-${activeTab}`}
        >
          {activeTab === 'profile' && (
            <div className="profile-settings-grid">
              <section className="profile-card">
                <div className="card-title">
                  <PencilSimple size={22} />
                  <span>Personal details</span>
                </div>
                <p className="profile-card__intro">
                  Your display name is visible in community conversations and
                  the leaderboard.
                </p>
                <form
                  onSubmit={(event) => {
                    event.preventDefault()
                    setSaved(false)
                    update.mutate({ name: displayName.trim() })
                  }}
                  noValidate
                  aria-busy={update.isPending}
                >
                  <label htmlFor="profile-name">
                    Display name
                    <input
                      id="profile-name"
                      name="name"
                      minLength={2}
                      maxLength={120}
                      required
                      value={displayName}
                      onChange={(event) => {
                        setName(event.target.value)
                        setSaved(false)
                      }}
                      aria-describedby="profile-name-help"
                      aria-invalid={
                        update.isError || displayName.trim().length < 2
                      }
                    />
                  </label>
                  <small id="profile-name-help" className="field-help">
                    Use at least 2 characters. Your email cannot be changed
                    here.
                  </small>
                  {update.isError && (
                    <p className="form-error" role="alert">
                      {update.error.message}
                    </p>
                  )}
                  {saved && (
                    <p className="form-success" role="status">
                      Profile saved successfully.
                    </p>
                  )}
                  <button
                    className="button button--primary"
                    type="submit"
                    disabled={update.isPending || displayName.trim().length < 2}
                  >
                    {update.isPending ? 'Saving…' : 'Save changes'}
                  </button>
                </form>
              </section>
              <section className="profile-card profile-photo-card">
                <div className="card-title">
                  <UserCircle size={22} />
                  <span>Profile picture</span>
                </div>
                <p className="profile-card__intro">
                  Choose a clear picture to make your profile feel like yours.
                </p>
                <label className="profile-upload">
                  <span className="button button--secondary button--small">
                    Choose image
                  </span>
                  <input
                    type="file"
                    accept="image/png,image/jpeg,image/webp"
                    onChange={handleAvatarChange}
                  />
                </label>
                {avatarError && (
                  <p className="form-error" role="alert">
                    {avatarError}
                  </p>
                )}
                <small className="field-help">
                  JPG, PNG, or WebP. Images up to 40 MB are resized automatically to fit the 10 MB storage limit.
                </small>
                <button
                  className="button button--primary button--small"
                  type="button"
                  disabled={!avatarFile || saveAvatar.isPending}
                  onClick={() => avatarFile && saveAvatar.mutate(avatarFile)}
                >
                  {saveAvatar.isPending
                    ? 'Saving image…'
                    : 'Save profile picture'}
                </button>
                {saveAvatar.isError && (
                  <p className="form-error" role="alert">
                    {saveAvatar.error.message}
                  </p>
                )}
              </section>
            </div>
          )}
          {activeTab === 'activity' && (
            <div className="profile-activity">
              {(likedPosts.isLoading ||
                repliedPosts.isLoading ||
                savedQuotes.isLoading ||
                checkIns.isLoading ||
                challengeHistory.isLoading) && <ContentSkeleton rows={3} />}
              <section className="profile-card challenge-history-card">
                <div className="challenge-history-card__header">
                  <div>
                    <span className="eyebrow">Little wins</span>
                    <div className="card-title"><Sparkle size={22} weight="fill" /><span>Challenge garden</span></div>
                    <p className="profile-card__intro">A gentle record of the moments you chose to show up.</p>
                  </div>
                  <Link className="button button--secondary button--small" to="/challenges">Find a prompt</Link>
                </div>
                {challengeHistory.isError ? (
                  <p className="form-error" role="alert">We could not load your challenge garden. Please try again shortly.</p>
                ) : (challengeHistory.data ?? []).length > 0 ? (
                  <div className="challenge-history-list">
                    {(challengeHistory.data ?? []).map((challenge) => (
                      <article className={`challenge-history-item challenge-history-item--${challenge.color}`} key={`${challenge.id}-${challenge.completed_at}`}>
                        <span className="challenge-history-item__icon" aria-hidden="true">{challenge.icon}</span>
                        <div>
                          <strong>{challenge.title}</strong>
                          <small>{challenge.completed_at ? new Date(challenge.completed_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : 'Completed'} · {challenge.category}</small>
                        </div>
                        <span className="challenge-history-item__xp">+{challenge.xp} XP</span>
                      </article>
                    ))}
                  </div>
                ) : (
                  <div className="profile-empty-state challenge-history-empty">
                    <p>Your completed challenges will bloom here.</p>
                    <Link className="button button--secondary button--small" to="/challenges">Start your first challenge</Link>
                  </div>
                )}
                <PaginationControls
                  page={challengeHistoryPage}
                  itemCount={challengeHistory.data?.length ?? 0}
                  pageSize={10}
                  onPageChange={setChallengeHistoryPage}
                  label="Completed challenges"
                />
              </section>
              <section className="profile-card">
                <div className="card-title">
                  <Heart size={22} weight="fill" />
                  <span>Liked posts</span>
                </div>
                {(likedPosts.data ?? []).length > 0 ? (
                  (likedPosts.data ?? []).map((post) => (
                    <article className="activity-post" key={post.id}>
                      <strong>{post.author}</strong>
                      <p>{post.text}</p>
                      <small>Liked conversation</small>
                    </article>
                  ))
                ) : (
                  <div className="profile-empty-state">
                    <p>
                      You have not liked a post yet. Posts you like will collect
                      here.
                    </p>
                    <Link
                      className="button button--secondary button--small"
                      to="/community"
                    >
                      Explore community
                    </Link>
                  </div>
                )}
                <PaginationControls
                  page={likedPage}
                  itemCount={likedPosts.data?.length ?? 0}
                  pageSize={5}
                  onPageChange={setLikedPage}
                  label="Liked posts"
                />
              </section>
              <section className="profile-card">
                <div className="card-title">
                  <ChatCircleDots size={22} />
                  <span>Posts you replied to</span>
                </div>
                {(repliedPosts.data ?? []).length > 0 ? (
                  (repliedPosts.data ?? []).map((post) => (
                    <article className="activity-post" key={post.id}>
                      <strong>{post.author}</strong>
                      <p>{post.text}</p>
                      <small>
                        {post.comments.length} repl
                        {post.comments.length === 1 ? 'y' : 'ies'} in this
                        conversation
                      </small>
                    </article>
                  ))
                ) : (
                  <div className="profile-empty-state">
                    <p>
                      Your replies will appear here when you join a
                      conversation.
                    </p>
                    <Link
                      className="button button--secondary button--small"
                      to="/community"
                    >
                      Join a conversation
                    </Link>
                  </div>
                )}
                <PaginationControls
                  page={repliedPage}
                  itemCount={repliedPosts.data?.length ?? 0}
                  pageSize={5}
                  onPageChange={setRepliedPage}
                  label="Replied posts"
                />
              </section>
              <section className="profile-card">
                <div className="card-title">
                  <BookmarkSimple size={22} weight="fill" />
                  <span>Saved quotes</span>
                </div>
                {(savedQuotes.data ?? []).length > 0 ? (
                  (savedQuotes.data ?? []).map((quote) => (
                    <article
                      className="activity-post activity-quote"
                      key={quote.id}
                    >
                      <p>“{quote.text}”</p>
                      <small>
                        — {quote.author} · {quote.category}
                      </small>
                    </article>
                  ))
                ) : (
                  <div className="profile-empty-state">
                    <p>Quotes you save will stay here for a quieter moment.</p>
                    <Link
                      className="button button--secondary button--small"
                      to="/quotes"
                    >
                      Find a quote
                    </Link>
                  </div>
                )}
                <PaginationControls
                  page={savedQuotesPage}
                  itemCount={savedQuotes.data?.length ?? 0}
                  pageSize={5}
                  onPageChange={setSavedQuotesPage}
                  label="Saved quotes"
                />
              </section>
              <section className="profile-card">
                <div className="card-title">
                  <Heart size={22} />
                  <span>Check-in history</span>
                </div>
                {(checkIns.data ?? []).length > 0 ? (
                  (checkIns.data ?? []).map((checkIn) => (
                    <CheckInReflection checkIn={checkIn} key={checkIn.id} />
                  ))
                ) : (
                  <div className="profile-empty-state">
                    <p>Your private check-in reflections will appear here.</p>
                    <Link
                      className="button button--secondary button--small"
                      to="/check-in"
                    >
                      Make a check-in
                    </Link>
                  </div>
                )}
                <PaginationControls
                  page={checkInsPage}
                  itemCount={checkIns.data?.length ?? 0}
                  pageSize={5}
                  onPageChange={setCheckInsPage}
                  label="Check-in history"
                />
              </section>
            </div>
          )}
          {activeTab === 'appearance' && (
            <div className="profile-card">
              <div className="card-title">
                <Palette size={22} />
                <span>Appearance</span>
              </div>
              <p className="profile-card__intro">
                Choose a calmer look for your daily check-ins and community
                time.
              </p>
              <div
                className="theme-options"
                role="radiogroup"
                aria-label="Theme preference"
              >
                {[
                  ['sage', 'Sage light', 'Soft cream and botanical green'],
                  ['night', 'Night garden', 'Low-light forest surfaces'],
                  ["purple", "Tatty's Garden", 'Warm lavender and plum surfaces'],
                  ['crimson', 'Crimson Ty', 'Deep red and ember night surfaces'],
                  [
                    'high-contrast',
                    'High contrast',
                    'Sharper text and controls',
                  ],
                ].map(([value, label, description]) => (
                  <button
                    className={
                      theme === value
                        ? 'theme-option theme-option--selected'
                        : 'theme-option'
                    }
                    type="button"
                    role="radio"
                    aria-checked={theme === value}
                    onClick={() => setTheme(value as typeof theme)}
                    key={value}
                  >
                    <span className={`theme-swatch theme-swatch--${value}`} />
                    <span>
                      <strong>{label}</strong>
                      <small>{description}</small>
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}
          {activeTab === 'privacy' && (
            <div className="profile-card profile-card--privacy">
              <div className="card-title">
                <ShieldCheck size={22} weight="fill" />
                <span>Your privacy</span>
              </div>
              <p>
                Check-ins are private to your account. Community posts are
                visible to members and can be reported for moderation.
              </p>
              <div className="privacy-row">
                <span>
                  <strong>Private check-ins</strong>
                  <small>Only you can view your reflections.</small>
                </span>
                <span className="privacy-badge">Protected</span>
              </div>
              <div className="privacy-row">
                <span>
                  <strong>Account session</strong>
                  <small>Secure, HTTP-only session cookie.</small>
                </span>
                <button
                  className="button button--secondary button--small"
                  type="button"
                  onClick={() => logout.mutate()}
                  disabled={logout.isPending}
                >
                  {logout.isPending ? 'Signing out…' : 'Log out'}
                </button>
              </div>
            </div>
          )}
          {activeTab === 'security' && (
            <section className="profile-card profile-security-card">
              <div className="card-title">
                <LockKey size={22} weight="fill" />
                <span>Change password</span>
              </div>
              <p className="profile-card__intro">
                Choose a password you do not use anywhere else. Your current
                session will stay signed in after the change.
              </p>
              <form
                onSubmit={(event) => {
                  event.preventDefault()
                  changePassword.mutate({
                    current_password: currentPassword,
                    new_password: newPassword,
                    confirm_password: confirmNewPassword,
                  })
                }}
                noValidate
                aria-busy={changePassword.isPending}
              >
                <label htmlFor="current-password">
                  Current password
                  <span className="password-field">
                    <input
                      id="current-password"
                      name="current-password"
                      type={showCurrentPassword ? 'text' : 'password'}
                      autoComplete="current-password"
                      value={currentPassword}
                      onChange={(event) => {
                        changePassword.reset()
                        setCurrentPassword(event.target.value)
                      }}
                      aria-invalid={currentPassword.length === 0}
                      aria-describedby="current-password-error"
                      required
                    />
                    <button
                      className="input-action"
                      type="button"
                      aria-label={
                        showCurrentPassword
                          ? 'Hide current password'
                          : 'Show current password'
                      }
                      onClick={() =>
                        setShowCurrentPassword((visible) => !visible)
                      }
                    >
                      {showCurrentPassword ? (
                        <EyeSlash size={20} />
                      ) : (
                        <Eye size={20} />
                      )}
                    </button>
                  </span>
                  {currentPassword.length === 0 && (
                    <small id="current-password-error" className="field-error">
                      Enter your current password.
                    </small>
                  )}
                </label>
                <label htmlFor="new-password">
                  New password
                  <span className="password-field">
                    <input
                      id="new-password"
                      name="new-password"
                      type={showNewPassword ? 'text' : 'password'}
                      autoComplete="new-password"
                      minLength={10}
                      maxLength={128}
                      value={newPassword}
                      onChange={(event) => {
                        changePassword.reset()
                        setNewPassword(event.target.value)
                      }}
                      aria-invalid={
                        newPassword.length > 0 && newPassword.length < 10
                      }
                      aria-describedby="password-help new-password-error"
                      required
                    />
                    <button
                      className="input-action"
                      type="button"
                      aria-label={
                        showNewPassword
                          ? 'Hide new password'
                          : 'Show new password'
                      }
                      onClick={() => setShowNewPassword((visible) => !visible)}
                    >
                      {showNewPassword ? (
                        <EyeSlash size={20} />
                      ) : (
                        <Eye size={20} />
                      )}
                    </button>
                  </span>
                  {newPassword.length === 0 ? (
                    <small id="new-password-error" className="field-error">
                      Enter a new password.
                    </small>
                  ) : (
                    newPassword.length < 10 && (
                      <small id="new-password-error" className="field-error">
                        Your new password must be at least 10 characters.
                      </small>
                    )
                  )}
                </label>
                <label htmlFor="confirm-new-password">
                  Confirm new password
                  <span className="password-field">
                    <input
                      id="confirm-new-password"
                      name="confirm-new-password"
                      type={showConfirmNewPassword ? 'text' : 'password'}
                      autoComplete="new-password"
                      minLength={10}
                      maxLength={128}
                      value={confirmNewPassword}
                      onChange={(event) => {
                        changePassword.reset()
                        setConfirmNewPassword(event.target.value)
                      }}
                      aria-invalid={
                        confirmNewPassword.length === 0 ||
                        newPassword !== confirmNewPassword
                      }
                      aria-describedby="confirm-password-error"
                      required
                    />
                    <button
                      className="input-action"
                      type="button"
                      aria-label={
                        showConfirmNewPassword
                          ? 'Hide confirmed password'
                          : 'Show confirmed password'
                      }
                      onClick={() =>
                        setShowConfirmNewPassword((visible) => !visible)
                      }
                    >
                      {showConfirmNewPassword ? (
                        <EyeSlash size={20} />
                      ) : (
                        <Eye size={20} />
                      )}
                    </button>
                  </span>
                  {confirmNewPassword.length === 0 ? (
                    <small id="confirm-password-error" className="field-error">
                      Confirm your new password.
                    </small>
                  ) : (
                    newPassword !== confirmNewPassword && (
                      <small
                        id="confirm-password-error"
                        className="field-error"
                      >
                        Your passwords do not match.
                      </small>
                    )
                  )}
                </label>
                <small id="password-help" className="field-help">
                  Use at least 10 characters. Passwords must match.
                </small>
                {passwordErrors.length > 0 && (
                  <div
                    className="form-error form-error--validation"
                    role="alert"
                    aria-live="polite"
                  >
                    <strong>Please fix the following:</strong>
                    <ul>
                      {passwordErrors.map((error) => (
                        <li key={error}>{error}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {changePassword.isError && (
                  <p className="form-error" role="alert">
                    {changePassword.error.message}
                  </p>
                )}
                {changePassword.isSuccess && (
                  <p className="form-success" role="status">
                    Password changed successfully.
                  </p>
                )}
                <button
                  className="button button--primary"
                  type="submit"
                  disabled={
                    changePassword.isPending ||
                    logout.isPending ||
                    currentPassword.length === 0 ||
                    newPassword.length < 10 ||
                    newPassword !== confirmNewPassword
                  }
                >
                  {logout.isPending
                    ? 'Signing you out…'
                    : changePassword.isPending
                      ? 'Changing password…'
                      : 'Change password'}
                </button>
              </form>
            </section>
          )}
        </section>
      </main>
      <PageFooter />
    </>
  )
}

function ContactScreen() {
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState('')
  const mutation = useMutation({
    mutationFn: api.createCommunityApplication,
    onSuccess: () => setSubmitted(true),
    onError: (cause) => setError(cause instanceof Error ? cause.message : 'We could not send your application.'),
  })
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError('')
    const data = new FormData(event.currentTarget)
    mutation.mutate({
      name: String(data.get('name') ?? '').trim(),
      email: String(data.get('email') ?? '').trim(),
      phone: String(data.get('phone') ?? '').trim() || undefined,
      message: String(data.get('message') ?? '').trim(),
      consent: data.get('consent') === 'on',
      website: String(data.get('website') ?? ''),
    })
  }
  return (
    <>
      <PageHeader screen="contact" />
      <main className="page-content contact-page">
        <section className="contact-intro">
          <span className="eyebrow">Come as you are</span>
          <h1>Join the Safe Space circle <span className="heart-doodle" aria-hidden="true">♡</span></h1>
          <p>Tell us a little about yourself and why this community feels like a good fit. A community steward will review your application and, if approved, send a private WhatsApp invite by email.</p>
          <div className="contact-note"><ShieldCheck size={24} weight="fill" /><span><strong>Your details stay with our stewards.</strong><small>We only use this information to review your application and contact you about joining.</small></span></div>
        </section>
        <section className="form-card contact-form-card" aria-labelledby="contact-form-title">
          {submitted ? (
            <div className="contact-success" role="status">
              <CheckCircle size={42} weight="fill" />
              <h2>Application received.</h2>
              <p>Thank you for reaching out. We’ll review your note and email you if your application is approved.</p>
              <Link className="button button--secondary" to="/">Return home</Link>
            </div>
          ) : (
            <form onSubmit={submit}>
              <h2 id="contact-form-title">Tell us about you</h2>
              <label className="field-label" htmlFor="community-name">Full name<input id="community-name" name="name" required minLength={2} maxLength={120} autoComplete="name" /></label>
              <label className="field-label" htmlFor="community-email">Email address<input id="community-email" name="email" type="email" required autoComplete="email" /></label>
              <label className="field-label" htmlFor="community-phone">Phone or WhatsApp number <span>(optional)</span><input id="community-phone" name="phone" maxLength={40} autoComplete="tel" /></label>
              <label className="field-label" htmlFor="community-message">Why would you like to join?<textarea id="community-message" name="message" required minLength={10} maxLength={3000} rows={6} placeholder="Share only what feels comfortable…" /></label>
              <label className="checkbox-label" htmlFor="community-consent"><input id="community-consent" name="consent" type="checkbox" required /> <span>I’m happy for Safe Space Saturdays to review this application and contact me about the community.</span></label>
              <input className="contact-honeypot" name="website" tabIndex={-1} autoComplete="off" aria-hidden="true" />
              {error && <div className="form-error" role="alert">{error}</div>}
              <button className="button button--primary button--wide" type="submit" disabled={mutation.isPending}>{mutation.isPending ? 'Sending application…' : 'Send application'}</button>
            </form>
          )}
        </section>
      </main>
      <PageFooter />
    </>
  )
}

export function SafeSpaceApp({ screen }: { screen: Screen }) {
  if (screen === 'login' || screen === 'registration')
    return <AuthLayout mode={screen} />
  if (screen === 'contact') return <ContactScreen />
  return <ProtectedApp screen={screen} />
}

function ProtectedApp({
  screen,
}: {
  screen: Exclude<Screen, 'login' | 'registration'>
}) {
  const navigate = useNavigate()
  const [sessionCheckEnabled, setSessionCheckEnabled] = useState(false)
  useEffect(() => setSessionCheckEnabled(true), [])
  const currentUser = useQuery({
    queryKey: ['me'],
    queryFn: api.me,
    retry: shouldRetryApiRequest,
    retryDelay: apiRetryDelay,
    enabled: sessionCheckEnabled,
  })
  const isUnauthenticated = currentUser.error instanceof ApiError && currentUser.error.status === 401
  useEffect(() => {
    if (isUnauthenticated) navigate({ to: '/login', replace: true })
  }, [isUnauthenticated, navigate])
  if (!sessionCheckEnabled || currentUser.isPending)
    return (
      <main className="page-content auth-gate">
        <GeneralLoader label="Checking your safe-space session…" />
      </main>
    )
  if (currentUser.isError && !isUnauthenticated)
    return (
      <main className="page-content auth-gate">
        <GeneralLoader label="Reconnecting to your safe space…" onRetry={() => void currentUser.refetch()} />
      </main>
    )
  if (isUnauthenticated || !currentUser.data) return null
  const content =
    screen === 'admin' ? (
      <AdminScreen />
    ) : screen === 'profile' ? (
      <ProfileScreen />
    ) : screen === 'check-in' ? (
      <CheckInScreen />
    ) : screen === 'challenges' ? (
      <ChallengesScreen />
    ) : screen === 'quotes' ? (
      <QuotesScreen />
    ) : screen === 'community' ? (
      <CommunityScreen />
    ) : screen === 'games' ? (
      <GamesScreen />
    ) : screen === 'leaderboard' ? (
      <LeaderboardScreen />
    ) : (
      <HomeScreen />
    )
  return (
    <>
      {content}
      <BugReportWidget />
    </>
  )
}
