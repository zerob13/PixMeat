import { existsSync } from 'node:fs'
import { join } from 'node:path'
import { app, BrowserWindow, shell } from 'electron'

export const createMainWindow = (): BrowserWindow => {
  const mainWindow = new BrowserWindow({
    width: 1280,
    height: 820,
    minWidth: 1100,
    minHeight: 700,
    title: 'PixMeat',
    titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
    backgroundColor: '#111318',
    webPreferences: {
      preload: resolvePreloadPath(),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true
    }
  })

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    void shell.openExternal(url)
    return { action: 'deny' }
  })

  if (process.env.ELECTRON_RENDERER_URL) {
    void mainWindow.loadURL(process.env.ELECTRON_RENDERER_URL)
  } else {
    void mainWindow.loadFile(join(__dirname, '../renderer/index.html'))
  }

  if (!app.isPackaged && !process.env.CI && !process.env.PIXMEAT_DISABLE_DEVTOOLS) {
    mainWindow.webContents.once('did-finish-load', () => {
      mainWindow.webContents.openDevTools({ mode: 'detach' })
    })
  }

  return mainWindow
}

const resolvePreloadPath = (): string => {
  const candidates = [
    join(__dirname, '../preload/preload.cjs'),
    join(__dirname, '../preload/preload.js'),
    join(__dirname, '../preload/preload.mjs')
  ]
  const found = candidates.find((candidate) => existsSync(candidate))
  return found ?? candidates[0]
}
