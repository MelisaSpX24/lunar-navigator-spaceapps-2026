import { scientificFixture } from './scientificFixtures'
import type { BodySample } from '../features/analysis-results/types'
// Deliberately synthetic directions, not an astronomical orbit or NASA measurement.
export function celestialFixture() {
 const r=scientificFixture()
 const rows=r.series as {sun:BodySample;earth:BodySample}[]
 for(const [i,row] of rows.entries()) {
  row.sun={...row.sun,azimuth_deg:[359,0,20][i]!,elevation_deg:[10,15,20][i]!,disk_state:'PARTIAL',disk_visible_fraction:.25,condition_met:false}
  row.earth={...row.earth,azimuth_deg:[10,20,30][i]!,elevation_deg:[12,17,22][i]!,horizon_id:'controlled-horizon-high'}
 }
 return r
}
