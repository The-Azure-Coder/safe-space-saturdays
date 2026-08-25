export type GameSocketStatus = 'connecting' | 'connected' | 'reconnecting' | 'failed'

type GameSocketOptions = {
  url: string
  onMessage: (message: Record<string, unknown>) => void
  onSocket: (socket: WebSocket | null) => void
  onStatus: (status: GameSocketStatus, detail?: string) => void
  onResync: () => void | Promise<unknown>
  createSocket?: (url: string) => WebSocket
  reconnectDelay?: (attempt: number) => number
}

export function openReconnectingGameSocket(options: GameSocketOptions): () => void {
  const createSocket = options.createSocket ?? ((url) => new WebSocket(url))
  const reconnectDelay = options.reconnectDelay ?? ((attempt) => Math.min(1_000 * 2 ** attempt, 10_000))
  let closed = false
  let attempt = 0
  let reconnectTimer: number | null = null
  let activeSocket: WebSocket | null = null

  const connect = () => {
    if (closed) return
    options.onStatus(attempt === 0 ? 'connecting' : 'reconnecting')
    const socket = createSocket(options.url)
    activeSocket = socket
    options.onSocket(socket)

    socket.onopen = () => {
      if (closed || socket !== activeSocket) return
      attempt = 0
      options.onStatus('connected')
      void Promise.resolve(options.onResync()).catch(() => {
        options.onStatus('reconnecting', 'Connected, but game state could not be refreshed. Retrying…')
        socket.close()
      })
    }
    socket.onmessage = (event) => {
      if (closed || socket !== activeSocket) return
      try {
        const message: unknown = JSON.parse(String(event.data))
        if (!message || typeof message !== 'object' || Array.isArray(message))
          throw new Error('WebSocket message must be an object')
        options.onMessage(message as Record<string, unknown>)
      } catch {
        options.onStatus('failed', 'The game sent an unreadable update. Reconnecting…')
        socket.close()
      }
    }
    socket.onerror = () => {
      if (!closed && socket === activeSocket)
        options.onStatus('reconnecting', 'Connection interrupted. Reconnecting…')
    }
    socket.onclose = (event) => {
      if (socket !== activeSocket) return
      activeSocket = null
      options.onSocket(null)
      if (closed) return
      if (event.code === 1008) {
        options.onStatus('failed', event.reason || 'Your game session expired. Refresh to sign in again.')
        return
      }
      const delay = reconnectDelay(attempt)
      attempt += 1
      options.onStatus('reconnecting', 'Connection interrupted. Reconnecting…')
      reconnectTimer = window.setTimeout(connect, delay)
    }
  }

  const reconnectWhenOnline = () => {
    if (closed || activeSocket) return
    if (reconnectTimer !== null) window.clearTimeout(reconnectTimer)
    reconnectTimer = null
    connect()
  }
  const reconnectWhenOffline = () => {
    if (closed || !activeSocket) return
    options.onStatus('reconnecting', 'Connection interrupted. Reconnecting…')
    activeSocket.close()
  }
  window.addEventListener('offline', reconnectWhenOffline)
  window.addEventListener('online', reconnectWhenOnline)
  connect()

  return () => {
    closed = true
    window.removeEventListener('offline', reconnectWhenOffline)
    window.removeEventListener('online', reconnectWhenOnline)
    if (reconnectTimer !== null) window.clearTimeout(reconnectTimer)
    reconnectTimer = null
    const socket = activeSocket
    activeSocket = null
    options.onSocket(null)
    socket?.close(1000, 'Page closed')
  }
}
