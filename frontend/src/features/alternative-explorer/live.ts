import { record } from '../../services/api/responses'
import { checkDecision,checkQuality,checkScore,finite } from '../analysis-results/validation'
import { completedPrototypeResult } from '../analysis-results/resultContext'
import { normalizedRequestMatches } from '../../services/api/normalizedRequest'
import { resourcePolicy,type ResultEnvelope } from '../../services/api/jobs'
import type { ResearchState } from '../scientific-jobs/useScientificJob'
import type { AnalysisRequestV1 } from '../mission-input/analysisRequest'
import { candidateInput,type CandidateInput } from './requests'
import { stable,finiteTree,text,strings,hash,coordinate,terrain,metrics,ruleEvidence,comparisonCompatible,type EvidenceCandidate,type EvidenceView,type Dimension } from './evidence'
import { utcStamp } from '../analysis-results/utc'

export type OptimizerKind='TEMPORAL'|'LOCAL'
export type OptimizerSettings={days:number;budget:number;radius:number;strategy:'SLOPE_ONLY'|'TERRAIN_DIVERSE';temporalStrategy:'LEGACY'|'COVERAGE_AWARE';wall:number}
export const defaultOptimizerSettings:OptimizerSettings={days:7,budget:4,radius:5000,strategy:'TERRAIN_DIVERSE',temporalStrategy:'COVERAGE_AWARE',wall:900}
/** Verify the consumed window-template fields against the actual submitted analysis.
 * Preserve the complete server template, including backend-owned sampling/limits. */
export function validWindowTemplate(v:unknown,a:AnalysisRequestV1):v is Record<string,unknown> {
 if(!record(v)||!finiteTree(v)||!record(v.visibility)||!record(v.visibility.terrain)||!record(v.visibility.terrain.location)||!record(v.visibility.terrain.policy))return false
 const vis=v.visibility,terrain=vis.terrain as Record<string,unknown>,loc=terrain.location,policy=terrain.policy as Record<string,unknown>
 const start=utcStamp(v.start_utc),utc=utcStamp(vis.utc),expected=utcStamp(a.time.start_utc)
 return !!start&&!!utc&&!!expected&&start.tick===expected.tick&&utc.tick===expected.tick&&v.duration_s===a.time.duration_s
  &&stable(loc)===stable({latitude_deg:a.site.latitude_deg,longitude_deg_east:a.site.longitude_deg_east,frame:a.site.frame,latitude_type:a.site.latitude_type})
  &&vis.solar_height_above_surface_m===a.observer.solar_height_above_surface_m&&vis.earth_height_above_surface_m===a.observer.earth_height_above_surface_m
  &&v.solar_fraction===a.operation.requirements.min_solar_disk_visible_fraction&&v.earth_margin_deg===a.operation.requirements.earth_clearance_margin_deg
  &&typeof v.joint==='boolean'&&(!a.operation.requirements.require_simultaneous||v.joint)&&typeof vis.correction==='string'&&['NONE','LT+S'].includes(vis.correction)
  &&finite(vis.disk_samples)&&[64,256].includes(vis.disk_samples)&&typeof policy.registration==='string'&&['PROTOTYPE','STRICT'].includes(policy.registration)&&policy.enable_lroc===false
  &&finite(v.step_s)&&v.step_s>=1&&v.step_s<=86400&&finite(terrain.max_range_m)&&terrain.max_range_m>0
}
export function optimizerPrerequisite(job:ResearchState,current:AnalysisRequestV1|null){
 const result=completedPrototypeResult(job,current)
 if(!result||job.mode!=='live'||job.status?.status!=='COMPLETED'||!job.envelope||!job.submitted)return null
 const window=job.envelope.result.window_evidence
 if(!record(window)||!validWindowTemplate(window.request,result.request))return null
 return {analysis:job.submitted,request:result.request,window:structuredClone(window.request)}
}
export function optimizerPayload(kind:OptimizerKind,prerequisite:NonNullable<ReturnType<typeof optimizerPrerequisite>>,s:OptimizerSettings):Record<string,unknown>|null {
 if(!Number.isSafeInteger(s.budget)||s.budget<1||s.budget>31||!finite(s.wall)||s.wall<=0||s.wall>3600)return null
 const base={baseline_analysis:prerequisite.analysis,window_template:prerequisite.window,evaluation_policy:'PROTOTYPE_SAMPLED_ESTIMATE'}
 const resources={...resourcePolicy,max_wall_time_s:s.wall}
 if(kind==='LOCAL'){
  if(![1000,3000,5000].includes(s.radius)||!['SLOPE_ONLY','TERRAIN_DIVERSE'].includes(s.strategy))return null
  return {optimization:{...base,search_radius_m:s.radius,coarse_step_m:500,refinement_step_m:100,max_generated_candidates:32,max_detailed_candidates:Math.min(s.budget,8),max_recommendations:3,max_slope_deg:10,selection_strategy:s.strategy},resources}
 }
 if(!Number.isSafeInteger(s.days)||s.days<1||s.days>31||!['LEGACY','COVERAGE_AWARE'].includes(s.temporalStrategy))return null
 const end=new Date(Date.parse(prerequisite.request.time.start_utc)+s.days*86400000)
 if(!Number.isFinite(end.getTime())||end.getUTCFullYear()>9999||s.days*86400<prerequisite.request.time.duration_s)return null
 return {optimization:{...base,search_start_utc:prerequisite.request.time.start_utc,search_end_utc:end.toISOString(),coarse_start_step_s:21600,refinement_step_s:3600,max_coarse_candidates:64,max_detailed_candidates:Math.min(s.budget,8),max_recommendations:3,selection_strategy:s.temporalStrategy},max_candidate_evaluations:s.budget,screening_strategy:'EXACT_ONLY',resources}
}
function scientificWindowKey(value:unknown,dimension:Dimension):string|null {
 if(!record(value)||!record(value.visibility)||!record(value.visibility.terrain))return null
 const v=structuredClone(value);delete v.start_utc
 const visibility=v.visibility as Record<string,unknown>;delete visibility.utc
 if(dimension==='COORDINATES_AND_DEM_SURFACE_ONLY')delete (visibility.terrain as Record<string,unknown>).location
 return stable(v)
}
/** Public optimizer results are distinct from recorded projections and AnalysisResult. */
export function liveEvidence(envelope:ResultEnvelope,payload:Record<string,unknown>):EvidenceView {
 const kind=envelope.job_type;if(kind!=='TEMPORAL'&&kind!=='LOCAL')throw Error('Wrong optimizer job type.')
 if(!['COMPLETED','PARTIAL'].includes(envelope.status))throw Error('No usable terminal optimizer evidence.')
 const v=envelope.result, expectedSchema=kind==='TEMPORAL'?'command-10-temporal-batch-v2':'command-10-local-v1'
 if(!finiteTree(v)||v.schema_version!==expectedSchema||v.science_ready!==false||!record(v.request)||!record(payload.optimization)||!Array.isArray(v.candidates)||!Array.isArray(v.recommendations)||!Array.isArray(v.comparisons)||!strings(v.limitations)||!text(v.search_status)||!(v.data_origin===null||(typeof v.data_origin==='string'&&['LIVE_COMPUTED','PRECOMPUTED'].includes(v.data_origin))))throw Error('Invalid optimizer schema, status or provenance.')
 const submitted=payload.optimization,baselineRaw=submitted.baseline_analysis
 if(!record(baselineRaw)||!record(baselineRaw.operation)||!record(baselineRaw.operation.requirements))throw Error('Missing submitted baseline identity.')
 const explicit=Object.keys(baselineRaw.operation.requirements),baselineInput=candidateInput(baselineRaw,explicit)
 if(!baselineInput||!normalizedRequestMatches(baselineInput.request,v.request.baseline_analysis))throw Error('Optimizer baseline does not match the submitted scenario.')
 // Only documented optimizer defaults may be expanded by Pydantic; never remove unknown keys.
 const defaults=kind==='TEMPORAL'?{selection_strategy:'LEGACY',coarse_start_step_s:21600,refinement_step_s:3600,max_coarse_candidates:64,max_detailed_candidates:3,max_recommendations:3,max_window_evaluations:24,max_new_horizon_rays:4000,max_terrain_samples:3000000,max_wall_time_s:1200,max_cache_entries:2048,resolved_site:null,resolved_site_id:null}:{evaluation_policy:'STRICT_EVIDENCE',selection_strategy:'SLOPE_ONLY',search_radius_m:5000,coarse_step_m:500,refinement_step_m:100,max_generated_candidates:32,max_detailed_candidates:2,max_recommendations:3,max_slope_deg:10}
 const wanted={...defaults,...submitted,baseline_analysis:baselineInput.request}, echoed={...v.request,baseline_analysis:baselineInput.request}
 // UTC strings may use equivalent zero-offset spellings.
 function canonical(x:unknown):unknown{if(typeof x==='string'&&utcStamp(x))return `UTC:${utcStamp(x)!.tick}`;if(Array.isArray(x))return x.map(canonical);if(record(x))return Object.fromEntries(Object.entries(x).map(([k,z])=>[k,canonical(z)]));return x}
 if(stable(canonical(wanted))!==stable(canonical(echoed)))throw Error('Optimizer scientific settings or search request mismatch.')
 const dimension:Dimension=kind==='TEMPORAL'?'START_UTC_ONLY':'COORDINATES_AND_DEM_SURFACE_ONLY',scenario=`${envelope.job_id}:${kind}`
 const origin=v.data_origin as string|null
 function candidate(raw:unknown):EvidenceCandidate{
  if(!record(raw)||!text(raw.candidate_id)||!strings(raw.reason_codes))throw Error('Invalid optimizer candidate.')
  const op=raw.operation,stage=kind==='TEMPORAL'?raw.evaluation_status:raw.stage
  const localStage=kind==='LOCAL'&&['ELIGIBLE_FOR_DETAIL','SLOPE_UNKNOWN','SCIENTIFICALLY_INCOMPLETE'].includes(stage as string)
  if(!text(stage)||!localStage&&!['DISCOVERED','DETAILED_EVALUATED','PARTIAL','NOT_SELECTED_FOR_DETAILED_EVALUATION','NOT_EVALUATED_RESOURCE_LIMIT','INVALID','SCREENED_OUT_TERRAIN','GENERATED','TERRAIN_ELIGIBLE'].includes(stage))throw Error('Unsupported candidate evaluation stage.')
  const location=kind==='LOCAL'?coordinate(raw.location):baselineInput!.request.site
  if(!location||!nullableFinite(raw.distance_m,kind==='LOCAL')||!(raw.bearing_deg===null||raw.bearing_deg===undefined||(finite(raw.bearing_deg)&&raw.bearing_deg>=0&&raw.bearing_deg<360)))throw Error('Invalid local distance, bearing or coordinate.')
  if(kind==='LOCAL'&&(raw.distance_m as number)>(submitted.search_radius_m as number)+1e-6)throw Error('Candidate outside submitted search radius.')
  const t=record(raw.terrain)&&Object.keys(raw.terrain).length?terrain(kind==='LOCAL'?{surface_elevation_m:null,resolution_m:null,...raw.terrain}:raw.terrain):null
  let input:CandidateInput|null=null,d:EvidenceCandidate['decision']=null,score:EvidenceCandidate['score']=null,q:EvidenceCandidate['quality']=null,r:EvidenceCandidate['rules']=null,m:EvidenceCandidate['metrics']=null,sourceKey:string|null=null,scientificKey='',evidenceHash:string|null=null,limitations:string[]=[]
  if(op!==null&&!record(op))throw Error('Invalid candidate operation evidence.')
  // A partial local window can retain operation diagnostics, including a stale
  // score. Only detailed candidates may project completed scientific results.
  if(op!==null&&(kind!=='LOCAL'||stage==='DETAILED_EVALUATED')){
   if(!record(op)||op.schema_version!=='command-08-v1'||op.execution_status!=='COMPLETED'||op.science_ready!==false||!record(op.request)||!record(op.request.analysis)||!record(op.request.analysis.operation)||!record(op.request.analysis.operation.requirements)||!record(op.provenance)||!record(op.provenance.sources)||!strings(op.limitations)||!hash(op.request.window_evidence_sha256))throw Error('Invalid candidate operation evidence.')
   const a=structuredClone(op.request.analysis),operation=a.operation as Record<string,unknown>;a.operation={...operation,requirements:Object.fromEntries(explicit.map(k=>[k,(operation.requirements as Record<string,unknown>)[k]]))}
   input=candidateInput(a,explicit);const decision=checkDecision(op.decision),s=checkScore(op.score),quality=checkQuality(op.quality)
   if(!input||decision.kind!=='valid'||s.kind!=='valid'||quality.kind!=='valid'||!(r=ruleEvidence(op.rule_evidence)))throw Error('Invalid candidate decision, request or quality.')
   const expected=structuredClone(baselineInput!.request);if(kind==='LOCAL')expected.site={...expected.site,...location};else {if(!utcStamp(raw.start_utc))throw Error('Invalid candidate UTC');expected.time.start_utc=String(raw.start_utc)}
   if(!normalizedRequestMatches(expected,op.request.analysis))throw Error('Candidate modifies unrelated scenario fields.')
   const start=utcStamp(input.request.time.start_utc)!
   if(kind==='TEMPORAL'){const end=utcStamp(raw.end_utc),rangeStart=utcStamp(submitted.search_start_utc),rangeEnd=utcStamp(submitted.search_end_utc);if(!end||!rangeStart||!rangeEnd||end.tick-start.tick!==BigInt(input.request.time.duration_s)*1_000_000n||start.tick<rangeStart.tick||end.tick>rangeEnd.tick)throw Error('Candidate outside temporal search interval.')}
   const mk=metrics(raw.metrics,input.request.time.duration_s);if(!mk)throw Error('Invalid evaluated candidate metrics.')
   d=decision.value;score=s.value;q=quality.value;m=mk;sourceKey=stable(op.provenance.sources);scientificKey=scientificWindowKey(op.provenance.window_request,dimension)??'';evidenceHash=op.request.window_evidence_sha256;limitations=op.limitations
   if(!scientificKey)throw Error('Candidate window configuration unavailable.')
  }
  return {id:raw.candidate_id,scenario,dimension,input,location,utc:input?.request.time.start_utc??(kind==='TEMPORAL'&&utcStamp(raw.start_utc)?String(raw.start_utc):baselineInput!.request.time.start_utc),decision:d,score,quality:q,metrics:m,rules:r,status:stage,distance:kind==='LOCAL'?raw.distance_m as number:null,bearing:finite(raw.bearing_deg)?raw.bearing_deg:null,terrain:t,sourceKey,sourceIdentity:null,scientificKey,origin:typeof raw.evidence_mode==='string'?raw.evidence_mode:origin,hash:evidenceHash,limitations,raw,comparisonAllowed:stage==='DETAILED_EVALUATED'&&!!input}
 }
 const baseline=candidate(v.baseline),candidates=v.candidates.map(candidate),ids=[baseline,...candidates].map(c=>c.id)
 // Some backends retain baseline in candidates; identical entries are allowed, conflicting identities are not.
 const seen=new Map<string,EvidenceCandidate>();for(const c of [baseline,...candidates]){const old=seen.get(c.id);if(old&&stable(old.raw)!==stable(c.raw))throw Error('Conflicting candidate IDs.');seen.set(c.id,c)}
 for(const rec of v.recommendations){
  if(!record(rec)||!text(rec.candidate_id)||!seen.has(rec.candidate_id))throw Error('Unknown recommended candidate.')
  const c=seen.get(rec.candidate_id)!
  if(kind==='LOCAL'&&(!c.comparisonAllowed||c.decision?.status!=='MET'))throw Error('Local recommendation lacks completed MET evidence.')
 }
 const validities=new Map<string,string>()
 for(const c of v.comparisons){if(!record(c)||!text(c.candidate_id)||!seen.has(c.candidate_id))throw Error('Invalid candidate comparison reference.');const validity=kind==='TEMPORAL'?c.validity:c.comparison_validity;if(typeof validity!=='string')throw Error('Missing comparison validity.');validities.set(c.candidate_id,validity)}
 const alternatives=[...seen.values()].filter(c=>c.id!==baseline.id).map(c=>({...c,comparisonAllowed:c.comparisonAllowed&&['EQUIVALENT_METHOD','SAME_SOURCES'].includes(validities.get(c.id)??'')}))
 const scope=kind==='LOCAL'?v.scope:v.discovery
 if(kind==='LOCAL'&&(!record(v.scope)||!record(v.resource_consumption)))throw Error('Missing local scope/resources.')
 if(kind==='TEMPORAL'&&(!record(v.resources)||!record(v.scientific_window_template)||!['generated_alternatives','detailed_evaluated_including_baseline','scientifically_incomplete_including_baseline','not_evaluated_alternatives','detailed_completed_including_baseline'].every(k=>Number.isSafeInteger(v[k])&&(v[k] as number)>=0)))throw Error('Invalid temporal counters/resources.')
 if(kind==='TEMPORAL'&&finite(payload.max_candidate_evaluations)&&(v.detailed_evaluated_including_baseline as number)>payload.max_candidate_evaluations)throw Error('Detailed evaluation count exceeds submitted admission budget.')
 if(kind==='LOCAL'&&finite(submitted.max_detailed_candidates)&&finite((v.scope as Record<string,unknown>).detailed_attempts_including_baseline)&&((v.scope as Record<string,number>).detailed_attempts_including_baseline!>submitted.max_detailed_candidates))throw Error('Local evaluation count exceeds submitted budget.')
 if(new Set(ids).size>5000)throw Error('Candidate display limit exceeded; no silent sampling.')
 return {schema:expectedSchema,scenario,dimension,mode:'live',origin,scientificOrigin:record(baseline.raw.operation)&&typeof baseline.raw.operation.data_origin==='string'?baseline.raw.operation.data_origin:null,baseline,alternatives,limitations:v.limitations,provenance:record(baseline.raw.operation)&&record(baseline.raw.operation.provenance)?baseline.raw.operation.provenance:{},scope:record(scope)?scope:null,status:envelope.status==='PARTIAL'?'PARTIAL':String(v.search_status),raw:v}
}
function nullableFinite(value:unknown,required:boolean){return !required&&value===undefined||finite(value)&&value>=0}
export function comparableLive(a:EvidenceCandidate,b:EvidenceCandidate){return comparisonCompatible(a,b)}
