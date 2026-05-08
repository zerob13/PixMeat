import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { app } from 'electron'

export type AppSettings = {
  preferredBackend: 'auto' | 'cpu' | 'cuda' | 'mps' | 'opencv_cuda'
  previewMaxSide: number
  showFaceBoxes: boolean
  cacheLimitGb: number
  privacyMode: boolean
}

const defaults: AppSettings = {
  preferredBackend: 'auto',
  previewMaxSide: 1600,
  showFaceBoxes: true,
  cacheLimitGb: 2,
  privacyMode: false
}

const settingsPath = (): string => join(app.getPath('userData'), 'settings.json')

export const readSettings = (): AppSettings => {
  try {
    const data = JSON.parse(readFileSync(settingsPath(), 'utf8')) as Partial<AppSettings>
    return { ...defaults, ...data }
  } catch {
    return defaults
  }
}

export const writeSettings = (settings: AppSettings): AppSettings => {
  const next = { ...defaults, ...settings }
  const path = settingsPath()
  mkdirSync(dirname(path), { recursive: true })
  writeFileSync(path, JSON.stringify(next, null, 2), 'utf8')
  return next
}
