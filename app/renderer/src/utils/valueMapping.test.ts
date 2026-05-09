import { describe, expect, it } from 'vitest'
import { defaultParams } from '@/types/params'
import { clampUiParams, toEngineParams } from './valueMapping'

describe('value mapping', () => {
  it('clamps UI params', () => {
    const params = clampUiParams({
      ...defaultParams,
      body: { ...defaultParams.body, bodySlim: 120 },
      liquify: { ...defaultParams.liquify, faceSlim: 200, chinLength: -90 },
      beauty: { ...defaultParams.beauty, brightness: 100 }
    })
    expect(params.body.bodySlim).toBe(100)
    expect(params.liquify.faceSlim).toBe(100)
    expect(params.liquify.chinLength).toBe(-50)
    expect(params.beauty.brightness).toBe(50)
  })

  it('normalizes engine params', () => {
    const params = toEngineParams({
      ...defaultParams,
      body: { ...defaultParams.body, waistSlim: 40 },
      liquify: { ...defaultParams.liquify, faceSlim: 30, chinLength: -25 },
      skin: { ...defaultParams.skin, textureKeep: 75 },
      beauty: { ...defaultParams.beauty, brightness: 10 }
    })
    expect(params.body.waistSlim).toBe(0.4)
    expect(params.liquify.faceSlim).toBe(0.3)
    expect(params.liquify.chinLength).toBe(-0.5)
    expect(params.skin.textureKeep).toBe(0.75)
    expect(params.beauty.brightness).toBe(0.2)
  })
})
