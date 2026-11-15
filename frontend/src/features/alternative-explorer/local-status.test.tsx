import { render,screen,fireEvent,within } from '@testing-library/react'
import { describe,it,expect,vi } from 'vitest'
import { backendOptimizerRecord } from '../../test/optimizerFixtures'
import { jobId } from '../../test/jobFixtures'
import { liveEvidence } from './live'
import { comparisonCompatible } from './evidence'
import { CandidateCard,Comparison } from './Comparison'
import { Radar } from './Radar'

// States emitted by local_site_optimizer.py. Mutations are test diagnostics;
// no NASA computation or recorded artifact is changed.
const localStages=['GENERATED','ELIGIBLE_FOR_DETAIL','SLOPE_UNKNOWN','SCREENED_OUT_TERRAIN','DETAILED_EVALUATED','SCIENTIFICALLY_INCOMPLETE','NOT_EVALUATED_RESOURCE_LIMIT'] as const
function fixture(stage:string){
 const result=backendOptimizerRecord('LOCAL')
 result.limitations.unshift('TEST DATA — local candidate status regression.')
 const candidate=structuredClone(result.candidates.find((c:any)=>c.stage==='DETAILED_EVALUATED'&&c.operation?.decision.status==='MET'))
 candidate.candidate_id='local-status-regression';candidate.stage=stage;candidate.reason_codes=[stage]
 if(stage!=='DETAILED_EVALUATED'){candidate.operation=null;candidate.metrics={};candidate.evidence_sha256=null}
 result.candidates.push(candidate);result.scope.generated_including_baseline++
 for(const c of [result.baseline,...result.candidates,...result.recommendations])if(c.operation)c.operation.data_origin='TEST_FIXTURE'
 const project=()=>liveEvidence({job_id:jobId,job_type:'LOCAL',status:'PARTIAL',result},{optimization:result.request})
 return {result,candidate,project}
}

describe('backend local candidate stage compatibility',()=>{
 it.each(localStages)('retains %s in a PARTIAL job without discarding valid candidates',stage=>{
  const f=fixture(stage),view=f.project(),c=view.alternatives.find(c=>c.id===f.candidate.candidate_id)!
  expect(view.status).toBe('PARTIAL');expect(c.status).toBe(stage)
  expect(view.alternatives.some(c=>c.decision?.status==='MET'&&c.score?.value===100&&comparisonCompatible(view.baseline,c))).toBe(true)
  if(stage!=='DETAILED_EVALUATED'){expect(c.score).toBeNull();expect(c.decision).toBeNull();expect(c.comparisonAllowed).toBe(false)}
 })
 it('preserves unknown slope and absent terrain measurements as null',()=>{
  const f=fixture('SLOPE_UNKNOWN')
  f.candidate.terrain={status:'NO_COVERAGE',slope_deg:null,slope_method:'UNKNOWN',eligible:false}
  const c=f.project().alternatives.find(c=>c.id===f.candidate.candidate_id)!
  expect(c.terrain?.slope_deg).toBeNull();expect(c.terrain?.surface_elevation_m).toBeNull();expect(c.terrain?.resolution_m).toBeNull()
  expect(c.terrain?.status).toBe('NO_COVERAGE');expect(c.raw.reason_codes).toEqual(['SLOPE_UNKNOWN'])
 })
 it.each(['COMPLETED','PARTIAL','FAILED'])('withholds diagnostic operation results for SCIENTIFICALLY_INCOMPLETE / %s',status=>{
  const f=fixture('SCIENTIFICALLY_INCOMPLETE'),op=structuredClone(f.result.recommendations[0].operation)
  op.execution_status=status;f.candidate.operation=op
  const c=f.project().alternatives.find(c=>c.id===f.candidate.candidate_id)!
  for(const value of [c.input,c.decision,c.score,c.rules,c.metrics,c.quality,c.hash,c.sourceKey])expect(value).toBeNull()
  expect(c.comparisonAllowed).toBe(false);expect(c.raw.operation).toEqual(op)
 })
 it.each(localStages.filter(s=>s!=='DETAILED_EVALUATED'))('does not promote a stale MET/100 operation attached to %s',stage=>{
  const f=fixture(stage);f.candidate.operation=structuredClone(f.result.recommendations[0].operation)
  const view=f.project(),c=view.alternatives.find(c=>c.id===f.candidate.candidate_id)!
  expect(c.decision).toBeNull();expect(c.score).toBeNull();expect(c.metrics).toBeNull();expect(comparisonCompatible(view.baseline,c)).toBe(false)
  expect((view.raw.recommendations as any[]).some(r=>r.candidate_id===c.id)).toBe(false)
 })
 it.each(['SLOPE_UNKNOWN','SCIENTIFICALLY_INCOMPLETE','NOT_EVALUATED_RESOURCE_LIMIT'])('rejects a purported recommendation without complete evidence: %s',stage=>{
  const f=fixture(stage);f.result.recommendations.push({candidate_id:f.candidate.candidate_id})
  expect(f.project).toThrow('Local recommendation lacks completed MET evidence')
 })
 it('still rejects noncompleted operation evidence labeled DETAILED_EVALUATED',()=>{
  const f=fixture('DETAILED_EVALUATED');f.candidate.operation.execution_status='PARTIAL'
  expect(f.project).toThrow('Invalid candidate operation evidence')
 })
 it('still rejects unsupported local stages',()=>expect(fixture('UNRECOGNIZED_STAGE').project).toThrow('Unsupported candidate evaluation stage'))
 it.each(['ELIGIBLE_FOR_DETAIL','SLOPE_UNKNOWN','SCIENTIFICALLY_INCOMPLETE'])('does not admit local-only %s as a temporal status',stage=>{
  const result=backendOptimizerRecord('TEMPORAL');result.candidates[0].evaluation_status=stage
  expect(()=>liveEvidence({job_id:jobId,job_type:'TEMPORAL',status:'PARTIAL',result},{optimization:result.request})).toThrow('Unsupported candidate evaluation stage')
 })
 it.each(['SLOPE_UNKNOWN','SCIENTIFICALLY_INCOMPLETE'])('keeps %s selectable on the radar while withholding score and A/B deltas',stage=>{
  const f=fixture(stage)
  if(stage==='SLOPE_UNKNOWN')f.candidate.terrain.slope_deg=null
  else {f.candidate.operation=structuredClone(f.result.recommendations[0].operation);f.candidate.operation.execution_status='PARTIAL'}
  const view=f.project(),c=view.alternatives.find(c=>c.id===f.candidate.candidate_id)!,choose=vi.fn()
  render(<><Radar baseline={view.baseline} candidates={[c]} selected={c.id} onSelect={choose}/><CandidateCard candidate={c} title="Selected Alternative"/><Comparison baseline={view.baseline} alternative={c}/></>)
  fireEvent.click(screen.getByRole('button',{name:/Select candidate 1/}));expect(choose).toHaveBeenCalledWith(c.id)
  const card=within(screen.getByRole('region',{name:'Selected Alternative'}))
  expect(card.getByText('Not calculated')).toBeInTheDocument();expect(card.getByText(`Evaluation: ${stage}. Origin: LIVE_COMPUTED`)).toBeInTheDocument()
  expect(card.queryByText('100 / 100')).not.toBeInTheDocument();expect(screen.getByRole('alert')).toHaveTextContent('Comparison unavailable')
  if(stage==='SLOPE_UNKNOWN')expect(card.getByText(/Slope: Unavailable \(null\)/)).toBeInTheDocument()
 })
})
