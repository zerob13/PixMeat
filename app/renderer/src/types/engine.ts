import type { EditParams } from './params'

export type EngineDevice = {
  type: string
  name: string
  available: boolean
}

export type EngineHealth = {
  status: 'starting' | 'ready' | 'error'
  version: string
  platform: string
  python_version: string
  available_backends: string[]
  active_backend: string
  devices: EngineDevice[]
}

export type FaceBox = {
  face_id: string
  bbox: [number, number, number, number]
  confidence: number
  landmark_count: number
}

export type LoadImageResult = {
  image_id: string
  source_path: string
  preview_path: string
  width: number
  height: number
  preview_width: number
  preview_height: number
  faces: FaceBox[]
  active_face_id: string | null
}

export type PreviewQuality = 'fast' | 'standard'

export type RenderPreviewRequest = {
  image_id: string
  request_token: string
  active_face_id: string | null
  quality: PreviewQuality
  params: EditParams
}

export type RenderPreviewResult = {
  request_token: string
  image_id: string
  preview_result_path: string
  width: number
  height: number
  backend: string
  elapsed_ms: number
}

export type ExportFormat = 'jpeg' | 'png' | 'tiff'

export type ExportRequest = {
  image_id: string
  job_id: string
  active_face_id: string | null
  output_path: string
  format: ExportFormat
  quality: number
  keep_metadata: boolean
  params: EditParams
}

export type ExportResult = {
  job_id: string
  output_path: string
  backend: string
  elapsed_ms: number
}

export type EngineEvent =
  | {
      type: 'engine_ready'
      payload: EngineHealth
    }
  | {
      type: 'engine_error'
      payload: { code: string; message: string }
    }
  | {
      type: 'backend_changed'
      payload: { active_backend: string }
    }
  | {
      type: 'job_progress'
      payload: { job_id: string; progress: number; stage: string }
    }
  | {
      type: 'job_cancelled'
      payload: { job_id: string }
    }
  | {
      type: 'job_completed'
      payload: { job_id: string; output_path: string }
    }

export type EngineError = {
  code: string
  message: string
  details?: unknown
}

export type ApiResult<T> =
  | {
      ok: true
      result: T
    }
  | {
      ok: false
      error: EngineError
    }
