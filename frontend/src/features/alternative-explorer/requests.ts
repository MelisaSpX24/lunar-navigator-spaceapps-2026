import { record } from '../../services/api/responses'
import { normalizeRequest, normalizedRequestMatches } from '../../services/api/normalizedRequest'
import { initialMissionState, type MissionFormState } from '../mission-input/missionState'
import { buildAnalysisRequest } from '../mission-input/buildAnalysisRequest'
import type { AnalysisInputV1, AnalysisRequestV1 } from '../mission-input/analysisRequest'
import { utcStamp } from '../analysis-results/utc'

const keys=(v:Record<string,unknown>,allowed:string[])=>Object.keys(v).every(k=>allowed.includes(k))
export const requirementNames=['min_solar_disk_visible_fraction','min_sun_visible_s','max_dark_gap_s','min_earth_continuous_s','earth_clearance_margin_deg','require_simultaneous','min_joint_continuous_s'] as const
const formRequirements={min_solar_disk_visible_fraction:'solarFraction',min_sun_visible_s:'minSun',max_dark_gap_s:'maxDark',min_earth_continuous_s:'minEarth',earth_clearance_margin_deg:'clearance',require_simultaneous:'simultaneous',min_joint_continuous_s:'minJoint'} as const
export type CandidateInput={form:MissionFormState;request:AnalysisRequestV1;source:AnalysisInputV1;explicit:string[]}
/** Backend defaults are expanded for display only; wire rule key-presence survives. */
export function candidateInput(value:unknown,explicit:unknown):CandidateInput|null {
  if(!record(value)||!keys(value,['schema_version','site','observer','time','operation','options']))return null
  const n=normalizeRequest(value)
  if(!record(n)||n.schema_version!=='1.0'||!record(n.site)||!record(n.time)||!record(n.observer)||!record(n.options)||!record(n.operation)||!record(n.operation.requirements)||!record(value.operation)||!record(value.operation.requirements))return null
  if(!keys(n.site,['kind','latitude_deg','longitude_deg_east','frame','latitude_type'])||n.site.kind!=='COORDINATES'||n.site.frame!=='MOON_ME_DE421'||n.site.latitude_type!=='PLANETOCENTRIC'||!keys(n.time,['start_utc','duration_s'])||!keys(n.observer,['surface_elevation_mode','solar_height_above_surface_m','earth_height_above_surface_m'])||n.observer.surface_elevation_mode!=='DEM'||!keys(n.options,['include_full_horizon','include_earth_disk_fraction','event_lookahead_s'])||!keys(n.operation,['profile','requirements'])||!keys(n.operation.requirements,[...requirementNames]))return null
  if(!Array.isArray(explicit)||!explicit.every(v=>typeof v==='string'&&requirementNames.includes(v as typeof requirementNames[number]))||new Set(explicit).size!==explicit.length||JSON.stringify([...explicit].sort())!==JSON.stringify(Object.keys(value.operation.requirements).sort()))return null
  const stamp=utcStamp(n.time.start_utc), duration=n.time.duration_s
  if(!stamp||stamp.tick%1_000_000n!==0n||typeof duration!=='number'||!Number.isSafeInteger(duration)||duration<=0)return null
  const iso=new Date(Number(stamp.tick/1000n)).toISOString()
  const f=initialMissionState()
  f.latitude=String(n.site.latitude_deg);f.longitude=String(n.site.longitude_deg_east)
  f.utcDate=iso.slice(0,10);f.utcTime=iso.slice(11,19);f.hours=String(Math.floor(duration/3600));f.minutes=String(Math.floor(duration%3600/60));f.seconds=String(duration%60)
  f.profile=n.operation.profile as MissionFormState['profile']
  for(const [key,field] of Object.entries(formRequirements)){
    const v=n.operation.requirements[key]
    if(field==='simultaneous'){if(typeof v!=='boolean')return null;f.simultaneous=v}
    else {if(v!==null&&(typeof v!=='number'||!Number.isFinite(v)))return null;f[field]=v===null?'':String(v)}
  }
  f.solarHeight=String(n.observer.solar_height_above_surface_m);f.earthHeight=String(n.observer.earth_height_above_surface_m)
  if(typeof n.options.include_full_horizon!=='boolean'||typeof n.options.include_earth_disk_fraction!=='boolean')return null
  f.fullHorizon=n.options.include_full_horizon;f.earthDisk=n.options.include_earth_disk_fraction;f.lookahead=String(n.options.event_lookahead_s)
  const built=buildAnalysisRequest(f).request
  if(!built||!normalizedRequestMatches(built,n))return null
  const requirements=Object.fromEntries(explicit.map(k=>[k,built.operation.requirements[k as keyof typeof built.operation.requirements]]))
  return {form:f,request:built,explicit:[...explicit],source:{...built,operation:{...built.operation,requirements}}}
}
