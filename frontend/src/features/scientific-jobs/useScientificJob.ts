import { useCallback, useEffect, useRef, useState } from 'react'
import { capabilities, completedAnalysis, isAccepted, isJobResult, isJobStatus, jobFetch, jobRequest, terminal, type Accepted, type ApiFailure, type Capabilities, type JobStatus, type ResultEnvelope, type JobType } from '../../services/api/jobs'
import { normalizedRequestMatches } from '../../services/api/normalizedRequest'
import { isAnalysis, record, type AnalysisResponse } from '../../services/api/responses'
import { requestMatches } from '../analysis-results/requestMatch'
import type { AnalysisRequestV1, AnalysisInputV1 } from '../mission-input/analysisRequest'

export type OptimizerExtension={type:Exclude<JobType,'ANALYSIS'>;payload:Record<string,unknown>;validate:(envelope:ResultEnvelope)=>boolean}
export type Availability = {kind:'checking'}|{kind:'available';data:Capabilities}|{kind:'unavailable';failure:ApiFailure}
export type ResearchState = {
  phase:'idle'|'submitting'|'watching'|'stopped'|'disconnected'|'error'|'terminal'|'received'
  message:string; accepted:Accepted|null; status:JobStatus|null; envelope:ResultEnvelope|null
  response:AnalysisResponse|null; request:AnalysisRequestV1|null; submitted:AnalysisInputV1|null; mode:'live'|'recorded'; failure:ApiFailure|null
}
const initial=():ResearchState=>({phase:'idle',message:'No research prototype has been requested.',accepted:null,status:null,envelope:null,response:null,request:null,submitted:null,mode:'live',failure:null})
export function useScientificJob(current: AnalysisRequestV1|null, explicitRequirements?: string[], extension?:OptimizerExtension|null, sharedAvailability?:Availability) {
  const extensionRef=useRef(extension);extensionRef.current=extension
  const extensionKey=extension?JSON.stringify({type:extension.type,payload:extension.payload}):''
  const keyRef=useRef(extensionKey);keyRef.current=extensionKey
  const submittedKey=useRef('')
  const submitted:AnalysisInputV1|null=current?{...current,operation:{...current.operation,requirements:Object.fromEntries(Object.entries(current.operation.requirements).filter(([key])=>explicitRequirements===undefined||explicitRequirements.includes(key)))}}:null
  const inputRef=useRef(submitted);inputRef.current=submitted
  const [localAvailability,setAvailability]=useState<Availability>({kind:'checking'})
  const availability=sharedAvailability??localAvailability
  const [job,setJob]=useState<ResearchState>(initial)
  const now=useRef(job), currentRef=useRef(current); currentRef.current=current
  const sequence=useRef(0), alive=useRef(false), busy=useRef(false), controller=useRef<AbortController|null>(null)
  const deadline=useRef(0)
  const timer=useRef<ReturnType<typeof setTimeout>|null>(null), checks=useRef<AbortController|null>(null)
  const publish=useCallback((next:ResearchState)=>{now.current=next;setJob(next)},[])
  const stop=useCallback(()=>{sequence.current++;controller.current?.abort();controller.current=null;if(timer.current)clearTimeout(timer.current);timer.current=null;busy.current=false},[])
  const clear=useCallback(()=>{stop();publish(initial())},[stop,publish])
  const check=useCallback(async()=>{
    checks.current?.abort();const c=new AbortController();checks.current=c;setAvailability({kind:'checking'})
    const timeout=setTimeout(()=>c.abort(),10_000)
    try {const r=await capabilities(c.signal);if(alive.current&&checks.current===c)setAvailability(r.ok?{kind:'available',data:r.data}:{kind:'unavailable',failure:r})}
    finally{clearTimeout(timeout)}
  },[])
  useEffect(()=>{alive.current=true;const t=sharedAvailability?undefined:setTimeout(()=>void check(),0);return()=>{alive.current=false;clearTimeout(t);checks.current?.abort();stop()}},[check,stop,!!sharedAvailability])
  // A changed/invalid form cannot retain another scenario's evidence, even if an abort is ignored.
  const signature=JSON.stringify(submitted)+extensionKey
  useEffect(()=>{if(now.current.submitted&&(JSON.stringify(now.current.submitted)!==JSON.stringify(inputRef.current)||submittedKey.current!==keyRef.current))clear()},[signature,clear])
  const valid=(seq:number)=>submittedKey.current===keyRef.current&&alive.current&&seq===sequence.current&&!!now.current.request&&!!currentRef.current&&requestMatches(now.current.request,currentRef.current)&&JSON.stringify(now.current.submitted)===JSON.stringify(inputRef.current)
  const call=async(path:string,seq:number,body?:unknown,post=false)=>{
    const c=new AbortController();controller.current=c;const timeout=setTimeout(()=>c.abort(),10_000)
    try {const r=await jobFetch(path,c.signal,body,post);return valid(seq)?r:null}finally{clearTimeout(timeout);if(controller.current===c)controller.current=null}
  }
  const failed=(failure:ApiFailure)=>publish({...now.current,phase:failure.kind==='network'||failure.kind==='aborted'?'disconnected':'error',failure,message:failure.kind==='aborted'?'Connection timed out. The calculation may still be running. Retry this job; do not resubmit.':failure.message})
  const invalid=(message:string):ApiFailure=>({ok:false,kind:'invalid',status:200,message})
  const loadResult=async(seq:number,status:JobStatus)=>{
    const r=await call(`jobs/${status.job_id}/result`,seq)
    if(!r)return
    if(!r.ok){failed(r);return}
    if(r.status!==200||!isJobResult(r.data,status.job_id,status.status,extensionRef.current?.type??'ANALYSIS')){failed(invalid('Invalid job result envelope or mismatched job identity.'));return}
    const envelope=r.data, response=extensionRef.current?null:completedAnalysis(envelope,now.current.request!)
    const usable=extensionRef.current?extensionRef.current.validate(envelope):!!response
    if(status.status==='COMPLETED'&&!usable){failed(invalid(extensionRef.current?'Completed job lacks a valid, matching optimizer result.':'Completed job lacks a valid, matching completed AnalysisResult 1.0.'));return}
    publish({...now.current,phase:usable?'received':'terminal',envelope,response,message:usable?(status.status==='COMPLETED'?'Completed research response received. Review model limitations.':'PARTIAL optimizer evidence received — incomplete execution.'):`${status.status} — partial evidence is retained, not presented as a complete scientific analysis.`,failure:null})
  }
  const poll=async(seq:number,attempt=0):Promise<void>=>{
    const a=now.current.accepted;if(!a||!valid(seq))return
    if(Date.now()>deadline.current){stop();publish({...now.current,phase:'stopped',message:'Stopped waiting after 60 minutes. The backend may still be running; reconnect explicitly to this job.'});return}
    const r=await call(`jobs/${a.job_id}`,seq)
    if(!r)return
    if(!r.ok){failed(r);if((r.kind==='network'||r.kind==='aborted'||r.status===502||r.status===504)&&attempt<3)timer.current=setTimeout(()=>void poll(seq,attempt+1),Math.min(1500*2**attempt,12000));return}
    if(r.status!==200||!isJobStatus(r.data,a.job_id,a.request_identity,extensionRef.current?.type??'ANALYSIS')){failed(invalid('Invalid job status or mismatched request identity.'));return}
    const s=r.data
    if(now.current.status&&((terminal(now.current.status.status)&&s.status!==now.current.status.status)||(now.current.status.status==='RUNNING'&&s.status==='QUEUED')||(now.current.status.status==='CANCEL_REQUESTED'&&['QUEUED','RUNNING'].includes(s.status)))){failed(invalid('Job status regressed after a terminal state.'));return}
    publish({...now.current,status:s,phase:terminal(s.status)?'terminal':'watching',failure:null,message:terminal(s.status)?`${s.status} — server execution state.`:s.status==='CANCEL_REQUESTED'?'Cancellation requested. Waiting for a safe backend checkpoint.':`${s.status} — ${s.progress.stage}. No completion is assumed.`})
    if(terminal(s.status)){busy.current=false;if(s.result_available)await loadResult(seq,s);return}
    timer.current=setTimeout(()=>void poll(seq),1500)
  }
  const run=async(mode:'live'|'recorded'='live',resume=false,checkpointId?:string)=>{
    const request=currentRef.current
    if(!alive.current||busy.current||['submitting','watching'].includes(now.current.phase)||(now.current.accepted&&(!now.current.status||!terminal(now.current.status.status)))||!request||availability.kind!=='available')return
    const c=availability.data
    if(!c.api_reachable||!c.job_types.includes(extensionRef.current?.type??'ANALYSIS')||(mode==='live'?!(c.scientific_job_runner_available&&c.configured_science_files_available&&c.bounded_live_prototype_supported):!c.recorded_prototype_supported))return
    if(extensionRef.current&&mode!=='live')return
    // The server revalidates terminal state, exact request and source identities.
    // An invalid checkpoint must never silently become a fresh expensive job.
    if(checkpointId!==undefined&&(mode!=='live'||resume||!/^[a-f0-9]{32}$/.test(checkpointId)))return
    const previous=now.current
    if(resume&&(!previous.accepted||!previous.status||!terminal(previous.status.status)||!previous.request||!requestMatches(previous.request,request)))return
    stop();submittedKey.current=keyRef.current;deadline.current=Date.now()+3_600_000;busy.current=true;const seq=sequence.current
    publish({...initial(),phase:'submitting',request:structuredClone(request),submitted:structuredClone(inputRef.current),mode,message:'Submitting research request. No completion is assumed.'})
    const path=extensionRef.current?`optimizations/${extensionRef.current.type.toLowerCase()}`:mode==='recorded'?'analyses?mode=recorded&registration=PROTOTYPE&evaluation_policy=PROTOTYPE_SAMPLED_ESTIMATE&step_s=3600':'analyses/jobs'
    const resumeFrom=checkpointId??(resume?previous.accepted!.job_id:undefined)
    const r=await call(path,seq,extensionRef.current?{...extensionRef.current.payload,...(resumeFrom?{resume_from:resumeFrom}:{})}:mode==='recorded'?inputRef.current:jobRequest(inputRef.current!,resumeFrom),true)
    if(!r)return
    busy.current=false
    if(!r.ok){failed(r);return}
    if(mode==='recorded'){
      if(r.status!==200||!isAnalysis(r.data)||r.data.execution_status!=='COMPLETED'||r.data.data_origin!=='PRECOMPUTED'||!normalizedRequestMatches(request,r.data.request)){failed(invalid('Invalid or mismatched recorded analysis. No alternative record was substituted.'));return}
      publish({...now.current,phase:'received',response:r.data,message:'PRECOMPUTED — exact-match recorded research response. No live calculation was performed.'});return
    }
    if(r.status!==202||!isAccepted(r.data,extensionRef.current?.type??'ANALYSIS')){failed(invalid('Invalid job acceptance, identity, resource policy or unsafe server URL.'));return}
    const requestedResources=extensionRef.current?.payload.resources
    if(record(requestedResources)&&Object.entries(r.data.resource_policy).some(([k,n])=>typeof requestedResources[k]!=='number'||n>(requestedResources[k] as number))){failed(invalid('Accepted resource policy exceeds the submitted limits.'));return}
    publish({...now.current,phase:'watching',accepted:r.data,message:'QUEUED — durable job accepted. This is not a completed analysis.'})
    void poll(seq)
  }
  const stopWaiting=()=>{stop();publish({...now.current,phase:'stopped',message:'Stopped waiting. The backend calculation may still be running. No cancellation was sent.'})}
  const retry=()=>{if(!now.current.accepted||busy.current)return;stop();deadline.current=Date.now()+3_600_000;const seq=sequence.current;publish({...now.current,phase:'watching',failure:null,message:'Reconnecting to the same job. No new analysis was submitted.'});void poll(seq)}
  const cancel=async()=>{
    const a=now.current.accepted;if(!a||busy.current||now.current.status&&terminal(now.current.status.status))return
    stop();deadline.current=Date.now()+3_600_000;busy.current=true;const seq=sequence.current
    publish({...now.current,phase:'watching',message:'Sending cancellation request; cancellation is not yet confirmed.'})
    const r=await call(`jobs/${a.job_id}/cancel`,seq,undefined,true);busy.current=false
    if(!r)return
    if(!r.ok){failed(r);return}
    if(r.status!==200||!isJobStatus(r.data,a.job_id,a.request_identity,extensionRef.current?.type??'ANALYSIS')){failed(invalid('Invalid cancellation response. Backend state is unknown.'));return}
    publish({...now.current,status:r.data,phase:terminal(r.data.status)?'terminal':'watching',message:r.data.status==='CANCEL_REQUESTED'?'Cancellation requested, not yet cancelled.':`${r.data.status} — server execution state.`})
    if(terminal(r.data.status)){if(r.data.result_available)await loadResult(seq,r.data)}else void poll(seq)
  }
  return {job,availability,isBusy:()=>busy.current||['submitting','watching'].includes(now.current.phase)||!!(now.current.accepted&&(!now.current.status||!terminal(now.current.status.status))),hasActiveRequirement:!!submitted&&Object.entries(submitted.operation.requirements).some(([key,value])=>key==='require_simultaneous'?value===true:value!==null),check,run,stopWaiting,retry,cancel,clear,active:['submitting','watching'].includes(job.phase)||!!(job.accepted&&(!job.status||!terminal(job.status.status)))}
}
