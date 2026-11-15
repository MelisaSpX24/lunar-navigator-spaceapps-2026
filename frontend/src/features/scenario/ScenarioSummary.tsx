import { Link } from 'react-router-dom'
import { Panel } from '../../components/Panel'
import { useScenario } from './ScenarioProvider'
import { PROFILES } from '../mission-input/analysisRequest'
import styles from './Scenario.module.css'

export function ScenarioSummary() {
  const { state, validation } = useScenario()
  return <Panel title="Current Scenario">
    <div className={styles.content}>
      <p>{validation.valid ? 'Scenario inputs valid. This is an input summary, not a scientific result.' : 'Scenario incomplete or invalid. Return to Mission Setup to correct the inputs.'}</p>
      <dl className={styles.summary}>
        <div><dt>Latitude input</dt><dd>{state.latitude ? `${state.latitude}°` : 'Not specified'}</dd></div>
        <div><dt>Longitude input (east)</dt><dd>{state.longitude ? `${state.longitude}°` : 'Not specified'}</dd></div>
        <div><dt>Operation profile</dt><dd>{PROFILES.find(p => p.value === state.profile)?.label ?? 'Unsupported profile'}</dd></div>
        <div><dt>UTC start</dt><dd>{validation.startUtc ?? 'Not specified or invalid'}</dd></div>
        <div><dt>Duration input</dt><dd>{validation.durationSeconds === null ? 'Invalid' : `${validation.durationSeconds} seconds`}</dd></div>
      </dl>
      <Link to="/">Edit scenario in Mission Setup</Link>
    </div>
  </Panel>
}
