import { buildAnalysisRequest } from '../features/mission-input/buildAnalysisRequest'
import { initialMissionState } from '../features/mission-input/missionState'
import type { AnalysisResponse } from '../services/api/responses'

// Controlled test envelopes, never imported by production modules.
export const healthFixture = (ready = false) => ({ status: 'ok', science_ready: ready, dem_ready: false, kernels_ready: false, reason_codes: ready ? [] : ['SCIENCE_ENGINE_NOT_READY'] })
export const validForm = () => ({ ...initialMissionState(), latitude: '-85', longitude: '340', utcDate: '2026-11-14', utcTime: '12:30' })
export const requestFixture = () => buildAnalysisRequest(validForm()).request!
export const analysisFixture = (patch: Partial<AnalysisResponse> = {}): AnalysisResponse => {
  const base: AnalysisResponse = {
  schema_version: '1.0', analysis_id: 'controlled-test-response', execution_status: 'NOT_RUN', data_origin: null,
  request: requestFixture(), decision: { status: 'INCOMPLETE', reason_codes: ['SCIENCE_ENGINE_NOT_READY'], rules: [] },
  score: { value: null, model_version: null, components: null }, quality: { status: 'NOT_ASSESSED', limitations: [], coverage_complete: null },
  limitations: ['Controlled test envelope; no scientific calculation.'], series: null, horizons: null, resolved_site: null,
  windows: { sun: null, earth: null, joint: null }, sources: [],
  }
  return {...base,...patch,decision:{...base.decision,...patch.decision},score:{...base.score,...patch.score},quality:{...base.quality,...patch.quality}}
}
export const jsonResponse = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
