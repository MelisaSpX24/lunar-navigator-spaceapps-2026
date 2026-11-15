import { useScenario, type HealthState } from './ScenarioProvider'
import styles from './Scenario.module.css'

export function healthMessage(health: HealthState): string {
  switch (health.kind) {
    case 'checking': return 'Checking backend connection…'
    case 'reachable_not_ready': return 'Backend reachable — scientific engine not ready'
    case 'ready': return 'Backend reachable — scientific engine ready'
    case 'unreachable': return 'Backend unreachable'
    case 'invalid_response': return 'Backend response invalid — readiness unknown'
  }
}
export function ConnectionStatus() {
  const { health, analysis, checkHealth } = useScenario()
  return <div className={styles.connection} role="group" aria-label="Backend connection">
    <span className={styles.caption}>BACKEND / SCIENTIFIC READINESS</span>
    <p role="status">{healthMessage(health)}</p>
    {(health.kind === 'unreachable' || health.kind === 'invalid_response') && <p className={styles.detail}>{health.message}{health.status !== null ? ` HTTP ${health.status}.` : ''}</p>}
    <button type="button" disabled={health.kind === 'checking' || analysis.kind === 'submitting'} onClick={() => { void checkHealth() }}>
      {health.kind === 'unreachable' || health.kind === 'invalid_response' ? 'Retry connection' : 'Check backend'}
    </button>
  </div>
}
