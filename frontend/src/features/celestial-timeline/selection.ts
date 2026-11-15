import type { BodyRow, BodySample, Checked, HorizonProfile } from '../analysis-results/types'
import type { Stamp, TimeBounds } from '../analysis-results/utc'

export function stampAt(tick: bigint): Stamp {
  // Floor division preserves pre-epoch microseconds rather than rounding to zero.
  const seconds = tick >= 0n ? tick / 1_000_000n : (tick - 999_999n) / 1_000_000n
  const fraction = tick - seconds * 1_000_000n
  return { tick, text: new Date(Number(seconds * 1000n)).toISOString().replace('.000Z', `.${fraction.toString().padStart(6, '0')}Z`) }
}
export function sliderStamp(position: number, bounds: TimeBounds): Stamp {
  if (!Number.isInteger(position) || position < 0 || position > 10000) throw new RangeError('Invalid timeline position')
  return stampAt(bounds.start.tick + (bounds.end.tick - bounds.start.tick) * BigInt(position) / 10000n)
}
export function exactSample(data: Checked<BodyRow[]>, selected: Stamp | null): BodyRow | null {
  if (!selected || data.kind !== 'valid') return null
  let low = 0, high = data.value.length
  while (low < high) { const mid = (low + high) >>> 1; if (data.value[mid]!.time.tick < selected.tick) low = mid + 1; else high = mid }
  return data.value[low]?.time.tick === selected.tick ? data.value[low]! : null
}
export function hasDirection(body: BodySample | null | undefined): body is BodySample & { azimuth_deg: number; elevation_deg: number } {
  return !!body && body.azimuth_deg !== null && body.elevation_deg !== null
}
export function horizonRelation(body: Pick<BodySample, 'horizon_id'>, profiles: HorizonProfile[], activeId: string | null): string {
  if (body.horizon_id === null) return 'Horizon relationship unknown (null horizon ID).'
  if (!profiles.some(p => p.id === body.horizon_id)) return 'Horizon profile unavailable for this sample.'
  if (body.horizon_id !== activeId) return 'Sample references a different horizon profile.'
  return 'Sample references the active horizon profile. Visibility remains a backend assessment.'
}
