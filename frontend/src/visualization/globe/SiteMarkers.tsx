import { useRef } from 'react'
import { SITE_CATALOG } from '../../features/lunar-sites/siteCatalog'
import { visualSiteCoordinate } from '../../features/lunar-sites/siteValidation'
import { toCartesian } from '../coordinates/lunarCoordinates'

const markers=SITE_CATALOG.flatMap(site=>{
 const coordinate=visualSiteCoordinate(site)
 return coordinate?[{id:site.id,position:toCartesian(coordinate.latitude,coordinate.longitude!,1.025)}]:[]
})
/** Marker clicks inspect catalog metadata only; sphere picking must not receive them. */
export function SiteMarkers({onInspect}:{onInspect:(id:string)=>void}) {
 const down=useRef<{x:number;y:number}|null>(null)
 return <group name="catalog-research-references">{markers.map(m=><mesh key={m.id} name={`site-${m.id}`} position={[m.position.x,m.position.y,m.position.z]}
  onPointerDown={e=>{e.stopPropagation();down.current={x:e.clientX,y:e.clientY}}}
  onClick={e=>{e.stopPropagation();const start=down.current;down.current=null;if(start&&e.delta<=5&&Math.hypot(e.clientX-start.x,e.clientY-start.y)<=5)onInspect(m.id)}}>
  <octahedronGeometry args={[.013,0]}/><meshBasicMaterial color="#e6c183"/>
 </mesh>)}</group>
}
