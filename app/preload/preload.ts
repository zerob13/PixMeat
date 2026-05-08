import { contextBridge, ipcRenderer } from 'electron'

const toImageUrl = (path: string): string => {
  return ipcRenderer.sendSync('image:register', path) as string
}

contextBridge.exposeInMainWorld('beautyApp', {
  engineHealth: () => ipcRenderer.invoke('engine:health'),
  restartEngine: () => ipcRenderer.invoke('engine:restart'),
  setBackend: (backend: string) => ipcRenderer.invoke('engine:setBackend', backend),
  openImageDialog: () => ipcRenderer.invoke('file:openImageDialog'),
  exportImageDialog: (defaultName: string) => ipcRenderer.invoke('file:exportImageDialog', defaultName),
  loadImage: (path: string, previewMaxSide: number) =>
    ipcRenderer.invoke('engine:loadImage', path, previewMaxSide),
  renderPreview: (payload: object) => ipcRenderer.invoke('engine:renderPreview', payload),
  exportImage: (payload: object) => ipcRenderer.invoke('engine:exportImage', payload),
  cancelJob: (jobId: string) => ipcRenderer.invoke('engine:cancelJob', jobId),
  getSettings: () => ipcRenderer.invoke('settings:get'),
  saveSettings: (settings: object) => ipcRenderer.invoke('settings:save', settings),
  onEngineEvent: (cb: (event: unknown) => void) => {
    const listener = (_: Electron.IpcRendererEvent, event: unknown): void => cb(event)
    ipcRenderer.on('engine:event', listener)
    return () => ipcRenderer.removeListener('engine:event', listener)
  },
  onMenuAction: (cb: (action: string) => void) => {
    const channels = ['menu:open', 'menu:export', 'menu:fit', 'menu:actual'] as const
    const listeners = channels.map((channel) => {
      const listener = (): void => cb(channel.replace('menu:', ''))
      ipcRenderer.on(channel, listener)
      return { channel, listener }
    })
    return () => {
      for (const { channel, listener } of listeners) {
        ipcRenderer.removeListener(channel, listener)
      }
    }
  },
  toImageUrl
})
