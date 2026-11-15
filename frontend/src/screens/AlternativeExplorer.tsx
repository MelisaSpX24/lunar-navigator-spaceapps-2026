import { useMemo,useState } from 'react'
import recorded from 'virtual:recorded-evidence'
import { PageHeading } from '../components/PageHeading'
import { Panel } from '../components/Panel'
import { recordedEvidence } from '../features/alternative-explorer/evidence'
import { EvidenceWorkspace } from '../features/alternative-explorer/EvidenceWorkspace'
import { LiveExplorer } from '../features/alternative-explorer/LiveExplorer'
import type { OptimizerKind } from '../features/alternative-explorer/live'
import styles from '../features/alternative-explorer/Explorer.module.css'
export function AlternativeExplorer(){
 const [mode,setMode]=useState<'recorded'|'live'>('recorded'),[kind,setKind]=useState<OptimizerKind>('TEMPORAL')
 const result=useMemo(()=>{try{return {view:recordedEvidence(kind==='TEMPORAL'?recorded.temporal:recorded.local,kind==='TEMPORAL'?'temporal':'local'),error:null}}catch(e){return {view:null,error:e instanceof Error?e.message:'Invalid recorded evidence'}}},[kind])
 return <div className={styles.workspace}>
  <PageHeading title="Alternative Explorer" workspace="EXPLORATION WORKSPACE" subtitle="Find a better time. Discover a better location." status={mode==='recorded'?'Recorded Evidence':'Live Optimizer'}/>
  <Panel title="Explore alternatives"><div className={`${styles.content} ${styles.controls}`}>
   <label htmlFor="explorer-scenario">Scenario</label><select id="explorer-scenario" value={kind} onChange={e=>setKind(e.target.value==='LOCAL'?'LOCAL':'TEMPORAL')}><option value="TEMPORAL">Temporal — Better Start Time</option><option value="LOCAL">Local — Better Site</option></select>
   <label htmlFor="explorer-mode">Data mode</label><select id="explorer-mode" value={mode} onChange={e=>setMode(e.target.value==='live'?'live':'recorded')}><option value="recorded">Recorded Evidence</option><option value="live">Live Optimizer</option></select>
   <p>Temporal and local scenarios have different durations and cannot be cross-compared. Recorded evidence works without a backend. Live optimizer work is always explicit.</p>
  </div></Panel>
  {mode==='recorded'?result.view?<EvidenceWorkspace key={result.view.scenario} view={result.view}/>:<p role="alert">Recorded evidence unavailable: {result.error}</p>:<LiveExplorer key={kind} kind={kind}/>}
 </div>
}
