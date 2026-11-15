import type { HorizonProfile } from '../../features/analysis-results/types'
import { renderDirection } from './directions'

/** UI proximity limits only; no terrain continuity or visibility is inferred. */
export const MAX_TRACE_GAP_DEG = 5
export function traceSegments(profile: HorizonProfile | null): Float32Array {
  if (!profile || profile.points.length < 2) return new Float32Array()
  const points = profile.points
  const gaps = points.slice(1).map((p, i) => p.azimuth_deg - points[i]!.azimuth_deg)
  const sorted = [...gaps].sort((a,b) => a-b)
  const cadence = sorted[Math.floor((sorted.length - 1) / 2)] ?? 0
  const limit = Math.min(MAX_TRACE_GAP_DEG, cadence * 2)
  const segments: number[] = []
  for (let i = 1; i < points.length; i++) {
    const a = points[i-1]!, b = points[i]!, gap = b.azimuth_deg - a.azimuth_deg
    if (a.elevation_deg === null || b.elevation_deg === null || gap <= 0 || gap > limit) continue
    segments.push(...renderDirection(a.azimuth_deg,a.elevation_deg), ...renderDirection(b.azimuth_deg,b.elevation_deg))
  }
  // Never connect last to first, even when coverage_complete is true.
  return new Float32Array(segments)
}
