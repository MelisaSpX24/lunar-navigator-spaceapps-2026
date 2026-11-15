import { mkdirSync, writeFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { scientificFixture } from '../../test/scientificFixtures'
import { requestFixture } from '../../test/apiFixtures'
import { checkDecision, checkHorizons, checkQuality, checkResolvedSite, checkScore, checkSeries, checkSources, checkWindows, MAX_RECORDS, safeSourceUrl } from './validation'
import { timeBounds, utcStamp } from './utc'
import { requestMatches } from './requestMatch'
import { completedResult } from './resultContext'
import type { AnalysisState, HealthState } from '../scenario/ScenarioProvider'

const bounds=timeBounds('2026-11-14T12:30:00Z',3600)
const health:HealthState={kind:'ready',status:200,data:{status:'ok',science_ready:true,dem_ready:false,kernels_ready:false,reason_codes:[]}}
function resultState():AnalysisState{return{kind:'received',status:200,response:scientificFixture(),request:requestFixture()}}
describe('UTC and scenario identity',()=>{
  it.each(['2026-02-30T00:00:00Z','2026-04-31T00:00:00Z','0000-01-01T00:00:00Z','2026-11-14T24:00:00Z','2026-11-14T12:30:00+03:00','not UTC','2026-11-14T12:30:00'])('rejects invalid timestamp %s',v=>expect(utcStamp(v)).toBeNull())
  it('preserves microsecond ordering at the backend calendar boundaries',()=>{
    for(const year of ['0001','9999']) {
      const a=utcStamp(`${year}-01-01T00:00:00.000001Z`)!,b=utcStamp(`${year}-01-01T00:00:00.000002+00:00`)!
      expect(b.tick-a.tick).toBe(1n)
    }
  })
  it('matches all request fields with equivalent zero-offset UTC spelling',()=>{
    const req=requestFixture(),echo={...req,time:{...req.time,start_utc:'2026-11-14T12:30:00.000000+00:00'}}
    expect(requestMatches(req,echo)).toBe(true)
    expect(requestMatches(req,{...echo,time:{...echo.time,start_utc:'2026-11-14T12:30:00.000001Z'}})).toBe(false)
    expect(requestMatches(req,{...echo,site:{...echo.site,longitude_deg_east:270}})).toBe(false)
    expect(requestMatches(req,{...echo,observer:{...echo.observer,earth_height_above_surface_m:2}})).toBe(false)
    expect(requestMatches(req,{...echo,extra:'not allowed'})).toBe(false)
  })
  it('requires COMPLETED, reachable ready backend and current/sent/echoed scenario agreement',()=>{
    expect(completedResult(resultState(),health,requestFixture())).not.toBeNull()
    for(const execution_status of ['NOT_RUN','RUNNING','FAILED'] as const) {
      expect(completedResult({...resultState(),kind:'received',status:200,request:requestFixture(),response:{...scientificFixture(),execution_status}},health,requestFixture())).toBeNull()
    }
    expect(completedResult(resultState(),{kind:'unreachable',status:null,message:'offline'},requestFixture())).toBeNull()
    expect(completedResult(resultState(),health,{...requestFixture(),site:{...requestFixture().site,latitude_deg:0}})).toBeNull()
    expect(completedResult({kind:'not_ready',status:503,request:requestFixture(),response:scientificFixture()},health,requestFixture())).toBeNull()
  })
})
describe('horizon profiles',()=>{
  it('keeps null elevations, actual zero, observer heights and metre ranges',()=>{
    const data=checkHorizons(scientificFixture().horizons)
    expect(data.kind).toBe('valid')
    if(data.kind==='valid') {
      expect(data.value[0]!.points.map(p=>p.elevation_deg)).toEqual([0,null,-2,3])
      expect(data.value.map(h=>h.observer_height_m)).toEqual([1,2])
      expect(data.value[0]!.range_m).toBe(1200)
      expect(data.value[0]!.coverage_complete).toBe(false)
    }
  })
  it.each([{azimuth_deg:360,elevation_deg:0},{azimuth_deg:-1,elevation_deg:0},{azimuth_deg:0,elevation_deg:91},{azimuth_deg:0,elevation_deg:NaN},{azimuth_deg:0}])('rejects invalid horizon point %j',point=>{
    const h=structuredClone(scientificFixture().horizons!) as Record<string,unknown>[]
    h[0]!.points=[point]
    expect(checkHorizons(h).kind).toBe('invalid')
  })
  it('rejects unsorted azimuths rather than silently sorting',()=>{
    const h=structuredClone(scientificFixture().horizons!) as {points:unknown[]}[]
    h[0]!.points.reverse();expect(checkHorizons(h).kind).toBe('invalid')
  })
  it('distinguishes missing, calculated-empty and oversized data',()=>{
    expect(checkHorizons(null).kind).toBe('missing')
    expect(checkHorizons([])).toEqual({kind:'valid',value:[]})
    expect(checkHorizons(undefined).kind).toBe('invalid')
    expect(checkHorizons(Array(MAX_RECORDS+1).fill({})).kind).toBe('limited')
  })
})
describe('independent Sun and Earth samples',()=>{
  it.each(['sun','earth'] as const)('retains server states and nullable values for %s',body=>{
    const data=checkSeries(scientificFixture().series,body,bounds)
    expect(data.kind).toBe('valid')
    if(data.kind==='valid') {
      expect(data.value.map(row=>row.body.disk_state)).toEqual(body==='sun'?['NONE','UNKNOWN','PARTIAL']:['FULL','UNKNOWN','PARTIAL'])
      expect(data.value[1]!.body.condition_met).toBeNull()
      expect(data.value[2]!.body.condition_met).toBe(body==='sun')
    }
  })
  it.each([{disk_visible_fraction:1.1},{elevation_deg:-91},{azimuth_deg:360},{angular_radius_deg:0},{condition_met:0},{disk_state:'VISIBLE'},{center_clearance_deg:Infinity}])('rejects invalid Sun values %j without invalidating Earth',patch=>{
    const rows=structuredClone(scientificFixture().series!) as {sun:object}[]
    rows[0]!.sun={...rows[0]!.sun,...patch}
    expect(checkSeries(rows,'sun',bounds).kind).toBe('invalid')
    expect(checkSeries(rows,'earth',bounds).kind).toBe('valid')
  })
  it('rejects duplicate, unordered, out-of-range and malformed UTC times',()=>{
    for(const t of ['2026-11-14T12:30:00Z','2026-11-14T12:20:00Z','2026-02-30T12:30:00Z','2026-11-14T14:00:00Z']) {
      const rows=structuredClone(scientificFixture().series!) as {time_utc:string}[]
      rows[1]!.time_utc=t;expect(checkSeries(rows,'sun',bounds).kind).toBe('invalid')
    }
  })
  it('keeps null versus calculated-empty time series',()=>{
    expect(checkSeries(null,'sun',bounds).kind).toBe('missing')
    expect(checkSeries([],'earth',bounds)).toEqual({kind:'valid',value:[]})
  })
})
describe('server windows, decisions, scores and quality',()=>{
  it('retains half-open ordered intervals, censoring and null/empty',()=>{
    const w=scientificFixture().windows
    expect(checkWindows(w.sun,bounds)).toMatchObject({kind:'valid',value:[{start_censored:true,end_censored:false}]})
    expect(checkWindows(w.earth,bounds)).toEqual({kind:'valid',value:[]})
    expect(checkWindows(w.joint,bounds).kind).toBe('missing')
  })
  it.each([
    ['2026-11-14T12:45:00Z','2026-11-14T12:45:00Z'],['2026-11-14T12:46:00Z','2026-11-14T12:45:00Z'],
    ['2026-11-14T12:20:00Z','2026-11-14T12:45:00Z'],['invalid','2026-11-14T12:45:00Z'],
  ])('rejects window %s to %s without repair',(start_utc,end_utc)=>{
    expect(checkWindows([{start_utc,end_utc,definition_id:'test',start_censored:false,end_censored:false}],bounds).kind).toBe('invalid')
  })
  it('preserves all decision enums and boolean/number/null types',()=>{
    const d=checkDecision(scientificFixture().decision)
    expect(d).toMatchObject({kind:'valid',value:{status:'INCOMPLETE',rules:[{status:'MET',required:true},{status:'NOT_MET',actual:0},{status:'INCOMPLETE',required:null,actual:false}]}})
    expect(checkDecision({status:'SUCCESS',rules:[],reason_codes:[]}).kind).toBe('invalid')
  })
  it('preserves null/zero scores and validates model version and component bounds',()=>{
    const s=scientificFixture().score
    expect(checkScore(s)).toMatchObject({kind:'valid',value:{value:0}})
    expect(checkScore({...s,value:null})).toMatchObject({kind:'valid',value:{value:null}})
    for(const patch of [{value:101},{value:NaN},{model_version:''},{components:[{name:'test',raw_value:0,weight:1.1,normalized_value:0}]},{components:[{name:'test',raw_value:Infinity,weight:1,normalized_value:0}]}]) expect(checkScore({...s,...patch}).kind).toBe('invalid')
    const {model_version:_,...missing}=s
    expect(checkScore(missing).kind).toBe('invalid')
  })
  it.each(['NOT_ASSESSED','SUFFICIENT','LIMITED','INSUFFICIENT'])('accepts explicit quality %s and unknown coverage',status=>{
    expect(checkQuality({status,coverage_complete:null,limitations:[]})).toMatchObject({kind:'valid',value:{coverage_complete:null}})
  })
  it('rejects missing or wrongly typed coverage',()=>{
    expect(checkQuality({status:'LIMITED',limitations:[]}).kind).toBe('invalid')
    expect(checkQuality({status:'LIMITED',coverage_complete:1,limitations:[]}).kind).toBe('invalid')
  })
  it('validates source product/version/checksum without certifying origin or unsafe URLs',()=>{
    const sources=scientificFixture().sources as Record<string,unknown>[]
    expect(checkSources(sources).kind).toBe('valid')
    expect(checkSources([{...sources[0],sha256:'not-a-checksum'}]).kind).toBe('invalid')
    expect(checkSources([])).toEqual({kind:'valid',value:[]})
    for(const url of ['javascript:alert(1)','data:text/html,test','file:///tmp/test','https://user:pass@example.invalid','not-a-url']) expect(safeSourceUrl(url)).toBeNull()
    expect(safeSourceUrl('https://example.invalid/test')).toBe('https://example.invalid/test')
  })
  it('validates resolved coordinates and preserves zero surface elevation versus null',()=>{
    expect(checkResolvedSite(scientificFixture().resolved_site)).toMatchObject({kind:'valid',value:{surface_elevation_m:0}})
    expect(checkResolvedSite(null).kind).toBe('missing')
    expect(checkResolvedSite({...scientificFixture().resolved_site,frame:'OTHER'}).kind).toBe('invalid')
  })
  it('exports complete test-only JSON for read-only Pydantic compatibility checks',()=>{
    const full=scientificFixture()
    const partial={...full,score:{value:null,model_version:null,components:null},quality:{status:'INSUFFICIENT',coverage_complete:null,limitations:['Controlled partial data']},series:null,horizons:[],sources:[]}
    const empty={...full,series:[],horizons:[],windows:{sun:null,earth:[],joint:[]},decision:{status:'INCOMPLETE',reason_codes:[],rules:[]},score:{value:null,model_version:null,components:[]}}
    mkdirSync('.validation',{recursive:true})
    writeFileSync('.validation/analysis-result-fixtures.json',JSON.stringify([full,partial,empty],null,2))
  })
})
