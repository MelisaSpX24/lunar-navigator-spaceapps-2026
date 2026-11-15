import { describe, expect, it, vi } from 'vitest'
import { getHealth, submitAnalysis } from './client'
import { isAnalysis } from './responses'
import { mapFieldErrors } from './fieldErrors'
import { analysisFixture, healthFixture, jsonResponse, requestFixture } from '../../test/apiFixtures'

function reply(body: unknown, status = 200) { vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(body, status))) }
describe('typed API client', () => {
  it('rejects a valid envelope for a different scenario, regardless of its analysis ID', async () => {
    const request=requestFixture()
    reply(analysisFixture({request:{...request,observer:{...request.observer,earth_height_above_surface_m:2}}}))
    expect(await submitAnalysis(request)).toMatchObject({kind:'invalid_response',status:200,message:expect.stringContaining('does not match')})
  })
  it.each([false, true])('accepts explicit health readiness %s without inferring it from HTTP 200', async ready => {
    reply(healthFixture(ready))
    expect(await getHealth()).toEqual({ kind: 'health', status: 200, health: healthFixture(ready) })
    expect(fetch).toHaveBeenCalledWith('/api/v1/health', expect.objectContaining({ method: 'GET' }))
  })
  it.each([{}, { ...healthFixture(), science_ready: 'true' }, { ...healthFixture(), schema_version: '2.0' }, { ...healthFixture(), reason_codes: null }])('rejects malformed health %j', async body => {
    reply(body)
    expect((await getHealth()).kind).toBe('invalid_response')
  })
  it('handles invalid health JSON', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('<html>proxy</html>')))
    expect(await getHealth()).toMatchObject({ kind: 'invalid_response', status: 200 })
  })
  it.each(['Connection refused', 'DNS failure', 'Proxy failure'])('separates transport failure: %s', async message => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError(message)))
    expect(await getHealth()).toMatchObject({ kind: 'network_error', status: null })
    expect(await submitAnalysis(requestFixture())).toMatchObject({ kind: 'network_error', status: null })
  })
  it.each([404,500,502,504])('preserves HTTP %s without calling it a network/scientific-engine error', async status => {
    reply({ detail: 'gateway' }, status)
    expect(await getHealth()).toMatchObject({ kind: 'server_error', status })
    expect(await submitAnalysis(requestFixture())).toMatchObject({ kind: 'server_error', status })
  })
  it('sends the exact validated request, content type and AbortSignal', async () => {
    reply(analysisFixture(), 503)
    const request = requestFixture(), controller = new AbortController()
    const result = await submitAnalysis(request, controller.signal)
    expect(fetch).toHaveBeenCalledTimes(1)
    expect(fetch).toHaveBeenCalledWith('/api/v1/analyses', expect.objectContaining({method:'POST',body:JSON.stringify(request),signal:controller.signal,headers:{'Content-Type':'application/json',Accept:'application/json'}}))
    expect(result).toEqual({kind:'not_ready',status:503,response:analysisFixture()})
    if (result.kind === 'not_ready') {
      expect(result.response.execution_status).toBe('NOT_RUN')
      expect(result.response.score.value).toBeNull()
      expect(result.response.series).toBeNull()
    }
  })
  it.each([
    analysisFixture({execution_status:'COMPLETED'}), analysisFixture({decision:{status:'INCOMPLETE',reason_codes:[]}}),
    analysisFixture({score:{value:0}}), analysisFixture({data_origin:'TEST_FIXTURE'}),
  ])('does not label an unexpected 503 as science-not-ready', async body => {
    reply(body,503)
    expect(await submitAnalysis(requestFixture())).toMatchObject({kind:'server_error',status:503})
  })
  it.each([200,503,422])('handles broken JSON with HTTP %s', async status => {
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response('broken',{status})))
    expect(await submitAnalysis(requestFixture())).toMatchObject({kind:'invalid_response',status})
  })
  it.each([
    {schema_version:'2.0'}, {execution_status:'SUCCESS'}, {execution_status:['NOT_RUN']}, {data_origin:'NASA'},
    {decision:{status:'APPROVED',reason_codes:[]}}, {score:{value:-1}}, {score:{value:101}},
    {quality:{status:'PERFECT',limitations:[]}}, {series:0}, {horizons:{}}, {windows:{sun:null,earth:null}},
    {analysis_id:''}, {limitations:[42]},
  ])('rejects unsupported/malformed analysis envelope %j', async patch => {
    reply({...analysisFixture(),...patch})
    expect((await submitAnalysis(requestFixture())).kind).toBe('invalid_response')
  })
  it.each(['NOT_RUN','RUNNING','COMPLETED','FAILED'] as const)('receives execution %s without converting HTTP 200 into success', async execution_status => {
    const body=analysisFixture({execution_status,data_origin:'TEST_FIXTURE'})
    reply(body)
    expect(await submitAnalysis(requestFixture())).toEqual({kind:'received',status:200,response:body})
  })
  it('rejects a nonfinite score before JSON transport', () => {
    expect(isAnalysis(analysisFixture({score:{value:Infinity}}))).toBe(false)
  })
  it('validates the FastAPI 422 shape and preserves messages as text', async () => {
    const issues=[{loc:['body','site','COORDINATES','latitude_deg'],msg:'Invalid latitude'}, {loc:['body','new_field'],msg:'<script>example</script>'}]
    reply({detail:issues},422)
    expect(await submitAnalysis(requestFixture())).toEqual({kind:'validation_error',status:422,issues})
    reply({detail:'validation failed'},422)
    expect((await submitAnalysis(requestFixture())).kind).toBe('invalid_response')
  })
  it('returns cancellation distinctly when transport is aborted', async () => {
    const controller=new AbortController()
    vi.stubGlobal('fetch',vi.fn().mockImplementation((_url,options)=>new Promise((_resolve,reject)=>options.signal.addEventListener('abort',()=>reject(new DOMException('Aborted','AbortError'))))))
    const pending=submitAnalysis(requestFixture(),controller.signal)
    controller.abort()
    expect(await pending).toMatchObject({kind:'aborted',status:null})
  })
  it('maps only known field paths, keeping unknown schema errors general', () => {
    const result=mapFieldErrors([
      {loc:['body','site','COORDINATES','latitude_deg'],msg:'Latitude'}, {loc:['body','site','longitude_deg_east'],msg:'Longitude'},
      {loc:['body','time','start_utc'],msg:'UTC'}, {loc:['body','time','duration_s'],msg:'Duration'},
      {loc:['body','operation','requirements','min_joint_continuous_s'],msg:'Joint'},
      {loc:['body','future','latitude_deg'],msg:'Unknown contract'}, {loc:['query','site','latitude_deg'],msg:'Wrong location'},
      {loc:['body','__proto__'],msg:'Unknown reserved path'}, {loc:['body','constructor'],msg:'Another unknown path'},
    ])
    expect(result.fields).toEqual({latitude:'Latitude',longitude:'Longitude',utcDate:'UTC',utcTime:'UTC',hours:'Duration',minutes:'Duration',seconds:'Duration',minJoint:'Joint'})
    expect(result.general).toEqual(['Unknown contract','Wrong location','Unknown reserved path','Another unknown path'])
  })
})
