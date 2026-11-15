import { record } from '../../services/api/responses'
import { lazy,Suspense,useMemo,useRef,useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Panel } from '../../components/Panel'
import { LoadingState } from '../../components/States'
import { GlobeBoundary } from '../../visualization/globe/GlobeBoundary'
import type { SiteFocus } from '../../visualization/globe/GlobeControls'
import { eastLongitudeToVisual } from '../mission-input/coordinates'
import { safeSourceUrl } from '../analysis-results/validation'
import { useScenario } from '../scenario/ScenarioProvider'
import type { EvidenceView } from './evidence'
import { Radar } from './Radar'
import { CandidateCard,Comparison,show } from './Comparison'
import styles from './Explorer.module.css'
function sourceLinks(value:unknown):string[]{const urls=new Set<string>();function walk(v:unknown){if(Array.isArray(v))v.forEach(walk);else if(record(v))for(const [key,x]of Object.entries(v)){if(['url','source_url','frame_evidence_source'].includes(key)&&typeof x==='string'){const safe=safeSourceUrl(x);if(safe)urls.add(safe)}else if(typeof x==='object'&&x!==null)walk(x)}}walk(value);return [...urls]}
const LunarGlobe=lazy(()=>import('../../visualization/globe/LunarGlobe'))
export function EvidenceWorkspace({view,activeJob=false}:{view:EvidenceView;activeJob?:boolean}){
 const [id,setId]=useState(()=>{const recs=Array.isArray(view.raw.recommendations)?view.raw.recommendations:[];const first=recs.find(r=>record(r)&&view.alternatives.some(c=>c.id===r.candidate_id));return record(first)?String(first.candidate_id):view.alternatives[0]?.id??null}),[globe,setGlobe]=useState(false),[focus,setFocus]=useState<SiteFocus|null>(null)
 const sequence=useRef(0),navigate=useNavigate(),scenario=useScenario()
 const recommended=useMemo(()=>new Set((Array.isArray(view.raw.recommendations)?view.raw.recommendations:[]).flatMap(r=>record(r)&&typeof r.candidate_id==='string'?[r.candidate_id]:[])),[view.raw])
 const [onlyRecommended,setOnlyRecommended]=useState(true)
 const shown=onlyRecommended&&recommended.size?view.alternatives.filter(c=>recommended.has(c.id)):view.alternatives
 const selected=view.alternatives.find(c=>c.id===id)??null
 const all=useMemo(()=>[view.baseline,...view.alternatives],[view])
 const markers=useMemo(()=>all.flatMap(c=>c.location?[{id:c.id,latitude:c.location.latitude_deg,longitude:eastLongitudeToVisual(c.location.longitude_deg_east),baseline:c.id===view.baseline.id}]:[]),[all,view.baseline.id])
 function choose(next:string){const c=all.find(c=>c.id===next);if(!c)return;setId(next);if(recommended.size&&!recommended.has(next))setOnlyRecommended(false);if(c.location)setFocus({kind:'site',coordinate:{latitude:c.location.latitude_deg,longitude:eastLongitudeToVisual(c.location.longitude_deg_east),radius:1},sequence:++sequence.current})}
 const isLocal=view.dimension==='COORDINATES_AND_DEM_SURFACE_ONLY',test=view.scientificOrigin==='TEST_FIXTURE'||view.scientificOrigin==='SYNTHETIC'
 return <div className={styles.workspace}>
  <div className={styles.notice} role="note"><strong>{test?'TEST DATA':view.mode==='recorded'?'RECORDED EVIDENCE':view.origin==='PRECOMPUTED'?'PRECOMPUTED PROTOTYPE':view.origin==='LIVE_COMPUTED'?'LIVE PROTOTYPE':'PROTOTYPE — ORIGIN UNKNOWN'}</strong><p>{view.mode==='recorded'?'Exported from previously evaluated NASA-source prototype calculations. No new calculation was performed.':view.origin==='PRECOMPUTED'?'Backend reports replayed evidence; this is not wholly new live computation.':view.origin==='LIVE_COMPUTED'?'Computed by the current bounded scientific backend. Independent scientific certification remains incomplete. Candidate evidence may include checkpoint replay; inspect new and retained resource counters.':'Backend origin is unknown; no new live computation is inferred.'}</p><p>Delivery: {view.origin??'Unknown (null)'}. Original scientific origin: {view.scientificOrigin??'Unknown (null)'}. Status: {view.status}.</p></div>
  <Panel title={isLocal?'Same Time. Better Site.':'Same Site. Better Time.'}><div className={styles.content}>
   <p>{view.scenario} · {view.dimension}. {isLocal?'Recorded search history and live search settings remain separate.':'Only operation start UTC changes within this comparison.'}</p>
   {isLocal&&<p>Reported search radius: {show((record(view.raw.request)?view.raw.request:record(view.raw.source_optimizer_request)?view.raw.source_optimizer_request:{}).search_radius_m)} m. The radar display uses a fixed 5 km outer ring; display scale does not expand the reported search.</p>}
   <div className={isLocal?styles.grid:undefined}>
    {isLocal&&<Radar baseline={view.baseline} candidates={shown} selected={id} onSelect={choose}/>}
    <section aria-label="Alternative candidates"><h3>{isLocal?'Nearby Candidate Sites':'Alternative Start Times'}</h3>
     {recommended.size>0&&<label><input type="checkbox" checked={onlyRecommended} onChange={e=>setOnlyRecommended(e.target.checked)}/> Show backend recommendations only</label>}
     <p>Showing {shown.length} of {view.alternatives.length} supplied alternatives. Filters change presentation only, not the evaluated search.</p>
     {view.alternatives.length===0?<p>No alternatives supplied (empty array). No recommendations inferred.</p>:<ol className={styles.list}>{shown.map((c,i)=><li key={c.id}><button type="button" aria-pressed={id===c.id} onClick={()=>choose(c.id)}>
      {isLocal?`Candidate ${i+1} · ${show(c.distance)} m · bearing ${show(c.bearing)}°`:c.utc??'UTC unavailable'}<br/>{c.decision?.status??c.status} · {c.score?.value===null||c.score===null?'Score not calculated':`${show(c.score.value)} / 100`}<br/>ID: {c.id}
     </button></li>)}</ol>}
    </section>
   </div>
   <button type="button" onClick={()=>{setGlobe(v=>!v);if(!globe&&selected)choose(selected.id)}}>{globe?'Hide candidate globe':'Show candidate globe'}</button>
   {globe&&<><p>White: baseline; amber: selected alternative; cyan: other candidates. Markers may overlap at global scale. Use the radar/list for close locations. This is visual scale, not a region boundary.</p><GlobeBoundary><Suspense fallback={<LoadingState>Loading candidate globe.</LoadingState>}><LunarGlobe selected={selected?.location?{latitude:selected.location.latitude_deg,longitude:eastLongitudeToVisual(selected.location.longitude_deg_east),radius:1}:null} onSelect={()=>{}} siteFocus={focus} candidates={markers} selectedCandidate={id} onSelectCandidate={choose}/></Suspense></GlobeBoundary></>}
  </div></Panel>
  <Panel title="A/B Scenario Comparison"><div className={styles.content}>
   <div className={styles.grid}><CandidateCard candidate={view.baseline} title="Baseline"/>{selected?<CandidateCard candidate={selected} title="Selected Alternative"/>:<p>No selected alternative.</p>}</div>
   <Comparison baseline={view.baseline} alternative={selected}/>
   {selected&&<><p>Full horizon profile is not included in this optimizer summary. Time series unavailable in this export. No event UTC or visibility windows are inferred from duration metrics.</p>
   <button type="button" disabled={!selected.input||activeJob} onClick={()=>{if(selected.input&&scenario.applyCandidateRequest(selected.input.source,selected.input.explicit,selected.id))navigate('/')}}>Load Candidate Parameters</button>
   <p>{activeJob?'Stop waiting before transferring candidate inputs. The backend job may still continue.':'Loading parameters invalidates previous analysis and stops local waiting. A previous backend calculation may continue; no cancellation or new POST is automatic.'}</p></>}
  </div></Panel>
  <Panel title="Data Quality and Source Evidence"><div className={styles.content}>
   <p className={styles.notice}>Sampled visibility is not continuous physical certification. Planning Score is not success probability. Solar visibility is not electrical power; Earth visibility is not RF link success. DEM slope is not landing safety. Absolute DEM registration and independent astronomy configuration equivalence remain unverified. A finite search is not a global optimum.</p>
   {view.limitations.map((l,i)=><p key={i}>{l}</p>)}
   {selected?.quality&&<p>Selected quality: {selected.quality.status}; coverage complete: {show(selected.quality.coverage_complete)}.</p>}
   <details><summary>Quality limitations, explicit requirements and source provenance</summary>
    {selected?.quality?.limitations.map((l,i)=><p key={i}>{l}</p>)}{selected?.limitations.map((l,i)=><p key={`l${i}`}>{l}</p>)}
    <p>Source identity: {selected?.sourceIdentity??'Not separately supplied; comparisons check supplied source metadata'}. Window evidence SHA-256: {selected?.hash??'Unavailable'}.</p>
    <p>Explicit requirement fields: {selected?.input?.explicit.join(', ')??'Unavailable'}. SHA-256 text and source references do not independently certify authenticity.</p>
    {Object.entries(view.provenance).filter(([,v])=>typeof v==='string').map(([k,v])=><p key={k}>{k}: {String(v)}</p>)}
    <pre className={styles.metadata}>{JSON.stringify(view.provenance,null,2)}</pre>
    <pre className={styles.metadata}>{JSON.stringify(view.scope,null,2)}</pre>
    <pre className={styles.metadata}>{JSON.stringify(selected?.metrics??null,null,2)}</pre>
    {selected?.terrain&&<pre className={styles.metadata}>{JSON.stringify(selected.terrain.raw,null,2)}</pre>}
    <ul>{sourceLinks(view.provenance).map(url=><li key={url}><a href={url} target="_blank" rel="noreferrer">{url}</a></li>)}</ul>
   </details>
  </div></Panel>
 </div>
}
