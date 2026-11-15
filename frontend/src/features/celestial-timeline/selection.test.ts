import { expect, it } from 'vitest'
import { scientificFixture } from '../../test/scientificFixtures'
import { checkSeries, checkHorizons } from '../analysis-results/validation'
import { timeBounds, utcStamp } from '../analysis-results/utc'
import { exactSample, hasDirection, horizonRelation, sliderStamp, stampAt } from './selection'
import { pathPositions } from '../../visualization/local-horizon/CelestialLayer'
const bounds=timeBounds('2026-11-14T12:30:00Z',3600)
it('uses exact UTC samples only and withholds sparse intermediate times',()=>{
 const data=checkSeries(scientificFixture().series,'sun',bounds)
 expect(exactSample(data,bounds.start)?.body.disk_state).toBe('NONE')
 expect(exactSample(data,sliderStamp(1,bounds))).toBeNull()
 expect(exactSample(data,utcStamp('2026-11-14T12:40:00Z'))?.body.condition_met).toBeNull()
 expect(exactSample(data,bounds.end)).toBeNull()
})
it.each(['0001-01-01T00:00:00.000001Z','1969-12-31T23:59:59.999999Z','2026-11-14T12:30:00.123456Z','9999-12-31T23:59:59.999999Z'])('preserves microsecond UTC %s',text=>{const s=utcStamp(text)!;expect(utcStamp(stampAt(s.tick).text)?.tick).toBe(s.tick)})
it('slider spans the complete operation without out-of-range selections',()=>{
 expect(sliderStamp(0,bounds).tick).toBe(bounds.start.tick);expect(sliderStamp(10000,bounds).tick).toBe(bounds.end.tick)
 for(const p of [-1,10001,NaN,Infinity,.5])expect(()=>sliderStamp(p,bounds)).toThrow()
})
it.each([null,[]])('null/empty %j never gives a sample',series=>expect(exactSample(checkSeries(series,'sun',bounds),bounds.start)).toBeNull())
it.each(['sun','earth'] as const)('invalid %s does not invalidate the other body',body=>{
 const r=scientificFixture(),rows=r.series as {sun:{azimuth_deg:number};earth:{azimuth_deg:number}}[]
 rows[0]![body].azimuth_deg=360
 expect(checkSeries(rows,body,bounds).kind).toBe('invalid')
 expect(checkSeries(rows,body==='sun'?'earth':'sun',bounds).kind).toBe('valid')
})
it.each(['2026-02-30T12:30:00Z','2026-11-14T12:29:00Z','2026-11-14T13:31:00Z'])('rejects malformed or out-of-operation UTC %s',time=>{
 const rows=scientificFixture().series as {time_utc:string}[];rows[0]!.time_utc=time
 expect(checkSeries(rows,'sun',bounds).kind).toBe('invalid')
})
it('paths retain exact 359/0 points and omit unknown directions without line vertices',()=>{
 const data=checkSeries(scientificFixture().series,'sun',bounds);if(data.kind!=='valid')throw Error()
 const rows=data.value;rows[0]!.body.azimuth_deg=359;rows[2]!.body.azimuth_deg=0
 const points=pathPositions(rows);expect(points.length).toBe(6);expect(points[0]).toBeLessThan(0);expect(points[3]).toBe(0)
 expect(hasDirection(rows[1]!.body)).toBe(false)
 expect(rows[1]!.body.disk_state).toBe('UNKNOWN');expect(rows[0]!.body.condition_met).toBe(false)
})
it('distinguishes matching, different, absent and null horizon IDs',()=>{
 const r=scientificFixture(),data=checkSeries(r.series,'sun',bounds),profiles=checkHorizons(r.horizons)
 if(data.kind!=='valid'||profiles.kind!=='valid')throw Error()
 const b=data.value[0]!.body
 expect(horizonRelation(b,profiles.value,'controlled-horizon-low')).toContain('active')
 expect(horizonRelation(b,profiles.value,'controlled-horizon-high')).toContain('different')
 expect(horizonRelation(b,[],null)).toContain('unavailable')
 expect(horizonRelation({...b,horizon_id:null},profiles.value,null)).toContain('unknown')
})

it('emits controlled celestial fixture for read-only backend model cross-validation',async()=>{
 const {celestialFixture}=await import('../../test/celestialFixture')
 const {writeFileSync,mkdirSync}=await import('node:fs')
 mkdirSync('.validation',{recursive:true})
 writeFileSync('.validation/celestial-fixture.json',JSON.stringify(celestialFixture(),null,2))
 expect(celestialFixture().data_origin).toBe('TEST_FIXTURE')
})
