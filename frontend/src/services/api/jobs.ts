/** Backend-local PR #28 contract. All network values remain unknown until checked. */
import { record, isAnalysis, isValidation, type AnalysisResponse, type ValidationIssue } from './responses'
import type { AnalysisRequestV1, AnalysisInputV1 } from '../../features/mission-input/analysisRequest'
import { utcStamp } from '../../features/analysis-results/utc'
import { normalizedRequestMatches } from './normalizedRequest'

export type JobType='ANALYSIS'|'TEMPORAL'|'LOCAL'
export const JOB_STATES = ['QUEUED','RUNNING','COMPLETED','PARTIAL','FAILED','CANCEL_REQUESTED','CANCELLED','INTERRUPTED'] as const
export type JobState = typeof JOB_STATES[number]
export const terminal = (state: JobState) => ['COMPLETED','PARTIAL','FAILED','CANCELLED','INTERRUPTED'].includes(state)
const text = (v: unknown): v is string => typeof v === 'string' && v.trim().length > 0
const strings = (v: unknown): v is string[] => Array.isArray(v) && v.every(text)
const count = (v: unknown): v is number => typeof v === 'number' && Number.isSafeInteger(v) && v >= 0
const id = (v: unknown): v is string => typeof v === 'string' && /^[a-f0-9]{32}$/.test(v)
const identity = (v: unknown): v is string => typeof v === 'string' && /^[a-f0-9]{64}$/.test(v)
const state = (v: unknown): v is JobState => typeof v === 'string' && (JOB_STATES as readonly string[]).includes(v)
export type Capabilities = {
  api_reachable: boolean; scientific_job_runner_available: boolean; configured_science_files_available: boolean
  bounded_live_prototype_supported: boolean; recorded_prototype_supported: boolean
  fully_independently_validated_science_ready: boolean; science_ready: boolean
  job_types: ('ANALYSIS'|'TEMPORAL'|'LOCAL')[]; worker_count: number; limits: Record<string, number>; reason_codes: string[]
}
export function isCapabilities(v: unknown): v is Capabilities {
  return record(v) && (v.schema_version===undefined||v.schema_version==='1.0') && ['api_reachable','scientific_job_runner_available','configured_science_files_available','bounded_live_prototype_supported','recorded_prototype_supported','fully_independently_validated_science_ready','science_ready'].every(k => typeof v[k] === 'boolean')
    && Array.isArray(v.job_types) && v.job_types.every(k => ['ANALYSIS','TEMPORAL','LOCAL'].includes(k)) && count(v.worker_count)
    && record(v.limits) && ['active_jobs','max_output_bytes','max_wall_time_s','max_local_radius_m'].every(k => count((v.limits as Record<string,unknown>)[k])) && strings(v.reason_codes)
}
export type Accepted = { job_id: string; job_type: JobType; status: JobState; submitted_at_utc: string; request_identity: string
  status_url: string; result_url: string; cancellation_url: string; scientific_mode: 'LIVE_PROTOTYPE'; resource_policy: Record<string,number> }
export const resourcePolicy = { max_wall_time_s: 900, max_visibility_evaluations: 24, max_horizon_rays: 5000, max_terrain_samples: 3000000, max_cache_entries: 2048 } as const
export function jobRequest(analysis: AnalysisInputV1, resume_from?: string) {
  return { analysis, evaluation_policy: 'PROTOTYPE_SAMPLED_ESTIMATE' as const, registration: 'PROTOTYPE' as const, step_s: 3600, disk_samples: 64, resources: resourcePolicy, ...(resume_from ? { resume_from } : {}) }
}
/** Deliberately exact canonical server paths. Never fetch an arbitrary returned URL. */
export function safeJobUrl(value: unknown, job: string, suffix = '') { return id(job) && value === `/api/v1/jobs/${job}${suffix}` }
export function isAccepted(v: unknown, expectedType:JobType='ANALYSIS'): v is Accepted {
  return record(v) && id(v.job_id) && v.job_type === expectedType && v.status === 'QUEUED' && !!utcStamp(v.submitted_at_utc)
    && identity(v.request_identity) && v.scientific_mode === 'LIVE_PROTOTYPE' && record(v.resource_policy)
    && Object.entries(resourcePolicy).every(([k,max]) => typeof (v.resource_policy as Record<string,unknown>)[k] === 'number' && Number.isFinite((v.resource_policy as Record<string,number>)[k]) && ((v.resource_policy as Record<string,number>)[k] as number) > 0 && ((v.resource_policy as Record<string,number>)[k] as number) <= max)
    && safeJobUrl(v.status_url,v.job_id) && safeJobUrl(v.result_url,v.job_id,'/result') && safeJobUrl(v.cancellation_url,v.job_id,'/cancel')
}
export type JobStatus = { job_id: string; job_type: JobType; status: JobState; request_identity: string
  created_at_utc: string; updated_at_utc: string; started_at_utc: string|null; finished_at_utc: string|null
  progress: { stage: string; progress_percent: number|null; completed_candidates: number; total_candidates: number|null; completed_visibility_evaluations: number }
  reason_codes: string[]; limitations: string[]; result_available: boolean; error: {code:string;error_class:string;message:string}|null }
export function isJobStatus(v: unknown, job: string, requestIdentity: string, expectedType:JobType='ANALYSIS'): v is JobStatus {
  if (!record(v) || v.job_id !== job || !id(job) || v.job_type !== expectedType || !state(v.status) || v.request_identity !== requestIdentity || !identity(requestIdentity)) return false
  const p=v.progress
  return !!utcStamp(v.created_at_utc) && !!utcStamp(v.updated_at_utc) && [v.started_at_utc,v.finished_at_utc].every(t=>t===null||!!utcStamp(t))
    && record(p) && text(p.stage) && (p.progress_percent===null || (typeof p.progress_percent==='number'&&Number.isFinite(p.progress_percent)&&p.progress_percent>=0&&p.progress_percent<=100))
    && count(p.completed_candidates) && (p.total_candidates===null||count(p.total_candidates)) && count(p.completed_visibility_evaluations)
    && strings(v.reason_codes) && strings(v.limitations) && typeof v.result_available==='boolean'
    && (v.error===null || (record(v.error)&&text(v.error.code)&&text(v.error.error_class)&&text(v.error.message)))
}
export type ResultEnvelope = {job_id:string; job_type:JobType; status:JobState; result:Record<string,unknown>}
export function isJobResult(v: unknown, job: string, status: JobState, expectedType:JobType='ANALYSIS'): v is ResultEnvelope {
  return record(v)&&id(job)&&v.job_id===job&&v.job_type===expectedType&&v.status===status&&terminal(status)&&record(v.result)
}
export function completedAnalysis(envelope: ResultEnvelope, request: AnalysisRequestV1): AnalysisResponse|null {
  const a=envelope.result.analysis
  return envelope.job_type==='ANALYSIS'&&envelope.status==='COMPLETED'&&isAnalysis(a)&&a.execution_status==='COMPLETED'&&normalizedRequestMatches(request,a.request) ? a : null
}
export type ApiFailure = {ok:false; kind:'network'|'aborted'|'http'|'invalid'; status:number|null; message:string; issues?:ValidationIssue[]}
export type ApiValue<T> = {ok:true; status:number; data:T}|ApiFailure
export async function jobFetch(path: string, signal: AbortSignal, body?: unknown, post=false): Promise<ApiValue<unknown>> {
  const base=(import.meta.env.VITE_API_BASE_URL||'/api/v1').trim().replace(/\/+$/,'')
  if (!/^\/(?!\/)[^?#\\]*$/.test(base)&&!/^https?:\/\/[^\s?#\\]+$/i.test(base)) return {ok:false,kind:'invalid',status:null,message:'Invalid API base configuration.'}
  let response:Response
  try { response=await fetch(`${base}/${path}`,{method:post?'POST':'GET',signal,headers:{Accept:'application/json',...(post?{'Content-Type':'application/json'}:{})},...(body!==undefined?{body:JSON.stringify(body)}:{})}) }
  catch {return {ok:false,kind:signal.aborted?'aborted':'network',status:null,message:'Connection lost. The calculation may still be running.'}}
  let data:unknown
  try {data=await response.json()} catch {return {ok:false,kind:signal.aborted?'aborted':'invalid',status:response.status,message:'Backend response is not valid JSON.'}}
  if(signal.aborted)return {ok:false,kind:'aborted',status:null,message:'Request cancelled or timed out; backend execution is unknown.'}
  if(!response.ok) {
    const code=record(data)&&record(data.detail)&&text(data.detail.code)?data.detail.code:null
    return {ok:false,kind:'http',status:response.status,message:`HTTP ${response.status}${code?` — ${code}`:''}.`,...(isValidation(data)?{issues:data.detail}:{})}
  }
  return {ok:true,status:response.status,data}
}
export async function capabilities(signal: AbortSignal): Promise<ApiValue<Capabilities>> {
  const r=await jobFetch('capabilities',signal)
  return !r.ok?r:r.status===200&&isCapabilities(r.data)?{...r,data:r.data}:{ok:false,kind:'invalid',status:r.status,message:'Invalid capabilities response; prototype availability is unknown.'}
}
