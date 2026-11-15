import { record } from './responses'
import { requestMatches } from '../../features/analysis-results/requestMatch'
import type { AnalysisRequestV1 } from '../../features/mission-input/analysisRequest'

/** Expand only documented Pydantic defaults. Never remove unknown keys, replace
 * explicit null/0/false or infer rule activation. The submitted request is retained
 * separately, including its original explicit requirement keys. */
export function normalizeRequest(value: unknown): unknown {
  if(!record(value))return value
  const v=structuredClone(value)
  const defaults: Record<string,Record<string,unknown>>={
    site:{frame:'MOON_ME_DE421',latitude_type:'PLANETOCENTRIC'},
    observer:{surface_elevation_mode:'DEM',solar_height_above_surface_m:1,earth_height_above_surface_m:1},
    options:{include_full_horizon:true,include_earth_disk_fraction:true,event_lookahead_s:86400},
  }
  if(!Object.hasOwn(v,'schema_version'))v.schema_version='1.0'
  for(const [key,d] of Object.entries(defaults)){
    if(!Object.hasOwn(v,key)&&key!=='site')v[key]={...d}
    else if(record(v[key]))v[key]={...d,...v[key]}
  }
  if(record(v.operation)&&record(v.operation.requirements))v.operation={...v.operation,requirements:{
    min_solar_disk_visible_fraction:0.5,min_sun_visible_s:null,max_dark_gap_s:null,min_earth_continuous_s:null,
    earth_clearance_margin_deg:0,require_simultaneous:false,min_joint_continuous_s:null,...v.operation.requirements,
  }}
  return v
}
export function normalizedRequestMatches(expected: AnalysisRequestV1, echoed: unknown): boolean {
  return requestMatches(expected,normalizeRequest(echoed))
}
