import { app } from 'electron'
import { EngineRpc } from './engineRpc'
import { registerIpcHandlers } from './ipcHandlers'
import {
  registerLocalImageIpc,
  registerLocalImageProtocol,
  registerLocalImageProtocolScheme
} from './localImageProtocol'
import { installMenu } from './menu'
import { createMainWindow } from './windows'

const engine = new EngineRpc()

app.setName('PixMeat')
registerLocalImageProtocolScheme()

app.whenReady().then(() => {
  registerLocalImageProtocol()
  registerLocalImageIpc()
  const mainWindow = createMainWindow()
  installMenu(mainWindow)
  registerIpcHandlers(mainWindow, engine)
  engine.start()

  app.on('activate', () => {
    if (mainWindow.isDestroyed()) {
      const window = createMainWindow()
      installMenu(window)
      registerIpcHandlers(window, engine)
    }
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('before-quit', () => {
  engine.stop()
})
