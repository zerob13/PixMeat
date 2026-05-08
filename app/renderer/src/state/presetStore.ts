import { create } from 'zustand'
import type { EditParams } from '@/types/params'
import { defaultParams } from '@/types/params'
import type { Preset } from '@/types/ui'

const builtInPresets: Preset[] = [
  {
    id: 'preset_natural',
    name: 'Natural',
    builtIn: true,
    params: {
      liquify: { faceSlim: 8, jawline: 5, chinLength: 0, eyeEnlarge: 6, noseSlim: 0, smile: 4 },
      skin: { skinSmooth: 25, textureKeep: 75, blemishSoften: 10, skinToneEven: 12 },
      beauty: { brightness: 5, eyeBright: 8, teethWhite: 0, softContrast: 4 }
    }
  },
  {
    id: 'preset_clean',
    name: 'Clean Portrait',
    builtIn: true,
    params: {
      liquify: { faceSlim: 14, jawline: 10, chinLength: 0, eyeEnlarge: 10, noseSlim: 8, smile: 6 },
      skin: { skinSmooth: 38, textureKeep: 72, blemishSoften: 22, skinToneEven: 22 },
      beauty: { brightness: 6, eyeBright: 12, teethWhite: 10, softContrast: 6 }
    }
  },
  {
    id: 'preset_soft',
    name: 'Soft Beauty',
    builtIn: true,
    params: {
      liquify: { faceSlim: 20, jawline: 12, chinLength: -2, eyeEnlarge: 16, noseSlim: 12, smile: 8 },
      skin: { skinSmooth: 52, textureKeep: 62, blemishSoften: 28, skinToneEven: 34 },
      beauty: { brightness: 9, eyeBright: 18, teethWhite: 14, softContrast: 2 }
    }
  }
]

type PresetState = {
  presets: Preset[]
  load: () => void
  saveCurrent: (params: EditParams) => Preset
  deletePreset: (id: string) => void
}

const storageKey = 'pixmeat.presets'

export const usePresetStore = create<PresetState>((set, get) => ({
  presets: builtInPresets,
  load: () => {
    const raw = window.localStorage.getItem(storageKey)
    const userPresets = raw ? (JSON.parse(raw) as Preset[]) : []
    set({ presets: [...builtInPresets, ...userPresets] })
  },
  saveCurrent: (params) => {
    const userPreset: Preset = {
      id: `user_${Date.now()}`,
      name: `Preset ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`,
      params,
      builtIn: false
    }
    const userPresets = [...get().presets.filter((preset) => !preset.builtIn), userPreset]
    window.localStorage.setItem(storageKey, JSON.stringify(userPresets))
    set({ presets: [...builtInPresets, ...userPresets] })
    return userPreset
  },
  deletePreset: (id) => {
    const userPresets = get().presets.filter((preset) => !preset.builtIn && preset.id !== id)
    window.localStorage.setItem(storageKey, JSON.stringify(userPresets))
    set({ presets: [...builtInPresets, ...userPresets] })
  }
}))

export const resetPreset: Preset = {
  id: 'reset',
  name: 'Reset',
  builtIn: true,
  params: defaultParams
}
