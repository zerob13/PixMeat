import * as DropdownMenu from '@radix-ui/react-dropdown-menu'
import { ChevronDown, Save } from 'lucide-react'
import type { EditParams } from '@/types/params'
import { Button } from './ui/button'

type PresetMenuProps = {
  presets: { id: string; name: string; params: EditParams; builtIn: boolean }[]
  onApply: (params: EditParams) => void
  onSave: () => void
}

export const PresetMenu = ({ presets, onApply, onSave }: PresetMenuProps): JSX.Element => (
  <DropdownMenu.Root>
    <DropdownMenu.Trigger asChild>
      <Button size="sm" variant="secondary">
        Presets
        <ChevronDown className="h-4 w-4" />
      </Button>
    </DropdownMenu.Trigger>
    <DropdownMenu.Portal>
      <DropdownMenu.Content className="z-50 min-w-48 rounded-md border border-border bg-card p-1 text-card-foreground">
        {presets.map((preset) => (
          <DropdownMenu.Item
            key={preset.id}
            className="cursor-default rounded-sm px-2 py-1.5 text-sm outline-none data-[highlighted]:bg-secondary"
            onSelect={() => onApply(preset.params)}
          >
            {preset.name}
          </DropdownMenu.Item>
        ))}
        <DropdownMenu.Separator className="my-1 h-px bg-border" />
        <DropdownMenu.Item
          className="flex cursor-default items-center gap-2 rounded-sm px-2 py-1.5 text-sm outline-none data-[highlighted]:bg-secondary"
          onSelect={onSave}
        >
          <Save className="h-4 w-4" />
          Save Current
        </DropdownMenu.Item>
      </DropdownMenu.Content>
    </DropdownMenu.Portal>
  </DropdownMenu.Root>
)
