import { mkdirSync, writeFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { PROFILES } from './analysisRequest'
import { buildAnalysisRequest } from './buildAnalysisRequest'
import { coordinateFields, eastLongitudeToVisual, visualCoordinate, visualLongitudeToEast } from './coordinates'
import { initialMissionState, type MissionFormState } from './missionState'
import { endWithinBackendRange, parseDuration, parseUtc } from './time'

function valid(patch: Partial<MissionFormState> = {}): MissionFormState {
  return { ...initialMissionState(), latitude: '-85', longitude: '340', utcDate: '2026-11-14', utcTime: '12:30', hours: '2', minutes: '30', ...patch }
}

describe('coordinates', () => {
  it.each([['0','0'], ['-89.999','359.999'], ['89.999','180']])('accepts latitude %s / east %s', (latitude, longitude) => {
    expect(buildAnalysisRequest(valid({ latitude, longitude })).valid).toBe(true)
  })
  it.each(['-90','90','-91','91','NaN','Infinity',''])('rejects latitude %s without changing the raw input', latitude => {
    const state = valid({ latitude })
    expect(buildAnalysisRequest(state).errors.latitude).toBeTruthy()
    expect(buildAnalysisRequest(state).request).toBeNull()
    expect(state.latitude).toBe(latitude)
  })
  it.each(['360','-20','NaN','Infinity',''])('rejects manual east longitude %s', longitude => {
    expect(buildAnalysisRequest(valid({ longitude })).errors.longitude).toBeTruthy()
  })
  it.each([[30,30],[-90,270],[180,180],[0,0],[-20,340]])('adapts visual %s to east %s', (input, east) => {
    expect(visualLongitudeToEast(input)).toBe(east)
    expect(visualLongitudeToEast(eastLongitudeToVisual(east))).toBe(east)
  })
  it('shares raw form coordinates with a derived marker, including unsupported poles', () => {
    expect(visualCoordinate('-85','270')).toEqual({ latitude: -85, longitude: -90, radius: 1 })
    expect(visualCoordinate('-85','360')).toBeNull()
    expect(visualCoordinate('-','0')).toBeNull()
    expect(visualCoordinate('-90','')).toEqual({ latitude: -90, longitude: null, radius: 1 })
    expect(coordinateFields({ latitude: -90, longitude: null, radius: 1 })).toEqual({ latitude: '-90', longitude: '' })
    expect(() => eastLongitudeToVisual(360)).toThrow()
  })
})

describe('UTC and duration', () => {
  it.each([
    ['2024-02-29','00:00','2024-02-29T00:00:00Z'],
    ['2026-12-31','23:59:59','2026-12-31T23:59:59Z'],
    ['2027-01-01','00:00:00','2027-01-01T00:00:00Z'],
    ['0001-01-01','00:00','0001-01-01T00:00:00Z'],
    ['2026-03-08','02:30','2026-03-08T02:30:00Z'],
    ['2026-11-01','01:30','2026-11-01T01:30:00Z'],
  ])('serializes %s %s as UTC', (date,time,expected) => expect(parseUtc(date,time).value).toBe(expected))
  it.each(['2026-02-30','2026-04-31','2100-02-29','0000-01-01','2026-13-01','2026-00-01','2026-01-00','2026-1-01',''])('rejects invalid date %s rather than rolling it', date => {
    expect(parseUtc(date,'12:00').value).toBeNull()
  })
  it.each(['24:00','12:60','23:59:60','12:30+03:00','1:30',''])('rejects invalid UTC time %s', time => {
    expect(parseUtc('2026-11-14',time).errors.utcTime).toBeTruthy()
  })
  it('converts 2h30m to exactly 9000 seconds', () => expect(parseDuration(valid()).value).toBe(9000))
  it.each([
    {hours:'0',minutes:'0',seconds:'0'}, {hours:'-1'}, {minutes:'-1'}, {seconds:'0.5'},
    {hours:'NaN'}, {hours:'Infinity'}, {hours:'1e2'}, {hours:''}, {minutes:'60'},
    {seconds:'60'}, {hours:'9007199254740992'}, {hours:'9007199254740991'},
  ])('rejects unsafe duration %j', patch => expect(parseDuration(valid(patch)).value).toBeNull())
  it('checks representable backend end dates before multiplying huge durations', () => {
    expect(endWithinBackendRange('9999-12-31T23:59:58Z',1)).toBe(true)
    expect(endWithinBackendRange('9999-12-31T23:59:59Z',1)).toBe(false)
    expect(buildAnalysisRequest(valid({utcDate:'9999-12-31',utcTime:'23:59:59',hours:'0',minutes:'0',seconds:'1'})).errors.hours).toBeTruthy()
    expect(endWithinBackendRange('invalid',1)).toBe(false)
  })
})

describe('requirements and exact request', () => {
  it('uses the exact six sections with draft observer/options defaults', () => {
    const result = buildAnalysisRequest(valid())
    expect(result.valid).toBe(true)
    const request = result.request!
    expect(Object.keys(request).sort()).toEqual(['observer','operation','options','schema_version','site','time'])
    expect(request.schema_version).toBe('1.0')
    expect(request.site).toEqual({kind:'COORDINATES',latitude_deg:-85,longitude_deg_east:340,frame:'MOON_ME_DE421',latitude_type:'PLANETOCENTRIC'})
    expect(request.time).toEqual({start_utc:'2026-11-14T12:30:00Z',duration_s:9000})
    expect(request.observer).toEqual({surface_elevation_mode:'DEM',solar_height_above_surface_m:1,earth_height_above_surface_m:1})
    expect(request.options).toEqual({include_full_horizon:true,include_earth_disk_fraction:true,event_lookahead_s:86400})
  })
  it.each(PROFILES)('keeps the same requirements for $label', profile => {
    const request = buildAnalysisRequest(valid({profile:profile.value})).request!
    expect(request.operation.profile).toBe(profile.value)
    expect(request.operation.requirements).toEqual({min_solar_disk_visible_fraction:.5,min_sun_visible_s:null,max_dark_gap_s:null,min_earth_continuous_s:null,earth_clearance_margin_deg:0,require_simultaneous:false,min_joint_continuous_s:null})
  })
  it('preserves optional null versus explicit zero and valid fractional thresholds', () => {
    const request = buildAnalysisRequest(valid({minSun:'0',minEarth:'0.5',maxDark:'0',solarFraction:'0',clearance:'90'})).request!
    expect(request.operation.requirements.min_sun_visible_s).toBe(0)
    expect(request.operation.requirements.min_earth_continuous_s).toBe(.5)
    expect(request.operation.requirements.min_joint_continuous_s).toBeNull()
  })
  it.each([
    ['solarFraction','-0.1'],['solarFraction','1.1'],['solarFraction','NaN'],['clearance','-1'],['clearance','90.1'],
    ['minSun','-1'],['minEarth','Infinity'],['maxDark','-1'],['minJoint','-1'],['solarHeight','-1'],['earthHeight','NaN'],
    ['lookahead','0.5'],['lookahead','9007199254740992'],
  ] as const)('rejects %s=%s', (field,value) => {
    expect(buildAnalysisRequest(valid({[field]:value})).errors[field]).toBeTruthy()
  })
  it('requires simultaneous visibility for a joint threshold without clearing the input', () => {
    const state = valid({minJoint:'0'})
    expect(buildAnalysisRequest(state).errors.minJoint).toBeTruthy()
    expect(state.minJoint).toBe('0')
    expect(buildAnalysisRequest({...state, simultaneous:true}).valid).toBe(true)
  })
  it.each(['minSun','minEarth','minJoint'] as const)('bounds %s by operation duration', field => {
    expect(buildAnalysisRequest(valid({[field]:'9001',simultaneous:true})).errors[field]).toContain('cannot exceed')
  })
  it('does not invent a duration bound on max_dark_gap_s', () => {
    expect(buildAnalysisRequest(valid({maxDark:'100000',solarHeight:'0',earthHeight:'0',lookahead:'0'})).valid).toBe(true)
  })
  it('emits real builder results for read-only Pydantic cross-validation', () => {
    const inputs = PROFILES.flatMap(profile => [valid({profile:profile.value}), valid({profile:profile.value,minSun:'0',minEarth:'0.5',minJoint:'1',simultaneous:true,fullHorizon:false,earthDisk:false,solarHeight:'0',earthHeight:'2'})])
    inputs.push(valid({utcDate:'0001-01-01',utcTime:'00:00'}), valid({utcDate:'9999-12-31',utcTime:'23:59:58',hours:'0',minutes:'0',seconds:'1'}))
    const requests = inputs.map(state => {
      const result = buildAnalysisRequest(state)
      expect(result.valid).toBe(true)
      return result.request!
    })
    mkdirSync('.validation',{recursive:true})
    writeFileSync('.validation/mission-requests.json',JSON.stringify(requests,null,2))
  })
})
