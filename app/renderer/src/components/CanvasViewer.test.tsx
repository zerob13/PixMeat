import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { CanvasViewer } from './CanvasViewer'

class TestResizeObserver {
  observe(): void {}
  disconnect(): void {}
}

const baseProps = {
  beforePath: 'before.png',
  afterPath: 'after.png',
  width: 1000,
  height: 500,
  faces: [],
  activeFaceId: null,
  showFaceBoxes: false,
  loading: false,
  viewCommand: null,
  onOpen: vi.fn(),
  onSelectFace: vi.fn()
}

describe('CanvasViewer', () => {
  it('uses a non-passive wheel listener for zooming', () => {
    vi.stubGlobal('ResizeObserver', TestResizeObserver)
    window.beautyApp.toImageUrl = (filePath: string) => `pixmeat://image/${filePath}`
    const addEventListener = vi.spyOn(HTMLDivElement.prototype, 'addEventListener')

    render(<CanvasViewer {...baseProps} compareMode="after" />)

    const wheelCall = addEventListener.mock.calls.find(
      ([eventName, _listener, options]) => eventName === 'wheel' && typeof options === 'object' && options?.passive === false
    )
    expect(wheelCall?.[2]).toMatchObject({ passive: false })
    addEventListener.mockRestore()
  })

  it('clips split compare on one aligned image frame', () => {
    vi.stubGlobal('ResizeObserver', TestResizeObserver)
    window.beautyApp.toImageUrl = (filePath: string) => `pixmeat://image/${filePath}`

    render(<CanvasViewer {...baseProps} compareMode="split" />)

    const before = screen.getByAltText('Before preview') as HTMLImageElement
    const after = screen.getByAltText('After preview') as HTMLImageElement
    const divider = screen.getByRole('button', { name: 'Split divider' })

    expect(before.style.clipPath).toBe('inset(0 50% 0 0)')
    expect(after.style.clipPath).toBe('inset(0 0 0 50%)')
    expect(before).toHaveClass('absolute', 'inset-0', 'h-full', 'w-full')
    expect(after).toHaveClass('absolute', 'inset-0', 'h-full', 'w-full')
    expect(divider).toHaveStyle({ left: '50%' })
  })
})
