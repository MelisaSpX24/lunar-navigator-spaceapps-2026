import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Panel } from '../../components/Panel'
import { useScenario } from '../scenario/ScenarioProvider'
import { terminal } from '../../services/api/jobs'
import styles from '../scenario/Scenario.module.css'

export const prototypeWarning='This analysis uses a bounded sampled scientific model and available lunar data. Absolute terrain registration and independent astronomical validation remain incomplete. Results do not certify landing safety, power availability, or radio-link success.'
export function PrototypeNotice() {
  return <aside id="prototype-limitations" role="note"><strong>Research prototype — not independently validated mission science.</strong><p>{prototypeWarning}</p><p>Planning Suitability Index is not a probability of mission success. A score of 100 is not a landing safety certification.</p></aside>
}
export function ScientificBackend() {
  const {research,validation,analysis,health}=useScenario()
  const {job,availability}=research
  const [mode,setMode]=useState<'live'|'recorded'>(job.mode)
  const [checkpointId,setCheckpointId]=useState('')
  const c=availability.kind==='available'?availability.data:null
  const supported=!!c&&c.api_reachable&&c.job_types.includes('ANALYSIS')&&(mode==='live'?c.scientific_job_runner_available&&c.configured_science_files_available&&c.bounded_live_prototype_supported:c.recorded_prototype_supported)
  const enabled=supported&&validation.valid&&research.hasActiveRequirement&&!research.active&&analysis.kind!=='submitting'
  const ended=job.status&&terminal(job.status.status)
  return <Panel title="Scientific Backend"><div className={styles.content}>
    <p>Scientific readiness: {health.kind==='ready'?'server reports ready':'not independently ready or not confirmed'}. Prototype availability is assessed separately.</p>
    {availability.kind==='checking'&&<p role="status">Checking scientific job capabilities…</p>}
    {availability.kind==='unavailable'&&<p role="status">{availability.failure.status===404?'Scientific integration unavailable — this backend does not expose the job API.':availability.failure.message}</p>}
    {c&&<><p>API reachable: {String(c.api_reachable)}. Bounded live prototype supported: {String(c.bounded_live_prototype_supported)}. Science files configured: {String(c.configured_science_files_available)}.</p><details><summary>Backend capabilities and source checks</summary><dl className={styles.summary}>
      <div><dt>API reachable</dt><dd>{String(c.api_reachable)}</dd></div>
      <div><dt>Scientific worker available</dt><dd>{String(c.scientific_job_runner_available)}</dd></div>
      <div><dt>Science files configured</dt><dd>{String(c.configured_science_files_available)} — source hashes and metadata are checked at execution, not certified by file existence.</dd></div>
      <div><dt>Bounded live prototype supported</dt><dd>{String(c.bounded_live_prototype_supported)}</dd></div>
      <div><dt>Independent scientific validation ready</dt><dd>{String(c.fully_independently_validated_science_ready)}</dd></div>
    </dl></details>{c.reason_codes.length>0&&<p>Capability reason codes: {c.reason_codes.join(', ')}</p>}</>}
    <button type="button" onClick={()=>void research.check() } disabled={availability.kind==='checking'}>Check scientific capabilities</button>
    <p><label htmlFor="research-execution-mode">Research execution mode</label> <select id="research-execution-mode" value={mode} onChange={e=>setMode(e.target.value==='recorded'?'recorded':'live')} disabled={research.active}>
      <option value="live">Live bounded prototype</option><option value="recorded">Recorded — exact match only</option>
    </select></p>
    <p>Mode for the next request: {mode==='recorded'?'Recorded — exact match only (PRECOMPUTED)':'Live bounded prototype'}.</p>
    <p id="research-explanation">Runs a bounded NASA-data sampled-model analysis. Results are research estimates, not certified mission predictions.</p>
    <details><summary>Research settings and recorded examples</summary>
    {mode==='recorded'&&<p>Explicit recorded mode returns PRECOMPUTED research evidence only for matching settings. No live fallback. Historical six-hour CR1 examples use −89.468°, 222.6° E, UTC 2026-11-20T08:00:00Z or 2026-11-23T17:26:15Z, 1 m device heights, 3600 s sampling, 64 disk samples, prototype policy and include_full_horizon=false. Your own requirements remain explicit; a mismatch returns 404. No form values are substituted.</p>}
    <p>Research requests send only requirements you have explicitly edited. Unset fields stay omitted; explicit null, zero and false are preserved. Displayed draft defaults alone do not activate rules.</p>
    <p>Prototype settings: PROTOTYPE_SAMPLED_ESTIMATE; PROTOTYPE registration; 3600 s step; 64 disk samples; bounded resources (900 s wall admission, 24 visibility calls, 5000 horizon rays). Limits may yield PARTIAL evidence.</p></details>
    <button type="button" disabled={!enabled} aria-describedby="research-explanation research-reason" onClick={()=>void research.run(mode)}>Run Research Prototype</button>
    <p id="research-reason">{!validation.valid?'Complete valid scenario inputs first.':!research.hasActiveRequirement?'Explicitly edit at least one operation requirement. Displayed draft defaults are not automatically activated for research jobs.':!supported?'This mode is not available from validated backend capabilities.':research.active?'A research request is already active.':'Prototype execution is available; scientific certification remains separate.'}</p>
    {mode==='live'&&<details><summary>Reuse a saved analysis checkpoint</summary>
      <p>Enter a terminal analysis job ID and keep the original scenario inputs and explicit requirements. This submits a new bounded job; the server revalidates the exact request and source hashes before reuse. Missing samples may require live computation. A mismatch is an error, with no automatic fresh-job fallback.</p>
      <label>Saved analysis job ID <input value={checkpointId} onChange={e=>setCheckpointId(e.target.value)} maxLength={32} autoComplete="off" spellCheck={false}/></label>{' '}
      <button type="button" disabled={!enabled||!/^[a-f0-9]{32}$/.test(checkpointId.trim())} onClick={()=>void research.run('live',false,checkpointId.trim())}>Resume Saved Analysis</button>
    </details>}
    <div role={job.phase==='error'?'alert':'status'} aria-atomic="true"><p>{job.message}</p></div>
    {job.failure?.issues&&<ul>{job.failure.issues.map((issue,i)=><li key={i}>{issue.loc.join('.')}: {issue.msg}</li>)}</ul>}
    {job.accepted&&<p>Job ID: {job.accepted.job_id}<br/>Request identity: {job.accepted.request_identity}</p>}
    {job.status&&<><p>Server status: {job.status.status}; stage: {job.status.progress.stage}; progress: {job.status.progress.progress_percent===null?'not reported':`${job.status.progress.progress_percent}%`}. Completed visibility evaluations: {job.status.progress.completed_visibility_evaluations}.</p>
      <p>Reason codes: {job.status.reason_codes.join(', ')||'none reported'}</p>
      {job.status.error&&<p role="alert">{job.status.error.code} ({job.status.error.error_class}): {job.status.error.message}</p>}
      {job.status.limitations.map((v,i)=><p key={i}>Job limitation: {v}</p>)}</>}
    {job.accepted&&!ended&&<><button type="button" disabled={job.phase!=='watching'&&job.phase!=='disconnected'} onClick={research.stopWaiting}>Stop Waiting</button>{' '}
      <button type="button" disabled={job.status?.status==='CANCEL_REQUESTED'} onClick={()=>void research.cancel()}>Request Cancellation</button></>}
    {job.accepted&&['stopped','disconnected','error','terminal'].includes(job.phase)&&<button type="button" onClick={research.retry}>Reconnect to same job</button>}
    {ended&&job.request&&job.status?.status!=='COMPLETED'&&<button type="button" disabled={!enabled||mode!=='live'} onClick={()=>void research.run('live',true)}>Resume same scientific request</button>}
    {job.phase==='received'&&<><p>Data origin: {job.response?.data_origin??'Unknown (null)'}. Scientific panels validate their own content.</p><Link to="/analysis">View research results in Mission Analysis</Link></>}
  </div></Panel>
}
