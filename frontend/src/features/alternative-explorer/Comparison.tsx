import { comparisonCompatible,delta,utcShift,type EvidenceCandidate } from './evidence'
import styles from './Explorer.module.css'
export const show=(v:unknown)=>v===null||v===undefined?'Unavailable (null)':typeof v==='number'?new Intl.NumberFormat('en',{maximumFractionDigits:3}).format(v):String(v)
export function seconds(v:number|null){if(v===null)return 'Unavailable (null)';const sign=v<0?'−':v>0?'+':'';let n=Math.abs(v);const days=Math.floor(n/86400);n%=86400;const hours=Math.floor(n/3600);n%=3600;const minutes=Math.floor(n/60);const secs=n%60;return `${sign}${days?`${days}d `:''}${hours}h ${minutes}m ${show(secs)}s`}
export function CandidateCard({candidate,title}:{candidate:EvidenceCandidate;title:string}){
 const c=candidate
 return <section aria-label={title} className={styles.card}><h3>{title}</h3><p className={styles.badge}>{c.decision?.status??'INCOMPLETE / not evaluated'}</p><p className={styles.score}>{c.score?.value===null||c.score===null?'Not calculated':!c.score.model_version?'Score withheld — model version unavailable':`${show(c.score.value)} / 100`}</p>
 <p>Evaluation: {c.status}. Origin: {c.origin??'Unknown (null)'}</p><p>UTC: {c.utc??'Unavailable'}</p><p>Duration: {c.input?`${c.input.request.time.duration_s} seconds`:'Unavailable'}</p><p>Coordinate: {c.location?`${c.location.latitude_deg}°, ${c.location.longitude_deg_east}° E`:'Unavailable'}</p>
 {c.dimension==='COORDINATES_AND_DEM_SURFACE_ONLY'&&<p>Distance: {show(c.distance)} m; bearing: {show(c.bearing)}°. Slope: {show(c.terrain?.slope_deg)}°; surface elevation: {show(c.terrain?.surface_elevation_m)} m; source resolution: {c.terrain?.resolution_m?.join(' × ')??'Unavailable'} m. Slope is not landing safety.</p>}
 <p>Quality: {c.quality?.status??'NOT_ASSESSED'}; coverage: {show(c.quality?.coverage_complete)}. Score model: {c.score?.model_version??'Unavailable'}.</p>
 </section>
}
export function Comparison({baseline,alternative}:{baseline:EvidenceCandidate;alternative:EvidenceCandidate|null}){
 if(!alternative)return <p>No alternative selected. No comparison has been performed.</p>
 if(!comparisonCompatible(baseline,alternative))return <p role="alert">Comparison unavailable — scientifically incompatible scenarios.</p>
 const rows:[string,number|null,number|null,string][]=[['Planning Score',baseline.score?.value??null,alternative.score?.value??null,'points']]
 for(const body of ['sun','earth','joint'] as const)for(const [key,label] of [['estimated_duration_s','sampled visibility'],['estimated_longest_continuous_s','sampled longest continuous'],['estimated_interruption_s','sampled interruption'],['estimated_longest_interruption_s','sampled longest interruption'],['unknown_duration_s','unknown duration']] as const)rows.push([`${body} ${label}`,baseline.metrics?.[body][key]??null,alternative.metrics?.[body][key]??null,'s'])
 return <section aria-label="A/B Comparison"><h3>Why is this alternative better?</h3><p>Decision: {baseline.decision?.status} → {alternative.decision?.status}. This is a finite sampled comparison, not a global optimum or mission success probability.</p>
 <p>Scroll the comparison table horizontally on narrow screens; it is also keyboard accessible.</p>
 <div className={styles.tableWrap} tabIndex={0} role="region" aria-label="Scrollable comparison table"><table><caption>Same-scenario backend evidence — alternative minus baseline</caption><thead><tr><th scope="col">Metric</th><th scope="col">Baseline</th><th scope="col">Alternative</th><th scope="col">Delta</th></tr></thead><tbody>{rows.map(([label,a,b,unit])=><tr key={label}><th scope="row">{label}</th><td>{show(a)} {unit}</td><td>{show(b)} {unit}</td><td>{unit==='s'?seconds(delta(a,b)):`${delta(a,b)!>0?'+':''}${show(delta(a,b))} ${unit}`}</td></tr>)}</tbody></table></div>
 <p>UTC shift: {seconds(utcShift(baseline,alternative))}. Distance from baseline: {show(alternative.distance)} m; distance delta: {show(delta(baseline.distance,alternative.distance))} m. Supplied baseline-to-candidate bearing: {show(alternative.bearing)}°. A null baseline bearing is not zero.</p>
 <h4>Mandatory requirements</h4>{baseline.rules?.map(e=>{const other=alternative.rules?.find(r=>r.rule.code===e.rule.code);return <div key={e.rule.code} className={styles.rule}><p><strong>{e.rule.code}</strong>: {e.rule.status} → {other?.rule.status??'INCOMPLETE / missing'}.</p><p>Required: {show(e.rule.required)} {e.unit}; actual: {show(e.rule.actual)} → {show(other?.rule.actual)} {e.unit}.</p><p>{other?.rule.message??'No matching rule evidence; no resolution inferred.'}</p><p>Evidence: {e.evidence_status}; source metric: {e.source_metric}.</p></div>})??<p>Rule evidence unavailable; no requirement resolution inferred.</p>}
 </section>
}
