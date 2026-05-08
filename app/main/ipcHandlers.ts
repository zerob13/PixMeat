import { ipcMain, type BrowserWindow } from 'electron'
import { EngineRpc } from './engineRpc'
import { exportImageDialog, openImageDialog } from './fileDialogs'
import { readSettings, writeSettings, type AppSettings } from './settingsStore'
import type { ApiResult, RpcResponse } from './types'

const toApiResult = <T>(response: RpcResponse<T>): ApiResult<T> =>
  response.ok ? { ok: true, result: response.result } : { ok: false, error: response.error }

export const registerIpcHandlers = (mainWindow: BrowserWindow, engine: EngineRpc): void => {
  ipcMain.handle('engine:health', async () => toApiResult(await engine.request('health', {}, 10_000)))
  ipcMain.handle('engine:restart', async () => toApiResult(await engine.restart()))
  ipcMain.handle('engine:setBackend', async (_, backend: string) =>
    toApiResult(await engine.request('set_backend', { backend }, 10_000))
  )

  ipcMain.handle('file:openImageDialog', async () => ({
    ok: true,
    result: await openImageDialog(mainWindow)
  }))

  ipcMain.handle('file:exportImageDialog', async (_, defaultName: string) => ({
    ok: true,
    result: await exportImageDialog(mainWindow, defaultName)
  }))

  ipcMain.handle('engine:loadImage', async (_, imagePath: string, previewMaxSide: number) =>
    toApiResult(
      await engine.request(
        'load_image',
        { image_path: imagePath, preview_max_side: previewMaxSide, detect_faces: true },
        120_000
      )
    )
  )

  ipcMain.handle('engine:renderPreview', async (_, payload: object) =>
    toApiResult(await engine.request('render_preview', payload, 120_000))
  )

  ipcMain.handle('engine:exportImage', async (_, payload: object) =>
    toApiResult(await engine.request('export_image', payload, 300_000))
  )

  ipcMain.handle('engine:cancelJob', async (_, jobId: string) =>
    toApiResult(await engine.request('cancel_job', { job_id: jobId }, 10_000))
  )

  ipcMain.handle('settings:get', () => readSettings())
  ipcMain.handle('settings:save', (_, settings: AppSettings) => writeSettings(settings))

  engine.on('event', (event) => {
    mainWindow.webContents.send('engine:event', {
      type: event.event,
      payload: event.payload
    })
  })
}
