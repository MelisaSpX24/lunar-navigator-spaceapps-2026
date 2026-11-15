import { record } from '../../services/api/responses'
import type { BodyRow, BodySample, Checked, Decision, HorizonProfile, Quality, ResolvedSite, Score, Source, VisibilityWindow } from './types'
import { utcStamp, type TimeBounds } from './utc'

export const MAX_RECORDS = 5000
export const TABLE_ROWS = 100
export const finite = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v)
const range = (v: unknown, min: number, max: number) => finite(v) && v >= min && v <= max
const text = (v: unknown): v is string => typeof v === 'string' && v.trim().length > 0
const strings = (v: unknown): v is string[] => Array.isArray(v) && v.every(s => typeof s === 'string')
const choice = (v: unknown, allowed: string[]) => typeof v === 'string' && allowed.includes(v)
const nullable = (v: unknown, check: (v: unknown) => boolean) => v === null || check(v)
const invalid = <T,>(message: string): Checked<T> => ({ kind: 'invalid', message })
const valid = <T,>(value: T): Checked<T> => ({ kind: 'valid', value })
function listGate<T>(value: unknown): Checked<T> | null {
  if (value === null) return { kind: 'missing' }
  if (!Array.isArray(value)) return invalid('Expected an array or explicit null; missing fields are not zero.')
  if (value.length > MAX_RECORDS) return { kind: 'limited', message: `Display limit exceeded (${MAX_RECORDS} records). No records have been plotted or silently sampled.` }
  return null
}
export function isBody(v: unknown): v is BodySample {
  return record(v) && nullable(v.azimuth_deg, n => range(n, 0, 360) && n !== 360)
    && nullable(v.elevation_deg, n => range(n, -90, 90))
    && nullable(v.angular_radius_deg, n => range(n, 0, 90) && n !== 0)
    && nullable(v.horizon_id, text) && nullable(v.center_clearance_deg, finite)
    && nullable(v.disk_visible_fraction, n => range(n, 0, 1))
    && choice(v.disk_state, ['FULL','PARTIAL','NONE','UNKNOWN']) && nullable(v.condition_met, n => typeof n === 'boolean')
}
export function checkSeries(value: unknown, body: 'sun' | 'earth', bounds: TimeBounds): Checked<BodyRow[]> {
  const gate = listGate<BodyRow[]>(value)
  if (gate) return gate
  const rows: BodyRow[] = []
  let previous: bigint | null = null
  for (const sample of value as unknown[]) {
    if (!record(sample)) return invalid('Time samples must be objects.')
    const time = utcStamp(sample.time_utc)
    if (!time || time.tick < bounds.start.tick || time.tick > bounds.end.tick || (previous !== null && time.tick <= previous)) return invalid('UTC samples must be valid, strictly increasing and inside the submitted time range; no sorting or repair was applied.')
    if (!nullable(sample.joint_condition_met, n => typeof n === 'boolean') || !isBody(sample[body])) return invalid(`Invalid ${body} sample fields, numeric ranges or enum values.`)
    previous = time.tick
    rows.push({ time, body: sample[body] })
  }
  return valid(rows)
}
export function checkHorizons(value: unknown): Checked<HorizonProfile[]> {
  const gate = listGate<HorizonProfile[]>(value)
  if (gate) return gate
  const ids = new Set<string>()
  if ((value as unknown[]).length > 20) return { kind: 'limited', message: 'Horizon display limit exceeded (20 profiles); no profiles have been silently hidden.' }
  let totalPoints = 0
  for (const h of value as unknown[]) {
    if (!record(h) || !text(h.id) || ids.has(h.id) || !finite(h.observer_height_m) || h.observer_height_m < 0 || !finite(h.range_m) || h.range_m <= 0
      || typeof h.coverage_complete !== 'boolean' || !strings(h.dem_source_ids) || !Array.isArray(h.points)) return invalid('Invalid horizon metadata or duplicate profile ID.')
    ids.add(h.id)
    totalPoints += h.points.length
    if (totalPoints > MAX_RECORDS) return { kind: 'limited', message: 'Horizon display limit exceeded; no points were silently sampled.' }
    let previous = -1
    for (const point of h.points) {
      if (!record(point) || !range(point.azimuth_deg, 0, 360) || point.azimuth_deg === 360 || (point.azimuth_deg as number) <= previous || !nullable(point.elevation_deg, n => range(n, -90, 90))) return invalid('Horizon azimuths must increase in [0°,360°); elevation must be [-90°,90°] or null. No points were repaired.')
      previous = point.azimuth_deg as number
    }
  }
  return valid(value as HorizonProfile[])
}
export function checkWindows(value: unknown, bounds: TimeBounds): Checked<VisibilityWindow[]> {
  const gate = listGate<VisibilityWindow[]>(value)
  if (gate) return gate
  const result: VisibilityWindow[] = []
  let previous: bigint | null = null
  for (const w of value as unknown[]) {
    if (!record(w) || !text(w.definition_id) || typeof w.start_censored !== 'boolean' || typeof w.end_censored !== 'boolean') return invalid('Invalid window metadata.')
    const start = utcStamp(w.start_utc), end = utcStamp(w.end_utc)
    if (!start || !end || start.tick >= end.tick || start.tick < bounds.start.tick || end.tick > bounds.end.tick || (previous !== null && start.tick < previous)) return invalid('Windows must be ordered, valid UTC [start,end) intervals inside the submitted range. No interval was sorted or clipped.')
    previous = start.tick
    result.push({ start, end, definition_id: w.definition_id, start_censored: w.start_censored, end_censored: w.end_censored })
  }
  return valid(result)
}
export function checkDecision(value: unknown): Checked<Decision> {
  if (!record(value) || !choice(value.status, ['MET','NOT_MET','INCOMPLETE']) || !strings(value.reason_codes) || !Array.isArray(value.rules)) return invalid('Invalid decision or missing rules.')
  if (value.rules.length > MAX_RECORDS) return { kind: 'limited', message: 'Rule display limit exceeded; no automatic decision was inferred.' }
  for (const r of value.rules) {
    if (!record(r) || !text(r.code) || !choice(r.status, ['MET','NOT_MET','INCOMPLETE']) || typeof r.message !== 'string'
      || !nullable(r.required, n => finite(n) || typeof n === 'boolean') || !nullable(r.actual, n => finite(n) || typeof n === 'boolean')) return invalid('Invalid rule fields; numeric, boolean and null values are distinct.')
  }
  return valid(value as Decision)
}
export function checkScore(value: unknown): Checked<Score> {
  if (!record(value) || !nullable(value.value, n => range(n, 0, 100)) || !nullable(value.model_version, text)
    || !(value.components === null || Array.isArray(value.components))) return invalid('Invalid score, missing model-version field or invalid components.')
  if (Array.isArray(value.components)) {
    if (value.components.length > MAX_RECORDS) return { kind: 'limited', message: 'Score component display limit exceeded.' }
    for (const c of value.components) if (!record(c) || !text(c.name) || !finite(c.raw_value) || !range(c.normalized_value, 0, 1) || !range(c.weight, 0, 1)) return invalid('Invalid component value, normalized value or weight. No score was recalculated.')
  }
  return valid(value as Score)
}
export function checkQuality(value: unknown): Checked<Quality> {
  return record(value) && choice(value.status, ['NOT_ASSESSED','SUFFICIENT','LIMITED','INSUFFICIENT']) && nullable(value.coverage_complete, n => typeof n === 'boolean') && strings(value.limitations)
    ? valid(value as Quality) : invalid('Invalid data-quality metadata; complete coverage cannot be assumed.')
}
export function checkSources(value: unknown): Checked<Source[]> {
  if (value === null) return invalid('Sources must be an array; null is not a verified source list.')
  const gate = listGate<Source[]>(value)
  if (gate) return gate
  for (const s of value as unknown[]) if (!record(s) || !text(s.id) || !choice(s.kind, ['DEM','SPK','PCK','FK','LSK','REFERENCE']) || !text(s.product) || !text(s.version)
    || typeof s.url !== 'string' || typeof s.sha256 !== 'string' || !/^[0-9a-f]{64}$/.test(s.sha256)) return invalid('Invalid source ID, kind, product, version or SHA-256 metadata.')
  return valid(value as Source[])
}
export function safeSourceUrl(value: string): string | null {
  try { const url = new URL(value); return ['http:','https:'].includes(url.protocol) && !url.username && !url.password ? url.href : null } catch { return null }
}
export function checkResolvedSite(value: unknown): Checked<ResolvedSite> {
  if (value === null) return { kind: 'missing' }
  return record(value) && range(value.latitude_deg, -90, 90) && Math.abs(value.latitude_deg as number) !== 90 && range(value.longitude_deg_east, 0, 360) && value.longitude_deg_east !== 360
    && value.frame === 'MOON_ME_DE421' && value.latitude_type === 'PLANETOCENTRIC' && nullable(value.surface_elevation_m, finite) && nullable(value.height_datum_id, text)
    ? valid(value as ResolvedSite) : invalid('Invalid resolved-site coordinates, frame or elevation metadata.')
}
