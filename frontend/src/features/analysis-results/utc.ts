import { parseUtc } from '../mission-input/time'

export type Stamp = { text: string; tick: bigint }
/** Strict Gregorian UTC, up to backend datetime's microsecond precision.
 * BigInt keeps ordering exact even near years 0001/9999. No local timezone.
 */
export function utcStamp(value: unknown): Stamp | null {
  if (typeof value !== 'string') return null
  const match = /^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})(?:\.(\d{1,6}))?(Z|\+00:00)$/.exec(value)
  if (!match) return null
  const parsed = parseUtc(match[1]!, match[2]!).value
  if (!parsed) return null
  return { text: value, tick: BigInt(Date.parse(parsed)) * 1000n + BigInt((match[3] ?? '').padEnd(6, '0')) }
}
export type TimeBounds = { start: Stamp; end: Stamp }
export function timeBounds(start: string, duration: number): TimeBounds {
  const stamp = utcStamp(start)
  if (!stamp || !Number.isSafeInteger(duration) || duration <= 0) throw new Error('Invalid submitted time range')
  const tick = stamp.tick + BigInt(duration) * 1_000_000n
  return { start: stamp, end: { tick, text: new Date(Number(tick / 1000n)).toISOString() } }
}
export function timePosition(stamp: Stamp, bounds: TimeBounds): number {
  return Number(stamp.tick - bounds.start.tick) / Number(bounds.end.tick - bounds.start.tick)
}
