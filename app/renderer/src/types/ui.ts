export type CompareMode = 'before' | 'split' | 'after'

export type CanvasTransform = {
  scale: number
  offsetX: number
  offsetY: number
  fitScale: number
}

export type AppSettings = {
  preferredBackend: 'auto' | 'cpu' | 'cuda' | 'mps' | 'opencv_cuda'
  previewMaxSide: number
  showFaceBoxes: boolean
  cacheLimitGb: number
  privacyMode: boolean
}

export type Preset = {
  id: string
  name: string
  params: import('./params').EditParams
  builtIn: boolean
}
