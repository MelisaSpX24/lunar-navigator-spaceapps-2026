import { Panel } from '../../components/Panel'
import { useScenario } from './ScenarioProvider'
import { healthMessage } from './ConnectionStatus'
import styles from './Scenario.module.css'

export function ResponseStatus() {
  const { health, analysis, cancel } = useScenario()
  const error = ['not_ready','validation_error','network_error','server_error','invalid_response'].includes(analysis.kind)
  return <Panel title="Analysis Connection / Response Status">
    <div className={styles.content}>
      <p>{healthMessage(health)}</p>
      <div role={error ? 'alert' : 'status'} aria-atomic="true">
        {analysis.kind === 'idle' && <p>{analysis.notice}</p>}
        {analysis.kind === 'submitting' && <p>Submitting scenario to the backend… No scientific completion is assumed.</p>}
        {analysis.kind === 'not_ready' && <p>Scientific analysis is currently unavailable. Your scenario inputs have been preserved.</p>}
        {analysis.kind === 'validation_error' && <>
          <p>Backend rejected the request (HTTP 422). Review the field errors in Mission Setup. Your values have been preserved.</p>
          {analysis.general.map((message, index) => <p key={index}>{message}</p>)}
        </>}
        {(analysis.kind === 'network_error' || analysis.kind === 'server_error' || analysis.kind === 'invalid_response') && <p>{analysis.message}{analysis.status !== null ? ` HTTP status: ${analysis.status}.` : ''} Your scenario inputs have been preserved.</p>}
        {analysis.kind === 'received' && <p>{analysis.response.execution_status === 'COMPLETED'
          ? 'Server reports COMPLETED. This does not certify an operation; scientific panels validate their data separately.'
          : 'Response received; the server has not reported a completed analysis.'}</p>}
      </div>
      {analysis.kind === 'submitting' && <button type="button" onClick={cancel}>Cancel request</button>}
      {(analysis.kind === 'received' || analysis.kind === 'not_ready') && <>
        {analysis.response.data_origin === 'TEST_FIXTURE' && <p role="note"><strong>Test fixture response — not a live NASA analysis.</strong></p>}
        <dl className={styles.summary}>
          <div><dt>HTTP status</dt><dd>{analysis.status}</dd></div>
          <div><dt>Schema version</dt><dd>{analysis.response.schema_version}</dd></div>
          <div><dt>Server execution status</dt><dd>{analysis.response.execution_status}</dd></div>
          <div><dt>Server data origin</dt><dd>{analysis.response.data_origin ?? 'Not provided (null)'}</dd></div>
          <div><dt>Server decision status</dt><dd>{analysis.response.decision.status} — this is not an operation approval.</dd></div>
          <div><dt>Server quality status</dt><dd>{analysis.response.quality.status}</dd></div>
        </dl>
        <p>Scientific score data: {analysis.response.score.value === null ? 'unavailable (null); no zero has been inferred.' : 'field received; see Planning Score for validation.'}</p>
        <p>Time series: {analysis.response.series === null ? 'not calculated or not provided (null).' : 'received; each visibility panel validates its samples.'}</p>
        <p>Response ID: {analysis.response.analysis_id}. This is not a saved analysis record or a retrieval link.</p>
        {analysis.response.decision.reason_codes.length > 0 && <p>Server reason codes: {analysis.response.decision.reason_codes.join(', ')}</p>}
        {[...analysis.response.limitations, ...analysis.response.quality.limitations].map((message, index) => <p key={index}>Server limitation: {message}</p>)}
      </>}
    </div>
  </Panel>
}
