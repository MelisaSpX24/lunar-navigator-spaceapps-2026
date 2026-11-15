import { recordedEvidence } from '../src/features/alternative-explorer/evidence.ts'
import { readFileSync } from 'node:fs'
import { createHash } from 'node:crypto'
import { fileURLToPath } from 'node:url'
import { resolve } from 'node:path'

export function readDemoEvidence(demoDir=fileURLToPath(new URL('../../data_pipeline/demo/',import.meta.url)), repoDir=fileURLToPath(new URL('../../',import.meta.url))) {
  const manifest=JSON.parse(readFileSync(resolve(demoDir,'manifest.json'),'utf8'))
  if(manifest.schema_version!=='24and28-demo-manifest-v1'||manifest.delivery_data_origin!=='RECORDED_EVIDENCE_EXPORT'||manifest.science_ready!==false||manifest.new_live_calculations!==false)throw Error('Invalid recorded evidence manifest')
  const sha=(bytes:Buffer)=>createHash('sha256').update(bytes).digest('hex')
  for(const file of ['data_pipeline/evidence/command-10-closure.json','data_pipeline/evidence/command-10-validation.json']){
    const source=manifest.sources.find((s:{file:string})=>s.file===file)
    if(!source||sha(readFileSync(resolve(repoDir,file)))!==source.sha256)throw Error(`Source evidence checksum mismatch: ${file}`)
  }
  const payloads:Record<string,unknown>={}
  for(const name of ['temporal','local']){
    const file=`${name}_demo.json`, bytes=readFileSync(resolve(demoDir,file)), expected=manifest.files[file]
    if(!expected||bytes.length!==expected.bytes||sha(bytes)!==expected.sha256)throw Error(`Recorded evidence bytes/checksum mismatch: ${file}`)
    const value=JSON.parse(bytes.toString('utf8'))
    if(value.schema_version!=='24and28-demo-evidence-v1'||value.science_ready!==false||!value.baseline||!Array.isArray(value.alternatives))throw Error(`Invalid recorded evidence schema: ${file}`)
    payloads[name]=value
  }
  return {manifest,temporal:payloads.temporal,local:payloads.local}
}
export function demoEvidencePlugin(){
  // Fail dev, build and tests before serving any unverified source bytes.
  const evidence=readDemoEvidence()
  recordedEvidence(evidence.temporal,'temporal');recordedEvidence(evidence.local,'local')
  return {name:'verified-recorded-evidence',resolveId(id:string){if(id==='virtual:recorded-evidence')return '\0verified-recorded-evidence'},load(id:string){if(id==='\0verified-recorded-evidence')return `export default ${JSON.stringify(evidence)}`}}
}
