import { test, expect, type Page } from '@playwright/test'
import { PerspectiveCamera, Vector3 } from 'three'
import { celestialFixture } from '../src/test/celestialFixture'
import { healthFixture } from '../src/test/apiFixtures'
import type { AnalysisResponse } from '../src/services/api/responses'
import type { BodySample } from '../src/features/analysis-results/types'
import { renderDirection } from '../src/visualization/local-horizon/directions'
const panel=(p:Page,name:string)=>p.getByRole('region',{name,exact:true})
async function open(p:Page,change:(r:AnalysisResponse)=>AnalysisResponse=r=>r){
 await p.route('**/api/v1/health',r=>r.fulfill({json:healthFixture(true)}))
 await p.route('**/api/v1/analyses',r=>{const data=celestialFixture();data.request=r.request().postDataJSON();return r.fulfill({json:change(data)})})
 await p.goto('/')
 for(const [label,value] of [['Latitude (degrees)','-85'],['Longitude (degrees east)','340'],['UTC date','2026-11-14'],['UTC time','12:30']])await p.getByLabel(label!,{exact:true}).fill(value!)
 await p.getByRole('button',{name:'Run Analysis',exact:true}).click()
 await p.getByRole('navigation').getByRole('link',{name:'Mission Analysis',exact:true}).click()
 await expect(p.getByLabel('Local camera orientation')).toContainText('Local 3D scene ready')
 await expect(p.getByLabel('Selected UTC', {exact:true})).toContainText('12:30:00')
}
async function capture(p:Page,path:string){await panel(p,'Local Horizon').screenshot({path})}

test('exact UTC drives scene, readouts and playhead without new network requests; paths and profile warnings',async({page},info)=>{
 let posts=0,assets=0;page.on('request',r=>{if(r.method()==='POST')posts++;if(/dem|\.tif|nasa\.gov/.test(r.url()))assets++})
 await open(page)
 await expect(panel(page,'Sun Selected UTC Sample')).toContainText('PARTIAL')
 await expect(panel(page,'Sun Selected UTC Sample')).toContainText('false')
 await expect(page.getByLabel('Celestial horizon relationships')).toContainText('Earth: Sample references a different horizon profile.')
 await capture(page,info.outputPath('Celestial-first-359.png'))
 await page.getByRole('button',{name:'Next sample',exact:true}).click()
 for(const name of ['Selected UTC','Scene UTC','Timeline selected UTC'])await expect(page.getByLabel(name,{exact:true})).toContainText('12:40:00')
 await expect(panel(page,'Sun Selected UTC Sample')).toContainText('12:40:00')
 await expect(panel(page,'Earth Selected UTC Sample')).toContainText('12:40:00')
 await capture(page,info.outputPath('Celestial-middle-zero.png'))
 await page.getByRole('button',{name:'Last sample',exact:true}).click()
 await expect(page.getByLabel('Scene UTC',{exact:true})).toContainText('12:50:00')
 await capture(page,info.outputPath('Celestial-last.png'))
 await page.getByLabel('Show Sun path',{exact:true}).check();await page.getByLabel('Show Earth path',{exact:true}).check()
 await page.getByLabel('3D horizon profile',{exact:true}).selectOption('controlled-horizon-high')
 await expect(page.getByLabel('Celestial horizon relationships')).toContainText('Sun: Sample references a different horizon profile.')
 await page.getByLabel('Selected UTC time',{exact:true}).fill('1')
 await expect(panel(page,'Sun Selected UTC Sample')).toContainText('No sample at selected time')
 await expect(panel(page,'Earth Selected UTC Sample')).toContainText('No sample at selected time')
 expect(posts).toBe(1);expect(assets).toBe(0)
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
 await page.getByRole('link',{name:'Edit scenario in Mission Setup'}).click()
 await expect(page.getByLabel('UTC time',{exact:true})).toHaveValue('12:30')
 await page.getByLabel('Latitude (degrees)',{exact:true}).fill('-84')
 await page.getByRole('navigation').getByRole('link',{name:'Mission Analysis',exact:true}).click()
 await expect(page.getByLabel('Selected UTC time',{exact:true})).toBeDisabled()
 await expect(page.getByText('Orientation preview only — no measured terrain horizon or celestial positions are available.',{exact:true})).toBeVisible()
})

test('actual WebGL marker matrices follow ENU directions at exact samples',async({page})=>{
 await page.addInitScript(()=>{
  const locations=new WeakMap<WebGLUniformLocation,string>(),matrices:number[][]=[]
  Object.assign(window,{celestialMatrices:matrices})
  const get=WebGL2RenderingContext.prototype.getUniformLocation,set=WebGL2RenderingContext.prototype.uniformMatrix4fv
  WebGL2RenderingContext.prototype.getUniformLocation=function(program,name){const loc=get.call(this,program,name);if(loc)locations.set(loc,name);return loc}
  WebGL2RenderingContext.prototype.uniformMatrix4fv=function(loc,transpose,data,...rest){if(loc&&locations.get(loc)==='modelViewMatrix')matrices.push(Array.from(data).slice(12,15));return set.call(this,loc,transpose,data,...rest)}
 })
 await open(page)
 const camera=new PerspectiveCamera();camera.lookAt(...renderDirection(0,10));camera.updateMatrixWorld()
 for(const [az,el] of [[359,10],[10,12]]){
  const v=new Vector3(...renderDirection(az!,el!,9)).applyMatrix4(camera.matrixWorldInverse)
  await expect.poll(()=>page.evaluate(expected=>(window as unknown as {celestialMatrices:number[][]}).celestialMatrices.some(v=>Math.hypot(v[0]!-expected[0]!,v[1]!-expected[1]!,v[2]!-expected[2]!)<.001),v.toArray())).toBe(true)
 }
 await page.evaluate(()=>{(window as unknown as {celestialMatrices:number[][]}).celestialMatrices.length=0})
 await page.getByRole('button',{name:'Next sample',exact:true}).click()
 const expected=new Vector3(...renderDirection(0,15,9)).applyMatrix4(camera.matrixWorldInverse).toArray()
 await expect.poll(()=>page.evaluate(expected=>(window as unknown as {celestialMatrices:number[][]}).celestialMatrices.some(v=>Math.hypot(v[0]!-expected[0]!,v[1]!-expected[1]!,v[2]!-expected[2]!)<.001),expected)).toBe(true)
})

test('null and invalid bodies are independent; absent and unknown horizon references stay explicit',async({page},info)=>{
 await open(page,r=>{const rows=r.series as {sun:BodySample;earth:BodySample}[];rows[0]!.sun.azimuth_deg=null;rows[0]!.earth.horizon_id='missing-profile';return r})
 await expect(panel(page,'Sun Selected UTC Sample')).toContainText('Direction unavailable')
 await expect(page.getByLabel('Celestial horizon relationships')).toContainText('Horizon profile unavailable for this sample.')
 await capture(page,info.outputPath('Celestial-null-direction.png'))
 await open(page,r=>{const rows=r.series as {sun:BodySample;earth:BodySample}[];rows[0]!.sun.azimuth_deg=360;rows[0]!.earth.horizon_id=null;return r})
 await expect(panel(page,'Sun Selected UTC Sample')).toContainText('Invalid sun sample')
 await expect(panel(page,'Earth Selected UTC Sample')).toContainText('12:30:00')
 await expect(page.getByLabel('Celestial horizon relationships')).toContainText('Horizon relationship unknown')
})

test('near-coincident markers, mobile controls and 200 percent text keep numeric alternatives',async({page},info)=>{
 await open(page,r=>{const rows=r.series as {sun:BodySample;earth:BodySample}[];rows[0]!.earth.azimuth_deg=359;rows[0]!.earth.elevation_deg=10;return r})
 await capture(page,info.outputPath('Celestial-coincident.png'))
 await page.addStyleTag({content:'html{font-size:200%}'})
 await page.getByRole('button',{name:'Next sample',exact:true}).focus();await page.keyboard.press('Enter')
 await expect(page.getByLabel('Scene UTC',{exact:true})).toContainText('12:40:00')
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
 await capture(page,info.outputPath('Celestial-200-percent.png'))
 await expect(panel(page,'Sun Visibility').getByRole('table')).toHaveCount(1)
 await expect(panel(page,'Earth Visibility').getByRole('table')).toHaveCount(1)
})

test('no result leaves slider disabled, no celestial controls and orientation preview available',async({page},info)=>{
 await page.route('**/api/v1/health',r=>r.abort());await page.goto('/#/analysis')
 await expect(page.getByLabel('Local camera orientation')).toContainText('Local 3D scene ready')
 await expect(page.getByLabel('Selected UTC time',{exact:true})).toBeDisabled()
 await expect(page.getByLabel('Show Sun path',{exact:true})).toHaveCount(0)
 await capture(page,info.outputPath('Celestial-offline.png'))
})

test('WebGL loss and retry preserve selected UTC and numeric samples; route change resets only time',async({page},info)=>{
 await open(page)
 await page.getByRole('button',{name:'Last sample',exact:true}).click()
 const canvas=page.getByLabel('Interactive local horizon sky',{exact:true}).locator('canvas')
 await canvas.evaluate(e=>{const ext=(e as HTMLCanvasElement).getContext('webgl2')?.getExtension('WEBGL_lose_context');if(!ext)throw Error('No loss extension');ext.loseContext()})
 await expect(panel(page,'Interactive 3D Horizon').getByRole('alert')).toContainText('WebGL context lost')
 await expect(page.getByLabel('Scene UTC',{exact:true})).toContainText('12:50:00')
 await expect(panel(page,'Sun Selected UTC Sample')).toContainText('12:50:00')
 await capture(page,info.outputPath('Celestial-WebGL-unavailable.png'))
 await page.getByRole('button',{name:'Retry 3D view',exact:true}).click()
 await expect(page.getByLabel('Local camera orientation')).toContainText('Local 3D scene ready')
 await expect(page.getByLabel('Scene UTC',{exact:true})).toContainText('12:50:00')
 await page.getByRole('navigation').getByRole('link',{name:'Alternative Explorer',exact:true}).click()
 await expect(page.locator('canvas')).toHaveCount(0)
 await page.getByRole('navigation').getByRole('link',{name:'Mission Analysis',exact:true}).click()
 await expect(page.getByLabel('Selected UTC',{exact:true})).toContainText('12:30:00')
})

test('celestial GPU textures and path buffers are released on route unmount',async({page})=>{
 await page.addInitScript(()=>{
  const counts={uploaded:0,textures:0,buffers:0,pathUploads:0,capturePaths:false}, markerTextures=new Set<WebGLTexture>(), pathBuffers=new Set<WebGLBuffer>()
  Object.assign(window,{celestialDisposals:counts})
  const watch=(gl:WebGL2RenderingContext,args:unknown[])=>{
   if(args.some(source=>source instanceof HTMLCanvasElement&&source.width===512&&source.height===256)){
    const texture=gl.getParameter(gl.TEXTURE_BINDING_2D) as WebGLTexture|null
    if(texture){markerTextures.add(texture);counts.uploaded=markerTextures.size}
   }
  }
  const image=WebGL2RenderingContext.prototype.texImage2D,sub=WebGL2RenderingContext.prototype.texSubImage2D
  WebGL2RenderingContext.prototype.texImage2D=function(...args:unknown[]){watch(this,args);return Reflect.apply(image,this,args)}
  WebGL2RenderingContext.prototype.texSubImage2D=function(...args:unknown[]){watch(this,args);return Reflect.apply(sub,this,args)}
  const upload=WebGL2RenderingContext.prototype.bufferData
  WebGL2RenderingContext.prototype.bufferData=function(...args:unknown[]){
   if(counts.capturePaths && args[1] instanceof Float32Array && args[1].length===9){
    const b=this.getParameter(this.ARRAY_BUFFER_BINDING) as WebGLBuffer|null
    if(b){pathBuffers.add(b);counts.pathUploads=pathBuffers.size}
   }
   return Reflect.apply(upload,this,args)
  }
  const texture=WebGL2RenderingContext.prototype.deleteTexture,buffer=WebGL2RenderingContext.prototype.deleteBuffer
  WebGL2RenderingContext.prototype.deleteTexture=function(t){if(t&&markerTextures.has(t)){counts.textures++;markerTextures.delete(t)}return texture.call(this,t)}
  WebGL2RenderingContext.prototype.deleteBuffer=function(b){if(b&&pathBuffers.has(b)){counts.buffers++;pathBuffers.delete(b)}return buffer.call(this,b)}
 })
 await open(page)
 await page.evaluate(()=>{(window as unknown as {celestialDisposals:{capturePaths:boolean}}).celestialDisposals.capturePaths=true})
 await page.getByLabel('Show Sun path',{exact:true}).check();await page.getByLabel('Show Earth path',{exact:true}).check()
 await page.getByLabel('Interactive local horizon sky',{exact:true}).locator('canvas').screenshot()
 const counts=()=>page.evaluate(()=>(window as unknown as {celestialDisposals:{uploaded:number;textures:number;buffers:number;pathUploads:number}}).celestialDisposals)
 await expect.poll(async()=>(await counts()).uploaded).toBe(2)
 await expect.poll(async()=>(await counts()).pathUploads).toBe(2)
 const before=await counts()
 await page.getByRole('navigation').getByRole('link',{name:'Alternative Explorer',exact:true}).click()
 await expect(page.locator('canvas')).toHaveCount(0)
 await expect.poll(async()=>(await counts()).textures-before.textures).toBe(2)
 await expect.poll(async()=>(await counts()).buffers-before.buffers).toBe(2)
})
