import { record } from '../../services/api/responses'
import { checkDecision,checkQuality,checkScore,finite,safeSourceUrl } from '../analysis-results/validation'
import type { Decision,Quality,Score } from '../analysis-results/types'
import { candidateInput,type CandidateInput } from './requests'
import { utcStamp } from '../analysis-results/utc'

export type Dimension='START_UTC_ONLY'|'COORDINATES_AND_DEM_SURFACE_ONLY'
export type Metric={estimated_duration_s:number|null;estimated_longest_continuous_s:number|null;estimated_interruption_s:number|null;estimated_longest_interruption_s:number|null;unknown_duration_s:number|null;duration_lower_bound_s:number|null;duration_upper_bound_s:number|null;duration_evidence_status:string;temporal_resolution_s:number|null;number_of_windows:number|null;number_of_brackets:number|null}
export type Metrics=Record<'sun'|'earth'|'joint',Metric>
export type RuleEvidence={rule:Decision['rules'][number];unit:string;source_metric:string;evidence_status:string;policy:string;reason_codes:string[]}
export type Terrain={surface_elevation_m:number|null;slope_deg:number|null;resolution_m:number[]|null;status:string;raw:Record<string,unknown>}
export type EvidenceCandidate={id:string;scenario:string;dimension:Dimension;input:CandidateInput|null;location:{latitude_deg:number;longitude_deg_east:number}|null;utc:string|null;decision:Decision|null;score:Score|null;quality:Quality|null;metrics:Metrics|null;rules:RuleEvidence[]|null;status:string;distance:number|null;bearing:number|null;terrain:Terrain|null;sourceKey:string|null;sourceIdentity:string|null;scientificKey:string;origin:string|null;hash:string|null;limitations:string[];raw:Record<string,unknown>;comparisonAllowed:boolean}
export type EvidenceView={schema:string;scenario:string;dimension:Dimension;mode:'recorded'|'live';origin:string|null;scientificOrigin:string|null;baseline:EvidenceCandidate;alternatives:EvidenceCandidate[];limitations:string[];provenance:Record<string,unknown>;scope:Record<string,unknown>|null;status:string;raw:Record<string,unknown>}
export const text=(v:unknown):v is string=>typeof v==='string'&&v.trim().length>0
export const strings=(v:unknown):v is string[]=>Array.isArray(v)&&v.every(x=>typeof x==='string')
export const hash=(v:unknown):v is string=>typeof v==='string'&&/^[a-f0-9]{64}$/.test(v)
export const nullableNumber=(v:unknown,min=-Number.MAX_VALUE,max=Number.MAX_VALUE)=>v===null||(finite(v)&&v>=min&&v<=max)
export function stable(v:unknown):string {if(Array.isArray(v))return `[${v.map(stable).join(',')}]`;if(record(v))return `{${Object.keys(v).sort().map(k=>`${JSON.stringify(k)}:${stable(v[k])}`).join(',')}}`;return JSON.stringify(v)??'undefined'}
export function finiteTree(v:unknown,depth=0):boolean {return depth<30&&(typeof v==='number'?finite(v):Array.isArray(v)?v.length<=5000&&v.every(x=>finiteTree(x,depth+1)):record(v)?Object.values(v).every(x=>finiteTree(x,depth+1)):true)}
export function metrics(value:unknown,duration:number):Metrics|null {
 if(!record(value))return null
 for(const body of ['sun','earth','joint']){
  const m=value[body];if(!record(m)||m.duration_evidence_status!=='SAMPLED_ESTIMATE')return null
  for(const key of ['estimated_duration_s','estimated_longest_continuous_s','estimated_interruption_s','estimated_longest_interruption_s','unknown_duration_s','duration_lower_bound_s','duration_upper_bound_s'])if(!nullableNumber(m[key],0,duration))return null
  if(!nullableNumber(m.temporal_resolution_s,0,86400)||!['number_of_windows','number_of_brackets'].every(k=>m[k]===null||(Number.isSafeInteger(m[k])&&(m[k] as number)>=0)))return null
 }
 return value as Metrics
}
export function ruleEvidence(v:unknown):RuleEvidence[]|null {
 if(!Array.isArray(v)||v.length>100)return null
 for(const e of v){if(!record(e)||!text(e.unit)||!text(e.source_metric)||!text(e.evidence_status)||!text(e.policy)||!strings(e.reason_codes)||checkDecision({status:'INCOMPLETE',reason_codes:[],rules:[e.rule]}).kind!=='valid')return null}
 return v as RuleEvidence[]
}
export function terrain(v:unknown):Terrain|null {
 if(!record(v)||!text(v.status)||!nullableNumber(v.surface_elevation_m)||!nullableNumber(v.slope_deg,0,90)||!(v.resolution_m===null||(Array.isArray(v.resolution_m)&&v.resolution_m.length===2&&v.resolution_m.every(n=>finite(n)&&n>0))))return null
 return {surface_elevation_m:v.surface_elevation_m as number|null,slope_deg:v.slope_deg as number|null,resolution_m:v.resolution_m as number[]|null,status:v.status,raw:v}
}
export function coordinate(v:unknown){return record(v)&&v.frame==='MOON_ME_DE421'&&v.latitude_type==='PLANETOCENTRIC'&&finite(v.latitude_deg)&&Math.abs(v.latitude_deg)<90&&finite(v.longitude_deg_east)&&v.longitude_deg_east>=0&&v.longitude_deg_east<360?{latitude_deg:v.latitude_deg,longitude_deg_east:v.longitude_deg_east}:null}
function recordedProvenance(v:unknown):v is Record<string,unknown>{
 if(!record(v)||!hash(v.id)||v.full_source_evidence_sha256!==v.id||v.frame!=='MOON_ME_DE421'||!text(v.absolute_registration)||!Array.isArray(v.kernel_ids)||!v.kernel_ids.every(x=>typeof x==='string'&&/^.+:[a-f0-9]{64}$/.test(x))||!record(v.dem))return false
 return Object.values(v.dem).every(s=>record(s)&&text(s.product)&&hash(s.sha256)&&(s.version===null||text(s.version))&&typeof s.source_url==='string'&&!!safeSourceUrl(s.source_url)&&typeof s.product_specific_frame_verified==='boolean'&&Array.isArray(s.resolution_m)&&s.resolution_m.every(n=>finite(n)&&n>0)&&Array.isArray(s.quality_layers))
}
export function recordedEvidence(value:unknown,kind:'temporal'|'local'):EvidenceView {
 if(!record(value)||!finiteTree(value)||value.schema_version!=='24and28-demo-evidence-v1'||value.science_ready!==false||value.scenario_id!==(kind==='temporal'?'cr1-same-site-better-time':'cr1-same-time-better-site')||value.comparison_dimension!==(kind==='temporal'?'START_UTC_ONLY':'COORDINATES_AND_DEM_SURFACE_ONLY')||!strings(value.limitations)||!record(value.source_reference)||!text(value.source_reference.file)||!hash(value.source_reference.sha256)||!text(value.source_pointer)||!text(value.unavailable_fields_reason)||!recordedProvenance(value.source_provenance)||!record(value.source_optimizer_request)||!record(value.source_optimizer_request.window_template)||!Array.isArray(value.alternatives)||value.alternatives.length>5000)throw Error('Invalid recorded evidence schema or provenance.')
 const scenario=value.scenario_id as string,scientificKey=stable(value.source_optimizer_request),dimension=value.comparison_dimension as Dimension,source=value.source_provenance
 function candidate(v:unknown):EvidenceCandidate{
  if(!record(v)||!text(v.candidate_id)||v.delivery_data_origin!=='RECORDED_EVIDENCE_EXPORT'||v.scientific_data_origin!=='REAL_NASA_PROTOTYPE'||v.scientific_evidence_status!=='SAMPLED_ESTIMATE'||v.evaluation_status!=='DETAILED_EVALUATED'||v.evaluation_policy!=='PROTOTYPE_SAMPLED_ESTIMATE'||v.source_identity!==source.id||!hash(v.window_evidence_sha256)||!strings(v.limitations)||!['analysis_result','horizon_profile','time_series','window_segments'].every(k=>v[k]===null))throw Error('Invalid recorded candidate or unsupported scientific payload.')
  const input=candidateInput(v.source_request,v.explicit_requirement_fields),d=checkDecision(v.decision),s=checkScore(v.planning_score),q=checkQuality(v.data_quality)
  const m=input?metrics(v.metrics,input.request.time.duration_s):null,r=ruleEvidence(v.rule_evidence),t=v.terrain===null?null:terrain(v.terrain)
  if(!input||d.kind!=='valid'||s.kind!=='valid'||q.kind!=='valid'||!m||!r||(v.terrain!==null&&!t)||!nullableNumber(v.distance_m,0,5000+1e-6)||!nullableNumber(v.bearing_deg,0,360)||v.bearing_deg===360||(kind==='local'&&(!finite(v.distance_m)||(v.distance_m>1e-6&&!finite(v.bearing_deg))||!t)))throw Error('Invalid recorded candidate request, metrics, terrain or decision.')
  return {id:v.candidate_id,scenario,dimension,input,location:input.request.site,utc:input.request.time.start_utc,decision:d.value,score:s.value,quality:q.value,metrics:m,rules:r,status:v.evaluation_status,distance:v.distance_m as number|null,bearing:v.bearing_deg as number|null,terrain:t,sourceKey:String(source.id),sourceIdentity:String(source.id),scientificKey,origin:v.delivery_data_origin,hash:v.window_evidence_sha256,limitations:v.limitations,raw:v,comparisonAllowed:true}
 }
 const baseline=candidate(value.baseline), alternatives=value.alternatives.map(candidate),ids=[baseline,...alternatives].map(c=>c.id)
 if(new Set(ids).size!==ids.length||!alternatives.every(c=>comparisonCompatible(baseline,c)))throw Error('Recorded comparison has incompatible scenarios or duplicate IDs.')
 return {schema:String(value.schema_version),scenario,dimension,mode:'recorded',origin:'RECORDED_EVIDENCE_EXPORT',scientificOrigin:'REAL_NASA_PROTOTYPE',baseline,alternatives,limitations:value.limitations,provenance:source,scope:record(value.search_scope)?value.search_scope:null,status:typeof value.search_status==='string'?value.search_status:'RECORDED_SELECTED_EVIDENCE',raw:value}
}
export function comparisonCompatible(a:EvidenceCandidate,b:EvidenceCandidate):boolean {
 if(!a.comparisonAllowed||!b.comparisonAllowed||a.scenario!==b.scenario||a.dimension!==b.dimension||!a.input||!b.input||!a.sourceKey||a.sourceKey!==b.sourceKey||a.scientificKey!==b.scientificKey||!a.score?.model_version||a.score.model_version!==b.score?.model_version)return false
 const left=structuredClone(a.input.request),right=structuredClone(b.input.request)
 if(stable([...a.input.explicit].sort())!==stable([...b.input.explicit].sort()))return false
 if(a.dimension==='START_UTC_ONLY')right.time.start_utc=left.time.start_utc
 else right.site={...left.site}
 return stable(left)===stable(right)
}
export const delta=(a:number|null|undefined,b:number|null|undefined)=>finite(a)&&finite(b)?b-a:null
export function radarPoint(distance:number,bearing:number,radius=5000){if(!finite(distance)||distance<0||distance>radius+1e-6||!finite(bearing)||bearing<0||bearing>=360)return null;const angle=bearing*Math.PI/180;return {x:distance*Math.sin(angle)/radius*200,y:-distance*Math.cos(angle)/radius*200}}
export function utcShift(a:EvidenceCandidate,b:EvidenceCandidate){const x=utcStamp(a.utc),y=utcStamp(b.utc);return x&&y?Number(y.tick-x.tick)/1e6:null}
