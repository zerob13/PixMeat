import { defaultParams, type EditParams } from '@/types/params'

const clamp = (value: number, min: number, max: number): number =>
  Math.min(max, Math.max(min, Number.isFinite(value) ? value : min))

export const clampUiParams = (params: EditParams): EditParams => {
  const body = params.body ?? defaultParams.body
  const liquify = params.liquify ?? defaultParams.liquify
  const skin = params.skin ?? defaultParams.skin
  const beauty = params.beauty ?? defaultParams.beauty
  return {
    body: {
      bodySlim: clamp(body.bodySlim, -100, 100),
      waistSlim: clamp(body.waistSlim, -100, 100),
      armSlim: clamp(body.armSlim, -100, 100)
    },
    liquify: {
      faceSlim: clamp(liquify.faceSlim, -100, 100),
      jawline: clamp(liquify.jawline, -100, 100),
      chinLength: clamp(liquify.chinLength, -50, 50),
      eyeEnlarge: clamp(liquify.eyeEnlarge, -100, 100),
      noseSlim: clamp(liquify.noseSlim, -100, 100),
      smile: clamp(liquify.smile, -100, 100)
    },
    skin: {
      skinSmooth: clamp(skin.skinSmooth, 0, 100),
      textureKeep: clamp(skin.textureKeep, 0, 100),
      blemishSoften: clamp(skin.blemishSoften, 0, 100),
      skinToneEven: clamp(skin.skinToneEven, 0, 100)
    },
    beauty: {
      brightness: clamp(beauty.brightness, -50, 50),
      eyeBright: clamp(beauty.eyeBright, 0, 100),
      teethWhite: clamp(beauty.teethWhite, 0, 100),
      softContrast: clamp(beauty.softContrast, -50, 50)
    }
  }
}

export const toEngineParams = (params: EditParams): EditParams => {
  const safe = clampUiParams(params)
  return {
    body: {
      bodySlim: safe.body.bodySlim / 100,
      waistSlim: safe.body.waistSlim / 100,
      armSlim: safe.body.armSlim / 100
    },
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
