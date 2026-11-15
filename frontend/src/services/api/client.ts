import type { AnalysisRequestV1 } from '../../features/mission-input/analysisRequest'
import { isAnalysis, isHealth, isValidation, record, type AnalysisResponse, type HealthResponse, type ValidationIssue } from './responses'
import { requestMatches } from '../../features/analysis-results/requestMatch'

type Failure = { kind: 'network_error' | 'aborted'; status: null; message: string }
  | { kind: 'invalid_response'; status: number | null; message: string }
type HttpFailure = { kind: 'server_error'; status: number; message: string }
export type HealthOutcome = { kind: 'health'; status: number; health: HealthResponse } | Failure | HttpFailure
export type AnalysisOutcome = { kind: 'received' | 'not_ready'; status: number; response: AnalysisResponse }
  | { kind: 'validation_error'; status: 422; issues: ValidationIssue[] } | Failure | HttpFailure

function endpoint(path: string): string {
  const base = (import.meta.env.VITE_API_BASE_URL || '/api/v1').trim().replace(/\/+$/, '')
  if (!(base.startsWith('/') && !base.startsWith('//')) && !/^https?:\/\//i.test(base)) throw new Error('Use a root-relative or HTTP(S) API base URL.')
  return `${base}/${path}`
}
async function send(path: string, signal?: AbortSignal, request?: AnalysisRequestV1): Promise<{ response: Response } | Failure> {
  let url: string
  try { url = endpoint(path) } catch { return { kind: 'invalid_response', status: null, message: 'Invalid API base configuration.' } }
  try {
    const response = await fetch(url, {
      method: request ? 'POST' : 'GET', headers: request ? { 'Content-Type': 'application/json', Accept: 'application/json' } : { Accept: 'application/json' },
      ...(request ? { body: JSON.stringify(request) } : {}), ...(signal ? { signal } : {}),
    })
    return { response }
  } catch (error) {
    return { kind: signal?.aborted || (error instanceof Error && error.name === 'AbortError') ? 'aborted' : 'network_error', status: null,
      message: 'The backend could not be reached. Check its address and connection.' }
  }
}
async function json(response: Response): Promise<unknown> { return response.json() }
const invalid = (status: number, message = 'The backend returned an unexpected response body.'): Failure => ({ kind: 'invalid_response', status, message })
const httpError = (status: number): HttpFailure => ({ kind: 'server_error', status, message: `Backend request returned HTTP ${status}.` })

export async function getHealth(signal?: AbortSignal): Promise<HealthOutcome> {
  const result = await send('health', signal)
  if (!('response' in result)) return result
  const { response } = result
  if (response.status !== 200) return httpError(response.status)
  try {
    const body = await json(response)
    return isHealth(body) ? { kind: 'health', status: response.status, health: body } : invalid(response.status, 'Invalid or unsupported health response.')
  } catch {
    return signal?.aborted ? { kind: 'aborted', status: null, message: 'Request cancelled.' } : invalid(response.status, 'Health response is not valid JSON.')
  }
}
export async function submitAnalysis(request: AnalysisRequestV1, signal?: AbortSignal): Promise<AnalysisOutcome> {
  const result = await send('analyses', signal, request)
  if (!('response' in result)) return result
  const { response } = result, status = response.status
  if (status !== 200 && status !== 503 && status !== 422) return httpError(status)
  let body: unknown
  try { body = await json(response) } catch {
    return signal?.aborted ? { kind: 'aborted', status: null, message: 'Request cancelled.' } : invalid(status, 'Analysis response is not valid JSON.')
  }
  if (status === 422) return isValidation(body) ? { kind: 'validation_error', status, issues: body.detail } : invalid(status, 'Invalid validation-error response.')
  if (record(body) && body.schema_version !== '1.0') return invalid(status, 'Unsupported analysis schema version; expected 1.0.')
  if (!isAnalysis(body)) return invalid(status)
  if (!requestMatches(request, body.request)) return invalid(status, 'Response request does not match the submitted scenario. No scientific result can be attached to these inputs.')
  if (status === 503) {
    const notReady = body.execution_status === 'NOT_RUN' && body.decision.status === 'INCOMPLETE'
      && body.decision.reason_codes.includes('SCIENCE_ENGINE_NOT_READY') && body.score.value === null
      && body.series === null && body.horizons === null && body.resolved_site === null && body.data_origin === null
    return notReady ? { kind: 'not_ready', status, response: body } : httpError(status)
  }
  return { kind: 'received', status, response: body }
}
