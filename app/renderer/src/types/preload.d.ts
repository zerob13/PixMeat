import type {
  ApiResult,
  EngineEvent,
  EngineHealth,
  ExportRequest,
  ExportResult,
  LoadImageResult,
  RenderPreviewRequest,
  RenderPreviewResult
} from './engine'
import type { AppSettings } from './ui'

declare global {
  interface Window {
    beautyApp: {
      engineHealth: () => Promise<ApiResult<EngineHealth>>
      restartEngine: () => Promise<ApiResult<EngineHealth>>
      setBackend: (backend: string) => Promise<ApiResult<{ active_backend: string; fallback_backend: string }>>
      openImageDialog: () => Promise<ApiResult<{ path: string } | null>>
      exportImageDialog: (defaultName: string) => Promise<ApiResult<{ path: string } | null>>
      loadImage: (path: string, previewMaxSide: number) => Promise<ApiResult<LoadImageResult>>
      renderPreview: (payload: RenderPreviewRequest) => Promise<ApiResult<RenderPreviewResult>>
      exportImage: (payload: ExportRequest) => Promise<ApiResult<ExportResult>>
      cancelJob: (jobId: string) => Promise<ApiResult<{ job_id: string; cancel_requested: boolean }>>
      getSettings: () => Promise<AppSettings>
      saveSettings: (settings: AppSettings) => Promise<AppSettings>
      onEngineEvent: (cb: (event: EngineEvent) => void) => () => void
      onMenuAction: (cb: (action: 'open' | 'export' | 'fit' | 'actual') => void) => () => void
      toImageUrl: (path: string) => string
    }
  }
}

export {}
