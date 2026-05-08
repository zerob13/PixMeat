import { useState } from 'react'
import { Input } from './ui/input'
import { Slider } from './ui/slider'

type SliderControlProps = {
  label: string
  value: number
  min: number
  max: number
  step?: number
  disabled?: boolean
  onChange: (value: number) => void
}

export const SliderControl = ({
  label,
  value,
  min,
  max,
  step = 1,
  disabled = false,
  onChange
}: SliderControlProps): JSX.Element => {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(String(value))

  const commit = (): void => {
    const next = Number(draft)
    if (Number.isFinite(next)) {
      onChange(Math.min(max, Math.max(min, next)))
    }
    setEditing(false)
  }

  return (
    <div className="grid grid-cols-[92px_1fr_52px] items-center gap-3">
      <label className="text-xs text-muted-foreground">{label}</label>
      <Slider
        aria-label={label}
        disabled={disabled}
        max={max}
        min={min}
        step={step}
        value={[value]}
        onValueChange={([next]) => onChange(next)}
      />
      {editing ? (
        <Input
          autoFocus
          className="h-7 px-2 text-right text-xs"
          value={draft}
          onBlur={commit}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') commit()
            if (event.key === 'Escape') setEditing(false)
          }}
        />
      ) : (
        <button
          className="h-7 rounded border border-transparent text-right text-xs tabular-nums text-foreground hover:border-border hover:bg-secondary"
          disabled={disabled}
          type="button"
          onClick={() => {
            setDraft(String(value))
            setEditing(true)
          }}
        >
          {value}
        </button>
      )}
    </div>
  )
}
