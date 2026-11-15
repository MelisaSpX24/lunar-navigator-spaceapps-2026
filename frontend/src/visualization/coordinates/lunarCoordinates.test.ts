import { describe, expect, it } from 'vitest'
import { fromCartesian, normalizeLongitude, toCartesian, toMapUv } from './lunarCoordinates'

const axes = [
  [0, 0, 1, 0, 0], [0, 90, 0, 0, -1], [0, 180, -1, 0, 0],
  [0, -90, 0, 0, 1], [90, 40, 0, 1, 0], [-90, -70, 0, -1, 0],
] as const

describe('visual lunar coordinate convention', () => {
  it.each(axes)('maps latitude %s longitude %s to the expected axes', (lat, lon, x, y, z) => {
    const p = toCartesian(lat, lon, 2)
    expect(p.x).toBeCloseTo(x * 2, 12)
    expect(p.y).toBeCloseTo(y * 2, 12)
    expect(p.z).toBeCloseTo(z * 2, 12)
  })
  it.each(axes)('inverts reference latitude %s longitude %s', (lat, lon, x, y, z) => {
    const p = fromCartesian({ x: x * 3, y: y * 3, z: z * 3 })
    expect(p.latitude).toBeCloseTo(lat, 10)
    expect(p.radius).toBeCloseTo(3, 12)
    if (Math.abs(lat) === 90) expect(p.longitude).toBeNull()
    else expect(p.longitude).toBeCloseTo(normalizeLongitude(lon), 10)
  })
  it('round-trips 500 seeded coordinates and radii', () => {
    let seed = 24628
    const random = () => { seed = (1664525 * seed + 1013904223) >>> 0; return seed / 2 ** 32 }
    for (let i = 0; i < 500; i++) {
      const lat = random() * 179.8 - 89.9
      const lon = random() * 360 - 180
      const radius = random() * 20 + 0.01
      const actual = fromCartesian(toCartesian(lat, lon, radius))
      expect(actual.latitude).toBeCloseTo(lat, 8)
      expect(normalizeLongitude(actual.longitude! - lon)).toBeCloseTo(0, 8)
      expect(actual.radius).toBeCloseTo(radius, 10)
    }
  })
  it.each([[180, -180], [-180, -180], [540, -180], [-270, 90], [360, 0]])('normalizes longitude %s to %s', (input, result) => {
    expect(normalizeLongitude(input)).toBe(result)
  })
  it('rejects invalid and degenerate inputs', () => {
    for (const lat of [NaN, Infinity, 90.1, -91]) expect(() => toCartesian(lat, 0)).toThrow(RangeError)
    for (const radius of [0, -1, Infinity, NaN]) expect(() => toCartesian(0, 0, radius)).toThrow(RangeError)
    expect(() => toCartesian(0, NaN)).toThrow(RangeError)
    expect(() => fromCartesian({ x: 0, y: 0, z: 0 })).toThrow(RangeError)
    expect(() => fromCartesian({ x: Infinity, y: 0, z: 0 })).toThrow(RangeError)
  })
  it('keeps near-pole coordinates finite and exact pole longitude undefined', () => {
    const near = fromCartesian(toCartesian(-89.999, -175))
    expect(near.latitude).toBeCloseTo(-89.999, 7)
    expect(near.longitude).toBeCloseTo(-175, 8)
    expect(fromCartesian(toCartesian(-90, 125)).longitude).toBeNull()
  })
  it('maps zero meridian to map centre and east to the right', () => {
    expect(toMapUv(0, 0)).toEqual({ u: 0.5, v: 0.5 })
    expect(toMapUv(0, 90)).toEqual({ u: 0.75, v: 0.5 })
    expect(toMapUv(90, -90)).toEqual({ u: 0.25, v: 1 })
    expect(toMapUv(-90, 0).v).toBe(0)
  })
})
