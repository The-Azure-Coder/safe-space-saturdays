import { afterEach, describe, expect, it, vi } from 'vitest'

import { openReconnectingGameSocket } from './game-websocket'

class FakeSocket {
  static OPEN = 1
  readyState = FakeSocket.OPEN
  onopen: (() => void) | null = null
  onmessage: ((event: MessageEvent) => void) | null = null
  onerror: (() => void) | null = null
  onclose: ((event: CloseEvent) => void) | null = null
  close = vi.fn(() => {
    this.readyState = 3
  })
  send = vi.fn()
}

describe('openReconnectingGameSocket', () => {
  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  const installWindow = () => vi.stubGlobal('window', {
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    setTimeout,
    clearTimeout,
  })

  it('resyncs on open and reconnects after an abnormal close', async () => {
    vi.useFakeTimers()
    installWindow()
    const sockets: Array<FakeSocket> = []
    const statuses: Array<string> = []
    const resync = vi.fn()
    const cleanup = openReconnectingGameSocket({
      url: 'ws://example.test/game',
      createSocket: () => {
        const socket = new FakeSocket()
        sockets.push(socket)
        return socket as unknown as WebSocket
      },
      reconnectDelay: () => 25,
      onMessage: vi.fn(),
      onSocket: vi.fn(),
      onStatus: (status) => statuses.push(status),
      onResync: resync,
    })

    sockets[0].onopen?.()
    expect(resync).toHaveBeenCalledOnce()
    sockets[0].onclose?.({ code: 1006, reason: '' } as CloseEvent)
    await vi.advanceTimersByTimeAsync(25)
    expect(sockets).toHaveLength(2)
    expect(statuses).toContain('reconnecting')
    cleanup()
  })

  it('rejects unreadable messages and does not retry policy closures', () => {
    vi.useFakeTimers()
    installWindow()
    const sockets: Array<FakeSocket> = []
    const details: Array<string> = []
    openReconnectingGameSocket({
      url: 'ws://example.test/game',
      createSocket: () => {
        const socket = new FakeSocket()
        sockets.push(socket)
        return socket as unknown as WebSocket
      },
      onMessage: vi.fn(),
      onSocket: vi.fn(),
      onStatus: (_status, detail) => { if (detail) details.push(detail) },
      onResync: vi.fn(),
    })

    sockets[0].onmessage?.({ data: 'not-json' } as MessageEvent)
    expect(sockets[0].close).toHaveBeenCalled()
    sockets[0].onclose?.({ code: 1008, reason: 'Origin is not allowed' } as CloseEvent)
    vi.runAllTimers()
    expect(sockets).toHaveLength(1)
    expect(details).toContain('Origin is not allowed')
  })
})
