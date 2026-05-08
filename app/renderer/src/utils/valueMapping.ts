import type { EditParams } from '@/types/params'

const clamp = (value: number, min: number, max: number): number =>
  Math.min(max, Math.max(min, Number.isFinite(value) ? value : min))

export const clampUiParams = (params: EditParams): EditParams => ({
  liquify: {
    faceSlim: clamp(params.liquify.faceSlim, 0, 100),
    jawline: clamp(params.liquify.jawline, 0, 100),
    chinLength: clamp(params.liquify.chinLength, -50, 50),
    eyeEnlarge: clamp(params.liquify.eyeEnlarge, 0, 100),
    noseSlim: clamp(params.liquify.noseSlim, 0, 100),
    smile: clamp(params.liquify.smile, 0, 100)
  },
  skin: {
    skinSmooth: clamp(params.skin.skinSmooth, 0, 100),
    textureKeep: clamp(params.skin.textureKeep, 0, 100),
    blemishSoften: clamp(params.skin.blemishSoften, 0, 100),
    skinToneEven: clamp(params.skin.skinToneEven, 0, 100)
  },
  beauty: {
    brightness: clamp(params.beauty.brightness, -50, 50),
    eyeBright: clamp(params.beauty.eyeBright, 0, 100),
    teethWhite: clamp(params.beauty.teethWhite, 0, 100),
    softContrast: clamp(params.beauty.softContrast, -50, 50)
  }
})

export const toEngineParams = (params: EditParams): EditParams => {
  const safe = clampUiParams(params)
  return {
    liquify: {
      faceSlim: safe.liquify.faceSlim / 100,
      jawline: safe.liquify.jawline / 100,
      chinLength: safe.liquify.chinLength / 50,
      eyeEnlarge: safe.liquify.eyeEnlarge / 100,
      noseSlim: safe.liquify.noseSlim / 100,
      smile: safe.liquify.smile / 100
    },
    skin: {
      skinSmooth: safe.skin.skinSmooth / 100,
      textureKeep: safe.skin.textureKeep / 100,
      blemishSoften: safe.skin.blemishSoften / 100,
      skinToneEven: safe.skin.skinToneEven / 100
    },
    beauty: {
      brightness: safe.beauty.brightness / 50,
      eyeBright: safe.beauty.eyeBright / 100,
      teethWhite: safe.beauty.teethWhite / 100,
      softContrast: safe.beauty.softContrast / 50
    }
  }
}

const imageUrlCache = new Map<string, string>()

export const filePathToUrl = (filePath: string): string => {
  const cached = imageUrlCache.get(filePath)
  if (cached) {
    return cached
  }
  const url = window.beautyApp.toImageUrl(filePath)
  imageUrlCache.set(filePath, url)
  return url
}
