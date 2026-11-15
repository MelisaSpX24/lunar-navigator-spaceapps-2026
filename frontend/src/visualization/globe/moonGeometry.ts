import { SphereGeometry } from 'three'
import { fromCartesian, toMapUv } from '../coordinates/lunarCoordinates'

export function createMoonGeometry() {
  const geometry = new SphereGeometry(1, 64, 32)
  const positions = geometry.getAttribute('position')
  const uv = geometry.getAttribute('uv')
  for (let i = 0; i < positions.count; i++) {
    const coordinate = fromCartesian({ x: positions.getX(i), y: positions.getY(i), z: positions.getZ(i) })
    const originalU = uv.getX(i)
    // Preserve both copies of the ±180° seam and pole UVs; they share positions.
    const isSeam = coordinate.longitude !== null && Math.abs(Math.abs(coordinate.longitude) - 180) < 1e-4
    const u = coordinate.longitude === null || isSeam ? originalU : toMapUv(coordinate.latitude, coordinate.longitude).u
    uv.setXY(i, u, (coordinate.latitude + 90) / 180)
  }
  uv.needsUpdate = true
  return geometry
}
