import { test, expect, type Page } from '@playwright/test'
import { PerspectiveCamera, Vector3 } from 'three'
import { celestialFixture } from '../src/test/celestialFixture'
import { healthFixture } from '../src/test/apiFixtures'
import type { AnalysisResponse } from '../src/services/api/responses'
import type { BodySample } from '../src/features/analysis-results/types'
import { renderDirection } from '../src/visualization/local-horizon/directions'
const region=(p:Page,name:string)=>p.getByRole('region',{name,exact:true})
const button=(p:Page,name:string)=>p.getByRole('button',{name,exact:true})
async function open(p:Page,change:(r:AnalysisResponse)=>AnalysisResponse=r=>r){
 await p.route('**/api/v1/health',r=>r.fulfill({json:healthFixture(true)}))
 await p.route('**/api/v1/analyses',r=>{const data=celestialFixture();data.request=r.request().postDataJSON();return r.fulfill({json:change(data)})})
 await p.goto('/')
 for(const [label,value] of [['Latitude (degrees)','-85'],['Longitude (degrees east)','340'],['UTC date','2026-11-14'],['UTC time','12:30']])await p.getByLabel(label!,{exact:true}).fill(value!)
 await button(p,'Run Analysis').click()
 await p.getByRole('navigation').getByRole('link',{name:'Mission Analysis',exact:true}).click()
 await expect(p.getByLabel('Local camera orientation')).toContainText('Local 3D scene ready')
}
async function shot(p:Page,path:string){await region(p,'Local horizon view').screenshot({path})}

test('exact and smooth modes keep independent scientific readouts and reject unsupported intervals',async({page},info)=>{
 let posts=0,dem=0;page.on('request',r=>{if(r.method()==='POST')posts++;if(/\.tif|nasa\.gov|\/dem/.test(r.url()))dem++})
 await open(page)
 await expect(page.getByLabel('Smooth visual preview',{exact:true})).not.toBeChecked()
 await shot(page,info.outputPath('Motion-exact.png'))
 await page.getByLabel('Selected UTC time',{exact:true}).fill('500')
 await expect(region(page,'Sun Selected UTC Sample')).toContainText('NO SUPPORTED POSITION')
 await page.getByLabel('Smooth visual preview',{exact:true}).check()
 for(const body of ['Sun','Earth']){
  const panel=region(page,`${body} Selected UTC Sample`)
  await expect(panel).toContainText('VISUAL INTERPOLATION — not a computed science sample')
  await expect(panel).toContainText('Visibility at this UTC has not been evaluated')
  await expect(panel.locator('dl')).toHaveCount(0)
 }
 await shot(page,info.outputPath('Motion-intermediate-wrap.png'))
 await page.getByLabel('Selected UTC time',{exact:true}).fill('2500')
 await expect(region(page,'Sun Selected UTC Sample')).toContainText('NO SUPPORTED POSITION')
 await expect(region(page,'Earth Selected UTC Sample')).toContainText('VISUAL INTERPOLATION')
 await shot(page,info.outputPath('Motion-independent-rejection.png'))
 await button(page,'Next sample').click()
 await expect(region(page,'Sun Selected UTC Sample')).toContainText('BACKEND SAMPLE')
 expect(posts).toBe(1);expect(dem).toBe(0)
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
})

test('real GPU markers move between samples without allocating new label textures or path buffers',async({page})=>{
 await page.addInitScript(()=>{
  const state={matrices:[] as number[][],textures:0,buffers:0},locations=new WeakMap<WebGLUniformLocation,string>()
  Object.assign(window,{motionGPU:state})
  const get=WebGL2RenderingContext.prototype.getUniformLocation,set=WebGL2RenderingContext.prototype.uniformMatrix4fv
  WebGL2RenderingContext.prototype.getUniformLocation=function(program,name){const loc=get.call(this,program,name);if(loc)locations.set(loc,name);return loc}
  WebGL2RenderingContext.prototype.uniformMatrix4fv=function(loc,transpose,data,...rest){if(loc&&locations.get(loc)==='modelViewMatrix')state.matrices.push(Array.from(data).slice(12,15));return set.call(this,loc,transpose,data,...rest)}
  const image=WebGL2RenderingContext.prototype.texImage2D,sub=WebGL2RenderingContext.prototype.texSubImage2D,buffer=WebGL2RenderingContext.prototype.bufferData
  const watch=(args:unknown[])=>{if(args.some(s=>s instanceof HTMLCanvasElement&&s.width===512&&s.height===256))state.textures++}
  WebGL2RenderingContext.prototype.texImage2D=function(...args:unknown[]){watch(args);return Reflect.apply(image,this,args)}
  WebGL2RenderingContext.prototype.texSubImage2D=function(...args:unknown[]){watch(args);return Reflect.apply(sub,this,args)}
  WebGL2RenderingContext.prototype.bufferData=function(...args:unknown[]){state.buffers++;return Reflect.apply(buffer,this,args)}
 })
 await open(page)
 await page.getByLabel('Show Sun path',{exact:true}).check();await page.getByLabel('Show Earth path',{exact:true}).check()
 await region(page,'Local horizon view').screenshot()
 const read=()=>page.evaluate(()=>(window as unknown as {motionGPU:{matrices:number[][];textures:number;buffers:number}}).motionGPU)
 const before=await read()
 await page.getByLabel('Smooth visual preview',{exact:true}).check()
 await page.evaluate(()=>{(window as unknown as {motionGPU:{matrices:number[][]}}).motionGPU.matrices=[]})
 await page.getByLabel('Selected UTC time',{exact:true}).fill('500')
 const camera=new PerspectiveCamera();camera.lookAt(...renderDirection(0,10));camera.updateMatrixWorld()
 for(const [az1,el1,az2,el2] of [[359,10,0,15],[10,12,20,17]]){
  const a=new Vector3(...renderDirection(az1!,el1!,1)),b=new Vector3(...renderDirection(az2!,el2!,1)),theta=a.angleTo(b),t=.3
  const expected=a.multiplyScalar(Math.sin((1-t)*theta)/Math.sin(theta)).add(b.multiplyScalar(Math.sin(t*theta)/Math.sin(theta))).normalize().multiplyScalar(9).applyMatrix4(camera.matrixWorldInverse).toArray()
  await expect.poll(async()=>(await read()).matrices.some(v=>Math.hypot(v[0]!-expected[0]!,v[1]!-expected[1]!,v[2]!-expected[2]!)<.001)).toBe(true)
 }
 await page.getByLabel('Selected UTC time',{exact:true}).fill('700');await region(page,'Local horizon view').screenshot()
 const after=await read();expect(after.textures).toBe(before.textures);expect(after.buffers).toBe(before.buffers)
})

test('Play Pause Replay speed and manual selection share one UTC and end without looping',async({page},info)=>{
 let posts=0;page.on('request',r=>{if(r.method()==='POST')posts++})
 await open(page);await page.getByLabel('Smooth visual preview',{exact:true}).check()
 const clockStart=new Date('2026-11-15T00:00:00Z');await page.clock.install({time:clockStart});await page.clock.pauseAt(new Date(clockStart.getTime()+1000))
 const before=await page.getByLabel('Selected UTC',{exact:true}).textContent()
 await button(page,'Play').click();await page.clock.runFor(1000)
 await expect(page.getByRole('status',{name:'Playback status'})).toContainText('playing')
 await shot(page,info.outputPath('Motion-playing.png'))
 await button(page,'Pause').click()
 const paused=await page.getByLabel('Selected UTC',{exact:true}).textContent();expect(paused).not.toBe(before)
 await page.clock.runFor(1000);await expect(page.getByLabel('Selected UTC',{exact:true})).toHaveText(paused!)
 await shot(page,info.outputPath('Motion-paused.png'))
 await button(page,'Play').click();await page.getByLabel('Selected UTC time',{exact:true}).fill('500')
 await expect(button(page,'Pause')).toBeDisabled()
 await button(page,'Play').click();await button(page,'Next sample').click();await expect(button(page,'Pause')).toBeDisabled()
 await page.getByLabel('Playback duration',{exact:true}).selectOption('30')
 await button(page,'Last sample').click();await button(page,'Play').click();await page.clock.runFor(20100)
 await expect(page.getByLabel('Selected UTC',{exact:true})).toContainText('13:30:00')
 await expect(button(page,'Play')).toBeDisabled()
 await shot(page,info.outputPath('Motion-end.png'))
 await button(page,'Replay').click();await page.clock.runFor(1000);await button(page,'Pause').click()
 const selected=await page.getByLabel('Selected UTC',{exact:true}).textContent();if(!selected)throw Error('Missing UTC readout')
 await expect(page.getByLabel('Scene UTC',{exact:true})).toHaveText(selected)
 await expect(page.getByLabel('Timeline selected UTC',{exact:true})).toContainText(selected)
 expect(posts).toBe(1)
})

test('missing or changed horizon and long gaps hide only unsupported interpolated directions',async({page},info)=>{
 await open(page,r=>{const rows=r.series as {time_utc:string;sun:BodySample;earth:BodySample}[];rows[0]!.sun.horizon_id=null;rows[1]!.earth.horizon_id='controlled-horizon-low';return r})
 await page.getByLabel('Smooth visual preview',{exact:true}).check();await page.getByLabel('Selected UTC time',{exact:true}).fill('500')
 await expect(region(page,'Sun Selected UTC Sample')).toContainText('known horizon profile is required')
 await expect(region(page,'Earth Selected UTC Sample')).toContainText('Horizon profile changes')
 await shot(page,info.outputPath('Motion-unknown-profile.png'))
 await open(page,r=>{const rows=r.series as {time_utc:string;sun:BodySample}[];rows[1]!.time_utc='2026-11-14T12:41:00Z';rows[0]!.sun.elevation_deg=null;return r})
 await page.getByLabel('Smooth visual preview',{exact:true}).check();await page.getByLabel('Selected UTC time',{exact:true}).fill('500')
 await expect(region(page,'Sun Selected UTC Sample')).toContainText('unknown direction')
 await expect(region(page,'Earth Selected UTC Sample')).toContainText('time-gap guard')
 await shot(page,info.outputPath('Motion-long-gap.png'))
})

test('reduced motion and 200% text retain manual accessible controls and 2D data',async({page},info)=>{
 await page.emulateMedia({reducedMotion:'reduce'});await open(page)
 await expect(button(page,'Play')).toBeDisabled();await expect(page.getByLabel('Smooth visual preview',{exact:true})).toBeDisabled()
 await button(page,'Next sample').focus();await page.keyboard.press('Enter')
 await expect(page.getByLabel('Scene UTC',{exact:true})).toContainText('12:40:00')
 await shot(page,info.outputPath('Motion-reduced.png'))
 await page.addStyleTag({content:'html{font-size:200%}'})
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
 await region(page,'UTC time selection').screenshot({path:info.outputPath('Motion-200-controls.png')})
 await expect(region(page,'Sun Visibility').getByRole('table')).toHaveCount(1)
 await expect(region(page,'Earth Visibility').getByRole('table')).toHaveCount(1)
})

test('WebGL loss pauses; route exit and scenario edits cannot leave old motion running',async({page},info)=>{
 await open(page);await page.getByLabel('Smooth visual preview',{exact:true}).check();await button(page,'Play').click()
 const canvas=page.getByLabel('Interactive local horizon sky',{exact:true}).locator('canvas')
 await canvas.evaluate(e=>(e as HTMLCanvasElement).getContext('webgl2')!.getExtension('WEBGL_lose_context')!.loseContext())
 await expect(button(page,'Pause')).toBeDisabled()
 await shot(page,info.outputPath('Motion-WebGL-fallback.png'))
 await button(page,'Retry 3D view').click();await expect(page.getByLabel('Local camera orientation')).toContainText('ready')
 await button(page,'Play').click()
 await page.getByRole('navigation').getByRole('link',{name:'Alternative Explorer',exact:true}).click()
 await page.getByRole('navigation').getByRole('link',{name:'Mission Analysis',exact:true}).click()
 await expect(button(page,'Pause')).toBeDisabled();await expect(page.getByLabel('Smooth visual preview',{exact:true})).not.toBeChecked()
 await page.getByRole('link',{name:'Edit scenario in Mission Setup'}).click();await page.getByLabel('Latitude (degrees)',{exact:true}).fill('-84')
 await page.getByRole('navigation').getByRole('link',{name:'Mission Analysis',exact:true}).click()
 await expect(button(page,'Play')).toBeDisabled();await expect(page.getByLabel('Celestial sample paths')).toHaveCount(0)
})
