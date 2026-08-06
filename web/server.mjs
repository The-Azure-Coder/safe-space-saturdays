import http from 'node:http'
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

const server = http.createServer(async (nodeRequest, nodeResponse) => {
  try {
    const protocol = nodeRequest.headers['x-forwarded-proto'] || 'http'
    const host = nodeRequest.headers.host || `localhost:${port}`
    const requestUrl = new URL(nodeRequest.url || '/', `${protocol}://${host}`)
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

server.listen(port, '0.0.0.0', () => {
  console.log(`Safe Space web listening on ${port}`)
})
