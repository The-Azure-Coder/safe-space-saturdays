import http from 'node:http'
import https from 'node:https'
import { readFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import handler from './dist/server/server.js'

const port = Number(process.env.PORT || 10000)
const clientDirectory = path.resolve(path.dirname(fileURLToPath(import.meta.url)), 'dist/client')
const contentTypes = new Map([
  ['.css', 'text/css; charset=utf-8'],
  ['.js', 'text/javascript; charset=utf-8'],
  ['.jpeg', 'image/jpeg'],
  ['.jpg', 'image/jpeg'],
  ['.png', 'image/png'],
  ['.svg', 'image/svg+xml'],
  ['.webp', 'image/webp'],
])

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

const server = http.createServer(async (nodeRequest, nodeResponse) => {
  try {
    const protocol = nodeRequest.headers['x-forwarded-proto'] || 'http'
    const host = nodeRequest.headers.host || `localhost:${port}`
    const requestUrl = new URL(nodeRequest.url || '/', `${protocol}://${host}`)
    if (requestUrl.pathname.startsWith('/api/') || requestUrl.pathname.startsWith('/uploads/')) {
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
        nodeResponse.setHeader('content-type', contentTypes.get(path.extname(assetPath)) || 'application/octet-stream')
        nodeResponse.setHeader('cache-control', 'public, max-age=31536000, immutable')
        nodeResponse.end(asset)
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
    nodeResponse.statusCode = response.status
    response.headers.forEach((value, key) => nodeResponse.setHeader(key, value))
    nodeResponse.end(Buffer.from(await response.arrayBuffer()))
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
})
