import { expect, it } from 'vitest'
import type { HorizonProfile } from '../../features/analysis-results/types'
import { traceSegments } from './trace'
import { renderDirection } from './directions'
const profile=(points: [number,number|null][]):HorizonProfile=>({id:'p',observer_height_m:1,range_m:1000,coverage_complete:true,dem_source_ids:[],points:points.map(([azimuth_deg,elevation_deg])=>({azimuth_deg,elevation_deg}))})
it.each([null,profile([]),profile([[0,0]]),profile([[0,null],[1,null]])])('never creates a trace from absent/single/unknown data',p=>expect(traceSegments(p).length).toBe(0))
it('joins only adjacent known samples and preserves zero and negative elevation',()=>{
 const p=profile([[0,-2],[1,0],[2,null],[3,1],[4,2]]),original=JSON.stringify(p)
 const result=traceSegments(p)
 expect(result.length).toBe(12)
 expect(Array.from(result.slice(0,3))).toEqual(renderDirection(0,-2).map(Math.fround))
 expect(Array.from(result.slice(3,6))).toEqual(renderDirection(1,0).map(Math.fround))
 expect(JSON.stringify(p)).toBe(original)
})
it('rejects absolute and anomalous cadence gaps without seam closure',()=>{
 expect(traceSegments(profile([[0,1],[90,2],[180,3],[359,1]])).length).toBe(0)
 expect(traceSegments(profile([[0,1],[.1,2],[4,3],[4.1,4]])).length).toBe(12)
 expect(traceSegments(profile([[0,1],[1,2],[358,2],[359,1]])).length).toBe(12)
})
it('does not infer continuity from coverage complete',()=>{
 const p=profile([[0,1],[180,2]])
 expect(traceSegments(p).length).toBe(0);p.coverage_complete=false;expect(traceSegments(p).length).toBe(0)
})
