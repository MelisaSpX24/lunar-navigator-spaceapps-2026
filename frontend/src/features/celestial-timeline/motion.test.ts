import { describe, expect, it } from 'vitest'
import { celestialFixture } from '../../test/celestialFixture'
import { checkSeries } from '../analysis-results/validation'
import { timeBounds, utcStamp } from '../analysis-results/utc'
import type { BodySample } from '../analysis-results/types'
import { lowerBound, prepareMotion, visualPosition } from './motion'
import { renderDirection } from '../../visualization/local-horizon/directions'
const bounds = timeBounds('2026-11-14T12:30:00Z', 3600)
const ids = new Set(['controlled-horizon-low','controlled-horizon-high'])
function fixture() { return celestialFixture() }
function track(r = fixture(), body: 'sun' | 'earth' = 'sun') { return prepareMotion(checkSeries(r.series, body, bounds), ids) }
const at = (time = '2026-11-14T12:35:00Z') => utcStamp(time)!
type Row = { time_utc: string; sun: BodySample; earth: BodySample }
const rows = (r: ReturnType<typeof fixture>) => r.series as Row[]
describe('guarded display-only SLERP', () => {
  it.each([[359,1],[1,359]])('takes the short north crossing %s to %s without changing scientific fields', (a,b) => {
    const r=fixture(); rows(r)[0]!.sun.azimuth_deg=a; rows(r)[1]!.sun.azimuth_deg=b
    rows(r)[0]!.sun.elevation_deg=0; rows(r)[1]!.sun.elevation_deg=0
    const before=JSON.stringify(r), p=visualPosition(track(r),at(),true)
    expect(p.kind).toBe('interpolated')
    if(p.kind!=='interpolated')throw Error()
    expect(p.direction[0]).toBeCloseTo(0,10); expect(p.direction[2]).toBeCloseTo(-1,10)
    expect(Math.hypot(...p.direction)).toBeCloseTo(1,10)
    expect(Object.keys(p).sort()).toEqual(['direction','from','horizonId','kind','to'])
    expect(JSON.stringify(r)).toBe(before)
  })
  it('keeps exact samples authoritative with smooth on or off and does not extrapolate',()=>{
    const t=track()
    for(const smooth of [false,true])expect(visualPosition(t,bounds.start,smooth)).toEqual({kind:'sample',direction:renderDirection(359,10,1),horizonId:'controlled-horizon-low'})
    expect(visualPosition(t,at(),false).kind).toBe('unavailable')
    expect(visualPosition(t,bounds.end,true).kind).toBe('unavailable')
  })
  it.each(['azimuth_deg','elevation_deg'] as const)('never skips a null %s neighbor',key=>{
    const r=fixture(); rows(r)[1]!.sun[key]=null
    expect(visualPosition(track(r),at(),true).kind).toBe('unavailable')
    expect(visualPosition(track(r),at('2026-11-14T12:45:00Z'),true).kind).toBe('unavailable')
    expect(visualPosition(track(r,'earth'),at(),true).kind).toBe('interpolated')
  })
  it.each([null,'missing-profile','controlled-horizon-high'])('blocks unknown or changing horizon %s',id=>{
    const r=fixture(); rows(r)[0]!.sun.horizon_id=id
    expect(visualPosition(track(r),at(),true).kind).toBe('unavailable')
  })
  it.each([90,180,200])('rejects large/ambiguous endpoint separation %s',az=>{
    const r=fixture(); rows(r)[1]!.sun.azimuth_deg=az
    expect(visualPosition(track(r),at(),true).kind).toBe('unavailable')
  })
  it('rejects absolute and anomalous cadence gaps',()=>{
    const r=fixture(); rows(r)[1]!.time_utc='2026-11-14T12:41:00Z'
    expect(visualPosition(track(r),at(),true).kind).toBe('unavailable')
    rows(r)[1]!.time_utc='2026-11-14T12:30:10Z'; rows(r)[2]!.time_utc='2026-11-14T12:35:00Z'
    rows(r)[2]!.sun.azimuth_deg=1
    expect(visualPosition(track(r),at('2026-11-14T12:32:00Z'),true).kind).toBe('unavailable')
  })
  it('handles identical directions without division by zero',()=>{
    const r=fixture(); rows(r)[1]!.sun={...rows(r)[0]!.sun}
    const p=visualPosition(track(r),at(),true)
    expect(p.kind).toBe('interpolated');if(p.kind==='interpolated')p.direction.forEach((n,i)=>expect(n).toBeCloseTo(renderDirection(359,10,1)[i]!,12))
  })
  it.each(['sun','earth'] as const)('invalid %s leaves the other body independent',body=>{
    const r=fixture();rows(r)[0]![body].elevation_deg=Infinity
    expect(visualPosition(track(r,body),at(),true).kind).toBe('unavailable')
    expect(visualPosition(track(r,body==='sun'?'earth':'sun'),at(),true).kind).toBe('interpolated')
  })
  it.each([null,[]])('does not manufacture positions from %j',series=>{
    const r=fixture();r.series=series
    expect(visualPosition(track(r),at(),true).kind).toBe('unavailable')
  })
  it('one sample stays a sample, never a segment',()=>{
    const r=fixture();r.series=r.series!.slice(0,1);const t=track(r)
    expect(t.known).toBe(1);expect(t.supportedSegments).toBe(0)
    expect(visualPosition(t,at(),true).kind).toBe('unavailable')
  })
  it('rejects unordered, duplicate, invalid and out-of-range UTC before motion',()=>{
    for(const date of ['2026-02-30T12:40:00Z','2026-11-14T12:30:00Z','2026-11-14T14:00:00Z']){
      const r=fixture();rows(r)[1]!.time_utc=date
      expect(track(r).known).toBe(0)
    }
  })
  it('retains east projection and positive/negative elevations',()=>{
    for(const el of [-10,0,10]){
      const r=fixture();for(const row of rows(r)){row.sun.azimuth_deg=90;row.sun.elevation_deg=el}
      const p=visualPosition(track(r),at(),true);if(p.kind!=='interpolated')throw Error()
      expect(p.direction[0]).toBeGreaterThan(0);expect(p.direction[1]).toBeCloseTo(Math.sin(el*Math.PI/180))
    }
  })
  it('binary-searches exact and between-sample positions including endpoints',()=>{
    const times=track().rows.map(r=>r.time)
    expect(lowerBound(times,bounds.start.tick)).toBe(0)
    expect(lowerBound(times,at().tick)).toBe(1)
    expect(lowerBound(times,bounds.end.tick)).toBe(3)
  })
})
