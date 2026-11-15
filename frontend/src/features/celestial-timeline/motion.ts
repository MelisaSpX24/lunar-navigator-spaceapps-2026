import type { BodyRow, Checked } from '../analysis-results/types'
import type { Stamp } from '../analysis-results/utc'
import { renderDirection } from '../../visualization/local-horizon/directions'
import { hasDirection } from './selection'

// Presentation guards, not NASA thresholds or a claim about the physical trajectory.
export const MAX_VISUAL_GAP_S = 600
export const MAX_VISUAL_ANGLE_DEG = 15
export type Direction = [number, number, number]
export type VisualPosition =
  | { kind: 'sample'; direction: Direction; horizonId: string | null }
  | { kind: 'interpolated'; direction: Direction; horizonId: string; from: Stamp; to: Stamp }
  | { kind: 'unavailable'; reason: string }
export type MotionTrack = { rows: BodyRow[]; directions: (Direction | null)[]; segments: (string | null)[]; known: number; supportedSegments: number }

/** First element at or after tick. Input order has already passed checkSeries. */
export function lowerBound(times: readonly Stamp[], tick: bigint): number {
  let low = 0, high = times.length
  while (low < high) { const mid = (low + high) >>> 1; if (times[mid]!.tick < tick) low = mid + 1; else high = mid }
  return low
}
function dot(a: Direction, b: Direction) { return a.reduce((sum, n, i) => sum + n * b[i]!, 0) }
function angle(a: Direction, b: Direction) { return Math.acos(Math.max(-1, Math.min(1, dot(a, b)))) }
/** Only called for an accepted segment; normalize the near-identical fallback. */
function slerp(a: Direction, b: Direction, t: number): Direction {
  const theta = angle(a, b), sin = Math.sin(theta)
  const wa = theta < 1e-7 ? 1 - t : Math.sin((1 - t) * theta) / sin
  const wb = theta < 1e-7 ? t : Math.sin(t * theta) / sin
  const v = a.map((n, i) => wa * n + wb * b[i]!) as Direction
  const length = Math.hypot(...v)
  return v.map(n => n / length) as Direction
}
export function prepareMotion(data: Checked<BodyRow[]>, profileIds: ReadonlySet<string>): MotionTrack {
  const rows = data.kind === 'valid' ? data.value : []
  const directions = rows.map(row => hasDirection(row.body) ? renderDirection(row.body.azimuth_deg, row.body.elevation_deg, 1) : null)
  const gaps = rows.slice(1).map((row, i) => Number(row.time.tick - rows[i]!.time.tick) / 1e6)
  const sorted = [...gaps].sort((a, b) => a - b)
  // Lower median resists isolated long gaps. Never increase the absolute cap.
  const cadence = sorted[Math.floor((sorted.length - 1) / 2)] ?? 0
  const limit = Math.min(MAX_VISUAL_GAP_S, cadence * 3)
  const segments = gaps.map((gap, i) => {
    const a = directions[i], b = directions[i + 1]
    if (!a || !b) return 'A neighboring sample has an unknown direction.'
    if (gap <= 0 || gap > limit) return 'Sample interval exceeds the visual time-gap guard.'
    const id = rows[i]!.body.horizon_id
    if (id === null || !profileIds.has(id)) return 'A known horizon profile is required for visual interpolation.'
    if (id !== rows[i + 1]!.body.horizon_id) return 'Horizon profile changes between samples.'
    if (angle(a, b) > MAX_VISUAL_ANGLE_DEG * Math.PI / 180) return 'Angular separation exceeds the visual guard; the path is not assumed.'
    return null
  })
  return { rows, directions, segments, known: directions.filter(Boolean).length, supportedSegments: segments.filter(s => s === null).length }
}
export function visualPosition(track: MotionTrack, selected: Stamp | null, smooth: boolean): VisualPosition {
  const unavailable = (reason: string): VisualPosition => ({ kind: 'unavailable', reason })
  if (!selected || !track.rows.length) return unavailable('No validated samples.')
  // Binary search directly over cached rows, without allocating a time array per frame.
  let low = 0, high = track.rows.length
  while (low < high) { const mid = (low + high) >>> 1; if (track.rows[mid]!.time.tick < selected.tick) low = mid + 1; else high = mid }
  const row = track.rows[low]
  if (row?.time.tick === selected.tick) {
    const direction = track.directions[low]
    return direction ? { kind: 'sample', direction, horizonId: row.body.horizon_id } : unavailable('Backend sample direction is unknown.')
  }
  if (!smooth) return unavailable('Exact Samples mode: no sample at selected time.')
  if (low === 0 || low === track.rows.length) return unavailable('Outside the supplied sample interval; no extrapolation.')
  const reason = track.segments[low - 1]
  if (reason !== null) return unavailable(reason ?? 'Unsupported segment.')
  const from = track.rows[low - 1]!, to = track.rows[low]!
  const ratio = Number(selected.tick - from.time.tick) / Number(to.time.tick - from.time.tick)
  return { kind: 'interpolated', direction: slerp(track.directions[low - 1]!, track.directions[low]!, ratio), horizonId: from.body.horizon_id!, from: from.time, to: to.time }
}
export function positionLabel(value: VisualPosition) {
  return value.kind === 'sample' ? 'BACKEND SAMPLE' : value.kind === 'interpolated' ? 'VISUAL INTERPOLATION' : 'NO SUPPORTED POSITION'
}
