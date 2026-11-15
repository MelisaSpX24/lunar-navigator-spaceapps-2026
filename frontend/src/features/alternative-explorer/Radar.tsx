import type { EvidenceCandidate } from './evidence'
import { radarPoint } from './evidence'
import styles from './Explorer.module.css'
export function Radar({baseline,candidates,selected,onSelect}:{baseline:EvidenceCandidate;candidates:EvidenceCandidate[];selected:string|null;onSelect:(id:string)=>void}){
 return <div><h3>Local Search Polar Radar</h3><p>North-up, east-right. Supplied distance and clockwise bearing; fixed 5 km display. Marker size is illustrative, not terrain or region size.</p>
 <svg className={styles.radar} viewBox="-250 -250 500 500" role="group" aria-label="Local search radar — evaluated candidate positions">
  <title>Local candidates relative to the baseline</title>
  {[1000,3000,5000].map(r=><g key={r}><circle r={r/5000*200} className={styles.ring}/><text x="6" y={-r/5000*200+18}>{r/1000} km</text></g>)}
  <path d="M -200 0 H 200 M 0 -200 V 200" className={styles.ring}/>
  <text x="-7" y="-225">N</text><text x="225" y="6">E</text><text x="-7" y="236">S</text><text x="-237" y="6">W</text>
  <rect x="-5" y="-5" width="10" height="10" fill="#f4efff"/><text x="12" y="20">Baseline</text>
  {candidates.map((c,i)=>{const p=c.distance!==null&&c.bearing!==null?radarPoint(c.distance,c.bearing):null;return p?<g key={c.id} role="button" tabIndex={0} aria-pressed={c.id===selected} aria-label={`Select candidate ${i+1}: ${c.distance!.toFixed(1)} metres, bearing ${c.bearing!.toFixed(2)} degrees`} onClick={()=>onSelect(c.id)} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();onSelect(c.id)}}} className={styles.radarMarker} transform={`translate(${p.x} ${p.y})`}>
    <title>{c.id}: {c.distance!.toFixed(1)} m, {c.bearing!.toFixed(2)}°; {c.decision?.status??c.status}</title><circle r="36" fill="transparent"/><circle r={c.id===selected?9:6} fill={c.id===selected?'#e9ca88':'#8cdee6'}/><text x={p.x>150?-35:14} y={i===2?26:-12}>{i+1}</text>
   </g>:null})}
 </svg><p>Baseline: {baseline.location?.latitude_deg}°, {baseline.location?.longitude_deg_east}° E. Unknown positions are not plotted. Finite evaluated candidates do not establish a global optimum.</p></div>
}
