import { ScientificBackend, PrototypeNotice } from '../features/scientific-jobs/ScientificBackend'
import { CelestialTimeProvider, TimeSelector } from '../features/celestial-timeline/CelestialTime'
import { SelectedBody } from '../features/celestial-timeline/SelectedBody'
import { Panel } from '../components/Panel'
import { PageHeading } from '../components/PageHeading'
import { LocalHorizon } from '../visualization/local-horizon/LocalHorizon'
import { EmptyState, UnsupportedDataState } from '../components/States'
import styles from './Screens.module.css'
import { ScenarioSummary } from '../features/scenario/ScenarioSummary'
import { ResponseStatus } from '../features/scenario/ResponseStatus'
import scenarioStyles from '../features/scenario/Scenario.module.css'
import { useMemo } from 'react'
import { useScenario } from '../features/scenario/ScenarioProvider'
import { completedResult, completedPrototypeResult } from '../features/analysis-results/resultContext'
import { ResultContext } from '../features/analysis-results/ResultContext'
import { HorizonData, BodyData } from '../features/analysis-results/VisibilityPanels'
import { TimelineData } from '../features/analysis-results/TimelineData'
import { DecisionData, ScoreData } from '../features/analysis-results/AssessmentData'
import { QualityData } from '../features/analysis-results/QualityData'
import resultStyles from '../features/analysis-results/Results.module.css'

export function MissionAnalysis() {
  const { analysis, health, validation, selected, research } = useScenario()
  const result = useMemo(() => research.job.phase === 'idle' ? completedResult(analysis, health, validation.request) : completedPrototypeResult(research.job, validation.request), [analysis, health, validation.request, research.job])
  return <CelestialTimeProvider result={result}>
    <PageHeading title="Mission Analysis" workspace="ANALYSIS WORKSPACE"
      subtitle="Understand the conditions. Keep the uncertainties in view." status={result ? 'Backend response' : 'No completed result'} />
    <p className={styles.intro}>{result ? 'Backend values are shown only after scenario matching and independent panel validation. Missing data remains unknown.' : 'No completed, current scientific response is available. Scientific visualizations are not populated; request status is described below.'}</p>
    <div className={scenarioStyles.stack}><ScenarioSummary /><ResponseStatus /><ScientificBackend /></div>
    {result && <ResultContext {...result} />}
    {result && research.job.phase==='received' && <PrototypeNotice />}
    <div className={`${styles.analysisGrid} ${result ? resultStyles.populatedGrid : ''}`}>
      <Panel title="Local Horizon" eyebrow="TERRAIN & LINE OF SIGHT" className={styles.horizonPanel}>
        <LocalHorizon response={result?.response ?? null} selected={selected} />
        <TimeSelector />
        {result ? <HorizonData response={result.response} /> : <EmptyState title="Horizon data unavailable">A validated topographic horizon profile is required for the 2D chart. No measured terrain or celestial positions are shown.</EmptyState>}
      </Panel>
      <Panel title="Sun Visibility" className={styles.sunPanel}>{result ? <><SelectedBody body="sun" /><BodyData response={result.response} body="sun" bounds={result.bounds} /></> : <EmptyState title="No visibility data">Solar positions and disk visibility have not been calculated.</EmptyState>}</Panel>
      <Panel title="Earth Visibility" className={styles.earthPanel}>{result ? <><SelectedBody body="earth" /><BodyData response={result.response} body="earth" bounds={result.bounds} /></> : <EmptyState title="No visibility data">Earth positions and line-of-sight conditions have not been calculated. Geometric visibility alone does not establish a verified radio link or data transfer rate.</EmptyState>}</Panel>
      <Panel title="Mission Timeline" className={styles.timelinePanel}>{result ? <TimelineData response={result.response} bounds={result.bounds} /> : <EmptyState title="No timeline available">Time samples and shared visibility windows will appear when supported results are available.</EmptyState>}</Panel>
      <Panel title="Operation Assessment" className={styles.assessmentPanel}>{result ? <DecisionData response={result.response} /> : <EmptyState title="Not assessed">No operation decision is available.</EmptyState>}</Panel>
      <Panel title="Planning Score" className={styles.scorePanel}>{result ? <div aria-describedby={research.job.phase==='received'?'prototype-limitations':undefined}><ScoreData response={result.response} /></div> : <EmptyState title="Not calculated">A planning score requires a completed backend assessment.</EmptyState>}</Panel>
      <Panel title="Data Quality" className={styles.qualityPanel}>{result ? <div aria-describedby={research.job.phase==='received'?'prototype-limitations':undefined}><QualityData response={result.response} /></div> : <UnsupportedDataState title="Scientific data unavailable">Scientific results are not connected in this phase. Source provenance, coverage and model versions are unavailable.</UnsupportedDataState>}</Panel>
    </div>
  </CelestialTimeProvider>
}
