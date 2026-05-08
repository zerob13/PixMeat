import type { EngineHealth, LoadImageResult } from '@/types/engine'

type StatusBarProps = {
  health: EngineHealth | null
  session: LoadImageResult | null
  previewRendering: boolean
  error: string | null
}

export const StatusBar = ({ health, session, previewRendering, error }: StatusBarProps): JSX.Element => (
  <div className="flex h-8 items-center gap-4 border-t border-border bg-card px-4 text-xs text-muted-foreground">
    <span>Engine: {error ? 'error' : health?.status ?? 'starting'}</span>
    <span>Backend: {health?.active_backend ?? 'checking'}</span>
    <span>Preview: {session ? `${session.preview_width}px` : '-'}</span>
    <span>{previewRendering ? 'Rendering' : 'Idle'}</span>
    {error && <span className="text-destructive">{error}</span>}
  </div>
)
