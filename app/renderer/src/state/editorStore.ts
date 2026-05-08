import { create } from 'zustand'
import type {
  EngineEvent,
  EngineHealth,
  ExportResult,
  LoadImageResult,
  RenderPreviewResult
} from '@/types/engine'
import type { EditParams, ParamGroup } from '@/types/params'
import { defaultParams } from '@/types/params'
import type { CompareMode } from '@/types/ui'
import { clampUiParams } from '@/utils/valueMapping'

type EditorState = {
  health: EngineHealth | null
  session: LoadImageResult | null
  originalPreviewPath: string | null
  processedPreviewPath: string | null
  activeFaceId: string | null
  params: EditParams
  compareMode: CompareMode
  showFaceBoxes: boolean
  previewRendering: boolean
  exportRunning: boolean
  exportProgress: number
  exportStage: string
  latestPreviewToken: string | null
  error: string | null
  setHealth: (health: EngineHealth | null) => void
  setSession: (session: LoadImageResult) => void
  setProcessedPreview: (result: RenderPreviewResult) => void
  updateParam: <G extends ParamGroup>(group: G, key: keyof EditParams[G], value: number) => void
  setParams: (params: EditParams) => void
  resetGroup: (group: ParamGroup) => void
  resetAll: () => void
  setCompareMode: (mode: CompareMode) => void
  setActiveFace: (faceId: string | null) => void
  setShowFaceBoxes: (value: boolean) => void
  setPreviewRendering: (value: boolean, token?: string | null) => void
  setError: (message: string | null) => void
  handleEngineEvent: (event: EngineEvent) => void
  setExportRunning: (value: boolean) => void
  setExportResult: (result: ExportResult) => void
}

export const useEditorStore = create<EditorState>((set, get) => ({
  health: null,
  session: null,
  originalPreviewPath: null,
  processedPreviewPath: null,
  activeFaceId: null,
  params: defaultParams,
  compareMode: 'after',
  showFaceBoxes: true,
  previewRendering: false,
  exportRunning: false,
  exportProgress: 0,
  exportStage: '',
  latestPreviewToken: null,
  error: null,
  setHealth: (health) => set({ health }),
  setSession: (session) =>
    set({
      session,
      originalPreviewPath: session.preview_path,
      processedPreviewPath: session.preview_path,
      activeFaceId: session.active_face_id,
      compareMode: 'after',
      error: null
    }),
  setProcessedPreview: (result) => {
    if (get().latestPreviewToken && result.request_token !== get().latestPreviewToken) {
      return
    }
    set({ processedPreviewPath: result.preview_result_path, previewRendering: false, error: null })
  },
  updateParam: (group, key, value) =>
    set((state) => ({
      params: clampUiParams({
        ...state.params,
        [group]: { ...state.params[group], [key]: value }
      })
    })),
  setParams: (params) => set({ params: clampUiParams(params) }),
  resetGroup: (group) =>
    set((state) => ({
      params: {
        ...state.params,
        [group]: defaultParams[group]
      }
    })),
  resetAll: () => set({ params: defaultParams }),
  setCompareMode: (compareMode) => set({ compareMode }),
  setActiveFace: (activeFaceId) => set({ activeFaceId }),
  setShowFaceBoxes: (showFaceBoxes) => set({ showFaceBoxes }),
  setPreviewRendering: (previewRendering, token = null) =>
    set({ previewRendering, latestPreviewToken: token ?? get().latestPreviewToken }),
  setError: (message) => set({ error: message, previewRendering: false, exportRunning: false }),
  handleEngineEvent: (event) => {
    if (event.type === 'job_progress') {
      set({ exportProgress: event.payload.progress, exportStage: event.payload.stage })
    } else if (event.type === 'engine_error') {
      set({ error: event.payload.message })
    } else if (event.type === 'job_completed') {
      set({ exportRunning: false, exportProgress: 1, exportStage: 'done' })
    } else if (event.type === 'engine_ready') {
      set({ health: event.payload })
    }
  },
  setExportRunning: (exportRunning) => set({ exportRunning, exportProgress: 0, exportStage: '' }),
  setExportResult: () => set({ exportRunning: false, exportProgress: 1, exportStage: 'done' })
}))
