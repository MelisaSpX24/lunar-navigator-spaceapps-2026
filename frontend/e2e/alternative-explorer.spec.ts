import {test,expect,type Page} from '@playwright/test'
import {healthFixture} from '../src/test/apiFixtures'
import {acceptedFixture,capabilitiesFixture,statusFixture,jobId} from '../src/test/jobFixtures'
import {optimizerFixture} from '../src/test/optimizerFixtures'
import {readFileSync} from 'node:fs'
const temporal=JSON.parse(readFileSync('../data_pipeline/demo/temporal_demo.json','utf8')),local=JSON.parse(readFileSync('../data_pipeline/demo/local_demo.json','utf8'))
const region=(p:Page,n:string)=>p.getByRole('region',{name:n,exact:true})
async function offline(p:Page){await p.route('**/api/v1/**',r=>r.abort());await p.goto('/#/alternatives')}
const nav=(p:Page,n:string)=>p.getByRole('navigation').getByRole('link',{name:n,exact:true})
test('offline temporal evidence explains real supplied deltas without fabricating analysis',async({page},info)=>{
 const posts:string[]=[];page.on('request',r=>{if(r.method()==='POST')posts.push(r.url())});await offline(page)
 await expect(page.getByText('RECORDED EVIDENCE',{exact:true})).toBeVisible()
 await expect(region(page,'Baseline')).toContainText('0 / 100');await expect(region(page,'Selected Alternative')).toContainText('100 / 100')
 await expect(region(page,'A/B Comparison')).toContainText('+3d 8h 26m 15s')
 await expect(region(page,'A/B Comparison')).toContainText('MIN_SUN_VISIBLE_DURATION: NOT_MET → MET')
 const sun=region(page,'A/B Comparison').getByRole('row',{name:/sun sampled visibility/});await expect(sun).toContainText('+6h 0m 0s')
 await expect(page.getByText(/Full horizon profile is not included/)).toBeVisible();await expect(page.locator('canvas')).toHaveCount(0)
 expect(posts).toEqual([]);await page.screenshot({path:info.outputPath('Temporal-offline.png'),fullPage:true})
})
test('local radar rings, exact bearing, keyboard/list selection and sparse atomic transfer work offline',async({page},info)=>{
 let posts=0;page.on('request',r=>{if(r.method()==='POST')posts++});await offline(page);await page.getByLabel('Scenario',{exact:true}).selectOption('LOCAL')
 const radar=page.getByRole('group',{name:'Local search radar — evaluated candidate positions'})
 for(const r of ['1 km','3 km','5 km'])await expect(radar.getByText(r,{exact:true})).toBeVisible()
 await expect(radar.getByRole('button')).toHaveCount(3)
 await radar.getByRole('button',{name:/Select candidate 2:/}).focus();await page.keyboard.press('Enter')
 await expect(region(page,'Selected Alternative')).toContainText('236.8622046686259')
 await region(page,'Alternative candidates').getByRole('button',{name:/Candidate 3/}).click();await expect(radar.getByRole('button',{name:/Select candidate 3:/})).toHaveAttribute('aria-pressed','true')
 await radar.getByRole('button',{name:/Select candidate 1:/}).click();await expect(region(page,'Selected Alternative')).toContainText('931.976 m')
 await page.screenshot({path:info.outputPath('Local-offline-radar.png'),fullPage:true})
 await page.getByRole('button',{name:'Load Candidate Parameters',exact:true}).click()
 await expect(page.getByRole('heading',{name:'Mission Setup',exact:true})).toBeVisible()
 await expect(page.getByLabel('Latitude (degrees)',{exact:true})).toHaveValue(String(local.alternatives[0].source_request.site.latitude_deg))
 await expect(page.getByLabel('UTC date',{exact:true})).toHaveValue('2026-11-20');await expect(page.getByLabel('UTC time',{exact:true})).toHaveValue('08:00:00');await expect(page.getByLabel('Hours',{exact:true})).toHaveValue('1')
 await expect(page.getByLabel('Minimum Sun visibility (seconds)',{exact:true})).toHaveValue('600');await expect(page.getByText(/Loaded candidate parameters/)).toBeVisible()
 await nav(page,'Mission Analysis').click();await expect(page.getByLabel('Backend planning score')).toHaveCount(0);expect(posts).toBe(0)
})
test('candidate globe reuses NASA renderer and synchronizes candidate selection with radar',async({page},info)=>{
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));await offline(page);await page.getByLabel('Scenario',{exact:true}).selectOption('LOCAL')
 await page.getByRole('button',{name:'Show candidate globe',exact:true}).click()
 await expect(page.getByText('NASA color texture loaded — visual imagery only')).toBeVisible();await expect(page.getByLabel('Camera view',{exact:true})).toContainText('3D scene ready')
 const radar=page.getByRole('group',{name:'Local search radar — evaluated candidate positions'})
 await radar.getByRole('button',{name:/Select candidate 2:/}).click();await expect(page.getByLabel('Camera view',{exact:true})).toContainText('-89.5')
 const enable=page.getByRole('button',{name:'Enable globe interaction'});if(await enable.isVisible())await enable.click()
 await page.locator('canvas').click();await expect(region(page,'Selected Alternative')).toBeVisible()
 await page.screenshot({path:info.outputPath('Local-globe.png'),fullPage:true});expect(errors).toEqual([])
})
test('200% text, WebGL unavailable and live prerequisites preserve offline exploration',async({page},info)=>{
 await page.addInitScript(()=>{const get=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(this:HTMLCanvasElement,type:string,...args:unknown[]){if(type==='webgl'||type==='webgl2')return null;return Reflect.apply(get,this,[type,...args])}as typeof get})
 await offline(page);await page.getByLabel('Scenario',{exact:true}).selectOption('LOCAL');await page.getByRole('button',{name:'Show candidate globe',exact:true}).click()
 await expect(page.getByText('WebGL unavailable',{exact:true}).first()).toBeVisible();await expect(page.getByRole('group',{name:/Local search radar/})).toBeVisible()
 await page.getByRole('button',{name:'Hide candidate globe',exact:true}).click();await page.evaluate(()=>document.documentElement.style.fontSize='200%')
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
 await page.screenshot({path:info.outputPath('Local-200percent.png'),fullPage:true})
 await page.getByLabel('Data mode',{exact:true}).selectOption('live');await expect(page.getByText(/A completed, current Research Prototype Analysis job/)).toBeVisible();await expect(page.getByRole('button',{name:'Run Live Local Optimizer',exact:true})).toBeDisabled()
})
async function baseline(p:Page,kind:'TEMPORAL'|'LOCAL'){
 const original=(kind==='TEMPORAL'?temporal:local).source_optimizer_request,window=original.window_template
 await p.route('**/api/v1/health',r=>r.fulfill({json:healthFixture()}));await p.route('**/api/v1/capabilities',r=>r.fulfill({json:capabilitiesFixture()}))
 await p.route('**/api/v1/analyses/jobs',r=>{const a=r.request().postDataJSON().analysis;(p as any).baseline=a;return r.fulfill({status:202,json:acceptedFixture()})})
 await p.route(`**/api/v1/jobs/${jobId}`,r=>r.fulfill({json:statusFixture('COMPLETED')}))
 await p.route(`**/api/v1/jobs/${jobId}/result`,r=>r.fulfill({json:{job_id:jobId,job_type:'ANALYSIS',status:'COMPLETED',result:{analysis:{schema_version:'1.0',analysis_id:'controlled-baseline',execution_status:'COMPLETED',data_origin:'TEST_FIXTURE',request:(p as any).baseline,decision:{status:'INCOMPLETE',rules:[],reason_codes:[]},score:{value:null,model_version:null,components:null},quality:{status:'LIMITED',coverage_complete:null,limitations:['TEST DATA']},limitations:['TEST DATA'],series:null,horizons:null,resolved_site:null,windows:{sun:null,earth:null,joint:null},sources:[]},window_evidence:{request:window}}}}))
 await p.goto('/');await p.getByLabel('Latitude (degrees)',{exact:true}).fill('-89.468');await p.getByLabel('Longitude (degrees east)',{exact:true}).fill('222.6');await p.getByLabel('UTC date',{exact:true}).fill('2026-11-20');await p.getByLabel('UTC time',{exact:true}).fill('08:00');await p.getByLabel('Hours',{exact:true}).fill(kind==='TEMPORAL'?'6':'1');await p.getByLabel('Operation profile',{exact:true}).selectOption('SOLAR_POWERED_EXPERIMENT');await p.getByLabel('Minimum Sun visibility (seconds)',{exact:true}).fill(kind==='TEMPORAL'?'3600':'600')
 await p.getByRole('button',{name:'Run Research Prototype',exact:true}).click();await expect(region(p,'Scientific Backend')).toContainText('Completed research response received')
 await nav(p,'Alternative Explorer').click();await p.getByLabel('Scenario',{exact:true}).selectOption(kind);await p.getByLabel('Data mode',{exact:true}).selectOption('live')
}
for(const kind of ['TEMPORAL','LOCAL'] as const)test(`typed live ${kind} job renders validated root result and never falls back to recorded data`,async({page},info)=>{
 await baseline(page,kind);const id='c'.repeat(32);let posts=0,polls=0,payload:any
 await page.route(`**/api/v1/optimizations/${kind.toLowerCase()}`,r=>{posts++;payload=r.request().postDataJSON();return r.fulfill({status:202,json:{...acceptedFixture(),job_id:id,job_type:kind,status_url:`/api/v1/jobs/${id}`,result_url:`/api/v1/jobs/${id}/result`,cancellation_url:`/api/v1/jobs/${id}/cancel`}})})
 await page.route(`**/api/v1/jobs/${id}`,r=>{polls++;return r.fulfill({json:{...statusFixture(polls<2?'RUNNING':'COMPLETED'),job_id:id,job_type:kind}})})
 await page.route(`**/api/v1/jobs/${id}/result`,r=>r.fulfill({json:{job_id:id,job_type:kind,status:'COMPLETED',result:optimizerFixture(kind,payload)}}))
 const run=page.getByRole('button',{name:`Run Live ${kind==='TEMPORAL'?'Temporal':'Local'} Optimizer`,exact:true});await expect(run).toBeEnabled();await run.evaluate(b=>{(b as HTMLButtonElement).click();(b as HTMLButtonElement).click()})
 await expect(page.getByText(/Server status: RUNNING/)).toBeVisible();await page.screenshot({path:info.outputPath(`Live-${kind}-running.png`),fullPage:true})
 await expect(page.getByText('TEST DATA',{exact:true})).toBeVisible();await expect(region(page,'Selected Alternative')).toBeVisible()
 expect(posts).toBe(1);expect(payload.optimization.baseline_analysis.operation.requirements).toEqual({min_sun_visible_s:kind==='TEMPORAL'?3600:600})
 if(kind==='TEMPORAL')expect(payload.screening_strategy).toBe('EXACT_ONLY');else {await expect(page.getByRole('group',{name:/Local search radar/})).toBeVisible();expect(payload.optimization.search_radius_m).toBe(5000)}
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.screenshot({path:info.outputPath(`Live-${kind}-complete.png`),fullPage:true})
})
test('live partial, cancellation, failure, interrupted and invalid envelopes retain scientific distinctions',async({page},info)=>{
 await baseline(page,'LOCAL');const id='d'.repeat(32);let outcome='PARTIAL',payload:any,cancelled=false
 await page.route('**/api/v1/optimizations/local',r=>{payload=r.request().postDataJSON();return r.fulfill({status:202,json:{...acceptedFixture(),job_id:id,job_type:'LOCAL',status_url:`/api/v1/jobs/${id}`,result_url:`/api/v1/jobs/${id}/result`,cancellation_url:`/api/v1/jobs/${id}/cancel`}})})
 await page.route(`**/api/v1/jobs/${id}`,r=>r.fulfill({json:{...statusFixture(),job_id:id,job_type:'LOCAL',status:outcome==='BAD_SCHEMA'?'COMPLETED':outcome,result_available:outcome==='PARTIAL'||outcome==='BAD_SCHEMA'}}))
 await page.route(`**/api/v1/jobs/${id}/result`,r=>r.fulfill({json:{job_id:id,job_type:'LOCAL',status:outcome==='BAD_SCHEMA'?'COMPLETED':outcome,result:outcome==='BAD_SCHEMA'?{schema_version:'future'}:optimizerFixture('LOCAL',payload)}}))
 await page.route(`**/api/v1/jobs/${id}/cancel`,r=>{cancelled=true;outcome='CANCEL_REQUESTED';return r.fulfill({json:{...statusFixture('CANCEL_REQUESTED'),job_id:id,job_type:'LOCAL'}})})
 const run=page.getByRole('button',{name:'Run Live Local Optimizer',exact:true})
 await run.click();await expect(page.getByText('TEST DATA',{exact:true})).toBeVisible();await expect(page.getByText(/Status: PARTIAL/)).toBeVisible();await page.screenshot({path:info.outputPath('Live-partial.png'),fullPage:true})
 for(const state of ['FAILED','INTERRUPTED']){outcome=state;await run.click();await expect(page.getByText(new RegExp(`Server status: ${state}`))).toBeVisible();await expect(page.getByRole('region',{name:'Selected Alternative',exact:true})).toHaveCount(0)}
 outcome='RUNNING';await run.click();await expect(page.getByText(/Server status: RUNNING/)).toBeVisible();await page.getByRole('button',{name:'Request Optimizer Cancellation',exact:true}).click();await expect(page.getByText(/Server status: CANCEL_REQUESTED/)).toBeVisible();expect(cancelled).toBe(true);outcome='CANCELLED';await expect(page.getByText(/Server status: CANCELLED/)).toBeVisible()
 outcome='BAD_SCHEMA';await run.click();await expect(page.getByRole('alert').first()).toContainText('valid, matching optimizer result');await expect(page.getByRole('region',{name:'Selected Alternative',exact:true})).toHaveCount(0)
 await page.screenshot({path:info.outputPath('Live-invalid.png'),fullPage:true})
})
