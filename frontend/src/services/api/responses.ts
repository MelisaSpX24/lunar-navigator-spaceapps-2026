/** Minimum response envelope from backend/app/models/analysis.py at PR #9.
 * Scientific fields remain untrusted until the panel-specific display guards run.
 */
export type HealthResponse = {
  status: 'ok'; science_ready: boolean; dem_ready: boolean; kernels_ready: boolean; reason_codes: string[]
}
export type AnalysisResponse = {
  schema_version: '1.0'; analysis_id: string
  execution_status: 'NOT_RUN' | 'RUNNING' | 'COMPLETED' | 'FAILED'
  data_origin: 'PRECOMPUTED' | 'LIVE_COMPUTED' | 'TEST_FIXTURE' | null
  request: Record<string, unknown>
  decision: { status: 'MET' | 'NOT_MET' | 'INCOMPLETE'; reason_codes: string[]; rules?: unknown }
  score: { value: number | null; model_version?: unknown; components?: unknown }
  quality: { status: 'NOT_ASSESSED' | 'SUFFICIENT' | 'LIMITED' | 'INSUFFICIENT'; limitations: string[]; coverage_complete?: unknown }
  limitations: string[]
  series: unknown[] | null; horizons: unknown[] | null; resolved_site: Record<string, unknown> | null
  windows: { sun: unknown[] | null; earth: unknown[] | null; joint: unknown[] | null }
  sources?: unknown
}
export type ValidationIssue = { loc: (string | number)[]; msg: string }
export function record(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}
const strings = (value: unknown): value is string[] => Array.isArray(value) && value.every(v => typeof v === 'string')
const enumValue = (value: unknown, choices: string[]) => typeof value === 'string' && choices.includes(value)
const nullableArray = (value: unknown) => value === null || Array.isArray(value)
export function isHealth(value: unknown): value is HealthResponse {
  return record(value) && value.status === 'ok' && typeof value.science_ready === 'boolean'
    && typeof value.dem_ready === 'boolean' && typeof value.kernels_ready === 'boolean' && strings(value.reason_codes)
    && (value.schema_version === undefined || value.schema_version === '1.0')
}
export function isAnalysis(value: unknown): value is AnalysisResponse {
  if (!record(value) || value.schema_version !== '1.0') return false
  const { decision, score, quality, windows } = value
  return typeof value.analysis_id === 'string' && value.analysis_id.trim().length > 0
    && enumValue(value.execution_status, ['NOT_RUN','RUNNING','COMPLETED','FAILED'])
    && (value.data_origin === null || enumValue(value.data_origin, ['PRECOMPUTED','LIVE_COMPUTED','TEST_FIXTURE']))
    && record(value.request) && value.request.schema_version === '1.0'
    && record(decision) && enumValue(decision.status, ['MET','NOT_MET','INCOMPLETE']) && strings(decision.reason_codes)
    && record(score) && (score.value === null || (typeof score.value === 'number' && Number.isFinite(score.value) && score.value >= 0 && score.value <= 100))
    && record(quality) && enumValue(quality.status, ['NOT_ASSESSED','SUFFICIENT','LIMITED','INSUFFICIENT']) && strings(quality.limitations)
    && strings(value.limitations) && nullableArray(value.series) && nullableArray(value.horizons)
    && (value.resolved_site === null || record(value.resolved_site))
    && record(windows) && nullableArray(windows.sun) && nullableArray(windows.earth) && nullableArray(windows.joint)
}
export function isValidation(value: unknown): value is { detail: ValidationIssue[] } {
  return record(value) && Array.isArray(value.detail) && value.detail.length > 0 && value.detail.every(issue =>
    record(issue) && Array.isArray(issue.loc) && issue.loc.every(part => typeof part === 'string' || (typeof part === 'number' && Number.isSafeInteger(part))) && typeof issue.msg === 'string')
}
