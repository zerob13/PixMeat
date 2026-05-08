import { BrowserWindow, Menu, app } from 'electron'

export const installMenu = (mainWindow: BrowserWindow): void => {
  const send = (action: 'open' | 'export' | 'fit' | 'actual'): void => {
    if (!mainWindow.isDestroyed()) {
      mainWindow.webContents.send(`menu:${action}`)
    }
  }

  const template: Electron.MenuItemConstructorOptions[] = [
    {
      label: app.name,
      submenu: [{ role: 'about' }, { type: 'separator' }, { role: 'quit' }]
    },
    {
      label: 'File',
      submenu: [
        { label: 'Open', accelerator: 'CmdOrCtrl+O', click: () => send('open') },
        { label: 'Export', accelerator: 'CmdOrCtrl+S', click: () => send('export') }
      ]
    },
    {
      label: 'View',
      submenu: [
        { label: 'Fit', accelerator: 'CmdOrCtrl+0', click: () => send('fit') },
        { label: '100%', accelerator: 'CmdOrCtrl+1', click: () => send('actual') },
        { type: 'separator' },
        { role: 'toggleDevTools' }
      ]
    }
  ]
  Menu.setApplicationMenu(Menu.buildFromTemplate(template))
}
