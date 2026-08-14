import { useEffect, useMemo, useState } from 'react'
import type { PropsWithChildren } from 'react'
import { CloudArrowUp, GameController, Heartbeat } from '@phosphor-icons/react'

import { API_HEALTH_URL } from '../lib/api'

// Render cold starts regularly take 40-60 seconds. Keep a single wake request
// alive long enough for Render to finish instead of cancelling and restarting it.
const PROBE_TIMEOUT_MS = 90_000
const RETRY_DELAY_MS = 1_000
const EXPECTED_WAKE_SECONDS = 55

type WakeState = 'checking' | 'finishing' | 'ready'

function estimatedProgress(elapsedSeconds: number): number {
  if (elapsedSeconds <= EXPECTED_WAKE_SECONDS)
    return Math.round(4 + (elapsedSeconds / EXPECTED_WAKE_SECONDS) * 91)
  return Math.min(
    99,
    Math.round(95 + ((elapsedSeconds - EXPECTED_WAKE_SECONDS) / 180) * 4),
  )
}

function wait(milliseconds: number) {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds))
}

export function ApiWakeGate({ children }: PropsWithChildren) {
  const [state, setState] = useState<WakeState>('checking')
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const [attempt, setAttempt] = useState(1)
  const [showLoader, setShowLoader] = useState(false)

  useEffect(() => {
    let active = true
    let activeController: AbortController | null = null
    let finishTimer: number | null = null
    const startedAt = Date.now()
    const revealTimer = window.setTimeout(() => setShowLoader(true), 450)
    const elapsedTimer = window.setInterval(
      () => setElapsedSeconds(Math.floor((Date.now() - startedAt) / 1_000)),
      500,
    )

    const probeUntilReady = async () => {
      let probeNumber = 1
      while (active) {
        setAttempt(probeNumber)
        activeController = new AbortController()
        const timeout = window.setTimeout(
          () => activeController?.abort(),
          PROBE_TIMEOUT_MS,
        )
        try {
          const response = await fetch(`${API_HEALTH_URL}?wake=${Date.now()}`, {
            cache: 'no-store',
            headers: { accept: 'application/json' },
            signal: activeController.signal,
          })
          const body = (await response.json().catch(() => null)) as {
            status?: unknown
          } | null
          if (response.ok && body?.status === 'ready') {
            window.clearTimeout(revealTimer)
            setElapsedSeconds(Math.floor((Date.now() - startedAt) / 1_000))
            setShowLoader(true)
            setState('finishing')
            finishTimer = window.setTimeout(() => setState('ready'), 500)
            return
          }
        } catch {
          // A timeout or network failure is expected while Render is waking.
        } finally {
          window.clearTimeout(timeout)
        }
        probeNumber += 1
        await wait(RETRY_DELAY_MS)
      }
    }

    void probeUntilReady()
    return () => {
      active = false
      activeController?.abort()
      if (finishTimer !== null) window.clearTimeout(finishTimer)
      window.clearTimeout(revealTimer)
      window.clearInterval(elapsedTimer)
    }
  }, [])

  const progress =
    state === 'finishing' || state === 'ready'
      ? 100
      : estimatedProgress(elapsedSeconds)
  const remainingEstimate = Math.max(0, EXPECTED_WAKE_SECONDS - elapsedSeconds)
  const phase = useMemo(() => {
    if (state === 'finishing' || state === 'ready') return 'Server ready'
    if (elapsedSeconds < 8) return 'Contacting Render'
    if (elapsedSeconds < 25) return 'Starting the API'
    if (elapsedSeconds < EXPECTED_WAKE_SECONDS) return 'Loading community data'
    return 'Still waking, checking again'
  }, [elapsedSeconds, state])

  if (state === 'ready') return <>{children}</>
  if (!showLoader)
    return (
      <main
        className="api-wake-screen api-wake-screen--quiet"
        aria-label="Connecting to Safe Space Saturdays"
      />
    )

  return (
    <main className="api-wake-screen">
      <section
        className="api-wake-console"
        role="status"
        aria-live="polite"
        aria-atomic="true"
      >
        <div className="api-wake-console__art" aria-hidden="true">
          <span>
            <GameController size={31} weight="duotone" />
          </span>
          <i>
            <Heartbeat size={17} weight="bold" />
          </i>
          <i>
            <CloudArrowUp size={18} weight="duotone" />
          </i>
        </div>
        <div className="api-wake-console__heading">
          <span>Safe Space Saturdays</span>
          <strong>Preparing your safe space</strong>
          <p>{phase}</p>
        </div>
        <div
          className="api-wake-console__track"
          role="progressbar"
          aria-label="Estimated API wake-up progress"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={progress}
          aria-valuetext={`${progress}% estimated. ${phase}`}
        >
          <span style={{ width: `${progress}%` }} />
          <i style={{ left: `${progress}%` }} />
        </div>
        <div className="api-wake-console__meta">
          <strong>
            {state === 'finishing'
              ? '100% ready'
              : remainingEstimate > 0
                ? `${progress}% estimated`
                : 'Final readiness check'}
          </strong>
          <span>
            {remainingEstimate > 0
              ? `Usually ready in about ${remainingEstimate}s`
              : 'Taking longer than usual. We are still checking.'}
          </span>
        </div>
        <div className="api-wake-console__probe">
          <span className="api-wake-console__signal" aria-hidden="true" />
          API readiness check {attempt}. This screen closes only when the API
          responds.
        </div>
      </section>
    </main>
  )
}
