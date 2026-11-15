import type { HorizonProfile } from '../../features/analysis-results/types'

/** Logical ENU display coordinates: X East, Y Up, Z North. Not globe coordinates. */
export function localDirection(azimuth: number, elevation: number): [number, number, number] {
  if (!Number.isFinite(azimuth) || azimuth < 0 || azimuth >= 360 || !Number.isFinite(elevation) || Math.abs(elevation) > 90) throw new RangeError('Invalid local angular direction')
  const az = azimuth * Math.PI / 180, el = elevation * Math.PI / 180
  return [Math.cos(el) * Math.sin(az), Math.sin(el), Math.cos(el) * Math.cos(az)]
}
/** E/U/N is left-handed. Reflect North at the renderer boundary so Three's
 * right-handed camera shows East to the right when looking North, without roll
 * or mirrored text. Logical data and camera readouts remain ENU. */
export function renderDirection(azimuth: number, elevation: number, radius = 10): [number, number, number] {
  const [e, u, n] = localDirection(azimuth, elevation)
  return [e * radius, u * radius, -n * radius]
}
export function samplePositions(profile: HorizonProfile | null): Float32Array {
  return new Float32Array(profile?.points.flatMap(p => p.elevation_deg === null ? [] : renderDirection(p.azimuth_deg, p.elevation_deg)) ?? [])
}
export type View = { azimuth: number; elevation: number; fov: number }
export const INITIAL_VIEW: View = { azimuth: 0, elevation: 10, fov: 75 }
export function boundedView(view: View): View {
  if (!Object.values(view).every(Number.isFinite)) throw new RangeError('Invalid camera view')
  return { azimuth: ((view.azimuth % 360) + 360) % 360, elevation: Math.max(-85, Math.min(85, view.elevation)), fov: Math.max(35, Math.min(100, view.fov)) }
}
