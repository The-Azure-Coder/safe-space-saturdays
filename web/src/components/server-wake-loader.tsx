import { useEffect, useRef, useState } from 'react'
import { GameController, Sparkle } from '@phosphor-icons/react'

import { API_HEALTH_URL } from '../lib/api'

type WakeContext = 'auth' | 'game' | 'lobby' | 'session'

const content: Record<WakeContext, { title: string; opening: string }> = {
  auth: {
    title: 'Waking your safe space',
    opening: 'Keeping your sign-in request safe while the server gets ready.',
  },
  game: {
    title: 'Waking the game server',
    opening: 'Keeping your place while the game server gets ready.',
  },
  lobby: {
    title: 'Preparing your game room',
    opening: 'Keeping your seat while the lobby reconnects.',
  },
  session: {
    title: 'Checking your safe space session',
    opening: 'Your session is still here while the server reconnects.',
  },
}

export function ServerWakeLoader({
  context = 'game',
  attempt = 0,
  exhausted = false,
  onRetry,
}: {
  context?: WakeContext
  attempt?: number
  exhausted?: boolean
  onRetry?: () => void
}) {
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const startedAt = useRef(Date.now())

  useEffect(() => {
    if (exhausted) return undefined
    const controller = new AbortController()
    const timeout = window.setTimeout(() => controller.abort(), 90_000)
    void fetch(`${API_HEALTH_URL}?wake=${Date.now()}`, {
      cache: 'no-store',
      headers: { accept: 'application/json' },
      signal: controller.signal,
    }).catch(() => {
      // The query owning this loader will retry while the API wakes.
    })
    const timer = window.setInterval(
      () => setElapsedSeconds(Math.floor((Date.now() - startedAt.current) / 1_000)),
      1_000,
    )
    return () => {
      controller.abort()
      window.clearTimeout(timeout)
      window.clearInterval(timer)
    }
  }, [exhausted])

  const progress = exhausted
    ? 100
    : elapsedSeconds <= 45
      ? Math.round(5 + (elapsedSeconds / 45) * 90)
      : Math.min(99, Math.round(95 + ((elapsedSeconds - 45) / 180) * 4))
  const remaining = Math.max(1, 45 - elapsedSeconds)
  const phase = exhausted
    ? 'Still waiting for the server'
    : elapsedSeconds >= 45
      ? 'Finishing the wake-up'
      : elapsedSeconds >= 12
        ? 'Loading your space'
        : 'Starting the server'
  const message = exhausted
    ? 'The server is still waking. We will keep your place safe while you try again.'
    : content[context].opening

  return (
    <section
      className={`server-wake-loader${exhausted ? ' server-wake-loader--error' : ''}`}
      role={exhausted ? 'alert' : 'status'}
      aria-live={exhausted ? 'assertive' : 'polite'}
      aria-atomic="true"
    >
      <div className="server-wake-loader__topline">
        <span className="server-wake-loader__icon" aria-hidden="true">
          <GameController size={18} weight="duotone" />
          <Sparkle size={8} weight="fill" />
        </span>
        <span>{phase}</span>
        <small>Attempt {attempt + 1}</small>
      </div>
      <div className="server-wake-loader__copy">
        <strong>{exhausted ? 'Your space is still here' : content[context].title}</strong>
        <p>{message}</p>
      </div>
      <div className="server-wake-loader__progress" aria-label={`${Math.round(progress)} percent of this server check complete`}>
        <span style={{ width: `${progress}%` }} />
      </div>
      <div className="server-wake-loader__countdown" aria-live="polite">
        {exhausted
          ? 'Ready when the server responds'
          : elapsedSeconds >= 45
            ? 'Final readiness check · we keep trying automatically'
            : `Usually ready in about ${remaining}s · we keep trying automatically`}
      </div>
      {exhausted ? (
        <button
          className="button button--small button--primary"
          type="button"
          onClick={onRetry}
        >
          Try again
        </button>
      ) : (
        <div className="server-wake-loader__status" aria-hidden="true">
          <span />
          <span />
          <span />
          <small>
            {attempt > 0 ? 'Reconnecting automatically' : 'Connecting securely'}
          </small>
        </div>
      )}
    </section>
  )
}
