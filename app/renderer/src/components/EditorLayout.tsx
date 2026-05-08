import { Download, Eye, FolderOpen, Maximize, RotateCcw, ScanFace } from 'lucide-react'
import type { FaceBox } from '@/types/engine'
import type { EditParams, ParamGroup } from '@/types/params'
import type { AppSettings, CompareMode } from '@/types/ui'
import { CanvasViewer } from './CanvasViewer'
import { PresetMenu } from './PresetMenu'
import { SettingsDialog } from './SettingsDialog'
import { SliderPanel } from './SliderPanel'
import { Button } from './ui/button'
import { Checkbox } from './ui/checkbox'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select'

type EditorLayoutProps = {
  beforePath: string | null
  afterPath: string | null
  imageSize: { width: number; height: number }
  faces: FaceBox[]
  activeFaceId: string | null
  params: EditParams
  compareMode: CompareMode
  showFaceBoxes: boolean
  previewRendering: boolean
  viewCommand: 'fit' | 'actual' | null
  settings: AppSettings
  presets: { id: string; name: string; params: EditParams; builtIn: boolean }[]
  onOpen: () => void
  onExport: () => void
  onParamChange: <G extends ParamGroup>(group: G, key: keyof EditParams[G], value: number) => void
  onResetGroup: (group: ParamGroup) => void
  onResetAll: () => void
  onSetCompareMode: (mode: CompareMode) => void
  onSetActiveFace: (faceId: string | null) => void
  onSetShowFaceBoxes: (value: boolean) => void
  onApplyPreset: (params: EditParams) => void
  onSavePreset: () => void
  onSaveSettings: (settings: AppSettings) => void
}

export const EditorLayout = ({
  beforePath,
  afterPath,
  imageSize,
  faces,
  activeFaceId,
  params,
  compareMode,
  showFaceBoxes,
  previewRendering,
  viewCommand,
  settings,
  presets,
  onOpen,
  onExport,
  onParamChange,
  onResetGroup,
  onResetAll,
  onSetCompareMode,
  onSetActiveFace,
  onSetShowFaceBoxes,
  onApplyPreset,
  onSavePreset,
  onSaveSettings
}: EditorLayoutProps): JSX.Element => (
  <div className="grid h-full grid-rows-[44px_1fr_32px] bg-background">
    <header className="drag-region flex items-center justify-between border-b border-border bg-card px-3">
      <div className="no-drag flex items-center gap-2">
        <Button size="sm" variant="secondary" onClick={onOpen}>
          <FolderOpen className="h-4 w-4" />
          Open
        </Button>
        <PresetMenu presets={presets} onApply={onApplyPreset} onSave={onSavePreset} />
        <Button size="sm" variant={compareMode === 'before' ? 'default' : 'ghost'} onClick={() => onSetCompareMode('before')}>
          Before
        </Button>
        <Button size="sm" variant={compareMode === 'split' ? 'default' : 'ghost'} onClick={() => onSetCompareMode('split')}>
          Split
        </Button>
        <Button size="sm" variant={compareMode === 'after' ? 'default' : 'ghost'} onClick={() => onSetCompareMode('after')}>
          After
        </Button>
      </div>
      <div className="no-drag flex items-center gap-2">
        <Button size="sm" variant="ghost">
          <Maximize className="h-4 w-4" />
          Fit
        </Button>
        <Button size="sm" variant="ghost" onClick={onResetAll}>
          <RotateCcw className="h-4 w-4" />
          Reset
        </Button>
        <SettingsDialog settings={settings} onSave={onSaveSettings} />
        <Button disabled={!beforePath} size="sm" onClick={onExport}>
          <Download className="h-4 w-4" />
          Export
        </Button>
      </div>
    </header>

    <main className="grid min-h-0 grid-cols-[58px_minmax(0,1fr)_340px]">
      <aside className="flex flex-col items-center gap-2 border-r border-border bg-card py-3">
        <Button aria-label="Open image" size="icon" variant="ghost" onClick={onOpen}>
          <FolderOpen className="h-4 w-4" />
        </Button>
        <Button
          aria-label="Split compare"
          size="icon"
          variant={compareMode === 'split' ? 'secondary' : 'ghost'}
          onClick={() => onSetCompareMode(compareMode === 'split' ? 'after' : 'split')}
        >
          <Eye className="h-4 w-4" />
        </Button>
        <Button
          aria-label="Face boxes"
          size="icon"
          variant={showFaceBoxes ? 'secondary' : 'ghost'}
          onClick={() => onSetShowFaceBoxes(!showFaceBoxes)}
        >
          <ScanFace className="h-4 w-4" />
        </Button>
      </aside>

      <section className="min-h-0">
        <CanvasViewer
          activeFaceId={activeFaceId}
          afterPath={afterPath}
          beforePath={beforePath}
          compareMode={compareMode}
          faces={faces}
          height={imageSize.height}
          loading={previewRendering}
          showFaceBoxes={showFaceBoxes}
          viewCommand={viewCommand}
          width={imageSize.width}
          onOpen={onOpen}
          onSelectFace={onSetActiveFace}
        />
      </section>

      <aside className="grid min-h-0 grid-rows-[124px_1fr] border-l border-border bg-card">
        <section className="border-b border-border px-4 py-3">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold">Face</h2>
            <label className="flex items-center gap-2 text-xs text-muted-foreground">
              <Checkbox checked={showFaceBoxes} onCheckedChange={(checked) => onSetShowFaceBoxes(checked === true)} />
              Boxes
            </label>
          </div>
          <Select value={activeFaceId ?? 'none'} onValueChange={(value) => onSetActiveFace(value === 'none' ? null : value)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {faces.length === 0 ? (
                <SelectItem value="none">No face</SelectItem>
              ) : (
                faces.map((face, index) => (
                  <SelectItem key={face.face_id} value={face.face_id}>
                    Face #{index + 1}
                  </SelectItem>
                ))
              )}
            </SelectContent>
          </Select>
        </section>
        <SliderPanel
          disabled={!beforePath}
          params={params}
          onParamChange={onParamChange}
          onResetGroup={onResetGroup}
        />
      </aside>
    </main>
  </div>
)
