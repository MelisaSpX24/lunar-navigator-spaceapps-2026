import { expect, it } from 'vitest'
import { createMoonGeometry } from './moonGeometry'

it('calibrates actual SphereGeometry UVs at cardinal points and preserves both seam edges', () => {
  const geometry = createMoonGeometry()
  const position = geometry.getAttribute('position')
  const uv = geometry.getAttribute('uv')
  function matches(x: number, y: number, z: number) {
    return Array.from({ length: position.count }, (_, i) => i).filter(i =>
      Math.abs(position.getX(i) - x) < 1e-5 && Math.abs(position.getY(i) - y) < 1e-5 && Math.abs(position.getZ(i) - z) < 1e-5)
  }
  for (const [x, z, u] of [[1, 0, .5], [0, -1, .75], [0, 1, .25]]) {
    const indices = matches(x!, 0, z!)
    expect(indices.length).toBeGreaterThan(0)
    for (const i of indices) { expect(uv.getX(i)).toBeCloseTo(u!, 5); expect(uv.getY(i)).toBeCloseTo(.5, 5) }
  }
  const seam = matches(-1, 0, 0).map(i => uv.getX(i)).sort()
  expect(seam[0]).toBeCloseTo(0, 5)
  expect(seam.at(-1)).toBeCloseTo(1, 5)
  for (const i of matches(0, 1, 0)) expect(uv.getY(i)).toBeCloseTo(1, 5)
  for (const i of matches(0, -1, 0)) expect(uv.getY(i)).toBeCloseTo(0, 5)
  geometry.dispose()
})
