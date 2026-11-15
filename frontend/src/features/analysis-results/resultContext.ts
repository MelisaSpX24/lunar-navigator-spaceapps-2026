import { normalizedRequestMatches } from '../../services/api/normalizedRequest'
import type { AnalysisState, HealthState } from '../scenario/ScenarioProvider'
import type { AnalysisRequestV1 } from '../mission-input/analysisRequest'
import { requestMatches } from './requestMatch'
import { timeBounds } from './utc'

export function completedResult(analysis: AnalysisState, health: HealthState, current: AnalysisRequestV1 | null) {
  if (health.kind !== 'ready' || analysis.kind !== 'received' || analysis.status !== 200 || analysis.response.execution_status !== 'COMPLETED') return null
  if (!current || !requestMatches(analysis.request, analysis.response.request) || !requestMatches(current, analysis.request)) return null
  return { response: analysis.response, request: analysis.request, bounds: timeBounds(analysis.request.time.start_utc, analysis.request.time.duration_s) }
}

/** Separate prototype trust path; never weakens the independently ready path. */
export function completedPrototypeResult(job: import('../scientific-jobs/useScientificJob').ResearchState, current: AnalysisRequestV1|null) {
  if(job.phase!=='received'||!job.response||!job.request||!current||job.response.execution_status!=='COMPLETED')return null
  if(!requestMatches(current,job.request)||!normalizedRequestMatches(job.request,job.response.request))return null
  if(job.mode==='live'&&(!job.accepted||job.accepted.job_type!=='ANALYSIS'||job.status?.status!=='COMPLETED'||job.envelope?.status!=='COMPLETED'||job.envelope.job_id!==job.accepted.job_id||job.status.request_identity!==job.accepted.request_identity))return null
  if(job.mode==='recorded'&&job.response.data_origin!=='PRECOMPUTED')return null
  return {response:job.response,request:job.request,bounds:timeBounds(job.request.time.start_utc,job.request.time.duration_s)}
}
