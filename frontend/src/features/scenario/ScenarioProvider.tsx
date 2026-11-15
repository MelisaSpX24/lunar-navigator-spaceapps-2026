import { candidateInput } from '../alternative-explorer/requests'
import { useScientificJob } from '../scientific-jobs/useScientificJob'
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { initialMissionState, type FormErrors, type FormField, type MissionFormState } from '../mission-input/missionState'
import { buildAnalysisRequest } from '../mission-input/buildAnalysisRequest'
import { coordinateFields, visualCoordinate } from '../mission-input/coordinates'
import type { VisualCoordinate } from '../../visualization/coordinates/lunarCoordinates'
import { getHealth, submitAnalysis } from '../../services/api/client'
import type { AnalysisResponse, HealthResponse } from '../../services/api/responses'
import { mapFieldErrors } from '../../services/api/fieldErrors'
import type { AnalysisRequestV1 } from '../mission-input/analysisRequest'

export type HealthState = { kind: 'checking' }
  | { kind: 'ready' | 'reachable_not_ready'; status: number; data: HealthResponse }
  | { kind: 'unreachable' | 'invalid_response'; status: number | null; message: string }
export type AnalysisState = { kind: 'idle'; notice: string } | { kind: 'submitting' }
  | { kind: 'received' | 'not_ready'; status: number; response: AnalysisResponse; request: AnalysisRequestV1 }
  | { kind: 'validation_error'; status: 422; fields: FormErrors; general: string[] }
  | { kind: 'network_error' | 'server_error' | 'invalid_response'; status: number | null; message: string }

function useScenarioState() {
  const [loadedCandidate,setLoadedCandidate]=useState<string|null>(null)
  const [state, setState] = useState(initialMissionState)
  const [explicitRequirements,setExplicitRequirements]=useState<string[]>([])
  const form = useRef(state)
  const validation = useMemo(() => buildAnalysisRequest(state), [state])
  const research = useScientificJob(validation.request,explicitRequirements)
  const [health, setHealth] = useState<HealthState>({ kind: 'checking' })
  const healthNow = useRef(health)
  const [analysis, setAnalysis] = useState<AnalysisState>({ kind: 'idle', notice: 'No analysis request has been sent.' })
  const healthAbort = useRef<AbortController | null>(null), analysisAbort = useRef<AbortController | null>(null)
  const healthSequence = useRef(0), analysisSequence = useRef(0), busy = useRef(false)
  const alive = useRef(false)
  const publishHealth = useCallback((next: HealthState) => { healthNow.current = next; setHealth(next) }, [])
  const stopAnalysis = useCallback(() => {
    analysisSequence.current++
    analysisAbort.current?.abort()
    analysisAbort.current = null
    busy.current = false
  }, [])
  const invalidate = useCallback(() => {
    stopAnalysis()
    research.clear()
    setAnalysis(previous => previous.kind === 'idle' ? previous : { kind: 'idle', notice: 'Scenario changed. The previous request or response was cleared; no result applies to these inputs.' })
  }, [stopAnalysis, research.clear])
  const change = useCallback(<K extends FormField,>(field: K, value: MissionFormState[K]) => {
    setLoadedCandidate(null)
    const requirementKeys:Partial<Record<FormField,string>>={solarFraction:'min_solar_disk_visible_fraction',minSun:'min_sun_visible_s',maxDark:'max_dark_gap_s',minEarth:'min_earth_continuous_s',clearance:'earth_clearance_margin_deg',simultaneous:'require_simultaneous',minJoint:'min_joint_continuous_s'}
    const requirement=requirementKeys[field]
    if(requirement)setExplicitRequirements(previous=>previous.includes(requirement)?previous:[...previous,requirement])
    form.current = { ...form.current, [field]: value }
    setState(form.current)
    invalidate()
  }, [invalidate])
  const select = useCallback((coordinate: VisualCoordinate) => {
    setLoadedCandidate(null)
    form.current = { ...form.current, ...coordinateFields(coordinate) }
    setState(form.current)
    invalidate()
  }, [invalidate])
  const reset = useCallback(() => {
    stopAnalysis()
    research.clear()
    setLoadedCandidate(null)
    setExplicitRequirements([])
    form.current = initialMissionState()
    setState(form.current)
    setAnalysis({ kind: 'idle', notice: 'Scenario reset. No analysis request has been sent for these inputs.' })
  }, [stopAnalysis, research.clear])
  const cancel = useCallback(() => {
    stopAnalysis()
    setAnalysis({ kind: 'idle', notice: 'Analysis request cancelled. Your scenario inputs have been preserved.' })
  }, [stopAnalysis])
  const checkHealth = useCallback(async () => {
    if (busy.current) return
    healthAbort.current?.abort()
    const sequence = ++healthSequence.current, controller = new AbortController()
    healthAbort.current = controller
    publishHealth({ kind: 'checking' })
    const timeout = setTimeout(() => controller.abort(), 10_000)
    try {
      const result = await getHealth(controller.signal)
      if (!alive.current || sequence !== healthSequence.current) return
      if (result.kind === 'health') publishHealth({ kind: result.health.science_ready ? 'ready' : 'reachable_not_ready', status: result.status, data: result.health })
      else publishHealth({ kind: result.kind === 'invalid_response' ? 'invalid_response' : 'unreachable', status: result.status,
        message: result.kind === 'aborted' ? 'Backend health check timed out. Try checking the connection again.' : result.message })
    } finally { clearTimeout(timeout) }
  }, [publishHealth])
  useEffect(() => {
    alive.current = true
    // StrictMode's discarded setup is cancelled before starting network work.
    const start = setTimeout(() => { void checkHealth() }, 0)
    return () => {
      alive.current = false
      clearTimeout(start)
      healthSequence.current++
      healthAbort.current?.abort()
      stopAnalysis()
    }
  }, [checkHealth, stopAnalysis])
  const run = useCallback(async () => {
    const validated = buildAnalysisRequest(form.current)
    if (!alive.current || busy.current || research.isBusy() || healthNow.current.kind !== 'ready' || !validated.request) return
    stopAnalysis()
    research.clear()
    busy.current = true
    const sequence = analysisSequence.current, controller = new AbortController()
    analysisAbort.current = controller
    setAnalysis({ kind: 'submitting' })
    const timeout = setTimeout(() => controller.abort(), 30_000)
    try {
      const result = await submitAnalysis(validated.request, controller.signal)
      if (!alive.current || sequence !== analysisSequence.current) return
      switch (result.kind) {
        case 'received': case 'not_ready':
          setAnalysis({ kind: result.kind, status: result.status, response: result.response, request: validated.request })
          if (result.kind === 'not_ready' && healthNow.current.kind === 'ready') {
            // A validated server rejection invalidates the earlier ready signal.
            publishHealth({ ...healthNow.current, kind: 'reachable_not_ready' })
          }
          break
        case 'validation_error': {
          const errors = mapFieldErrors(result.issues)
          setAnalysis({ kind: result.kind, status: result.status, fields: errors.fields, general: errors.general })
          break
        }
        case 'aborted': setAnalysis({ kind: 'network_error', status: null, message: 'Analysis request timed out. Your inputs are preserved; no completion is assumed.' }); break
        default: setAnalysis({ kind: result.kind, status: result.status, message: result.message })
      }
    } finally {
      clearTimeout(timeout)
      if (sequence === analysisSequence.current) { busy.current = false; analysisAbort.current = null }
    }
  }, [stopAnalysis, publishHealth, research.active, research.clear])
  const applyCandidateRequest=(source:unknown,explicit:unknown,label:string)=>{
    const input=candidateInput(source,explicit)
    if(!input)return false
    invalidate();form.current=input.form;setState(input.form);setExplicitRequirements(input.explicit);setLoadedCandidate(label)
    return true
  }
  const selected = useMemo(() => visualCoordinate(state.latitude, state.longitude), [state.latitude, state.longitude])
  return { state, loadedCandidate, applyCandidateRequest, change, select, reset, selected, validation, health, analysis, checkHealth, run, cancel, research: {...research,run:(mode:'live'|'recorded'='live',resume=false,checkpointId?:string)=>busy.current?Promise.resolve():research.run(mode,resume,checkpointId)} }
}
type Scenario = ReturnType<typeof useScenarioState>
const ScenarioContext = createContext<Scenario | null>(null)
export function ScenarioProvider({ children }: { children: ReactNode }) {
  const value = useScenarioState()
  return <ScenarioContext.Provider value={value}>{children}</ScenarioContext.Provider>
}
export function useScenario(): Scenario {
  const scenario = useContext(ScenarioContext)
  if (!scenario) throw new Error('ScenarioProvider is required.')
  return scenario
}
