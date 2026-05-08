import { describe, expect, it } from 'vitest'
import { useEditorStore } from './editorStore'

describe('editor store', () => {
  it('ignores stale preview results', () => {
    const store = useEditorStore.getState()
    store.setPreviewRendering(true, 'new')
    store.setProcessedPreview({
      request_token: 'old',
      image_id: 'img',
      preview_result_path: 'old.png',
      width: 1,
      height: 1,
      backend: 'cpu',
      elapsed_ms: 1
    })
    expect(useEditorStore.getState().processedPreviewPath).not.toBe('old.png')
  })
})
