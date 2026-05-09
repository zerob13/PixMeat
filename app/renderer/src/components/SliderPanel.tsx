import type * as React from 'react'
import type { EditParams, ParamGroup } from '@/types/params'
import { Button } from './ui/button'
import { SliderControl } from './SliderControl'

type SliderPanelProps = {
  params: EditParams
  disabled?: boolean
  onParamChange: <G extends ParamGroup>(group: G, key: keyof EditParams[G], value: number) => void
  onResetGroup: (group: ParamGroup) => void
}

export const SliderPanel = ({
  params,
  disabled = false,
  onParamChange,
  onResetGroup
}: SliderPanelProps): JSX.Element => (
  <div className="flex h-full flex-col gap-5 overflow-y-auto px-4 py-4">
    <SliderSection title="Body" onReset={() => onResetGroup('body')}>
      <SliderControl
        disabled={disabled}
        label="Body Shape"
        max={100}
        min={-100}
        value={params.body.bodySlim}
        onChange={(value) => onParamChange('body', 'bodySlim', value)}
      />
      <SliderControl
        disabled={disabled}
        label="Waist"
        max={100}
        min={-100}
        value={params.body.waistSlim}
        onChange={(value) => onParamChange('body', 'waistSlim', value)}
      />
      <SliderControl
        disabled={disabled}
        label="Arms"
        max={100}
        min={-100}
        value={params.body.armSlim}
        onChange={(value) => onParamChange('body', 'armSlim', value)}
      />
    </SliderSection>

    <SliderSection title="Liquify" onReset={() => onResetGroup('liquify')}>
      <SliderControl
        disabled={disabled}
        label="Face Shape"
        max={100}
        min={-100}
        value={params.liquify.faceSlim}
        onChange={(value) => onParamChange('liquify', 'faceSlim', value)}
      />
      <SliderControl
        disabled={disabled}
        label="Jawline"
        max={100}
        min={-100}
        value={params.liquify.jawline}
        onChange={(value) => onParamChange('liquify', 'jawline', value)}
      />
      <SliderControl
        disabled={disabled}
        label="Chin"
        max={50}
        min={-50}
        value={params.liquify.chinLength}
        onChange={(value) => onParamChange('liquify', 'chinLength', value)}
      />
      <SliderControl
        disabled={disabled}
        label="Eye Size"
        max={100}
        min={-100}
        value={params.liquify.eyeEnlarge}
        onChange={(value) => onParamChange('liquify', 'eyeEnlarge', value)}
      />
      <SliderControl
        disabled={disabled}
        label="Nose Width"
        max={100}
        min={-100}
        value={params.liquify.noseSlim}
        onChange={(value) => onParamChange('liquify', 'noseSlim', value)}
      />
      <SliderControl
        disabled={disabled}
        label="Smile"
        max={100}
        min={-100}
        value={params.liquify.smile}
        onChange={(value) => onParamChange('liquify', 'smile', value)}
      />
    </SliderSection>

    <SliderSection title="Skin" onReset={() => onResetGroup('skin')}>
      <SliderControl
        disabled={disabled}
        label="Smooth"
        max={100}
        min={0}
        value={params.skin.skinSmooth}
        onChange={(value) => onParamChange('skin', 'skinSmooth', value)}
      />
      <SliderControl
        disabled={disabled}
        label="Texture"
        max={100}
        min={0}
        value={params.skin.textureKeep}
        onChange={(value) => onParamChange('skin', 'textureKeep', value)}
      />
      <SliderControl
        disabled={disabled}
        label="Blemish"
        max={100}
        min={0}
        value={params.skin.blemishSoften}
        onChange={(value) => onParamChange('skin', 'blemishSoften', value)}
      />
      <SliderControl
        disabled={disabled}
        label="Tone Even"
        max={100}
        min={0}
        value={params.skin.skinToneEven}
        onChange={(value) => onParamChange('skin', 'skinToneEven', value)}
      />
    </SliderSection>

    <SliderSection title="Beauty" onReset={() => onResetGroup('beauty')}>
      <SliderControl
        disabled={disabled}
        label="Brightness"
        max={50}
        min={-50}
        value={params.beauty.brightness}
        onChange={(value) => onParamChange('beauty', 'brightness', value)}
      />
      <SliderControl
        disabled={disabled}
        label="Eye Bright"
        max={100}
        min={0}
        value={params.beauty.eyeBright}
        onChange={(value) => onParamChange('beauty', 'eyeBright', value)}
      />
      <SliderControl
        disabled={disabled}
        label="Teeth White"
        max={100}
        min={0}
        value={params.beauty.teethWhite}
        onChange={(value) => onParamChange('beauty', 'teethWhite', value)}
      />
      <SliderControl
        disabled={disabled}
        label="Contrast"
        max={50}
        min={-50}
        value={params.beauty.softContrast}
        onChange={(value) => onParamChange('beauty', 'softContrast', value)}
      />
    </SliderSection>
  </div>
)

const SliderSection = ({
  title,
  onReset,
  children
}: {
  title: string
  onReset: () => void
  children: React.ReactNode
}): JSX.Element => (
  <section className="space-y-3">
    <div className="flex items-center justify-between">
      <h2 className="text-sm font-semibold">{title}</h2>
      <Button size="sm" variant="ghost" onClick={onReset}>
        Reset
      </Button>
    </div>
    <div className="space-y-3">{children}</div>
  </section>
)
