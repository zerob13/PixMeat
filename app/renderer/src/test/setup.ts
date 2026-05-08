import '@testing-library/jest-dom/vitest'

Object.defineProperty(window, 'beautyApp', {
  value: {
    toImageUrl: () => 'pixmeat://image/test-token',
    getSettings: async () => ({
      preferredBackend: 'auto',
      previewMaxSide: 1600,
      showFaceBoxes: true,
      cacheLimitGb: 2,
      privacyMode: false
    }),
    saveSettings: async (settings: unknown) => settings,
    engineHealth: async () => ({ ok: true, result: null }),
    onEngineEvent: () => () => {}
  },
  writable: true
})
