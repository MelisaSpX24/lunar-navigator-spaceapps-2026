import { useRef } from 'react'
import { toCartesian } from '../coordinates/lunarCoordinates'
export type GlobeCandidate={id:string;latitude:number;longitude:number;baseline:boolean}
/** Recorded/evaluated coordinates, not region boundaries or certified landing sites. */
export function CandidateMarkers({candidates,selected,onSelect}:{candidates:GlobeCandidate[];selected:string|null;onSelect:(id:string)=>void}){
 const start=useRef<{x:number;y:number}|null>(null)
 return <group name="evaluated-candidate-markers">{candidates.map(c=>{const p=toCartesian(c.latitude,c.longitude,1.028);return <mesh key={c.id} name={`candidate-${c.id}`} position={[p.x,p.y,p.z]}
  onPointerDown={e=>{e.stopPropagation();start.current={x:e.clientX,y:e.clientY}}}
  onClick={e=>{e.stopPropagation();const down=start.current;start.current=null;if(down&&e.delta<=5&&Math.hypot(e.clientX-down.x,e.clientY-down.y)<=5)onSelect(c.id)}}>
  <octahedronGeometry args={[c.id===selected? .016:.011,0]}/><meshBasicMaterial color={c.baseline?'#f3f1ff':c.id===selected?'#e9ca88':'#8cdee6'}/>
 </mesh>})}</group>
}
