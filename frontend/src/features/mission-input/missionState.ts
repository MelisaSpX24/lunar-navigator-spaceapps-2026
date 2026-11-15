import type { Profile } from './analysisRequest'

export type MissionFormState = {
  latitude: string; longitude: string; profile: Profile
  utcDate: string; utcTime: string
  hours: string; minutes: string; seconds: string
  solarFraction: string; minSun: string; maxDark: string; minEarth: string
  clearance: string; simultaneous: boolean; minJoint: string
  solarHeight: string; earthHeight: string
  fullHorizon: boolean; earthDisk: boolean; lookahead: string
}
export type FormField = keyof MissionFormState
export type TextFieldName = { [K in FormField]: MissionFormState[K] extends string ? K : never }[FormField]
export type FormErrors = Partial<Record<FormField, string>>

export function initialMissionState(): MissionFormState {
  return {
    latitude: '', longitude: '', profile: 'CUSTOM_OPERATION', utcDate: '', utcTime: '',
    hours: '1', minutes: '0', seconds: '0',
    solarFraction: '0.5', minSun: '', maxDark: '', minEarth: '', clearance: '0', simultaneous: false, minJoint: '',
    solarHeight: '1', earthHeight: '1', fullHorizon: true, earthDisk: true, lookahead: '86400',
  }
}

/** Strict decimal syntax; unlike Number(''), an empty string is never zero. */
export function finiteDecimal(raw: string): number | null {
  if (!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/i.test(raw.trim())) return null
  const value = Number(raw)
  return Number.isFinite(value) ? value : null
}
