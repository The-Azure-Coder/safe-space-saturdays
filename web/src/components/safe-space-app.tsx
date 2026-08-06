import { useEffect, useRef, useState } from 'react'
import type { ChangeEvent, ComponentType, FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import {
  ArrowRight,
  BookmarkSimple,
  CaretLeft,
  CaretRight,
  CaretDown,
  Check,
  CheckCircle,
  CheckSquare,
  ChatCircleDots,
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
  ThumbsDown,
  ThumbsUp,
  UserCircle,
  UsersThree,
  X,
} from '@phosphor-icons/react'

import { API_URL, api } from '../lib/api'

type Screen =
  | 'home'
  | 'check-in'
  | 'games'
  | 'leaderboard'
  | 'community'
  | 'quotes'
  | 'login'
  | 'registration'
  | 'profile'

type Icon = ComponentType<{ size?: number; weight?: 'regular' | 'fill' | 'duotone'; color?: string }>

const navItems: Array<{ href: string; label: string; icon: Icon }> = [
  { href: '/', label: 'Home', icon: House },
  { href: '/check-in', label: 'Daily Check-In', icon: Heart },
  { href: '/games', label: 'Games', icon: GameController },
  { href: '/leaderboard', label: 'Leaderboard', icon: Trophy },
  { href: '/community', label: 'Community', icon: UsersThree },
  { href: '/quotes', label: 'Quotes', icon: Quotes },
]

const moods = [
  { label: 'Great', icon: '😄' },
  { label: 'Good', icon: '🙂' },
  { label: 'Okay', icon: '😐' },
  { label: 'Not Great', icon: '🙁' },
  { label: 'Struggling', icon: '😔' },
]

type GameDefinition = { name: string; players: string; icon: Icon | string; color: string }

const games: Array<GameDefinition> = [
  { name: 'Ludo', players: '2–4 players', icon: '/assets/game-ludo.png', color: 'sage' },
  { name: 'Dominoes', players: '2–4 players', icon: '/assets/game-dominoes.png', color: 'peach' },
  { name: 'Trivia Battle', players: '2+ players', icon: '/assets/game-trivia.png', color: 'lilac' },
  { name: 'Connect Four', players: '2 players', icon: '/assets/game-connect-four.png', color: 'blue' },
]

function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <Link className={`brand-mark ${compact ? 'brand-mark--compact' : ''}`} to="/" aria-label="Safe Space Saturdays home">
      <img className="brand-mark__image" src="/assets/safe-space-saturdays-logo.jpeg" alt="Safe Space Saturdays — you are not alone" />
    </Link>
  )
}

function PageHeader({ screen }: { screen: Screen }) {
  const currentUser = useQuery({ queryKey: ['me'], queryFn: api.me, retry: false })
  const queryClient = useQueryClient()
  const [menuOpen, setMenuOpen] = useState(false)
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const logout = useMutation({ mutationFn: api.logout, onSuccess: () => { queryClient.clear(); window.location.href = '/login' } })
  const displayName = currentUser.data?.name
  return (
    <header className="app-header">
      <Logo compact />
      <nav id="main-navigation" className={mobileNavOpen ? 'app-nav app-nav--mobile-open' : 'app-nav'} aria-label="Main navigation">
        {navItems.map(({ href, label, icon: NavIcon }) => (
          <Link onClick={() => setMobileNavOpen(false)} className={isActive(screen, href) ? 'app-nav__link app-nav__link--active' : 'app-nav__link'} to={href} key={href}>
            <NavIcon size={22} weight={isActive(screen, href) ? 'fill' : 'regular'} aria-hidden="true" />
            <span>{label}</span>
          </Link>
        ))}
      </nav>
      <button className="mobile-nav-toggle" type="button" aria-label={mobileNavOpen ? 'Close navigation menu' : 'Open navigation menu'} aria-expanded={mobileNavOpen} aria-controls="main-navigation" onClick={() => setMobileNavOpen((open) => !open)}>
        {mobileNavOpen ? <X size={22} aria-hidden="true" /> : <List size={22} aria-hidden="true" />}
      </button>
      {displayName ? <div className="profile-menu-wrap">
        <button className="profile-menu" type="button" aria-label={`Open ${displayName} profile menu`} aria-expanded={menuOpen} aria-haspopup="menu" onClick={() => setMenuOpen((open) => !open)}>
          <span className="avatar avatar--gold">{currentUser.data?.avatar_url ? <img src={`${API_URL}${currentUser.data.avatar_url}`} alt="" /> : displayName[0].toUpperCase()}</span>
          <span className="profile-menu__name">{displayName}</span>
          <CaretDown size={16} aria-hidden="true" />
        </button>
        {menuOpen && <div className="profile-dropdown" role="menu"><Link to="/profile" role="menuitem" onClick={() => setMenuOpen(false)}>Profile & settings</Link><button type="button" role="menuitem" onClick={() => logout.mutate()} disabled={logout.isPending}>{logout.isPending ? 'Signing out…' : 'Log out'}</button></div>}
      </div> : <div className="auth-actions" aria-label="Account actions"><Link className="auth-actions__login" to="/login">Log in</Link><Link className="button button--primary button--small" to="/registration">Sign up</Link></div>}
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
      <span className="footer-leaf footer-leaf--right">❧</span>
    </footer>
  )
}

function SectionHeading({ eyebrow, title, description }: { eyebrow?: string; title: string; description?: string }) {
  return (
    <div className="section-heading">
      {eyebrow && <span className="eyebrow">{eyebrow}</span>}
      <h1>{title} <span className="heart-doodle" aria-hidden="true">♡</span></h1>
      {description && <p>{description}</p>}
    </div>
  )
}

function StatCard({ icon: StatIcon, label, value, detail, tone = 'sage', progress }: { icon: Icon; label: string; value: string; detail: string; tone?: string; progress?: number }) {
  return (
    <article className={`stat-card stat-card--${tone}`}>
      <div className="stat-card__label"><StatIcon size={22} weight="fill" aria-hidden="true" /> <span>{label}</span></div>
      <div className="stat-card__value">{value} <small>{detail}</small></div>
      {progress !== undefined ? <div className="progress-track" aria-label={`${progress}% complete`}><span style={{ width: `${progress}%` }} /></div> : <p>Keep it going!</p>}
    </article>
  )
}

function PaginationControls({ page, itemCount, pageSize, onPageChange, label = 'Results' }: { page: number; itemCount: number; pageSize: number; onPageChange: (page: number) => void; label?: string }) {
  const hasNext = itemCount === pageSize
  return <nav className="pagination-controls" aria-label={`${label} pagination`}><button className="button button--secondary button--small" type="button" disabled={page === 1} onClick={() => onPageChange(page - 1)}>Previous</button><span aria-live="polite">Page {page}</span><button className="button button--secondary button--small" type="button" disabled={!hasNext} onClick={() => onPageChange(page + 1)}>Next</button></nav>
}

function Avatar({ initials, color = 'sage', imageUrl }: { initials: string; color?: string; imageUrl?: string | null }) {
  return <span className={`avatar avatar--${color}`}>{imageUrl ? <img src={`${API_URL}${imageUrl}`} alt="" /> : initials}</span>
}

function AuthLayout({ mode }: { mode: 'login' | 'registration' }) {
  const [showPassword, setShowPassword] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [formError, setFormError] = useState('')
  const [passwordValue, setPasswordValue] = useState('')
  const [confirmPasswordValue, setConfirmPasswordValue] = useState('')
  const isLogin = mode === 'login'
  const mutation = useMutation({
    mutationFn: (body: { name?: string; email: string; password: string; confirm_password?: string }) =>
      isLogin ? api.login({ email: body.email, password: body.password, remember_me: true }) : api.register({ name: body.name ?? '', email: body.email, password: body.password, confirm_password: body.confirm_password ?? '' }),
    onSuccess: () => { setSubmitted(true); window.location.href = '/' },
  })
  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    const name = String(data.get('name') ?? '').trim()
    const email = String(data.get('email') ?? '').trim()
    const password = String(data.get('password') ?? '')
    const confirmPassword = String(data.get('confirm-password') ?? '')
    if (!isLogin && name.length < 2) return setFormError('Please enter your full name.')
    if (password.length < 10) return setFormError('Your password must be at least 10 characters.')
    if (!isLogin && password !== confirmPassword) return setFormError('Passwords do not match.')
    setFormError('')
    mutation.mutate({ name, email, password, confirm_password: confirmPassword })
  }
  return (
    <main className="auth-page">
      <section className="auth-intro">
        <Logo />
        <h1>{isLogin ? 'You are not alone.' : 'Come as you are.'} <span className="heart-doodle">♡</span></h1>
        <p>{isLogin ? 'A gentle place to reconnect, reflect, and find your people.' : 'This is a space to breathe, be seen, and belong. We’re here to listen, support, and walk alongside you.'}</p>
        <img src="/assets/community-circle.png" alt="A group of people gathered together in a supportive circle" />
      </section>
      <section className="auth-panel" aria-labelledby="auth-title">
        <span className="auth-panel__leaf" aria-hidden="true">❧</span>
        <h2 id="auth-title">{isLogin ? 'Welcome back' : 'Create your safe space'}</h2>
        <p className="auth-panel__intro">{isLogin ? 'It’s good to have you here.' : 'Join a community that cares. You are not alone.'}</p>
        {submitted && <div className="form-success" role="status"><CheckCircle size={20} weight="fill" /> {isLogin ? 'Welcome back, Jasmine.' : 'Your account is ready to begin.'}</div>}
        {(formError || mutation.isError) && <div className="form-error" role="alert">{formError || mutation.error?.message || 'We could not complete that request.'}</div>}
        <form onSubmit={onSubmit} noValidate>
          {!isLogin && <label>Full name<input name="name" type="text" placeholder="Your full name" required /></label>}
          <label>Email {isLogin && <span className="sr-only">address</span>}<span className="input-wrap"><EnvelopeSimple size={20} aria-hidden="true" /><input name="email" type="email" placeholder="you@example.com" required /></span></label>
          <label>Password<span className="input-wrap"><LockKey size={20} aria-hidden="true" /><input name="password" type={showPassword ? 'text' : 'password'} placeholder={isLogin ? '••••••••••' : 'Create a strong password'} minLength={10} required value={passwordValue} onChange={(event) => setPasswordValue(event.target.value)} /><button className="input-action" type="button" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? 'Hide password' : 'Show password'}>{showPassword ? <EyeSlash size={20} /> : <Eye size={20} />}</button></span>{!isLogin && <small className="field-help">Use at least 10 characters.</small>}</label>
          {!isLogin && <label>Confirm password<span className="input-wrap"><LockKey size={20} aria-hidden="true" /><input name="confirm-password" type="password" placeholder="Confirm your password" minLength={10} required value={confirmPasswordValue} onChange={(event) => setConfirmPasswordValue(event.target.value)} aria-invalid={confirmPasswordValue.length > 0 && passwordValue !== confirmPasswordValue} />{confirmPasswordValue.length > 0 && passwordValue === confirmPasswordValue && passwordValue.length >= 10 && <Check size={20} className="input-valid" aria-label="Passwords match" />}</span></label>}
          {isLogin ? <div className="form-row"><label className="checkbox-label"><input type="checkbox" defaultChecked /> <span>Remember me</span></label><button className="text-link" type="button">Forgot password?</button></div> : <label className="checkbox-label"><input type="checkbox" required /> <span>I agree to the Safe Space Saturdays Privacy Policy and Terms of Service.</span></label>}
          <button className="button button--primary button--wide" type="submit" disabled={mutation.isPending}>{mutation.isPending ? 'Please wait…' : isLogin ? 'Log in' : 'Create account'}</button>
        </form>
        <p className="auth-switch">{isLogin ? 'New here?' : 'Already have an account?'} <Link to={isLogin ? '/registration' : '/login'}>{isLogin ? 'Create an account' : 'Log in'}</Link></p>
      </section>
    </main>
  )
}

function HomeScreen() {
  const dashboard = useQuery({ queryKey: ['dashboard'], queryFn: api.dashboard })
  const data = dashboard.data
  return <>
    <PageHeader screen="home" />
    <main className="page-content home-page">
      <WelcomeCarousel />
      <section className="stats-grid">
        <StatCard icon={Flame} label="Login Streak" value={data ? String(data.user.streak) : '—'} detail="days" />
        <StatCard icon={Star} label="Total XP" value={data ? data.user.xp.toLocaleString() : '—'} detail="XP" tone="peach" progress={data?.level_progress} />
        <StatCard icon={Leaf} label="Level" value={data ? String(data.user.level) : '—'} detail="Rooted" tone="sage" />
      </section>
      <section className="dashboard-grid">
        <article className="quote-card"><div className="card-title"><Quotes size={22} weight="fill" /> <span>Daily Quote</span></div><blockquote>“{data?.featured_quote?.text ?? 'Take a moment for yourself today.'}”</blockquote><cite>— {data?.featured_quote?.author ?? 'Safe Space Saturdays'}</cite></article>
        <article className="check-card"><div className="card-title"><Smiley size={22} weight="fill" /> <span>How are you feeling today?</span></div><p>Your check-in helps us support you better.</p><div className="mood-row">{moods.map((mood) => <button key={mood.label} type="button"><span>{mood.icon}</span><small>{mood.label}</small></button>)}</div><Link className="button button--primary" to="/check-in">Check In</Link></article>
        <article className="community-card"><div className="card-title"><UsersThree size={22} weight="fill" /> <span>Community Corner</span></div><h3>You are not alone.</h3><p>Join a space that listens, encourages, and grows together.</p><Link className="button button--lilac" to="/community">Explore Community <ArrowRight size={16} /></Link></article>
      </section>
      <GameStrip />
    </main>
    <PageFooter />
  </>
}

const welcomeSlides = [
  { eyebrow: 'Welcome back', title: 'Welcome back to your safe space.', body: 'Here, we talk. We listen. We support. We heal. We grow. You are not alone.', cta: 'Start a check-in', to: '/check-in', tone: 'sage', icon: Heart },
  { eyebrow: 'Small steps count', title: 'Progress can be soft.', body: 'Celebrate the tiny wins too. They are how a steadier, kinder rhythm begins.', cta: 'Visit the community', to: '/community', tone: 'peach', icon: Sparkle },
  { eyebrow: 'Make room to breathe', title: 'You do not have to rush healing.', body: 'Find a quote, settle your shoulders, and give yourself permission to move gently.', cta: 'Find a little calm', to: '/quotes', tone: 'lilac', icon: Leaf },
] as const

function WelcomeCarousel() {
  const [activeSlide, setActiveSlide] = useState(0)
  useEffect(() => {
    const timer = window.setInterval(() => setActiveSlide((slide) => (slide + 1) % welcomeSlides.length), 6500)
    return () => window.clearInterval(timer)
  }, [])
  const slide = welcomeSlides[activeSlide]
  const SlideIcon = slide.icon
  const move = (direction: -1 | 1) => setActiveSlide((current) => (current + direction + welcomeSlides.length) % welcomeSlides.length)
  return <section className={`welcome-carousel welcome-carousel--${slide.tone}`} aria-roledescription="carousel" aria-label="A little encouragement"><div key={`copy-${activeSlide}`} className="welcome-carousel__copy" aria-live="polite"><span className="welcome-carousel__eyebrow">{slide.eyebrow}</span><h2>{slide.title}</h2><p>{slide.body}</p><Link className="button button--primary button--small" to={slide.to}>{slide.cta} <ArrowRight size={16} /></Link></div><div key={`art-${activeSlide}`} className="welcome-carousel__art"><img className="welcome-carousel__image" src="/assets/community-circle.png" alt="Friends supporting one another in a safe space" /><span className="welcome-carousel__sun" aria-hidden="true" /><span className="welcome-carousel__flower welcome-carousel__flower--one" aria-hidden="true">✦</span><span className="welcome-carousel__flower welcome-carousel__flower--two" aria-hidden="true">✿</span><span className="welcome-carousel__icon" aria-hidden="true"><SlideIcon size={36} weight="fill" /></span></div><div className="welcome-carousel__controls"><button type="button" aria-label="Previous encouragement" onClick={() => move(-1)}><CaretLeft size={20} /></button><div className="welcome-carousel__dots">{welcomeSlides.map((item, index) => <button type="button" key={item.title} className={index === activeSlide ? 'welcome-carousel__dot welcome-carousel__dot--active' : 'welcome-carousel__dot'} aria-label={`Show encouragement ${index + 1}`} aria-current={index === activeSlide ? 'true' : undefined} onClick={() => setActiveSlide(index)} />)}</div><button type="button" aria-label="Next encouragement" onClick={() => move(1)}><CaretRight size={20} /></button></div></section>
}

function GameStrip() {
  return <section className="game-strip"><div className="section-row"><div className="card-title"><GameController size={22} weight="fill" /> <span>Featured Games</span></div><Link to="/games">View all games <ArrowRight size={16} /></Link></div><div className="game-strip__items">{games.concat({ name: 'Bingo', players: '2+ players', icon: '/assets/game-bingo.png', color: 'peach' }).map((game) => <GameTile game={game} key={game.name} compact />)}</div></section>
}

function GameTile({ game, compact = false }: { game: GameDefinition; compact?: boolean }) {
  const GameIcon = typeof game.icon === 'string' ? null : game.icon
  const generatedIcon = typeof game.icon === 'string' && game.icon.startsWith('/') ? game.icon : ({
    Ludo: '/assets/game-ludo.png',
    Dominoes: '/assets/game-dominoes.png',
    'Trivia Battle': '/assets/game-trivia.png',
    'Connect Four': '/assets/game-connect-four.png',
    Bingo: '/assets/game-bingo.png',
  }[game.name] ?? null)
  return <article className={`game-tile game-tile--${game.color} ${compact ? 'game-tile--compact' : ''}`}><span className="game-tile__icon" aria-hidden="true">{generatedIcon ? <img src={generatedIcon} alt="" /> : GameIcon ? <GameIcon size={compact ? 34 : 48} weight="duotone" /> : null}</span><h3>{game.name}</h3><Link className="button button--small button--primary" to="/games">Play</Link>{!compact && <small>{game.players}</small>}</article>
}

function CheckInScreen() {
  const [selectedMood, setSelectedMood] = useState('')
  const [needs, setNeeds] = useState<Array<string>>([])
  const [energy, setEnergy] = useState(3)
  const [stress, setStress] = useState(3)
  const [thoughts, setThoughts] = useState('')
  const [gratitude, setGratitude] = useState('')
  const [complete, setComplete] = useState(false)
  const mutation = useMutation({ mutationFn: api.createCheckIn, onSuccess: () => setComplete(true) })
  const submit = () => {
    if (!selectedMood) return
    mutation.mutate({ mood: selectedMood, needs, energy, stress, thoughts: thoughts || null, gratitude: gratitude || null, completed: true })
  }
  return <><PageHeader screen="check-in" /><main className="page-content checkin-page"><div className="checkin-main"><SectionHeading title="Daily Check-In" description="Take a moment to check in with yourself. Your responses help us support you better." />
    <section className="form-card"><h2><Smiley size={24} weight="fill" /> 1. How are you feeling today?</h2><div className="mood-row mood-row--large">{moods.map((mood) => <button className={selectedMood === mood.label ? 'mood-option mood-option--selected' : 'mood-option'} key={mood.label} type="button" onClick={() => setSelectedMood(mood.label)}><span>{mood.icon}</span><small>{mood.label}</small></button>)}</div></section>
    <div className="two-column"><section className="form-card"><h2><Leaf size={24} weight="fill" /> 2. What do you need today?</h2><div className="choice-list">{['Rest', 'Encouragement', 'Space', 'Someone to Talk To', 'Motivation', 'Fun', 'Prayer / Positive Words'].map((choice) => <button type="button" key={choice} className={needs.includes(choice) ? 'choice-chip choice-chip--selected' : 'choice-chip'} onClick={() => setNeeds((current) => current.includes(choice) ? current.filter((item) => item !== choice) : [...current, choice])}><span aria-hidden="true">{choice === 'Rest' ? '🛏️' : choice === 'Encouragement' ? '🧡' : choice === 'Space' ? '☁️' : choice === 'Motivation' ? '⭐' : '🌿'}</span>{choice}</button>)}</div></section><section className="form-card"><h2><Sparkle size={24} weight="fill" /> 3. Energy & Stress Check</h2><RangeRow label="Energy Level" left="Low" right="High" value={energy} onChange={setEnergy} /><RangeRow label="Stress Level" left="Calm" right="Overwhelmed" value={stress} onChange={setStress} accent /></section></div>
    <div className="two-column"><section className="form-card"><h2><PencilSimple size={24} /> 4. What’s on your mind?</h2><label className="field-label" htmlFor="checkin-thoughts">Your thoughts<textarea id="checkin-thoughts" placeholder="Write a few thoughts about your day..." value={thoughts} onChange={(event) => setThoughts(event.target.value)} /></label></section><section className="form-card"><h2><Heart size={24} weight="fill" /> 5. What are you grateful for today?</h2><label className="field-label" htmlFor="checkin-gratitude">A small gratitude<textarea id="checkin-gratitude" placeholder="Write about something you are grateful for..." value={gratitude} onChange={(event) => setGratitude(event.target.value)} /></label></section></div>
    <div className="privacy-note"><ShieldCheck size={24} weight="fill" /><span><strong>Your privacy matters.</strong><small>Your check-in is private and only you can see your responses.</small></span></div>{mutation.isError && <div className="form-error" role="alert">{mutation.error.message}</div>}<div className="checkin-actions"><button className="button button--primary button--wide" type="button" onClick={submit} disabled={mutation.isPending || !selectedMood}><CheckSquare size={22} /> {complete ? 'Check-In Complete' : mutation.isPending ? 'Saving…' : 'Complete Check-In'}</button><button className="button button--secondary button--wide" type="button"><BookmarkSimple size={22} /> Save for Later</button></div>
  </div><aside className="checkin-sidebar"><StatCard icon={Flame} label="Current Streak" value="12" detail="days" /><article className="quote-card"><div className="card-title"><Quotes size={22} weight="fill" /> <span>Quote of the Day</span></div><blockquote>“You don’t have to have it all figured out to move forward.”</blockquote><cite>— Unknown</cite></article><article className="support-card"><div className="card-title"><UsersThree size={22} weight="fill" /> <span>Need Extra Support?</span></div><p>You are not alone. Reach out to a trusted club leader or join the <em>Wellness Circle.</em></p><Link className="button button--lilac" to="/community">Join Wellness Circle</Link></article></aside></main><PageFooter /></>
}

function RangeRow({ label, left, right, accent = false, value, onChange }: { label: string; left: string; right: string; accent?: boolean; value?: number; onChange?: (value: number) => void }) {
  const inputId = `range-${label.toLowerCase().replaceAll(' ', '-')}`
  return <div className={`range-row ${accent ? 'range-row--accent' : ''}`}><div className="range-row__heading"><label htmlFor={inputId}>{label}</label><output htmlFor={inputId}>{value ?? 3} / 5</output></div><input id={inputId} aria-label={label} type="range" min="1" max="5" value={value ?? 3} onInput={(event) => onChange?.(Number(event.currentTarget.value))} onChange={(event) => onChange?.(Number(event.currentTarget.value))} /><div className="range-labels"><span>{left}</span><span>{right}</span></div></div>
}

function QuotesScreen() {
  const [category, setCategory] = useState('All')
  const [page, setPage] = useState(1)
  const queryClient = useQueryClient()
  const quotes = useQuery({ queryKey: ['quotes', category, page], queryFn: () => api.quotes(category, page, 4) })
  const save = useMutation({ mutationFn: api.saveQuote, onSuccess: () => queryClient.invalidateQueries({ queryKey: ['quotes'] }) })
  const featured = quotes.data?.find((quote) => quote.is_featured) ?? quotes.data?.[0]
  return <><PageHeader screen="quotes" /><main className="page-content quotes-page"><SectionHeading title="A little something for today" description="Words can uplift, comfort, and remind us we’re not alone. Take what you need, and come back anytime." /><article className="featured-quote"><span className="quote-mark"><Quotes size={28} weight="fill" /></span><blockquote>“{featured?.text ?? 'Take a moment for yourself today.'}”</blockquote><cite>— {featured?.author ?? 'Safe Space Saturdays'}</cite><div className="carousel-dots"><i /><i /><i /></div></article><div className="quote-grid">{(quotes.data ?? []).filter((quote) => quote.id !== featured?.id).slice(0, 3).map((quote, index) => <article className={`small-quote small-quote--${index}`} key={quote.id}><Quotes size={20} weight="fill" /><p>{quote.text}</p><cite>— {quote.author}</cite></article>)}</div><div className="quote-actions"><button className="button button--primary" type="button" disabled={!featured} onClick={() => featured && save.mutate(featured.id)}><BookmarkSimple size={20} /> {featured?.saved ? 'Saved' : 'Save this quote'}</button><button className="button button--secondary" type="button"><UsersThree size={20} /> Share with community</button></div><div className="filter-row">{['All', 'Encouragement', 'Rest', 'Growth', 'Connection'].map((filter, index) => <button className={category === filter ? 'filter-chip filter-chip--active' : 'filter-chip'} type="button" onClick={() => { setCategory(filter); setPage(1) }} key={filter}>{index === 0 ? <Leaf size={18} /> : index === 1 ? <Sparkle size={18} /> : index === 2 ? <span>☾</span> : <Leaf size={18} />}{filter}</button>)}</div><PaginationControls page={page} itemCount={quotes.data?.length ?? 0} pageSize={4} onPageChange={setPage} label="Quotes" /></main><PageFooter /></>
}

function CommunityScreen() {
  const [draft, setDraft] = useState('')
  const [page, setPage] = useState(1)
  const [replyDrafts, setReplyDrafts] = useState<Record<number, string>>({})
  const [openReplyPostId, setOpenReplyPostId] = useState<number | null>(null)
  const [imageFile, setImageFile] = useState<File | undefined>()
  const [imageError, setImageError] = useState('')
  const imageInput = useRef<HTMLInputElement>(null)
  const queryClient = useQueryClient()
  const postsQuery = useQuery({ queryKey: ['posts', page], queryFn: () => api.posts(page, 10) })
  const create = useMutation({ mutationFn: () => api.createPost(draft.trim(), imageFile), onSuccess: () => { setDraft(''); setImageFile(undefined); if (imageInput.current) imageInput.current.value = ''; queryClient.invalidateQueries({ queryKey: ['posts'] }) } })
  const react = useMutation({ mutationFn: ({ id, kind }: { id: number; kind: 'like' | 'dislike' }) => api.react(id, kind), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['posts'] }) })
  const reply = useMutation({ mutationFn: ({ id, text }: { id: number; text: string }) => api.reply(id, text), onSuccess: (_, variables) => { setReplyDrafts((drafts) => ({ ...drafts, [variables.id]: '' })); setOpenReplyPostId(null); queryClient.invalidateQueries({ queryKey: ['posts'] }); queryClient.invalidateQueries({ queryKey: ['replied-posts'] }) } })
  const chooseImage = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type) || file.size > 5_000_000) {
      setImageError('Choose a JPEG, PNG, or WebP image smaller than 5 MB.')
      setImageFile(undefined)
      event.currentTarget.value = ''
      return
    }
    setImageError('')
    setImageFile(file)
  }
  return <><PageHeader screen="community" /><main className="page-content community-page"><section className="community-hero"><img src="/assets/community-circle.png" alt="A group of friends supporting each other" /><SectionHeading title="Community" description="A place to talk, listen, and feel less alone." /></section><div className="community-promos"><PromoCard title="Wellness Circle" body="Open talks and guided conversations in a judgement-free space." cta="Join Circle" tone="sage" icon="🌿" /><PromoCard title="Game Night" body="Play fun games, connect, and unwind with friends." cta="See Upcoming" tone="peach" icon="🎮" /><PromoCard title="Small Wins" body="Celebrate progress, share wins, and uplift each other." cta="Share a Win" tone="lilac" icon="🪴" /></div><div className="community-layout"><section className="conversation-card"><div className="section-row"><div className="card-title"><ChatCircleDots size={24} weight="fill" /><span>Community Conversations</span><small>Share, support, and grow together.</small></div><button className="button button--primary" type="button" onClick={() => document.getElementById('post-composer')?.focus()}><PencilSimple size={18} /> Start a Post</button></div><div className="post-composer"><label className="sr-only" htmlFor="post-composer">Share something with the community</label><textarea id="post-composer" value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Share a small win or a kind thought…" /><div className="post-composer__controls"><label className="button button--secondary button--small post-image-picker"><span>Attach image</span><input ref={imageInput} type="file" accept="image/jpeg,image/png,image/webp" onChange={chooseImage} /></label>{imageFile && <small>{imageFile.name}</small>}{imageError && <p className="form-error" role="alert">{imageError}</p>}<button className="button button--small button--primary" type="button" disabled={!draft.trim() || create.isPending || Boolean(imageError)} onClick={() => create.mutate()}>{create.isPending ? 'Posting…' : 'Post'}</button></div></div>{(postsQuery.data ?? []).map((post) => <article className="post-row" key={post.id}><Avatar initials={post.initials} color="sage" /><div className="post-row__body"><div className="post-row__meta"><strong>{post.author}</strong><span>• {new Date(post.created_at).toLocaleString()}</span></div><p>{post.text}</p>{post.image_url && <img className="post-row__image" src={`${API_URL}${post.image_url}`} alt={`Image shared by ${post.author}`} />}<div className="post-row__actions"><button className={post.my_reaction === 'like' ? 'reaction-button reaction-button--active' : 'reaction-button'} type="button" aria-label={`Like ${post.author}'s post`} aria-pressed={post.my_reaction === 'like'} onClick={() => react.mutate({ id: post.id, kind: 'like' })}><ThumbsUp size={17} weight="fill" /> <span>Like</span> {post.likes}</button><button className={post.my_reaction === 'dislike' ? 'reaction-button reaction-button--active' : 'reaction-button'} type="button" aria-label={`Dislike ${post.author}'s post`} aria-pressed={post.my_reaction === 'dislike'} onClick={() => react.mutate({ id: post.id, kind: 'dislike' })}><ThumbsDown size={17} weight="fill" /> <span>Dislike</span> {post.dislikes}</button><button className="reaction-button" type="button" aria-expanded={openReplyPostId === post.id} onClick={() => setOpenReplyPostId((current) => current === post.id ? null : post.id)}><ChatCircleDots size={17} /> <span>Reply</span></button></div>{post.comments.length > 0 && <div className="post-replies" aria-label={`Replies to ${post.author}'s post`}>{post.comments.map((comment) => <div className="post-reply" key={comment.id}><Avatar initials={comment.initials} color="lilac" /><div><strong>{comment.author}</strong><p>{comment.text}</p></div></div>)}</div>}{openReplyPostId === post.id && <form className="reply-form" onSubmit={(event) => { event.preventDefault(); const text = (replyDrafts[post.id] ?? '').trim(); if (text) reply.mutate({ id: post.id, text }) }}><label className="sr-only" htmlFor={`reply-${post.id}`}>Reply to {post.author}'s post</label><input id={`reply-${post.id}`} autoFocus value={replyDrafts[post.id] ?? ''} onChange={(event) => setReplyDrafts((drafts) => ({ ...drafts, [post.id]: event.target.value }))} placeholder="Write a thoughtful reply…" maxLength={1000} /><button className="button button--secondary button--small" type="submit" disabled={!(replyDrafts[post.id] ?? '').trim() || reply.isPending}>Reply</button></form>}</div><button className="more-button" aria-label={`More actions for ${post.author}`} type="button">•••</button></article>)}<PaginationControls page={page} itemCount={postsQuery.data?.length ?? 0} pageSize={10} onPageChange={setPage} label="Community posts" /></section><aside className="guidelines-card"><div className="card-title"><Leaf size={24} weight="fill" /><span>Community guidelines</span></div><p>We care for each other.</p>{[['🧡', 'Be Kind', 'Choose compassion and respect in every interaction.'], ['🔒', 'Respect Privacy', 'What’s shared here stays here. Protect each other’s stories.'], ['🌱', 'Encourage & Uplift', 'Cheer each other on and celebrate every step forward.']].map(([icon, title, text]) => <div className="guideline" key={title}><span>{icon}</span><div><strong>{title}</strong><p>{text}</p></div></div>)}</aside></div></main><PageFooter /></>
}

function PromoCard({
  title,
  body,
  cta,
  tone,
  icon,
}: {
  title: string
  body: string
  cta: string
  tone: string
  icon: string
}) {
  return (
    <article className={`promo-card promo-card--${tone}`}>
      <span className="promo-card__icon" aria-hidden="true">
        {icon}
      </span>
      <div>
        <h2>{title}</h2>
        <p>{body}</p>
        <button className="button button--small button--primary">{cta}</button>
      </div>
    </article>
  )
}

function GamesScreen() {
  const [gamesPage, setGamesPage] = useState(1)
  const [roomsPage, setRoomsPage] = useState(1)
  const gamesQuery = useQuery({
    queryKey: ['games', gamesPage],
    queryFn: () => api.games(gamesPage, 4),
  })
  const roomsQuery = useQuery({
    queryKey: ['rooms', roomsPage],
    queryFn: () => api.rooms(roomsPage, 5),
  })
  const queryClient = useQueryClient()
  const join = useMutation({
    mutationFn: api.joinRoom,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['rooms'] }),
  })
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
              Game Night Starts at 6:30 PM!{' '}
              <span className="heart-doodle">♡</span>
            </h2>
            <p>Join friends for fun, connection, and friendly competition.</p>
          </div>
          <button className="button button--orange" type="button">
            Join Game Night
          </button>
          <button className="button button--ghost" type="button">
            Create Room
          </button>
        </section>
        <div className="games-layout">
          <section className="games-panel">
            <div className="card-title">
              <GameController size={24} weight="fill" />
              <span>Featured Games</span>
            </div>
            <div className="game-grid">
              {(gamesQuery.data ?? []).map((game) => (
                <GameTile game={{ ...game, color: game.color }} key={game.id} />
              ))}
            </div>
            <PaginationControls
              page={gamesPage}
              itemCount={gamesQuery.data?.length ?? 0}
              pageSize={4}
              onPageChange={setGamesPage}
              label="Games"
            />
          </section>
          <section className="rooms-panel">
            <div className="section-row">
              <div className="card-title">
                <UsersThree size={24} weight="fill" />
                <span>Live Rooms</span>
              </div>
            </div>
            {(roomsQuery.data ?? []).map((room) => (
              <div className="room-row" key={room.id}>
                <span className="room-icon" aria-hidden="true">
                  🎲
                </span>
                <div>
                  <strong>{room.name}</strong>
                  <small>
                    {room.players} / {room.max_players} players
                  </small>
                </div>
                <button
                  className="button button--small button--primary"
                  type="button"
                  disabled={room.joined || join.isPending}
                  onClick={() => join.mutate(room.id)}
                >
                  {room.joined ? 'Joined' : 'Join'}
                </button>
              </div>
            ))}
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
            <div className="winner-row">
              <Avatar initials="★" color="gold" />
              <div>
                <strong>Community winners</strong>
                <small>Results will appear after game night.</small>
              </div>
            </div>
          </section>
        </div>
      </main>
      <PageFooter />
    </>
  )
}

function LeaderboardScreen() {
  const [period, setPeriod] = useState('week')
  const [page, setPage] = useState(1)
  const leaderboard = useQuery({
    queryKey: ['leaderboard', period, page],
    queryFn: () => api.leaderboard(period, page, 10),
  })
  const entries = leaderboard.data ?? []
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
            {page === 1 &&
              entries.slice(0, 3).map((entry, index) => (
                <div
                  className={`podium-member podium-member--${index + 1}`}
                  key={entry.user.id}
                >
                  <span className="podium-rank">{index + 1}</span>
                  <Avatar initials={entry.user.name[0]} color="sage" />
                  <strong>{entry.user.name}</strong>
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
                <strong>
                  #
                  {entries.find((entry) => entry.user.name === 'Jasmine')
                    ?.rank ?? '—'}
                </strong>
              </span>
              <span>
                Total XP
                <strong>
                  {entries
                    .find((entry) => entry.user.name === 'Jasmine')
                    ?.user.xp.toLocaleString() ?? '—'}{' '}
                  <small>XP</small>
                </strong>
              </span>
            </div>
            <p>Keep it going!</p>
          </aside>
        </section>
        <div className="leaderboard-filter">
          {[
            ['week', 'This Week'],
            ['month', 'This Month'],
            ['all', 'All Time'],
          ].map(([value, label]) => (
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
            <span>Total XP</span>
            <span>Current Streak</span>
          </div>
          {entries.map((entry) => (
            <div className="leaderboard-row" key={entry.user.id}>
              <strong>{entry.rank}</strong>
              <div>
                <Avatar initials={entry.user.name[0]} color="sage" />
                <span>
                  {entry.user.name} <Leaf size={16} weight="fill" />
                </span>
              </div>
              <span className="xp xp--sage">
                {entry.user.xp.toLocaleString()} <small>XP</small>
              </span>
              <span>
                {entry.user.streak} <small>days</small>
              </span>
            </div>
          ))}
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
    'profile' | 'activity' | 'appearance' | 'privacy'
  >('profile')
  const [avatarPreview, setAvatarPreview] = useState<string | null>(null)
  const [avatarFile, setAvatarFile] = useState<File | undefined>()
  const [likedPage, setLikedPage] = useState(1)
  const [repliedPage, setRepliedPage] = useState(1)
  const [avatarError, setAvatarError] = useState('')
  const [theme, setTheme] = useState<'sage' | 'night' | 'high-contrast'>(() => {
    if (typeof window === 'undefined') return 'sage'
    return (
      (window.localStorage.getItem('safe-space-theme') as
        'sage' | 'night' | 'high-contrast' | null) ?? 'sage'
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
  const handleAvatarChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return
    if (!file.type.startsWith('image/') || file.size > 2_000_000) {
      setAvatarError('Choose an image smaller than 2 MB.')
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
                  src={`${API_URL}${user.avatar_url}`}
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
                  JPG, PNG, or WebP. Maximum 2 MB.
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
        </section>
      </main>
      <PageFooter />
    </>
  )
}

export function SafeSpaceApp({ screen }: { screen: Screen }) {
  if (screen === 'login' || screen === 'registration') return <AuthLayout mode={screen} />
  if (screen === 'profile') return <ProfileScreen />
  if (screen === 'check-in') return <CheckInScreen />
  if (screen === 'quotes') return <QuotesScreen />
  if (screen === 'community') return <CommunityScreen />
  if (screen === 'games') return <GamesScreen />
  if (screen === 'leaderboard') return <LeaderboardScreen />
  return <HomeScreen />
}
