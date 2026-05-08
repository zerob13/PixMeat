import { useState } from 'react'
import type { AppSettings } from '@/types/ui'
import { Button } from './ui/button'
import { Checkbox } from './ui/checkbox'
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogTitle,
  DialogTrigger
} from './ui/dialog'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select'

type SettingsDialogProps = {
  settings: AppSettings
  onSave: (settings: AppSettings) => void
}

export const SettingsDialog = ({ settings, onSave }: SettingsDialogProps): JSX.Element => {
  const [draft, setDraft] = useState(settings)

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button size="sm" variant="ghost">
          Settings
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogTitle className="text-base font-semibold">Settings</DialogTitle>
        <DialogDescription className="sr-only">Application settings</DialogDescription>
        <div className="mt-5 space-y-4">
          <label className="grid gap-2 text-sm">
            Preferred backend
            <Select
              value={draft.preferredBackend}
              onValueChange={(value) => setDraft({ ...draft, preferredBackend: value as AppSettings['preferredBackend'] })}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="auto">Auto</SelectItem>
                <SelectItem value="cpu">CPU</SelectItem>
                <SelectItem value="cuda">CUDA</SelectItem>
                <SelectItem value="mps">MPS</SelectItem>
                <SelectItem value="opencv_cuda">OpenCV CUDA</SelectItem>
              </SelectContent>
            </Select>
          </label>
          <label className="grid gap-2 text-sm">
            Preview max side
            <Select
              value={String(draft.previewMaxSide)}
              onValueChange={(value) => setDraft({ ...draft, previewMaxSide: Number(value) })}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="1200">1200</SelectItem>
                <SelectItem value="1600">1600</SelectItem>
                <SelectItem value="1800">1800</SelectItem>
              </SelectContent>
            </Select>
          </label>
          <label className="flex items-center gap-3 text-sm">
            <Checkbox
              checked={draft.privacyMode}
              onCheckedChange={(checked) => setDraft({ ...draft, privacyMode: checked === true })}
            />
            Redact paths in logs
          </label>
          <div className="flex justify-end gap-2">
            <DialogClose asChild>
              <Button variant="secondary">Cancel</Button>
            </DialogClose>
            <DialogClose asChild>
              <Button onClick={() => onSave(draft)}>Save</Button>
            </DialogClose>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
