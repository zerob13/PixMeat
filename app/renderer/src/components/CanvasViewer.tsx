import { useEffect, useMemo, useRef, useState } from 'react'
import type * as React from 'react'
import { ImageOff } from 'lucide-react'
import type { FaceBox } from '@/types/engine'
import type { CompareMode } from '@/types/ui'
import { filePathToUrl } from '@/utils/valueMapping'
import { Button } from './ui/button'

type CanvasViewerProps = {
  beforePath: string | null
  afterPath: string | null
  width: number
  height: number
  faces: FaceBox[]
  activeFaceId: string | null
  compareMode: CompareMode
  showFaceBoxes: boolean
  loading: boolean
  viewCommand: 'fit' | 'actual' | null
  onOpen: () => void
  onSelectFace: (faceId: string) => void
}

type Size = { width: number; height: number }

export const CanvasViewer = ({
  beforePath,
  afterPath,
  width,
  height,
  faces,
  activeFaceId,
  compareMode,
  showFaceBoxes,
  loading,
  viewCommand,
  onOpen,
  onSelectFace
}: CanvasViewerProps): JSX.Element => {
  const containerRef = useRef<HTMLDivElement>(null)
  const [container, setContainer] = useState<Size>({ width: 1, height: 1 })
  const [zoom, setZoom] = useState(1)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const [drag, setDrag] = useState<{ x: number; y: number; panX: number; panY: number } | null>(null)
  const [split, setSplit] = useState(0.5)
  const [naturalSize, setNaturalSize] = useState<Size>({ width: 1, height: 1 })

  useEffect(() => {
    const element = containerRef.current
    if (!element) return
    const updateSize = (): void => {
      const rect = element.getBoundingClientRect()
      setContainer({ width: Math.max(1, rect.width), height: Math.max(1, rect.height) })
    }
    updateSize()
    const observer = new ResizeObserver(([entry]) => {
      setContainer({
        width: Math.max(1, entry.contentRect.width),
        height: Math.max(1, entry.contentRect.height)
      })
    })
    observer.observe(element)
    return () => observer.disconnect()
  }, [beforePath])

  const imageWidth = Number.isFinite(width) && width > 1 ? width : naturalSize.width
  const imageHeight = Number.isFinite(height) && height > 1 ? height : naturalSize.height

  const baseScale = useMemo(() => {
    if (!imageWidth || !imageHeight) return 1
    const availableWidth = Math.max(1, container.width - 48)
    const availableHeight = Math.max(1, container.height - 48)
    return Math.max(0.01, Math.min(availableWidth / imageWidth, availableHeight / imageHeight, 1))
  }, [container.height, container.width, imageHeight, imageWidth])

  useEffect(() => {
    if (viewCommand === 'fit') {
      setZoom(1)
      setPan({ x: 0, y: 0 })
    } else if (viewCommand === 'actual') {
      setZoom(1 / Math.max(baseScale, 0.001))
      setPan({ x: 0, y: 0 })
    }
  }, [baseScale, viewCommand])

  useEffect(() => {
    const element = containerRef.current
    if (!element || !beforePath) return
    const handleWheel = (event: WheelEvent): void => {
      event.preventDefault()
      setZoom((current) => Math.min(4, Math.max(0.25, current * (event.deltaY > 0 ? 0.92 : 1.08))))
    }
    element.addEventListener('wheel', handleWheel, { passive: false })
    return () => element.removeEventListener('wheel', handleWheel)
  }, [beforePath])

  const display = {
    width: Math.max(1, imageWidth * baseScale * zoom),
    height: Math.max(1, imageHeight * baseScale * zoom)
  }
  const frameLeft = container.width / 2 - display.width / 2 + pan.x
  const frameTop = container.height / 2 - display.height / 2 + pan.y

  const imageStyle = {
    width: display.width,
    height: display.height
  }
  const splitPercent = split * 100

  const beforeUrl = beforePath ? filePathToUrl(beforePath) : null
  const afterUrl = afterPath ? filePathToUrl(afterPath) : beforeUrl
  const handleImageLoad = (event: React.SyntheticEvent<HTMLImageElement>): void => {
    const image = event.currentTarget
    if (image.naturalWidth > 1 && image.naturalHeight > 1) {
      setNaturalSize({ width: image.naturalWidth, height: image.naturalHeight })
    }
  }

  if (!beforeUrl) {
    return (
      <div ref={containerRef} className="flex h-full items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-md border border-border bg-card">
            <ImageOff className="h-7 w-7 text-muted-foreground" />
          </div>
          <div>
            <div className="text-base font-medium">Drop a portrait image</div>
            <div className="mt-1 text-sm text-muted-foreground">JPG · PNG · WebP · TIFF</div>
          </div>
          <Button onClick={onOpen}>Open Image</Button>
        </div>
      </div>
    )
  }

  return (
    <div
      ref={containerRef}
      className="checkerboard relative h-full overflow-hidden bg-background"
      onDoubleClick={() => {
        setZoom((current) => (current === 1 ? 1 / baseScale : 1))
        setPan({ x: 0, y: 0 })
      }}
      onPointerDown={(event) => {
        if (event.button !== 0 || compareMode === 'split') return
        setDrag({ x: event.clientX, y: event.clientY, panX: pan.x, panY: pan.y })
        event.currentTarget.setPointerCapture(event.pointerId)
      }}
      onPointerMove={(event) => {
        if (!drag) return
        setPan({ x: drag.panX + event.clientX - drag.x, y: drag.panY + event.clientY - drag.y })
      }}
      onPointerUp={() => setDrag(null)}
    >
      <div className="absolute" style={{ left: frameLeft, top: frameTop, ...imageStyle }}>
        {compareMode === 'before' ? (
          <img
            alt="Before preview"
            className="h-full w-full select-none object-fill"
            draggable={false}
            src={beforeUrl}
            onLoad={handleImageLoad}
          />
        ) : compareMode === 'after' ? (
          <img
            alt="After preview"
            className="h-full w-full select-none object-fill"
            draggable={false}
            src={afterUrl ?? beforeUrl}
            onLoad={handleImageLoad}
          />
        ) : (
          <div className="relative h-full w-full overflow-hidden">
            <img
              alt="Before preview"
              className="absolute inset-0 h-full w-full select-none object-fill"
              draggable={false}
              src={beforeUrl}
              style={{ clipPath: `inset(0 ${100 - splitPercent}% 0 0)` }}
              onLoad={handleImageLoad}
            />
            <img
              alt="After preview"
              className="absolute inset-0 h-full w-full select-none object-fill"
              draggable={false}
              src={afterUrl ?? beforeUrl}
              style={{ clipPath: `inset(0 0 0 ${splitPercent}%)` }}
              onLoad={handleImageLoad}
            />
            <button
              aria-label="Split divider"
              className="absolute top-0 h-full w-6 -translate-x-1/2 cursor-ew-resize"
              style={{ left: `${splitPercent}%` }}
              type="button"
              onPointerDown={(event) => {
                event.currentTarget.setPointerCapture(event.pointerId)
              }}
              onPointerMove={(event) => {
                if (event.buttons !== 1) return
                const rect = event.currentTarget.parentElement?.getBoundingClientRect()
                if (!rect) return
                setSplit(Math.min(0.95, Math.max(0.05, (event.clientX - rect.left) / rect.width)))
              }}
            >
              <span className="mx-auto block h-full w-1 bg-primary" />
            </button>
          </div>
        )}

        {showFaceBoxes &&
          faces.map((face) => {
            const [x, y, w, h] = face.bbox
            const selected = face.face_id === activeFaceId
            return (
              <button
                key={face.face_id}
                className={`absolute rounded-sm border ${selected ? 'border-primary' : 'border-accent/75'} bg-transparent`}
                style={{
                  left: x * baseScale * zoom,
                  top: y * baseScale * zoom,
                  width: w * baseScale * zoom,
                  height: h * baseScale * zoom
                }}
                title={face.face_id}
                type="button"
                onClick={() => onSelectFace(face.face_id)}
              />
            )
          })}
      </div>
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-background/20">
          <div className="h-9 w-9 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        </div>
      )}
    </div>
  )
}
