import { useCallback, useEffect, useMemo, useState } from 'react'
import { EditorLayout } from './components/EditorLayout'
import { ExportDialog } from './components/ExportDialog'
import { StatusBar } from './components/StatusBar'
import { useEditorStore } from './state/editorStore'
import { usePresetStore } from './state/presetStore'
import { useSettingsStore } from './state/settingsStore'
import type { ExportFormat } from './types/engine'
import { debounce } from './utils/debounce'
import { toEngineParams } from './utils/valueMapping'

export const App = (): JSX.Element => {
  const [exportOpen, setExportOpen] = useState(false)
  const [currentExportJobId, setCurrentExportJobId] = useState<string | null>(null)
  const [viewCommand, setViewCommand] = useState<'fit' | 'actual' | null>(null)
  const editor = useEditorStore()
  const presets = usePresetStore()
  const settings = useSettingsStore()

  const loadHealth = useCallback(async () => {
    const health = await window.beautyApp.engineHealth()
    if (health.ok) {
      editor.setHealth(health.result)
    } else {
      editor.setError(health.error.message)
    }
  }, [editor])

  useEffect(() => {
    void settings.loadSettings()
    presets.load()
    void loadHealth()
    const unsubscribe = window.beautyApp.onEngineEvent(editor.handleEngineEvent)
    return unsubscribe
  }, [])

  const renderPreview = useCallback(
    async (quality: 'fast' | 'standard' = 'standard') => {
      if (!editor.session) return
      const token = `preview_${Date.now()}`
      editor.setPreviewRendering(true, token)
      const response = await window.beautyApp.renderPreview({
        image_id: editor.session.image_id,
        request_token: token,
        active_face_id: editor.activeFaceId,
        quality,
        params: toEngineParams(editor.params)
      })
      if (response.ok) {
        editor.setProcessedPreview(response.result)
      } else if (response.error.code !== 'stale_preview') {
        editor.setError(response.error.message)
      }
    },
    [editor.session, editor.activeFaceId, editor.params]
  )

  const debouncedPreview = useMemo(() => debounce(() => void renderPreview('fast'), 260), [renderPreview])

  useEffect(() => {
    if (!editor.session) return
    debouncedPreview()
    return () => debouncedPreview.cancel()
  }, [editor.params, editor.activeFaceId])

  const openImage = useCallback(async () => {
    const selected = await window.beautyApp.openImageDialog()
    if (!selected.ok || !selected.result) return
    const loaded = await window.beautyApp.loadImage(selected.result.path, settings.settings.previewMaxSide)
    if (loaded.ok) {
      editor.setSession(loaded.result)
    } else {
      editor.setError(loaded.error.message)
    }
  }, [editor, settings.settings.previewMaxSide])

  useEffect(() => {
    const unsubscribe = window.beautyApp.onMenuAction((action) => {
      if (action === 'open') {
        void openImage()
      } else if (action === 'export') {
        setExportOpen(true)
      } else if (action === 'fit' || action === 'actual') {
        setViewCommand(null)
        window.requestAnimationFrame(() => setViewCommand(action))
      }
    })
    return unsubscribe
  }, [openImage])

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent): void => {
      const mod = event.metaKey || event.ctrlKey
      if (mod && event.key.toLowerCase() === 'o') {
        event.preventDefault()
        void openImage()
      }
      if (mod && event.key.toLowerCase() === 's') {
        event.preventDefault()
        setExportOpen(true)
      }
      if (mod && event.key.toLowerCase() === 'r') {
        editor.resetAll()
      }
      if (!mod && event.key.toLowerCase() === 'b') {
        editor.setCompareMode(editor.compareMode === 'before' ? 'after' : 'before')
      }
      if (!mod && event.key.toLowerCase() === 's') {
        editor.setCompareMode('split')
      }
      if (!mod && event.key.toLowerCase() === 'f') {
        editor.setShowFaceBoxes(!editor.showFaceBoxes)
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [editor, openImage])

  const startExport = async (options: {
    fileName: string
    format: ExportFormat
    quality: number
    keepMetadata: boolean
  }): Promise<void> => {
    if (!editor.session) return
    const defaultName = withExtension(options.fileName, options.format)
    const selected = await window.beautyApp.exportImageDialog(defaultName)
    if (!selected.ok || !selected.result) return
    const jobId = `job_${Date.now()}`
    setCurrentExportJobId(jobId)
    editor.setExportRunning(true)
    const response = await window.beautyApp.exportImage({
      image_id: editor.session.image_id,
      job_id: jobId,
      active_face_id: editor.activeFaceId,
      output_path: selected.result.path,
      format: options.format,
      quality: options.quality,
      keep_metadata: options.keepMetadata,
      params: toEngineParams(editor.params)
    })
    if (response.ok) {
      editor.setExportResult(response.result)
      setCurrentExportJobId(null)
      setExportOpen(false)
    } else {
      setCurrentExportJobId(null)
      editor.setError(response.error.message)
    }
  }

  const imageSize = editor.session
    ? { width: editor.session.preview_width, height: editor.session.preview_height }
    : { width: 1, height: 1 }

  return (
    <>
      <div className="grid h-full grid-rows-[1fr_32px]">
        <EditorLayout
          activeFaceId={editor.activeFaceId}
          afterPath={editor.processedPreviewPath}
          beforePath={editor.originalPreviewPath}
          compareMode={editor.compareMode}
          faces={editor.session?.faces ?? []}
          imageSize={imageSize}
          params={editor.params}
          presets={presets.presets}
          previewRendering={editor.previewRendering}
          settings={settings.settings}
          showFaceBoxes={editor.showFaceBoxes}
          viewCommand={viewCommand}
          onApplyPreset={editor.setParams}
          onExport={() => setExportOpen(true)}
          onOpen={openImage}
          onParamChange={editor.updateParam}
          onResetAll={editor.resetAll}
          onResetGroup={editor.resetGroup}
          onSavePreset={() => presets.saveCurrent(editor.params)}
          onSaveSettings={(next) => {
            void settings.saveSettings(next)
            void window.beautyApp.setBackend(next.preferredBackend).then(() => loadHealth())
          }}
          onSetActiveFace={editor.setActiveFace}
          onSetCompareMode={editor.setCompareMode}
          onSetShowFaceBoxes={editor.setShowFaceBoxes}
        />
        <StatusBar
          error={editor.error}
          health={editor.health}
          previewRendering={editor.previewRendering}
          session={editor.session}
        />
      </div>
      <ExportDialog
        open={exportOpen}
        progress={editor.exportProgress}
        running={editor.exportRunning}
        stage={editor.exportStage}
      onCancel={() => {
          if (currentExportJobId) void window.beautyApp.cancelJob(currentExportJobId)
          setCurrentExportJobId(null)
          editor.setExportRunning(false)
        }}
        onExport={(options) => void startExport(options)}
        onOpenChange={setExportOpen}
      />
    </>
  )
}

const withExtension = (name: string, format: ExportFormat): string => {
  const extension = format === 'jpeg' ? 'jpg' : format === 'tiff' ? 'tif' : 'png'
  return name.replace(/\.[^.]+$/, '') + `.${extension}`
}
