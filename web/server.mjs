import http from 'node:http'
import https from 'node:https'
import { readFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { brotliCompress, gzip } from 'node:zlib'
import { promisify } from 'node:util'

import handler from './dist/server/server.js'

const port = Number(process.env.PORT || 10000)
const clientDirectory = path.resolve(path.dirname(fileURLToPath(import.meta.url)), 'dist/client')
const compressBrotli = promisify(brotliCompress)
const compressGzip = promisify(gzip)
const contentTypes = new Map([
  ['.css', 'text/css; charset=utf-8'],
  ['.js', 'text/javascript; charset=utf-8'],
  ['.jpeg', 'image/jpeg'],
  ['.jpg', 'image/jpeg'],
  ['.png', 'image/png'],
  ['.svg', 'image/svg+xml'],
  ['.avif', 'image/avif'],
  ['.webp', 'image/webp'],
])

const hashedAssetPattern = /[-.][a-f0-9]{8,}(?:\.|$)/i

function isCompressible(contentType) {
  return /^(text\/|application\/(?:javascript|json|wasm)|image\/svg\+xml)/.test(contentType)
}

async function sendBody(nodeResponse, body, contentType, requestHeaders, cacheControl) {
  const acceptEncoding = requestHeaders['accept-encoding'] || ''
  let output = body
  let contentEncoding = ''
  if (isCompressible(contentType) && /br/.test(acceptEncoding)) {
    output = await compressBrotli(body)
    contentEncoding = 'br'
  } else if (isCompressible(contentType) && /gzip/.test(acceptEncoding)) {
    output = await compressGzip(body)
    contentEncoding = 'gzip'
  }
  nodeResponse.setHeader('content-type', contentType)
  nodeResponse.setHeader('cache-control', cacheControl)
  if (contentEncoding) {
    nodeResponse.setHeader('content-encoding', contentEncoding)
    nodeResponse.setHeader('vary', 'Accept-Encoding')
  }
  nodeResponse.setHeader('content-length', output.byteLength)
  nodeResponse.end(output)
}

function apiTarget() {
  const configured = process.env.API_PROXY_URL || process.env.VITE_API_URL
  if (!configured) throw new Error('API_PROXY_URL or VITE_API_URL is required')
  return new URL(configured)
}

function proxyHeaders(headers, target) {
  return {
    ...headers,
    host: target.host,
    'x-forwarded-host': headers.host || '',
    'x-forwarded-proto': headers['x-forwarded-proto'] || 'https',
  }
}

function proxyHttp(nodeRequest, nodeResponse, requestUrl) {
  const target = apiTarget()
  const transport = target.protocol === 'https:' ? https : http
  const upstream = transport.request(
    {
      protocol: target.protocol,
      hostname: target.hostname,
      port: target.port || undefined,
      method: nodeRequest.method,
      path: `${requestUrl.pathname}${requestUrl.search}`,
      headers: proxyHeaders(nodeRequest.headers, target),
    },
    (upstreamResponse) => {
      nodeResponse.writeHead(upstreamResponse.statusCode || 502, upstreamResponse.headers)
      upstreamResponse.pipe(nodeResponse)
    },
  )
  upstream.on('error', (error) => {
    console.error('API proxy request failed', error)
    if (!nodeResponse.headersSent) nodeResponse.writeHead(502, { 'content-type': 'application/json' })
    nodeResponse.end(JSON.stringify({ detail: 'The API is temporarily unavailable' }))
  })
  nodeRequest.pipe(upstream)
}

let readinessState = 'idle'
let readinessProbe = null
let readinessReadyAt = 0
const READINESS_CACHE_MS = 30_000

function startReadinessProbe() {
  if (
    readinessProbe ||
    (readinessState === 'ready' && Date.now() - readinessReadyAt < READINESS_CACHE_MS)
  )
    return
  readinessState = 'warming'
  readinessProbe = (async () => {
    const target = apiTarget()
    target.pathname = '/health/ready'
    target.search = ''
    const deadline = Date.now() + 90_000
    let attempt = 0

    while (Date.now() < deadline) {
      attempt += 1
      try {
        const response = await fetch(target, {
          headers: { accept: 'application/json' },
          cache: 'no-store',
        })
        const body = await response.json().catch(() => null)
        if (response.ok && body?.status === 'ready') {
          readinessState = 'ready'
          readinessReadyAt = Date.now()
          console.log(`API readiness background probe succeeded on attempt ${attempt}`)
          return
        }
        console.warn(`API readiness background probe attempt ${attempt} returned ${response.status}`)
      } catch (error) {
        console.warn(`API readiness background probe attempt ${attempt} failed`, error)
      }
      await new Promise((resolve) => setTimeout(resolve, 1_000))
    }

    readinessState = 'idle'
    console.warn(`API readiness background probe timed out after ${attempt} attempts`)
  })().finally(() => {
    readinessProbe = null
  })
}

async function proxyReadiness(nodeResponse) {
  startReadinessProbe()
  nodeResponse.statusCode = readinessState === 'ready' ? 200 : 202
  nodeResponse.setHeader('cache-control', 'no-store')
  nodeResponse.setHeader('content-type', 'application/json')
  nodeResponse.end(JSON.stringify({ status: readinessState, service: 'api' }))
}

const server = http.createServer(async (nodeRequest, nodeResponse) => {
  try {
    const protocol = nodeRequest.headers['x-forwarded-proto'] || 'http'
    const host = nodeRequest.headers.host || `localhost:${port}`
    const requestUrl = new URL(nodeRequest.url || '/', `${protocol}://${host}`)
    if (
      requestUrl.pathname === '/api/system/ready' ||
      requestUrl.pathname === '/health/ready'
    ) {
      await proxyReadiness(nodeResponse)
      return
    }
    if (
      requestUrl.pathname.startsWith('/api/') ||
      requestUrl.pathname.startsWith('/uploads/') ||
      requestUrl.pathname === '/health/ready'
    ) {
      proxyHttp(nodeRequest, nodeResponse, requestUrl)
      return
    }
    if (requestUrl.pathname.startsWith('/assets/')) {
      const assetPath = path.resolve(clientDirectory, `.${requestUrl.pathname}`)
      if (!assetPath.startsWith(`${clientDirectory}${path.sep}`)) {
        nodeResponse.statusCode = 403
        nodeResponse.end('Forbidden')
        return
      }
      try {
        const asset = await readFile(assetPath)
        nodeResponse.statusCode = 200
        const contentType = contentTypes.get(path.extname(assetPath)) || 'application/octet-stream'
        const cacheControl = hashedAssetPattern.test(path.basename(assetPath))
          ? 'public, max-age=31536000, immutable'
          : 'public, max-age=604800, stale-while-revalidate=86400'
        await sendBody(nodeResponse, asset, contentType, nodeRequest.headers, cacheControl)
      } catch {
        nodeResponse.statusCode = 404
        nodeResponse.end('Not Found')
      }
      return
    }
    const hasBody = !['GET', 'HEAD'].includes(nodeRequest.method || 'GET')
    const request = new Request(requestUrl, {
      method: nodeRequest.method,
      headers: nodeRequest.headers,
      body: hasBody ? nodeRequest : undefined,
      duplex: hasBody ? 'half' : undefined,
    })
    const response = await handler.fetch(request)
    const body = Buffer.from(await response.arrayBuffer())
    nodeResponse.statusCode = response.status
    const contentType = response.headers.get('content-type') || 'text/html; charset=utf-8'
    response.headers.forEach((value, key) => {
      if (!['content-length', 'content-encoding', 'content-type'].includes(key))
        nodeResponse.setHeader(key, value)
    })
    await sendBody(nodeResponse, body, contentType, nodeRequest.headers, 'no-cache')
  } catch (error) {
    console.error('SSR request failed', error)
    nodeResponse.statusCode = 500
    nodeResponse.setHeader('content-type', 'text/plain; charset=utf-8')
    nodeResponse.end('Internal Server Error')
  }
})

server.on('upgrade', (nodeRequest, clientSocket, head) => {
  try {
    const requestUrl = new URL(nodeRequest.url || '/', 'http://localhost')
    if (!requestUrl.pathname.startsWith('/api/')) {
      clientSocket.destroy()
      return
    }
    const target = apiTarget()
    const transport = target.protocol === 'https:' ? https : http
    const upstreamRequest = transport.request({
      protocol: target.protocol,
      hostname: target.hostname,
      port: target.port || undefined,
      method: 'GET',
      path: `${requestUrl.pathname}${requestUrl.search}`,
      headers: proxyHeaders(nodeRequest.headers, target),
    })
    upstreamRequest.on('upgrade', (upstreamResponse, upstreamSocket, upstreamHead) => {
      const statusLine = `HTTP/1.1 ${upstreamResponse.statusCode || 101} ${upstreamResponse.statusMessage || 'Switching Protocols'}\r\n`
      const responseHeaders = []
      for (let index = 0; index < upstreamResponse.rawHeaders.length; index += 2) {
        responseHeaders.push(`${upstreamResponse.rawHeaders[index]}: ${upstreamResponse.rawHeaders[index + 1]}`)
      }
      clientSocket.write(`${statusLine}${responseHeaders.join('\r\n')}\r\n\r\n`)
      if (upstreamHead.length) clientSocket.write(upstreamHead)
      if (head.length) upstreamSocket.write(head)
      upstreamSocket.pipe(clientSocket).pipe(upstreamSocket)
    })
    upstreamRequest.on('response', (upstreamResponse) => {
      clientSocket.write(`HTTP/1.1 ${upstreamResponse.statusCode || 502} Bad Gateway\r\n\r\n`)
      clientSocket.destroy()
    })
    upstreamRequest.on('error', (error) => {
      console.error('WebSocket proxy failed', error)
      clientSocket.destroy()
    })
    upstreamRequest.end()
  } catch (error) {
    console.error('WebSocket upgrade failed', error)
    clientSocket.destroy()
  }
})

server.listen(port, '0.0.0.0', () => {
  console.log(`Safe Space web listening on ${port}`)
  void warmApi()
})

async function warmApi() {
  const configuredApiUrl = process.env.API_PROXY_URL || process.env.VITE_API_URL
  if (!configuredApiUrl) {
    console.log('API warm-up skipped: no API URL configured')
    return
  }

  let healthUrl
  try {
    healthUrl = new URL('/health/ready', configuredApiUrl).toString()
  } catch {
    console.warn('API warm-up skipped: invalid API URL')
    return
  }

  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 10_000)
  try {
    const response = await fetch(healthUrl, {
      method: 'GET',
      headers: { accept: 'application/json' },
      cache: 'no-store',
      signal: controller.signal,
    })
    console.log(`API warm-up completed with status ${response.status}`)
  } catch (error) {
    const message = error instanceof Error && error.name === 'AbortError' ? 'timed out' : 'unavailable'
    console.warn(`API warm-up ${message}; the next request will retry normally`)
  } finally {
    clearTimeout(timeout)
  }
}
