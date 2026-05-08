export type LiquifyParams = {
  faceSlim: number
  jawline: number
  chinLength: number
  eyeEnlarge: number
  noseSlim: number
  smile: number
}

export type SkinParams = {
  skinSmooth: number
  textureKeep: number
  blemishSoften: number
  skinToneEven: number
}

export type BeautyParams = {
  brightness: number
  eyeBright: number
  teethWhite: number
  softContrast: number
}

export type EditParams = {
  liquify: LiquifyParams
  skin: SkinParams
  beauty: BeautyParams
}

export const defaultParams: EditParams = {
  liquify: {
    faceSlim: 0,
    jawline: 0,
    chinLength: 0,
    eyeEnlarge: 0,
    noseSlim: 0,
    smile: 0
  },
  skin: {
    skinSmooth: 0,
    textureKeep: 70,
    blemishSoften: 0,
    skinToneEven: 0
  },
  beauty: {
    brightness: 0,
    eyeBright: 0,
    teethWhite: 0,
    softContrast: 0
  }
}

export type ParamGroup = keyof EditParams
