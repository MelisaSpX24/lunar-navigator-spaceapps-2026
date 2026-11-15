import { act,renderHook,waitFor } from '@testing-library/react'
import { describe,it,expect,vi } from 'vitest'
import recorded from 'virtual:recorded-evidence'
import { ScenarioProvider,useScenario } from '../scenario/ScenarioProvider'
import { recordedEvidence } from './evidence'
import { acceptedFixture,capabilitiesFixture,statusFixture,jobId } from '../../test/jobFixtures'
import { jsonResponse,healthFixture,analysisFixture } from '../../test/apiFixtures'
describe('atomic candidate transfer to existing scenario',()=>{
 it('loads sparse local input, preserves explicit rules, clears old analysis, and does not POST until explicit run',async()=>{
  const posts:unknown[]=[]
  vi.spyOn(globalThis,'fetch').mockImplementation(async(u,o)=>{
   if(o?.method==='POST')posts.push(JSON.parse(String(o.body)))
   if(String(u).endsWith('/health'))return jsonResponse(healthFixture())
   if(String(u).endsWith('/capabilities'))return jsonResponse({api_reachable:true,scientific_job_runner_available:true,configured_science_files_available:true,bounded_live_prototype_supported:true,recorded_prototype_supported:true,fully_independently_validated_science_ready:false,science_ready:false,job_types:['ANALYSIS','TEMPORAL','LOCAL'],worker_count:1,limits:{active_jobs:4,max_output_bytes:8388608,max_wall_time_s:3600,max_local_radius_m:5000},reason_codes:[]})
   return jsonResponse({detail:{code:'CONTROLLED_NO_COMPUTE'}},503)
  })
  const h=renderHook(()=>useScenario(),{wrapper:ScenarioProvider}),c=recordedEvidence(recorded.local,'local').alternatives[0]!
  await waitFor(()=>expect(h.result.current.research.availability.kind).toBe('available'))
  act(()=>{expect(h.result.current.applyCandidateRequest(c.input!.source,c.input!.explicit,c.id)).toBe(true)})
  expect(posts).toHaveLength(0);expect(h.result.current.state.latitude).toBe(String(c.location!.latitude_deg));expect(h.result.current.selected?.longitude).toBeCloseTo(c.location!.longitude_deg_east-360);expect(h.result.current.state.utcTime).toBe('08:00:00');expect(h.result.current.state.hours).toBe('1');expect(h.result.current.analysis.kind).toBe('idle')
  await act(async()=>h.result.current.research.run());expect(posts).toHaveLength(1);expect((posts[0] as any).analysis.operation.requirements).toEqual({min_sun_visible_s:600})
  act(()=>{h.result.current.applyCandidateRequest(c.input!.source,c.input!.explicit,c.id)});expect(h.result.current.research.job.phase).toBe('idle');expect(h.result.current.research.job.response).toBeNull()
  const before=h.result.current.state;act(()=>{expect(h.result.current.applyCandidateRequest({},[],c.id)).toBe(false)});expect(h.result.current.state).toBe(before)
 })
 it('clears a completed prior scientific response on atomic transfer without another POST',async()=>{
  let submitted:Record<string,unknown>={},posts=0
  vi.spyOn(globalThis,'fetch').mockImplementation(async(u,o)=>{
   if(String(u).endsWith('/health'))return jsonResponse(healthFixture())
   if(String(u).endsWith('/capabilities'))return jsonResponse(capabilitiesFixture())
   if(String(u).endsWith('/analyses/jobs')){posts++;submitted=JSON.parse(String(o?.body)).analysis;return jsonResponse(acceptedFixture(),202)}
   if(String(u).endsWith('/result'))return jsonResponse({job_id:jobId,job_type:'ANALYSIS',status:'COMPLETED',result:{analysis:analysisFixture({execution_status:'COMPLETED',data_origin:'TEST_FIXTURE',request:submitted})}})
   return jsonResponse(statusFixture('COMPLETED'))
  })
  const h=renderHook(()=>useScenario(),{wrapper:ScenarioProvider}),local=recordedEvidence(recorded.local,'local').alternatives[0]!,temporal=recordedEvidence(recorded.temporal,'temporal').alternatives[0]!
  await waitFor(()=>expect(h.result.current.research.availability.kind).toBe('available'))
  act(()=>{h.result.current.applyCandidateRequest(local.input!.source,local.input!.explicit,local.id)})
  await act(async()=>h.result.current.research.run());await waitFor(()=>expect(h.result.current.research.job.phase).toBe('received'))
  act(()=>{h.result.current.applyCandidateRequest(temporal.input!.source,temporal.input!.explicit,temporal.id)})
  expect(h.result.current.research.job.response).toBeNull();expect(h.result.current.analysis.kind).toBe('idle');expect(h.result.current.state.utcTime).toBe('16:26:15');expect(h.result.current.state.hours).toBe('6');expect(posts).toBe(1)
 })

})
