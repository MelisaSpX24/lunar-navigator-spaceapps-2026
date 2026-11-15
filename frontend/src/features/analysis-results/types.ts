import type { Stamp } from './utc'

/** Displayed subset of backend-local AnalysisResult 1.0, not a shared contract. */
export type Checked<T> = { kind: 'valid'; value: T } | { kind: 'missing' } | { kind: 'invalid'; message: string } | { kind: 'limited'; message: string }
export type BodySample = {
  azimuth_deg: number | null; elevation_deg: number | null; angular_radius_deg: number | null
  horizon_id: string | null; center_clearance_deg: number | null; disk_visible_fraction: number | null
  disk_state: 'FULL' | 'PARTIAL' | 'NONE' | 'UNKNOWN'; condition_met: boolean | null
}
export type BodyRow = { time: Stamp; body: BodySample }
export type HorizonProfile = { id: string; observer_height_m: number; range_m: number; coverage_complete: boolean; dem_source_ids: string[]; points: { azimuth_deg: number; elevation_deg: number | null }[] }
export type VisibilityWindow = { start: Stamp; end: Stamp; definition_id: string; start_censored: boolean; end_censored: boolean }
export type Rule = { code: string; status: 'MET' | 'NOT_MET' | 'INCOMPLETE'; required: number | boolean | null; actual: number | boolean | null; message: string }
export type Decision = { status: Rule['status']; rules: Rule[]; reason_codes: string[] }
export type Score = { value: number | null; model_version: string | null; components: { name: string; raw_value: number; normalized_value: number; weight: number }[] | null }
export type Quality = { status: 'NOT_ASSESSED' | 'SUFFICIENT' | 'LIMITED' | 'INSUFFICIENT'; coverage_complete: boolean | null; limitations: string[] }
export type Source = { id: string; kind: 'DEM' | 'SPK' | 'PCK' | 'FK' | 'LSK' | 'REFERENCE'; product: string; version: string; url: string; sha256: string }
export type ResolvedSite = { latitude_deg: number; longitude_deg_east: number; frame: 'MOON_ME_DE421'; latitude_type: 'PLANETOCENTRIC'; surface_elevation_m: number | null; height_datum_id: string | null }
