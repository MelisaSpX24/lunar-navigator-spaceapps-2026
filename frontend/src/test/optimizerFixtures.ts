/** Controlled HTTP fixtures projected from backend-owned recorded shapes.
 * Test only: deliberately marked TEST_FIXTURE; never imported by production. */
import { readFileSync } from 'node:fs'
import { normalizeRequest } from '../services/api/normalizedRequest'
import { stable } from '../features/alternative-explorer/evidence'
const archive=JSON.parse(readFileSync('../data_pipeline/evidence/command-10-closure.json','utf8'))
export const backendOptimizerRecord=(kind:'TEMPORAL'|'LOCAL')=>structuredClone(kind==='TEMPORAL'?archive.temporal.result:archive.local.runs[0].result.result)
export function optimizerFixture(kind:'TEMPORAL'|'LOCAL',payload:any){
 const r=backendOptimizerRecord(kind),submitted=payload.optimization
 const defaults=kind==='TEMPORAL'?{selection_strategy:'LEGACY',coarse_start_step_s:21600,refinement_step_s:3600,max_coarse_candidates:64,max_detailed_candidates:3,max_recommendations:3,max_window_evaluations:24,max_new_horizon_rays:4000,max_terrain_samples:3000000,max_wall_time_s:1200,max_cache_entries:2048,resolved_site:null,resolved_site_id:null}:{evaluation_policy:'STRICT_EVIDENCE',selection_strategy:'SLOPE_ONLY',search_radius_m:5000,coarse_step_m:500,refinement_step_m:100,max_generated_candidates:32,max_detailed_candidates:2,max_recommendations:3,max_slope_deg:10}
 r.request={...defaults,...submitted,baseline_analysis:normalizeRequest(submitted.baseline_analysis)}
 r.limitations.unshift('TEST DATA — controlled optimizer transport response, not a live NASA calculation.')
 const base=r.request.baseline_analysis,explicit=Object.keys(submitted.baseline_analysis.operation.requirements)
 let admitted=1
 if(kind==='TEMPORAL'){
  const recommendations=new Set(r.recommendations.map((c:any)=>c.candidate_id))
  for(const c of r.candidates){if(!recommendations.has(c.candidate_id)||admitted>=payload.max_candidate_evaluations){c.operation=null;c.metrics={};c.evaluation_status='NOT_EVALUATED_RESOURCE_LIMIT';c.evidence_sha256=null;c.evidence_mode=null}else admitted++}
  r.recommendations=r.candidates.filter((c:any)=>c.operation&&recommendations.has(c.candidate_id))
  r.detailed_evaluated_including_baseline=admitted;r.detailed_completed_including_baseline=admitted;r.scientifically_incomplete_including_baseline=0;r.not_evaluated_alternatives=r.candidates.length-admitted+1
 }else{
  r.candidates=r.candidates.filter((c:any)=>c.distance_m<=submitted.search_radius_m+1e-6)
  const ids=new Set(r.candidates.map((c:any)=>c.candidate_id));r.recommendations=r.recommendations.filter((c:any)=>ids.has(c.candidate_id));r.comparisons=r.comparisons.filter((c:any)=>ids.has(c.candidate_id))
  r.scope={...r.scope,generated_including_baseline:r.candidates.length+1,detailed_attempts_including_baseline:r.candidates.filter((c:any)=>c.operation).length+1}
 }
 function patch(c:any){if(!c.operation)return;const op=c.operation,old=op.request.analysis
  op.data_origin='TEST_FIXTURE'
  const site=kind==='LOCAL'?old.site:base.site,time=kind==='TEMPORAL'?old.time:base.time
  op.request.analysis={...base,site,time}
  op.request.analysis.operation={...base.operation,requirements:{...base.operation.requirements}}
  // Preserve the actual submitted rule activation in this controlled response.
  if(!explicit.includes('earth_clearance_margin_deg')){op.decision.rules=op.decision.rules.filter((x:any)=>x.code!=='EARTH_CLEARANCE_MARGIN');op.rule_evidence=op.rule_evidence.filter((x:any)=>x.rule.code!=='EARTH_CLEARANCE_MARGIN')}
  op.provenance.window_request={...submitted.window_template,start_utc:time.start_utc,visibility:{...submitted.window_template.visibility,utc:time.start_utc,terrain:{...submitted.window_template.visibility.terrain,location:{latitude_deg:site.latitude_deg,longitude_deg_east:site.longitude_deg_east,frame:site.frame,latitude_type:site.latitude_type}}}}
 }
 patch(r.baseline);r.candidates.forEach(patch)
 const index=new Map(r.candidates.map((c:any)=>[c.candidate_id,c]));r.recommendations=r.recommendations.map((c:any)=>index.get(c.candidate_id))
 // Keep the backend defaults expanded; no unknown frontend fields in this result.
 if(stable(r.request.baseline_analysis)!==stable(base))throw Error('Unexpected test baseline mutation')
 return r
}
