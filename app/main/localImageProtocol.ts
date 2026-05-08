import { existsSync } from 'node:fs'
import { extname, resolve } from 'node:path'
import { pathToFileURL } from 'node:url'
import { ipcMain, net, protocol } from 'electron'

const imageExtensions = new Set(['.jpg', '.jpeg', '.png', '.webp', '.tif', '.tiff'])
const tokenToPath = new Map<string, string>()
const pathToToken = new Map<string, string>()
let tokenSeq = 0

export const registerLocalImageProtocolScheme = (): void => {
  protocol.registerSchemesAsPrivileged([
    {
      scheme: 'pixmeat',
      privileges: {
        standard: true,
        secure: true,
        supportFetchAPI: true
      }
    }
  ])
}

export const registerLocalImageProtocol = (): void => {
  protocol.handle('pixmeat', async (request) => {
    try {
      const url = new URL(request.url)
      if (url.hostname !== 'image') {
        return new Response('Not found', { status: 404 })
      }

      const token = decodeURIComponent(url.pathname.replace(/^\/+/, ''))
      const filePath = tokenToPath.get(token)
      if (!filePath) {
        return new Response('Image not registered', { status: 404 })
      }
      if (!imageExtensions.has(extname(filePath).toLowerCase()) || !existsSync(filePath)) {
        return new Response('Image not found', { status: 404 })
      }

      return net.fetch(pathToFileURL(filePath).toString())
    } catch {
      return new Response('Invalid image URL', { status: 400 })
    }
  })
}

export const registerLocalImageIpc = (): void => {
  ipcMain.on('image:register', (event, filePath: string) => {
    event.returnValue = registerImagePath(filePath)
  })
}

const registerImagePath = (filePath: string): string => {
  const normalizedPath = resolve(filePath)
  const existingToken = pathToToken.get(normalizedPath)
  if (existingToken) {
    return `pixmeat://image/${encodeURIComponent(existingToken)}`
  }

  const token = `img_${++tokenSeq}`
  pathToToken.set(normalizedPath, token)
  tokenToPath.set(token, normalizedPath)
  return `pixmeat://image/${encodeURIComponent(token)}`
}
