import { capabilitiesFixture } from '../../test/jobFixtures'
import { StrictMode } from 'react'
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ScenarioProvider, useScenario } from './ScenarioProvider'
import { analysisFixture, healthFixture, jsonResponse, requestFixture, validForm } from '../../test/apiFixtures'

vi.mock('../../services/api/jobs',async importOriginal=>({...await importOriginal<typeof import('../../services/api/jobs')>(),capabilities:vi.fn(async()=>({ok:true,status:200,data:capabilitiesFixture(false)}))}))

function Probe() {
  const s=useScenario()
  return <>
    <output aria-label="Scenario probe">{JSON.stringify({state:s.state,health:s.health,analysis:s.analysis,selected:s.selected})}</output>
    <button onClick={()=>{ for(const [key,value] of Object.entries(validForm())) s.change(key as keyof typeof s.state,value as never) }}>Fill scenario</button>
    <button onClick={()=>s.change('longitude','360')}>Invalid edit</button>
    <button onClick={()=>s.change('longitude','270')}>Valid edit</button>
    <button onClick={()=>{void s.run();void s.run()}}>Run twice</button>
    <button onClick={s.reset}>Reset</button><button onClick={s.cancel}>Cancel</button>
    <button onClick={()=>{void s.checkHealth()}}>Check</button>
  </>
}
function mount() { render(<StrictMode><ScenarioProvider><Probe /></ScenarioProvider></StrictMode>) }
function probe() { return JSON.parse(screen.getByLabelText('Scenario probe').textContent!) }
const click=(name:string)=>fireEvent.click(screen.getByRole('button',{name}))
async function ready() { await waitFor(()=>expect(probe().health.kind).toBe('ready')) }
function deferred() { let resolve!:(response:Response)=>void;const promise=new Promise<Response>(r=>{resolve=r});return {promise,resolve} }
function server(body:unknown,status=200,healthReady=true) {
  const mock=vi.fn().mockImplementation(async (url:string)=>url.endsWith('/health')?jsonResponse(healthFixture(healthReady)):jsonResponse(body,status))
  vi.stubGlobal('fetch',mock);return mock
}
describe('shared scenario and request lifecycle',()=>{
  it('checks health once under StrictMode and never polls on edits',async()=>{
    const mock=server(analysisFixture())
    mount();await ready();click('Fill scenario');click('Valid edit')
    expect(mock).toHaveBeenCalledTimes(1)
    expect(probe().selected.longitude).toBe(-90)
  })
  it('blocks invalid inputs even when ready',async()=>{
    const mock=server(analysisFixture());mount();await ready();click('Run twice')
    expect(mock).toHaveBeenCalledTimes(1)
    expect(probe().analysis.kind).toBe('idle')
  })
  it('blocks valid inputs when HTTP 200 explicitly says not ready',async()=>{
    const mock=server(analysisFixture(),503,false);mount()
    await waitFor(()=>expect(probe().health.kind).toBe('reachable_not_ready'))
    click('Fill scenario');click('Run twice');expect(mock).toHaveBeenCalledTimes(1)
  })
  it('uses the builder output and synchronous lock for exactly one POST',async()=>{
    const pending=deferred(),mock=vi.fn().mockImplementation((url:string)=>url.endsWith('/health')?Promise.resolve(jsonResponse(healthFixture(true))):pending.promise)
    vi.stubGlobal('fetch',mock);mount();await ready();click('Fill scenario');click('Run twice')
    expect(probe().analysis.kind).toBe('submitting')
    expect(mock).toHaveBeenCalledTimes(2)
    expect(JSON.parse(mock.mock.calls[1]![1].body)).toEqual(requestFixture())
    await act(async()=>pending.resolve(jsonResponse(analysisFixture(),503)))
    expect(probe().analysis).toMatchObject({kind:'not_ready',status:503,response:{execution_status:'NOT_RUN',score:{value:null},series:null}})
    expect(probe().health.kind).toBe('reachable_not_ready')
    expect(probe().state).toEqual(validForm())
  })
  it('maps 422 without mutating input and clears stale server errors on edit',async()=>{
    server({detail:[{loc:['body','site','latitude_deg'],msg:'Backend latitude error'},{loc:['body'],msg:'Model rule'}]},422)
    mount();await ready();click('Fill scenario');click('Run twice')
    await waitFor(()=>expect(probe().analysis.kind).toBe('validation_error'))
    expect(probe().analysis.fields.latitude).toBe('Backend latitude error')
    expect(probe().analysis.general).toEqual(['Model rule'])
    expect(probe().state).toEqual(validForm())
    click('Valid edit');expect(probe().analysis.kind).toBe('idle')
  })
  it.each([
    [500,{detail:'server'},'server_error'],[502,{},'server_error'],[503,analysisFixture({decision:{status:'INCOMPLETE',reason_codes:[]}}),'server_error'],
    [200,{...analysisFixture(),schema_version:'9.0'},'invalid_response'],
  ])('preserves status %s as %s',async(status,body,kind)=>{
    server(body,Number(status));mount();await ready();click('Fill scenario');click('Run twice')
    await waitFor(()=>expect(probe().analysis.kind).toBe(kind))
    expect(probe().analysis.status).toBe(status)
  })
  it('separates a network rejection from HTTP errors',async()=>{
    vi.stubGlobal('fetch',vi.fn().mockImplementation(async(url:string)=>{
      if(url.endsWith('/health')) return jsonResponse(healthFixture(true))
      throw new TypeError('Connection refused')
    }))
    mount();await ready();click('Fill scenario');click('Run twice')
    await waitFor(()=>expect(probe().analysis.kind).toBe('network_error'))
    expect(probe().analysis.status).toBeNull()
  })
  it.each(['Cancel','Invalid edit','Reset'])('aborts on %s and ignores a delayed response even if transport ignores abort',async action=>{
    const pending=deferred(),signals:AbortSignal[]=[]
    vi.stubGlobal('fetch',vi.fn().mockImplementation((url:string,options:RequestInit)=>{
      if(url.endsWith('/health')) return Promise.resolve(jsonResponse(healthFixture(true)))
      signals.push(options.signal!);return pending.promise
    }))
    mount();await ready();click('Fill scenario');click('Run twice');click(action)
    expect(signals[0]!.aborted).toBe(true)
    await act(async()=>pending.resolve(jsonResponse(analysisFixture({execution_status:'COMPLETED',data_origin:'TEST_FIXTURE'}))))
    expect(probe().analysis.kind).toBe('idle')
    if(action==='Reset') {expect(probe().state.latitude).toBe('');expect(probe().selected).toBeNull()}
    else expect(probe().state.latitude).toBe('-85')
  })
  it('never applies an old request after a new request has completed',async()=>{
    const old=deferred(),current=deferred();let posts=0
    vi.stubGlobal('fetch',vi.fn().mockImplementation((url:string)=>url.endsWith('/health')?Promise.resolve(jsonResponse(healthFixture(true))):++posts===1?old.promise:current.promise))
    mount();await ready();click('Fill scenario');click('Run twice');click('Valid edit');click('Run twice')
    await act(async()=>current.resolve(jsonResponse(analysisFixture({analysis_id:'new',execution_status:'RUNNING',data_origin:'TEST_FIXTURE',request:{...requestFixture(),site:{...requestFixture().site,longitude_deg_east:270}}}))))
    expect(probe().analysis.response.analysis_id).toBe('new')
    await act(async()=>old.resolve(jsonResponse(analysisFixture({analysis_id:'old'}),503)))
    expect(probe().analysis.response.analysis_id).toBe('new')
    expect(probe().health.kind).toBe('ready')
  })
  it('ignores superseded health responses and supports explicit retry',async()=>{
    const old=deferred();let calls=0;const signals:AbortSignal[]=[]
    vi.stubGlobal('fetch',vi.fn().mockImplementation((_url:string,options:RequestInit)=>{signals.push(options.signal!);return ++calls===1?old.promise:Promise.resolve(jsonResponse(healthFixture(true)))}))
    mount();await waitFor(()=>expect(calls).toBe(1));click('Check');await ready()
    expect(signals[0]!.aborted).toBe(true)
    await act(async()=>old.resolve(jsonResponse(healthFixture(false))))
    expect(probe().health.kind).toBe('ready')
  })
  it.each(['network','invalid'])('handles %s health without readiness',async kind=>{
    vi.stubGlobal('fetch',kind==='network'?vi.fn().mockRejectedValue(new TypeError('DNS')):vi.fn().mockResolvedValue(new Response('bad json')))
    mount();await waitFor(()=>expect(probe().health.kind).toBe(kind==='network'?'unreachable':'invalid_response'))
    click('Fill scenario');click('Run twice');expect(probe().analysis.kind).toBe('idle')
  })
  it('bounds a delayed health check and analysis request with cancellation timeouts',async()=>{
    vi.useFakeTimers()
    try {
      let readyHealth=false
      vi.stubGlobal('fetch',vi.fn().mockImplementation((url:string,options:RequestInit)=>{
        if(url.endsWith('/health') && readyHealth) return Promise.resolve(jsonResponse(healthFixture(true)))
        return new Promise((_resolve,reject)=>options.signal!.addEventListener('abort',()=>reject(new DOMException('Aborted','AbortError'))))
      }))
      mount()
      await act(async()=>{await vi.advanceTimersByTimeAsync(10_000)})
      expect(probe().health.kind).toBe('unreachable')
      readyHealth=true
      await act(async()=>{click('Check')})
      expect(probe().health.kind).toBe('ready')
      click('Fill scenario');click('Run twice')
      await act(async()=>{await vi.advanceTimersByTimeAsync(30_000)})
      expect(probe().analysis.kind).toBe('network_error')
      expect(probe().analysis.message).toContain('timed out')
    } finally { vi.useRealTimers() }
  })
})
