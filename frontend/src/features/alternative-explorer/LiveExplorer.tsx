import { useCallback,useMemo,useState } from 'react'
import { Panel } from '../../components/Panel'
import { useScenario } from '../scenario/ScenarioProvider'
import { useScientificJob } from '../scientific-jobs/useScientificJob'
import { terminal,type ResultEnvelope } from '../../services/api/jobs'
import { defaultOptimizerSettings,liveEvidence,optimizerPayload,optimizerPrerequisite,type OptimizerKind } from './live'
import { EvidenceWorkspace } from './EvidenceWorkspace'
import styles from './Explorer.module.css'
export function LiveExplorer({kind}:{kind:OptimizerKind}){
 const {research,validation}=useScenario(),[settings,setSettings]=useState(defaultOptimizerSettings)
 const prerequisite=useMemo(()=>optimizerPrerequisite(research.job,validation.request),[research.job,validation.request])
 const payload=useMemo(()=>prerequisite?optimizerPayload(kind,prerequisite,settings):null,[kind,prerequisite,settings])
 const validate=useCallback((envelope:ResultEnvelope)=>{if(!payload)return false;try{liveEvidence(envelope,payload);return true}catch{return false}},[payload])
 const optimizer=useScientificJob(validation.request,undefined,{type:kind,payload:payload??{},validate},research.availability)
 const {job}=optimizer,c=research.availability.kind==='available'?research.availability.data:null
 const [checkpointId,setCheckpointId]=useState('')
 const ready=!!c&&c.api_reachable&&c.scientific_job_runner_available&&c.configured_science_files_available&&c.bounded_live_prototype_supported&&c.job_types.includes(kind)
 const projected=useMemo(()=>{if(job.phase!=='received'||!job.envelope||!payload)return null;try{return liveEvidence(job.envelope,payload)}catch{return null}},[job.phase,job.envelope,payload])
 const ended=!!job.status&&terminal(job.status.status),canRun=ready&&!!payload&&!optimizer.active
 return <div className={styles.workspace}><Panel title={`Live ${kind==='TEMPORAL'?'Temporal':'Local Site'} Optimizer`}><div className={styles.content}>
  <p>Scientific certification readiness remains false unless independently established by the backend. Bounded prototype availability: {ready?'available':'unavailable or unconfirmed'}.</p>
  <button type="button" onClick={()=>void research.check()}>Check optimizer capabilities</button>
  {!prerequisite&&<p role="status">A completed, current Research Prototype Analysis job with validated window_evidence.request is required. Run that analysis in Mission Setup first. Recorded demos never supply automatic live prerequisites.</p>}
  <div className={styles.controls}>
   {kind==='TEMPORAL'?<><label>Search horizon<select aria-label="Search horizon" value={settings.days} onChange={e=>setSettings({...settings,days:Number(e.target.value)})}><option value="1">1 day</option><option value="7">7 days</option><option value="14">14 days</option><option value="31">31 days</option></select></label><label>Temporal selection strategy<select aria-label="Temporal selection strategy" value={settings.temporalStrategy} onChange={e=>setSettings({...settings,temporalStrategy:e.target.value==='LEGACY'?'LEGACY':'COVERAGE_AWARE'})}><option value="COVERAGE_AWARE">COVERAGE_AWARE</option><option value="LEGACY">LEGACY</option></select></label></>:<><label>Live search radius<select aria-label="Live search radius" value={settings.radius} onChange={e=>setSettings({...settings,radius:Number(e.target.value)})}><option value="1000">1 km</option><option value="3000">3 km</option><option value="5000">5 km</option></select></label><label>Local selection strategy<select aria-label="Local selection strategy" value={settings.strategy} onChange={e=>setSettings({...settings,strategy:e.target.value==='SLOPE_ONLY'?'SLOPE_ONLY':'TERRAIN_DIVERSE'})}><option value="TERRAIN_DIVERSE">TERRAIN_DIVERSE</option><option value="SLOPE_ONLY">SLOPE_ONLY</option></select></label></>}
   <label>Candidate evaluation budget<select aria-label="Candidate evaluation budget" value={settings.budget} onChange={e=>setSettings({...settings,budget:Number(e.target.value)})}>{(kind==='TEMPORAL'?[2,4,8,16,31]:[2,4,8]).map(n=><option key={n} value={n}>{n} including baseline</option>)}</select></label>
   <label>Cooperative wall budget<select aria-label="Cooperative wall budget" value={settings.wall} onChange={e=>setSettings({...settings,wall:Number(e.target.value)})}><option value="300">300 seconds</option><option value="900">900 seconds</option></select></label>
  </div><p>Temporal screening: EXACT_ONLY. Resource budgets bound computation; they do not guarantee completion or scientific MET. Changing settings stops local waiting and invalidates older optimizer evidence; server work may continue. Leaving this screen stops local polling, not server computation.</p>
  <button type="button" disabled={!canRun} onClick={()=>{if(payload)void optimizer.run()}}>Run Live {kind==='TEMPORAL'?'Temporal':'Local'} Optimizer</button>
  <details><summary>Resume a saved optimizer checkpoint</summary><p>Use a terminal {kind} job ID with the same scientific scenario and search. The server validates compatibility; no fresh search is submitted automatically on mismatch. Local detailed budgets may be increased to 4 or 8 including baseline. Retained evidence is reported separately from new computation.</p>
   <label>Saved optimizer job ID <input value={checkpointId} onChange={e=>setCheckpointId(e.target.value)} maxLength={32} autoComplete="off" spellCheck={false}/></label>{' '}
   <button type="button" disabled={!canRun||!/^[a-f0-9]{32}$/.test(checkpointId.trim())} onClick={()=>void optimizer.run('live',false,checkpointId.trim())}>Resume Saved Optimizer</button>
  </details>
  <p role={job.phase==='error'?'alert':'status'}>{job.message}</p>
  {job.accepted&&<p>Job ID: {job.accepted.job_id}; type: {job.accepted.job_type}; request identity: {job.accepted.request_identity}.</p>}
  {job.status&&<><p>Server status: {job.status.status}; stage: {job.status.progress.stage}; progress: {job.status.progress.progress_percent===null?'not reported':`${job.status.progress.progress_percent}%`}. Reasons: {job.status.reason_codes.join(', ')||'none supplied'}.</p>{job.status.error&&<p role="alert">{job.status.error.code}: {job.status.error.message}</p>}{job.status.limitations.map((l,i)=><p key={i}>{l}</p>)}</>}
  {job.failure&&<p role="alert">{job.failure.message} Execution may be unknown; no recorded fallback or automatic resubmission occurred.</p>}
  {job.failure?.issues&&<ul>{job.failure.issues.map((e,i)=><li key={i}>{e.loc.join('.')}: {e.msg}</li>)}</ul>}
  {job.accepted&&!ended&&<div className={styles.controls}><button type="button" onClick={optimizer.stopWaiting}>Stop Waiting for Optimizer</button><button type="button" disabled={job.status?.status==='CANCEL_REQUESTED'} onClick={()=>void optimizer.cancel()}>Request Optimizer Cancellation</button></div>}
  {job.accepted&&['stopped','disconnected','error','terminal'].includes(job.phase)&&<button type="button" onClick={optimizer.retry}>Reconnect to Optimizer</button>}
  {ended&&job.status?.status!=='COMPLETED'&&<button type="button" disabled={!canRun} onClick={()=>void optimizer.run('live',true)}>Resume Optimizer</button>}
  {job.envelope&&!projected&&<p>No validated comparison projection is available for this terminal evidence. Partial or unevaluated candidates are not successful science.</p>}
  {projected&&<details><summary>Search counts, resource accounting and backend recommendations</summary><pre className={styles.metadata}>{JSON.stringify({status:projected.status,generated:projected.raw.generated_alternatives,evaluated:projected.raw.detailed_evaluated_including_baseline,incomplete:projected.raw.scientifically_incomplete_including_baseline,not_evaluated:projected.raw.not_evaluated_alternatives,scope:projected.scope,resources:projected.raw.resources??projected.raw.resource_consumption,new_resources:projected.raw.new_resources??projected.raw.new_scientific_resources,checkpoint_resources:projected.raw.checkpoint_resources??projected.raw.checkpoint_scientific_resources,recommendations:projected.raw.recommendations},null,2)}</pre></details>}
 </div></Panel>{projected&&<EvidenceWorkspace key={projected.scenario} view={projected} activeJob={optimizer.active}/>}</div>
}
