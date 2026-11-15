import { PROFILES, type AnalysisRequestV1 } from './analysisRequest'
import { finiteDecimal, type FormErrors, type MissionFormState, type TextFieldName } from './missionState'
import { endWithinBackendRange, parseDuration, parseUtc } from './time'

export type RequestValidation = {
  valid: boolean; request: AnalysisRequestV1 | null; errors: FormErrors
  durationSeconds: number | null; startUtc: string | null
}

export function buildAnalysisRequest(state: MissionFormState): RequestValidation {
  const utc = parseUtc(state.utcDate, state.utcTime), duration = parseDuration(state)
  const errors: FormErrors = { ...utc.errors, ...duration.errors }
  function numeric(field: TextFieldName, min: number, max = Number.MAX_VALUE, optional = false, integer = false) {
    if (optional && state[field].trim() === '') return null
    const value = finiteDecimal(state[field])
    if (value === null || value < min || value > max || (integer && !Number.isSafeInteger(value))) {
      errors[field] = integer ? 'Enter a nonnegative safe whole number.' : `Enter a finite number from ${min} to ${max === Number.MAX_VALUE ? 'the supported numeric limit' : max}.`
      return null
    }
    return value
  }
  const latitude = numeric('latitude', -90, 90)
  if (latitude !== null && Math.abs(latitude) === 90) errors.latitude = 'Exact ±90° poles are not supported by the current backend. Choose another coordinate; the pole has not been adjusted.'
  const longitude = numeric('longitude', 0, 360)
  if (errors.longitude || longitude === 360) errors.longitude = 'Enter a finite east-positive longitude from 0° up to, but not including, 360°. 360° is excluded; use 0° for that meridian.'
  const solarFraction = numeric('solarFraction', 0, 1), clearance = numeric('clearance', 0, 90)
  const minSun = numeric('minSun', 0, Number.MAX_VALUE, true)
  const minEarth = numeric('minEarth', 0, Number.MAX_VALUE, true)
  const minJoint = numeric('minJoint', 0, Number.MAX_VALUE, true)
  const maxDark = numeric('maxDark', 0, Number.MAX_VALUE, true)
  const solarHeight = numeric('solarHeight', 0), earthHeight = numeric('earthHeight', 0)
  const lookahead = numeric('lookahead', 0, Number.MAX_SAFE_INTEGER, false, true)
  if (!PROFILES.some(profile => profile.value === state.profile)) errors.profile = 'Choose one of the four supported operation profiles.'
  for (const field of ['simultaneous', 'fullHorizon', 'earthDisk'] as const) {
    if (typeof state[field] !== 'boolean') errors[field] = 'Use a boolean selection.'
  }
  if (minJoint !== null && !state.simultaneous) errors.minJoint = 'Enable simultaneous visibility when a minimum joint duration is provided.'
  for (const [field, value] of [['minSun', minSun], ['minEarth', minEarth], ['minJoint', minJoint]] as const) {
    if (value !== null && duration.value !== null && value > duration.value) errors[field] = 'This requirement cannot exceed the total operation duration.'
  }
  if (utc.value && duration.value !== null && !endWithinBackendRange(utc.value, duration.value)) errors.hours = 'Start plus duration exceeds the backend calendar range (year 9999).'
  const base = { errors, durationSeconds: duration.value, startUtc: utc.value }
  if (Object.keys(errors).length) return { ...base, valid: false, request: null }
  // All required numeric values are present after the error gate above. Fields
  // are built explicitly: raw form state and display-only metadata never leak.
  const request: AnalysisRequestV1 = {
    schema_version: '1.0',
    site: { kind: 'COORDINATES', latitude_deg: latitude!, longitude_deg_east: longitude!, frame: 'MOON_ME_DE421', latitude_type: 'PLANETOCENTRIC' },
    observer: { surface_elevation_mode: 'DEM', solar_height_above_surface_m: solarHeight!, earth_height_above_surface_m: earthHeight! },
    time: { start_utc: utc.value!, duration_s: duration.value! },
    operation: { profile: state.profile, requirements: {
      min_solar_disk_visible_fraction: solarFraction!, earth_clearance_margin_deg: clearance!,
      min_sun_visible_s: minSun, max_dark_gap_s: maxDark, min_earth_continuous_s: minEarth,
      require_simultaneous: state.simultaneous, min_joint_continuous_s: minJoint,
    } },
    options: { include_full_horizon: state.fullHorizon, include_earth_disk_fraction: state.earthDisk, event_lookahead_s: lookahead! },
  }
  return { ...base, valid: true, request }
}
