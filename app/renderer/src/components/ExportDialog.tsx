import { useState } from 'react'
import type { ExportFormat } from '@/types/engine'
import { Button } from './ui/button'
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogTitle
} from './ui/dialog'
import { Input } from './ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select'
import { SliderControl } from './SliderControl'

type ExportDialogProps = {
  open: boolean
  running: boolean
  progress: number
  stage: string
  onOpenChange: (open: boolean) => void
  onExport: (options: { fileName: string; format: ExportFormat; quality: number; keepMetadata: boolean }) => void
  onCancel: () => void
}

export const ExportDialog = ({
  open,
  running,
  progress,
  stage,
  onOpenChange,
  onExport,
  onCancel
}: ExportDialogProps): JSX.Element => {
  const [fileName, setFileName] = useState('portrait_retouched.jpg')
  const [format, setFormat] = useState<ExportFormat>('jpeg')
  const [quality, setQuality] = useState(92)

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogTitle className="text-base font-semibold">Export</DialogTitle>
        <DialogDescription className="sr-only">Export full resolution image</DialogDescription>
        {running ? (
          <div className="mt-5 space-y-4">
            <div className="text-sm text-muted-foreground">{stage || 'exporting'}</div>
            <div className="h-2 overflow-hidden rounded-full bg-secondary">
              <div className="h-full bg-primary" style={{ width: `${Math.round(progress * 100)}%` }} />
            </div>
            <div className="flex justify-end">
              <Button variant="secondary" onClick={onCancel}>
                Cancel
              </Button>
            </div>
          </div>
        ) : (
          <div className="mt-5 space-y-4">
            <label className="grid gap-2 text-sm">
              File name
              <Input value={fileName} onChange={(event) => setFileName(event.target.value)} />
            </label>
            <label className="grid gap-2 text-sm">
              Format
              <Select value={format} onValueChange={(value) => setFormat(value as ExportFormat)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="jpeg">JPEG</SelectItem>
                  <SelectItem value="png">PNG</SelectItem>
                  <SelectItem value="tiff">TIFF</SelectItem>
                </SelectContent>
              </Select>
            </label>
            <SliderControl label="Quality" max={100} min={1} value={quality} onChange={setQuality} />
            <div className="flex justify-end gap-2">
              <DialogClose asChild>
                <Button variant="secondary">Cancel</Button>
              </DialogClose>
              <Button onClick={() => onExport({ fileName, format, quality, keepMetadata: true })}>Export</Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
