import { act, renderHook } from '@testing-library/react'
import { afterEach,beforeEach,describe,expect,it,vi } from 'vitest'
import { StrictMode, type ReactNode } from 'react'
import { useScientificJob } from './useScientificJob'
import { acceptedFixture,capabilitiesFixture,jobId,resultFixture,statusFixture } from '../../test/jobFixtures'
import { jsonResponse,requestFixture } from '../../test/apiFixtures'
import { jobRequest,type JobState } from '../../services/api/jobs'

const flush=async(ms=0)=>{await act(async()=>{await vi.advanceTimersByTimeAsync(ms)})}
const start=async()=>{const h=renderHook(({request})=>useScientificJob(request),{initialProps:{request:requestFixture()},wrapper:({children}:{children:ReactNode})=><StrictMode>{children}</StrictMode>});await flush();return h}
beforeEach(()=>vi.useFakeTimers())
afterEach(()=>vi.useRealTimers())
function server(status:JobState='RUNNING'){
 return vi.spyOn(globalThis,'fetch').mockImplementation(async(url)=>{
  const path=String(url)
  if(path.endsWith('/capabilities'))return jsonResponse(capabilitiesFixture())
  if(path.endsWith('/analyses/jobs'))return jsonResponse(acceptedFixture(),202)
  if(path.endsWith('/cancel'))return jsonResponse(statusFixture('CANCEL_REQUESTED'))
  if(path.endsWith('/result'))return jsonResponse(resultFixture())
  return jsonResponse(statusFixture(status))
 })
}
describe('research lifecycle and race protection',()=>{
 it('resumes a persisted analysis from a new browser session without first recomputing it',async()=>{
  const fetch=server('COMPLETED'),h=await start(),checkpoint='c'.repeat(32)
  await act(async()=>h.result.current.run('live',false,checkpoint));await flush()
  const posts=fetch.mock.calls.filter(([,o])=>o?.method==='POST')
  expect(posts).toHaveLength(1)
  expect(JSON.parse(String(posts[0]?.[1]?.body))).toEqual(jobRequest(requestFixture(),checkpoint))
  expect(h.result.current.job.phase).toBe('received')
  expect(h.result.current.job.accepted?.job_id).toBe(jobId)
 })
 it('does not submit malformed or recorded-mode checkpoint IDs',async()=>{
  const fetch=server(),h=await start()
  for(const id of ['','../jobs/other','A'.repeat(32),'a'.repeat(31)])await act(async()=>h.result.current.run('live',false,id))
  await act(async()=>h.result.current.run('recorded',false,'a'.repeat(32)))
  expect(fetch.mock.calls.some(([,o])=>o?.method==='POST')).toBe(false)
 })
 it('retains an explicit checkpoint mismatch error without retrying a fresh calculation',async()=>{
  const fetch=server(),h=await start()
  fetch.mockResolvedValueOnce(jsonResponse({detail:{code:'RESUME_REQUEST_MISMATCH'}},409))
  await act(async()=>h.result.current.run('live',false,'c'.repeat(32)));await flush(6000)
  expect(h.result.current.job.failure?.status).toBe(409)
  expect(h.result.current.job.message).toContain('RESUME_REQUEST_MISMATCH')
  expect(fetch.mock.calls.filter(([,o])=>o?.method==='POST')).toHaveLength(1)
 })
 it('one capability setup in StrictMode, duplicate POST guard, queued/running beyond 30s, stop and reconnect same job',async()=>{
  const fetch=server();const h=await start();expect(fetch).toHaveBeenCalledTimes(1)
  await act(async()=>{void h.result.current.run();void h.result.current.run()});await flush()
  expect(h.result.current.job.status?.status).toBe('RUNNING');await flush(32_000)
  expect(h.result.current.job.phase).toBe('watching');expect(fetch.mock.calls.filter(([u])=>String(u).endsWith('/analyses/jobs'))).toHaveLength(1)
  act(()=>h.result.current.stopWaiting());expect(h.result.current.job.message).toContain('No cancellation was sent');const n=fetch.mock.calls.length;await flush(3000);expect(fetch).toHaveBeenCalledTimes(n)
  act(()=>h.result.current.retry());await flush();expect(h.result.current.job.status?.status).toBe('RUNNING');expect(fetch.mock.calls.filter(([u])=>String(u).endsWith('/analyses/jobs'))).toHaveLength(1);h.unmount();const end=fetch.mock.calls.length;await flush(4000);expect(fetch).toHaveBeenCalledTimes(end)
 })
 it('fetches completed envelope and retains evidence even though science readiness is false',async()=>{server('COMPLETED');const h=await start();await act(async()=>h.result.current.run());await flush();expect(h.result.current.job.phase).toBe('received');expect(h.result.current.job.response?.data_origin).toBe('TEST_FIXTURE');expect(h.result.current.job.envelope?.result.window_evidence).toEqual({request:{test_only:true}})})
 it.each(['PARTIAL','FAILED','CANCELLED','INTERRUPTED'] as const)('does not promote %s to a complete result',async s=>{server(s);const h=await start();await act(async()=>h.result.current.run());await flush();expect(h.result.current.job.status?.status).toBe(s);expect(h.result.current.job.response).toBeNull();expect(h.result.current.job.phase).toBe('terminal')})
 it('retains PARTIAL null analysis and window evidence without publishing scientific completion',async()=>{
  const fetch=server('PARTIAL'), h=await start()
  const evidence={request:{test_only:true},decision:'INCOMPLETE',score:null}
  fetch.mockImplementation(async u=>{
   if(String(u).endsWith('/analyses/jobs'))return jsonResponse(acceptedFixture(),202)
   if(String(u).endsWith('/result'))return jsonResponse({job_id:jobId,job_type:'ANALYSIS',status:'PARTIAL',result:{analysis:null,window_evidence:evidence}})
   return jsonResponse({...statusFixture('PARTIAL'),result_available:true})
  })
  await act(async()=>h.result.current.run());await flush()
  expect(h.result.current.job.phase).toBe('terminal')
  expect(h.result.current.job.response).toBeNull()
  expect(h.result.current.job.envelope?.result.analysis).toBeNull()
  expect(h.result.current.job.envelope?.result.window_evidence).toEqual(evidence)
  expect(h.result.current.job.failure).toBeNull()
 })
 it('rejects COMPLETED with null analysis instead of promoting retained window evidence',async()=>{
  const fetch=server('COMPLETED'), h=await start()
  fetch.mockImplementation(async u=>{
   if(String(u).endsWith('/analyses/jobs'))return jsonResponse(acceptedFixture(),202)
   if(String(u).endsWith('/result'))return jsonResponse({job_id:jobId,job_type:'ANALYSIS',status:'COMPLETED',result:{analysis:null,window_evidence:{test_only:true}}})
   return jsonResponse(statusFixture('COMPLETED'))
  })
  await act(async()=>h.result.current.run());await flush()
  expect(h.result.current.job.phase).toBe('error')
  expect(h.result.current.job.response).toBeNull()
  expect(h.result.current.job.failure?.kind).toBe('invalid')
  expect(h.result.current.job.message).toContain('lacks a valid, matching completed AnalysisResult')
 })
 it('keeps cancellation requested separate from cancelled and confirms through polling',async()=>{const fetch=server();let state:JobState='RUNNING';const h=await start();fetch.mockImplementation(async(url)=>{if(String(url).endsWith('/analyses/jobs'))return jsonResponse(acceptedFixture(),202);if(String(url).endsWith('/cancel'))state='CANCEL_REQUESTED';return jsonResponse(statusFixture(state))});await act(async()=>h.result.current.run());await flush();await act(async()=>h.result.current.cancel());expect(fetch.mock.calls.some(([u,o])=>String(u).endsWith('/cancel')&&o?.method==='POST')).toBe(true);expect(h.result.current.job.status?.status).toBe('CANCEL_REQUESTED');state='CANCELLED';await flush(1500);expect(h.result.current.job.status?.status).toBe('CANCELLED');expect(h.result.current.job.response).toBeNull()})
 it('bounded backoff on network loss stops without resubmitting and retry uses original ID',async()=>{const fetch=server();const h=await start();await act(async()=>h.result.current.run());await flush();fetch.mockRejectedValue(new TypeError('offline'));await flush(30_000);expect(h.result.current.job.phase).toBe('disconnected');expect(h.result.current.job.message).toContain('may still be running');const n=fetch.mock.calls.length;await flush(60_000);expect(fetch).toHaveBeenCalledTimes(n);fetch.mockResolvedValue(jsonResponse(statusFixture('RUNNING')));act(()=>h.result.current.retry());await flush();expect(String(fetch.mock.calls.at(-1)?.[0])).toBe(`/api/v1/jobs/${jobId}`)})
 it('rejects unsafe accepted URLs without polling or following them',async()=>{const fetch=server();const h=await start();fetch.mockResolvedValueOnce(jsonResponse({...acceptedFixture(),result_url:'https://evil.test/'},202));await act(async()=>h.result.current.run());await flush();expect(h.result.current.job.phase).toBe('error');expect(fetch.mock.calls.some(([u])=>String(u).includes('/jobs/'))).toBe(false)})
 it('invalidates on changed UTC, ignores late result even when fetch ignores abort, and clears on reset',async()=>{
  const fetch=server();const h=await start();let release!:(r:Response)=>void
  fetch.mockImplementation(async(url)=>String(url).endsWith('/analyses/jobs')?new Promise<Response>(r=>{release=r}):jsonResponse(capabilitiesFixture()))
  act(()=>{void h.result.current.run()});h.rerender({request:{...requestFixture(),time:{...requestFixture().time,start_utc:'2026-11-15T00:00:00Z'}}});await flush();await act(async()=>release(jsonResponse(acceptedFixture(),202)));expect(h.result.current.job.phase).toBe('idle');expect(h.result.current.job.response).toBeNull();act(()=>h.result.current.clear());expect(h.result.current.job.accepted).toBeNull()
 })
 it('rejects mismatched completed response and retains exact submitted requirement keys',async()=>{const fetch=server('COMPLETED');const h=await start();fetch.mockImplementation(async u=>{if(String(u).endsWith('/analyses/jobs'))return jsonResponse(acceptedFixture(),202);if(String(u).endsWith('/result')){const e=resultFixture();e.result.analysis.request={...requestFixture(),time:{...requestFixture().time,duration_s:7200}};return jsonResponse(e)}return jsonResponse(statusFixture('COMPLETED'))});await act(async()=>h.result.current.run());await flush();expect(h.result.current.job.phase).toBe('error');expect(h.result.current.job.request?.operation.requirements).toEqual(requestFixture().operation.requirements)})
 it('recorded is explicit, PRECOMPUTED only, and 404 never falls back to live',async()=>{const fetch=server();const h=await start();fetch.mockResolvedValueOnce(jsonResponse({detail:{code:'RECORDED_REQUEST_NOT_FOUND'}},404));await act(async()=>h.result.current.run('recorded'));expect(h.result.current.job.failure?.status).toBe(404);expect(fetch.mock.calls.filter(([u])=>String(u).includes('/analyses'))).toHaveLength(1);expect(String(fetch.mock.calls.at(-1)?.[0])).toContain('mode=recorded');const r=resultFixture().result.analysis;fetch.mockResolvedValueOnce(jsonResponse({...r,data_origin:'PRECOMPUTED'}));await act(async()=>h.result.current.run('recorded'));expect(h.result.current.job.response?.data_origin).toBe('PRECOMPUTED');expect(h.result.current.job.mode).toBe('recorded')})
 it('no POST for invalid form or unavailable live capability',async()=>{const fetch=server();fetch.mockResolvedValue(jsonResponse(capabilitiesFixture(false)));const h=await start();await act(async()=>h.result.current.run());expect(fetch).toHaveBeenCalledTimes(1);h.rerender({request:null as unknown as ReturnType<typeof requestFixture>});await act(async()=>h.result.current.run('recorded'));expect(fetch).toHaveBeenCalledTimes(1)})
 it('preserves omitted requirement activation separately from expanded echoed defaults',async()=>{const fetch=server('COMPLETED');const h=renderHook(()=>useScientificJob(requestFixture(),['min_sun_visible_s']));await flush();await act(async()=>h.result.current.run());await flush();const body=JSON.parse(String(fetch.mock.calls.find(([u])=>String(u).endsWith('/analyses/jobs'))?.[1]?.body));expect(body.analysis.operation.requirements).toEqual({min_sun_visible_s:null});expect(h.result.current.job.submitted?.operation.requirements).toEqual({min_sun_visible_s:null});expect(h.result.current.job.response).not.toBeNull()})
 it('resumes only a terminal unchanged request, binds the new accepted ID, and blocks duplicate resume submissions',async()=>{
  const fetch=server('PARTIAL'), h=await start();await act(async()=>h.result.current.run());await flush()
  expect(h.result.current.job.status?.status).toBe('PARTIAL')
  const next='c'.repeat(32), identity='d'.repeat(64)
  fetch.mockImplementation(async(u)=>String(u).endsWith('/analyses/jobs')?jsonResponse({...acceptedFixture(),job_id:next,request_identity:identity,status_url:`/api/v1/jobs/${next}`,result_url:`/api/v1/jobs/${next}/result`,cancellation_url:`/api/v1/jobs/${next}/cancel`},202):jsonResponse({...statusFixture('RUNNING'),job_id:next,request_identity:identity}))
  await act(async()=>{void h.result.current.run('live',true);void h.result.current.run('live',true)});await flush()
  const posts=fetch.mock.calls.filter(([u])=>String(u).endsWith('/analyses/jobs'))
  expect(posts).toHaveLength(2)
  const resumed=JSON.parse(String(posts[1]?.[1]?.body));expect(resumed.resume_from).toBe(jobId);expect(resumed.analysis).toEqual(requestFixture())
  expect(h.result.current.job.accepted?.job_id).toBe(next);expect(h.result.current.job.status?.request_identity).toBe(identity)
  h.rerender({request:{...requestFixture(),observer:{...requestFixture().observer,earth_height_above_surface_m:2}}});await flush();await act(async()=>h.result.current.run('live',true))
  expect(fetch.mock.calls.filter(([u])=>String(u).endsWith('/analyses/jobs'))).toHaveLength(2)
 })
 it('each HTTP request has a timeout without a whole-job deadline',async()=>{const fetch=server();const h=await start();fetch.mockImplementation((_u,o)=>new Promise((_r,reject)=>o?.signal?.addEventListener('abort',()=>reject(new DOMException('cancel','AbortError')))));act(()=>{void h.result.current.run()});await flush(10001);expect(h.result.current.job.phase).toBe('disconnected');expect(h.result.current.job.message).toContain('timed out')})
})
