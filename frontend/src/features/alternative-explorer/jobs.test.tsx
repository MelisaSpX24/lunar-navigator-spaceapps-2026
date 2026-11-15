import { optimizerFixture } from '../../test/optimizerFixtures'
import { act,renderHook } from '@testing-library/react'
import { afterEach,beforeEach,describe,it,expect,vi } from 'vitest'
import { readFileSync,writeFileSync,mkdirSync } from 'node:fs'
import { useScientificJob,type OptimizerExtension } from '../scientific-jobs/useScientificJob'
import { acceptedFixture,capabilitiesFixture,jobId,requestIdentity,statusFixture } from '../../test/jobFixtures'
import { jsonResponse } from '../../test/apiFixtures'
import { candidateInput } from './requests'
import { liveEvidence,optimizerPayload,defaultOptimizerSettings } from './live'
import { isAccepted,isJobResult,isJobStatus,type JobType } from '../../services/api/jobs'
const closure=JSON.parse(readFileSync('../data_pipeline/evidence/command-10-closure.json','utf8'))
const actual=(kind:'TEMPORAL'|'LOCAL')=>structuredClone(kind==='TEMPORAL'?closure.temporal.result:closure.local.runs[0].result.result)
const flush=async(ms=0)=>{await act(async()=>{await vi.advanceTimersByTimeAsync(ms)})}
beforeEach(()=>vi.useFakeTimers());afterEach(()=>vi.useRealTimers())
describe('shared typed optimizer lifecycle',()=>{
 it.each(['TEMPORAL','LOCAL'] as const)('resumes persisted %s evidence with current explicit budgets and no initial fresh POST',async kind=>{
  const data=actual(kind),fields=Object.keys(data.request.baseline_analysis.operation.requirements),baseline=candidateInput(data.request.baseline_analysis,fields)!
  const payload=optimizerPayload(kind,{analysis:baseline.source,request:baseline.request,window:data.request.window_template},{...defaultOptimizerSettings,budget:4,radius:1000})!
  const fetch=vi.spyOn(globalThis,'fetch').mockImplementation(async u=>String(u).includes('/optimizations/')?jsonResponse({...acceptedFixture(),job_type:kind},202):jsonResponse({...statusFixture('RUNNING'),job_type:kind}))
  const h=renderHook(()=>useScientificJob(baseline.request,fields,{type:kind,payload,validate:()=>false},{kind:'available',data:capabilitiesFixture()}));await flush()
  await act(async()=>h.result.current.run('live',false,'c'.repeat(32)));await flush()
  const posts=fetch.mock.calls.filter(([,o])=>o?.method==='POST')
  expect(posts).toHaveLength(1)
  expect(JSON.parse(String(posts[0]?.[1]?.body))).toEqual({...payload,resume_from:'c'.repeat(32)})
  expect(h.result.current.job.status?.status).toBe('RUNNING')
  h.unmount()
 })
 it.each(['TEMPORAL','LOCAL'] as const)('submits/polls/extracts %s at result root with one POST and no extra capabilities fetch',async kind=>{
  const data=actual(kind),raw=data.request.baseline_analysis,fields=Object.keys(raw.operation.requirements),baseline=candidateInput(raw,fields)!
  const payload={optimization:data.request},extension:OptimizerExtension={type:kind,payload,validate:e=>{try{liveEvidence(e,payload);return true}catch{return false}}}
  const fetch=vi.spyOn(globalThis,'fetch').mockImplementation(async u=>{
   if(String(u).includes('/optimizations/'))return jsonResponse({...acceptedFixture(),job_type:kind},202)
   if(String(u).endsWith('/result'))return jsonResponse({job_id:jobId,job_type:kind,status:'COMPLETED',result:data})
   return jsonResponse({...statusFixture('COMPLETED'),job_type:kind})
  })
  const h=renderHook(()=>useScientificJob(baseline.request,fields,extension,{kind:'available',data:capabilitiesFixture()}));await flush()
  await act(async()=>{void h.result.current.run();void h.result.current.run()});await flush()
  expect(fetch.mock.calls.filter(([u])=>String(u).includes('/optimizations/'))).toHaveLength(1)
  expect(String(fetch.mock.calls[0]?.[0])).toBe(`/api/v1/optimizations/${kind.toLowerCase()}`)
  expect(h.result.current.job.phase).toBe('received');expect(h.result.current.job.response).toBeNull();expect(h.result.current.job.envelope?.result.schema_version).toBe(data.schema_version)
  expect(fetch.mock.calls.some(([u])=>String(u).endsWith('/capabilities'))).toBe(false)
 })
 it('keeps job-type validation strict by default and rejects cross-type status/envelopes',()=>{const a={...acceptedFixture(),job_type:'LOCAL' as JobType},s={...statusFixture(),job_type:'LOCAL'};expect(isAccepted(a)).toBe(false);expect(isAccepted(a,'LOCAL')).toBe(true);expect(isJobStatus(s,jobId,requestIdentity,'TEMPORAL')).toBe(false);expect(isJobResult({job_id:jobId,job_type:'LOCAL',status:'COMPLETED',result:{}},jobId,'COMPLETED','ANALYSIS')).toBe(false)})
 it('cancels an optimizer cooperatively, reconnects the same ID and clears stale settings',async()=>{
  const data=actual('LOCAL'),baseline=candidateInput(data.request.baseline_analysis,Object.keys(data.request.baseline_analysis.operation.requirements))!
  let status='RUNNING',posts=0
  const fetch=vi.spyOn(globalThis,'fetch').mockImplementation(async(u,o)=>{
   if(String(u).includes('/optimizations/')){posts++;return jsonResponse({...acceptedFixture(),job_type:'LOCAL'},202)}
   if(String(u).endsWith('/cancel')){expect(o?.method).toBe('POST');status='CANCEL_REQUESTED'}
   return jsonResponse({...statusFixture(),job_type:'LOCAL',status})
  })
  const extension:OptimizerExtension={type:'LOCAL',payload:{optimization:data.request},validate:()=>false}
  const h=renderHook(({ext})=>useScientificJob(baseline.request,undefined,ext,{kind:'available',data:capabilitiesFixture()}),{initialProps:{ext:extension}});await flush();await act(async()=>h.result.current.run());await flush()
  act(()=>h.result.current.stopWaiting());expect(h.result.current.job.phase).toBe('stopped');act(()=>h.result.current.retry());await flush();expect(posts).toBe(1)
  await act(async()=>h.result.current.cancel());await flush();expect(h.result.current.job.status?.status).toBe('CANCEL_REQUESTED');status='CANCELLED';await flush(1500);expect(h.result.current.job.phase).toBe('terminal')
  h.rerender({ext:{...extension,payload:{optimization:{...data.request,search_radius_m:1000}}}});await flush();expect(h.result.current.job.accepted).toBeNull();expect(h.result.current.job.envelope).toBeNull()
  h.unmount();const n=fetch.mock.calls.length;await flush(6000);expect(fetch).toHaveBeenCalledTimes(n)
 })
 it.each(['TEMPORAL','LOCAL'] as const)('accepts controlled normalized %s responses for sparse user requirements and bounded budgets',kind=>{
  const data=actual(kind),raw=data.request.baseline_analysis;raw.operation.requirements={min_sun_visible_s:kind==='TEMPORAL'?3600:600}
  const input=candidateInput(raw,['min_sun_visible_s'])!,payload=optimizerPayload(kind,{analysis:input.source,request:input.request,window:data.request.window_template},defaultOptimizerSettings)!
  const fixture=optimizerFixture(kind,payload),view=liveEvidence({job_id:jobId,job_type:kind,status:'COMPLETED',result:fixture},payload)
  expect(view.scientificOrigin).toBe('TEST_FIXTURE');expect(view.alternatives.some(c=>c.score?.value===100)).toBe(true)
 })
 it('exports actual typed payloads for read-only backend Pydantic verification',()=>{
  const t=actual('TEMPORAL'),l=actual('LOCAL'),ti=candidateInput(t.request.baseline_analysis,Object.keys(t.request.baseline_analysis.operation.requirements))!,li=candidateInput(l.request.baseline_analysis,Object.keys(l.request.baseline_analysis.operation.requirements))!
  const temporal=optimizerPayload('TEMPORAL',{analysis:ti.source,request:ti.request,window:t.request.window_template},defaultOptimizerSettings)!,local=optimizerPayload('LOCAL',{analysis:li.source,request:li.request,window:l.request.window_template},defaultOptimizerSettings)!
  expect(temporal.optimization).toBeDefined();expect(local.optimization).toBeDefined();mkdirSync('.validation',{recursive:true});writeFileSync('.validation/command12-contract.json',JSON.stringify({temporal,local,temporal_result:t,local_result:l}))
 })
})
