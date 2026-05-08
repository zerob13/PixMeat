import { create } from 'zustand'
import type { AppSettings } from '@/types/ui'

const defaults: AppSettings = {
  preferredBackend: 'auto',
  previewMaxSide: 1600,
  showFaceBoxes: true,
  cacheLimitGb: 2,
  privacyMode: false
}

type SettingsState = {
  settings: AppSettings
  setSettings: (settings: AppSettings) => void
  loadSettings: () => Promise<void>
  saveSettings: (settings: AppSettings) => Promise<void>
}

export const useSettingsStore = create<SettingsState>((set) => ({
  settings: defaults,
  setSettings: (settings) => set({ settings }),
  loadSettings: async () => {
    const settings = await window.beautyApp.getSettings()
    set({ settings })
  },
  saveSettings: async (settings) => {
    const saved = await window.beautyApp.saveSettings(settings)
    set({ settings: saved })
  }
}))
