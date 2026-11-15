/** Coordinate-only subset of backend/app/models/analysis.py, AnalysisRequest 1.0.
 * Backend-local draft, not an independently approved shared contract.
 */
export const PROFILES = [
  { value: 'SOLAR_POWERED_EXPERIMENT', label: 'Solar-Powered Experiment', description: 'Prepare inputs for a solar-dependent experiment.' },
  { value: 'EARTH_DATA_TRANSMISSION', label: 'Earth Data Transmission', description: 'Prepare inputs for an Earth-facing transmission operation.' },
  { value: 'SHORT_SURFACE_OBSERVATION', label: 'Short Surface Observation', description: 'Prepare inputs for a bounded surface observation.' },
  { value: 'CUSTOM_OPERATION', label: 'Custom Operation', description: 'Specify your own operation requirements.' },
] as const
export type Profile = typeof PROFILES[number]['value']

export type AnalysisRequestV1 = {
  schema_version: '1.0'
  site: { kind: 'COORDINATES'; latitude_deg: number; longitude_deg_east: number; frame: 'MOON_ME_DE421'; latitude_type: 'PLANETOCENTRIC' }
  observer: { surface_elevation_mode: 'DEM'; solar_height_above_surface_m: number; earth_height_above_surface_m: number }
  time: { start_utc: string; duration_s: number }
  operation: { profile: Profile; requirements: {
    min_solar_disk_visible_fraction: number
    min_sun_visible_s: number | null
    max_dark_gap_s: number | null
    min_earth_continuous_s: number | null
    earth_clearance_margin_deg: number
    require_simultaneous: boolean
    min_joint_continuous_s: number | null
  } }
  options: { include_full_horizon: boolean; include_earth_disk_fraction: boolean; event_lookahead_s: number }
}

/** Wire request preserves Pydantic fields_set: omitted requirements are inactive. */
export type AnalysisInputV1 = Omit<AnalysisRequestV1,'operation'> & { operation: {
  profile: Profile; requirements: Partial<AnalysisRequestV1['operation']['requirements']>
} }
