import { SITE_CATALOG } from './siteCatalog'
import { matchesSite, transferReason, visualSiteCoordinate, sourceLongitudeEast, analysisCoordinate } from './siteValidation'
import { safeSourceUrl } from '../analysis-results/validation'
import type { LunarSite } from './siteTypes'
import type { VisualCoordinate } from '../../visualization/coordinates/lunarCoordinates'
import styles from './Sites.module.css'
export function SiteExplorer({latitude,longitude,inspected,onInspect,onView,onUse,sites=SITE_CATALOG}:{latitude:string;longitude:string;inspected:string|null;onInspect:(id:string|null)=>void;onView:(site:LunarSite)=>void;onUse:(point:VisualCoordinate)=>void;sites?:readonly LunarSite[]}) {
 return <section className={styles.explorer} aria-label="South Pole Site Explorer">
  <h2>South Pole Site Explorer</h2>
  <p>Explore documented south-pole references, then plan your own scenario. External research is labeled separately from direct source review. No catalog location is Analysis Ready.</p>
  <p className={styles.notice}>Official document requests remain blocked at the network tunnel (403). Coordinate transfers stay locked until object-specific latitude and frame evidence is reviewed.</p>
  <p>Current location: {sites.find(s=>matchesSite(s,latitude,longitude))?.name ?? 'Custom coordinates / no verified catalog match'}</p>
  <div className={styles.cards}>{sites.map(site=>{
   const visual=visualSiteCoordinate(site),reason=transferReason(site),c=site.coordinate,reference=site.sourceCoordinate,east=reference?sourceLongitudeEast(reference):null
   const documented=site.sources.some(s=>s.review==='DIRECTLY_REVIEWED'&&s.access==='VERIFIED')
   return <article key={site.id} className={styles.card} aria-label={site.name}>
    <header><h3>{site.name}</h3><p>{site.kind==='REGION'?'Region':'Research point'} · Exploration Only</p>
     <p className={styles.badge}>{documented?'Source documented':'External research referenced'} · {reason?'Coordinate compatibility: NOT VERIFIED':'Coordinate Verified'}</p>
    </header>
    {reference?<div className={styles.coordinate} aria-label={`Source reference coordinate — ${site.name}`}>
      <strong>Source coordinate recorded</strong>
      <p>{reference.objectId}: {reference.latitude}° latitude, {reference.longitude}° source longitude.</p>
      <p>Source latitude type: {reference.latitudeType==='UNKNOWN'?'Not established':reference.latitudeType==='PLANETOGRAPHIC'?'Planetographic':'Planetocentric'}. {reference.frame==='UNKNOWN'?'Reference frame not established.':'MOON_ME / DE421 reported via DEM; table compatibility not established.'}</p>
      {east!==null&&<p>East-positive representation: {Number(east.toFixed(8))}°E. Longitude representation only; no latitude or frame conversion.</p>}
      <p>External research — not independently reverified in this task.</p>
      {reference.latitudeType==='PLANETOGRAPHIC'&&<p>USGS source uses planetographic latitude. Direct transfer to the planetocentric backend is disabled. Control network: {reference.controlNetwork}.</p>}
    </div>:<p className={styles.coordinate}>{c?`Reference coordinate: ${c.latitude}° latitude, ${c.longitude}° east. ${c.latitudeType}; ${c.frame}. Backend-input precision only, not an accuracy claim.`:'No verified coordinate supplied; no globe marker is drawn.'}</p>}
    {site.historicalCandidate&&<p>Historical candidate reference: {site.historicalCandidate.year} · {site.historicalCandidate.date}. External research; not a current approved flight target.</p>}
    <div className={styles.actions}>
      <button type="button" aria-pressed={inspected===site.id} onClick={()=>onInspect(inspected===site.id?null:site.id)}>Inspect {site.name}</button>
      <button type="button" disabled={!visual} aria-describedby={`${site.id}-view`} onClick={()=>onView(site)}>View on Globe<span className={styles.sr}> — {site.name}</span></button>
      <button type="button" disabled={reason!==null} aria-describedby={`${site.id}-reason`} onClick={()=>{if(!reason&&analysisCoordinate(site)&&visual)onUse(visual)}}>Use These Coordinates<span className={styles.sr}> — {site.name}</span></button>
    </div>
    <p id={`${site.id}-reason`}>{reason??'Transfers coordinates only; does not start analysis.'}</p>
    <p id={`${site.id}-view`}>{visual?'Visual research reference only; focus preserves mission inputs. Marker size is not a region boundary.':'Globe focus unavailable: no trustworthy visual coordinate reference.'}</p>
    <p className={styles.badge}>Scientific Coverage Unknown · Analysis Unavailable</p>
    <details open={inspected===site.id} onToggle={e=>{if(e.currentTarget.open&&inspected!==site.id)onInspect(site.id);else if(!e.currentTarget.open&&inspected===site.id)onInspect(null)}}><summary>Sources and limitations — {site.name}</summary>
     <p>{site.description}</p><p>{site.context}</p>
     {c&&<p>{c.evidence}</p>}
     {reference&&<><p>Longitude convention: {reference.longitudeConvention}; source frame: {reference.frame}. {reference.section}</p><p>{reference.precisionNote}</p></>}
     {site.sources.map(source=><div key={source.url} className={styles.source}>
      <p>Source: {safeSourceUrl(source.url)?<a href={source.url} target="_blank" rel="noopener noreferrer">{source.name}</a>:source.name}</p>
      {source.documentId&&<p>Document ID: {source.documentId} · Version: {source.version}</p>}
      {!source.documentId&&source.version&&<p>Version: {source.version}</p>}
      <p>Reference year: {source.referenceYear??'Not verified'} · Publication date: {source.publicationDate??'Not verified'} · Retrieval: {source.access==='BLOCKED_403'?'Blocked at tunnel (403)':'Reviewed'}</p><p>{source.section}</p>
      <p>Independent task review: {source.review==='DIRECTLY_REVIEWED'?'Directly reviewed':'Not independently reverified in this task'}. External findings are not direct document inspection.</p>
      {source.history&&<ul>{source.history.map(item=><li key={item}>{item}</li>)}</ul>}
     </div>)}
     <h4>Evidence needed to unlock</h4><ol>{site.unlockRequirements?.map(item=><li key={item}>{item}</li>)}</ol>
     <ul>{site.limitations.map(l=><li key={l}>{l}</li>)}</ul>
     {site.coverage==='LOCAL_EVIDENCE_LIMITED'&&<p>Local raster evidence does not guarantee registration, NoData quality, far-horizon range or kernel time support.</p>}
    </details>
   </article>
  })}</div>
 </section>
}
