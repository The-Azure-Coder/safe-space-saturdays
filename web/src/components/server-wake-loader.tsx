import { useEffect, useState } from 'react'
import { GameController, Sparkle } from '@phosphor-icons/react'

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

  useEffect(() => {
    if (exhausted) return
    const timer = window.setInterval(
      () => setElapsedSeconds((current) => current + 1),
      1_000,
    )
    return () => window.clearInterval(timer)
  }, [exhausted])

  const message = exhausted
    ? 'The server is taking longer than expected. Your place is safe, and you can try again.'
    : elapsedSeconds >= 30
      ? 'Still reconnecting. Your room and progress are being kept safe.'
      : elapsedSeconds >= 12
        ? 'This can take a little longer after a quiet spell. We will keep trying for you.'
        : content[context].opening

  return (
    <section
      className={`server-wake-loader${exhausted ? ' server-wake-loader--error' : ''}`}
      role={exhausted ? 'alert' : 'status'}
      aria-live={exhausted ? 'assertive' : 'polite'}
      aria-atomic="true"
    >
      <div className="server-wake-loader__visual" aria-hidden="true">
        <span className="server-wake-loader__halo" />
        <GameController size={35} weight="duotone" />
        <Sparkle
          className="server-wake-loader__spark server-wake-loader__spark--one"
          size={15}
          weight="fill"
        />
        <Sparkle
          className="server-wake-loader__spark server-wake-loader__spark--two"
          size={11}
          weight="fill"
        />
      </div>
      <div className="server-wake-loader__copy">
        <strong>
          {exhausted ? 'We could not reconnect yet' : content[context].title}
        </strong>
        <p>{message}</p>
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
