import { mapFieldErrors } from '../services/api/fieldErrors'
import { ScientificBackend } from '../features/scientific-jobs/ScientificBackend'
import { SiteExplorer } from '../features/lunar-sites/SiteExplorer'
import { visualSiteCoordinate } from '../features/lunar-sites/siteValidation'
import type { SiteFocus } from '../visualization/globe/GlobeControls'
import { Panel } from '../components/Panel'
import { PageHeading } from '../components/PageHeading'
import { SceneViewport } from '../components/SceneViewport'
import { lazy, Suspense, useRef, useState } from 'react'
import { LoadingState } from '../components/States'
import { GlobeBoundary } from '../visualization/globe/GlobeBoundary'
import styles from './Screens.module.css'
import { MissionForm } from '../features/mission-input/MissionForm'
import { useScenario } from '../features/scenario/ScenarioProvider'
import { healthMessage } from '../features/scenario/ConnectionStatus'
import { ResponseStatus } from '../features/scenario/ResponseStatus'
import scenarioStyles from '../features/scenario/Scenario.module.css'

const LunarGlobe = lazy(() => import('../visualization/globe/LunarGlobe'))

export function MissionSetup() {
  const { state, selected, validation, change, select, reset, health, analysis, run, research, loadedCandidate } = useScenario()
  const [inspected, setInspected] = useState<string|null>(null)
  const [siteFocus, setSiteFocus] = useState<SiteFocus|null>(null)
  const sequence=useRef(0)
  const globe = useRef<HTMLDivElement>(null)
  const submitting = analysis.kind === 'submitting'
  const runEnabled = validation.valid && health.kind === 'ready' && !submitting && !research.active
  const runReason = submitting ? 'An analysis request is already in progress.' : !validation.valid
    ? 'No analysis will be performed. Complete or correct the scenario inputs.'
    : health.kind !== 'ready' ? `No analysis will be performed. ${healthMessage(health)}.`
    : 'Backend reports scientific readiness. Run Analysis sends this validated scenario once.'
  return <>
    <PageHeading title="Mission Setup" workspace="MISSION WORKSPACE"
      subtitle="Explore the Moon. Evaluate the Conditions. Find a Better Site." status="Interface preview" />
    {loadedCandidate&&<p role="status">Loaded candidate parameters: {loadedCandidate}. No analysis has been started.</p>}
    <p className={styles.intro}>24&28 — Lunar Landing Site Navigator is being built to explore lunar surface operations, with a focus on the south pole.</p>
    <div className={styles.setupGrid}>
      <div className={styles.globePanel} ref={globe}><Panel title="Lunar exploration" eyebrow="01 / SITE SELECTION">
        <SceneViewport interactive label="Global lunar view" caption="GLOBAL VIEW / VISUAL COORDINATES" footer="Visual exploration only. No analysis or landing-site certification.">
          <GlobeBoundary><Suspense fallback={<LoadingState title="Loading 3D scene">Preparing the interactive lunar globe.</LoadingState>}>
            <LunarGlobe selected={selected} onSelect={select} siteFocus={siteFocus} onInspectSite={setInspected} />
          </Suspense></GlobeBoundary>
        </SceneViewport>
      </Panel></div>
      <Panel title="Mission parameters" eyebrow="02 / OPERATION PLANNING">
        <MissionForm state={state} onChange={change} validation={validation} runEnabled={runEnabled} runReason={runReason}
          onRun={() => { void run() }} onReset={() => {setInspected(null);setSiteFocus(null);reset()}} serverErrors={analysis.kind === 'validation_error' ? analysis.fields : mapFieldErrors((research.job.failure?.issues ?? []).map(issue=>({...issue,loc:issue.loc.filter((part,index)=>!(index===1&&part==='analysis'))}))).fields} onShowGlobe={() => {
          globe.current?.scrollIntoView({ block: 'start', behavior: 'auto' })
          globe.current?.querySelector('button')?.focus({ preventScroll: true })
        }} />
      </Panel>
    </div>
    <SiteExplorer latitude={state.latitude} longitude={state.longitude} inspected={inspected} onInspect={setInspected} onUse={select} onView={site=>{
      const coordinate=visualSiteCoordinate(site)
      if(!coordinate)return
      setInspected(site.id);setSiteFocus({kind:'site',coordinate,sequence:++sequence.current})
      globe.current?.scrollIntoView({block:'start',behavior:'auto'})
      globe.current?.querySelector('button')?.focus({preventScroll:true})
    }}/>
    <div className={scenarioStyles.responseArea}><ScientificBackend /><ResponseStatus /></div>
    <aside className={styles.notice} aria-label="Development status">
      <span className={styles.noticeIcon} aria-hidden="true">i</span>
      <p><strong>A foundation for informed exploration.</strong> Assessments are supplied only by the scientific backend. Prototype availability is separate from scientific certification.</p>
    </aside>
  </>
}
