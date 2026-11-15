import { expect, it } from 'vitest'
import { PerspectiveCamera, Vector3 } from 'three'
import { localDirection, renderDirection, samplePositions, boundedView } from './directions'
import { checkHorizons } from '../../features/analysis-results/validation'
import { scientificFixture } from '../../test/scientificFixtures'

it.each([[0,[0,0,1]],[90,[1,0,0]],[180,[0,0,-1]],[270,[-1,0,0]]] as const)('ENU azimuth %s at horizon', (az, expected) => {
  localDirection(az, 0).forEach((v, i) => expect(v).toBeCloseTo(expected[i]!))
})
it.each([-90,-30,0,30,90])('preserves elevation %s and unit length', el => {
  const direction=localDirection(25,el)
  expect(direction[1]).toBeCloseTo(Math.sin(el*Math.PI/180));expect(Math.hypot(...direction)).toBeCloseTo(1)
})
it.each([[360,0],[-1,0],[NaN,0],[0,Infinity],[0,91],[0,-91]])('rejects invalid angles %s %s', (az,el)=>expect(()=>localDirection(az,el)).toThrow())
it('renderer handedness puts East on the right of a north-facing camera',()=>{
  const camera=new PerspectiveCamera(75,1,.1,20);camera.lookAt(...renderDirection(0,0));camera.updateMatrixWorld()
  expect(new Vector3(...renderDirection(30,0)).project(camera).x).toBeGreaterThan(0)
  expect(new Vector3(...renderDirection(330,0)).project(camera).x).toBeLessThan(0)
  expect(new Vector3(...renderDirection(0,30)).project(camera).y).toBeGreaterThan(0)
})
it('uses all the same validated 2D samples; null is omitted, zero retained, no closure vertex',()=>{
  const checked=checkHorizons(scientificFixture().horizons);expect(checked.kind).toBe('valid')
  if(checked.kind!=='valid')throw new Error('fixture invalid')
  const profile=checked.value[0]!,original=JSON.stringify(profile),positions=samplePositions(profile)
  expect(positions).toHaveLength(9)
  expect([...positions.slice(0,3)]).toEqual([0,0,-10])
  expect(JSON.stringify(profile)).toBe(original)
  expect(samplePositions(null)).toHaveLength(0)
  expect(samplePositions({...profile,points:[{azimuth_deg:0,elevation_deg:null},{azimuth_deg:359,elevation_deg:null}]})).toHaveLength(0)
})
it('does not append a wrap vertex between 359 degrees and zero',()=>{
  const profile={id:'test',observer_height_m:1,range_m:100,coverage_complete:false,dem_source_ids:[],points:[{azimuth_deg:0,elevation_deg:0},{azimuth_deg:359,elevation_deg:1}]}
  expect(samplePositions(profile)).toHaveLength(6)
})
it('bounds camera pitch and FOV without moving the observer',()=>{
  expect(boundedView({azimuth:-90,elevation:100,fov:200})).toEqual({azimuth:270,elevation:85,fov:100})
  expect(boundedView({azimuth:720,elevation:-100,fov:0})).toEqual({azimuth:0,elevation:-85,fov:35})
  expect(()=>boundedView({azimuth:0,elevation:NaN,fov:75})).toThrow()
})
