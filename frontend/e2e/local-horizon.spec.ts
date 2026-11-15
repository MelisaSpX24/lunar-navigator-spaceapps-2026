import { test, expect, type Page } from '@playwright/test'
import { scientificFixture } from '../src/test/scientificFixtures'
import { healthFixture } from '../src/test/apiFixtures'
import type { AnalysisResponse } from '../src/services/api/responses'
import type { HorizonProfile } from '../src/features/analysis-results/types'

const local=(page:Page)=>page.getByRole('region',{name:'Interactive 3D Horizon',exact:true})
const orientation=(page:Page)=>page.getByRole('status',{name:'Local camera orientation'})
async function ready(page:Page){await expect(orientation(page)).toContainText('Local 3D scene ready');return page.getByLabel('Interactive local horizon sky',{exact:true}).locator('canvas')}
async function preview(page:Page){await page.route('**/api/v1/health',r=>r.abort());await page.goto('/#/analysis');return ready(page)}
async function result(page:Page,change:(r:AnalysisResponse)=>AnalysisResponse=r=>r){
  await page.route('**/api/v1/health',r=>r.fulfill({json:healthFixture(true)}))
  await page.route('**/api/v1/analyses',r=>{const response=scientificFixture();response.request=r.request().postDataJSON();return r.fulfill({json:change(response)})})
  await page.goto('/')
  for(const [name,value] of [['Latitude (degrees)','-85'],['Longitude (degrees east)','340'],['UTC date','2026-11-14'],['UTC time','12:30']]) await page.getByLabel(name!,{exact:true}).fill(value!)
  await expect(page.getByRole('button',{name:'Run Analysis',exact:true})).toBeEnabled()
  await page.getByRole('button',{name:'Run Analysis',exact:true}).click()
  await page.getByRole('navigation').getByRole('link',{name:'Mission Analysis',exact:true}).click()
}
async function enable(page:Page){const button=page.getByRole('button',{name:'Enable 3D interaction',exact:true});if(await button.count())await button.click()}
async function shot(page:Page,path:string){await local(page).scrollIntoViewIfNeeded();await local(page).screenshot({path})}

test('orientation preview, cardinal shortcuts, fixed origin camera and FOV bounds',async({page},info)=>{
  const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message))
  await preview(page)
  await expect(local(page)).toContainText('Orientation preview only')
  await expect(local(page)).toContainText('No valid observer coordinate')
  await expect(local(page).getByRole('combobox')).toHaveCount(0)
  await expect(local(page)).not.toContainText('Backend Horizon View')
  await shot(page,info.outputPath('Orientation-preview.png'))
  for(const [name,angle] of [['North','0.0'],['East','90.0'],['South','180.0'],['West','270.0']]){
    await page.getByRole('button',{name:`Look ${name}`,exact:true}).focus();await page.keyboard.press('Enter')
    await expect(orientation(page)).toContainText(`Azimuth ${angle}°`)
  }
  await page.getByRole('button',{name:'Look up',exact:true}).click()
  await expect(orientation(page)).toContainText('Elevation 20.0°')
  await page.getByRole('button',{name:'Horizon level',exact:true}).click()
  await expect(orientation(page)).toContainText('Elevation 0.0°')
  for(let i=0;i<12;i++)await page.getByRole('button',{name:'Zoom in',exact:true}).click()
  await expect(orientation(page)).toContainText('FOV 35.0°')
  for(let i=0;i<12;i++)await page.getByRole('button',{name:'Zoom out',exact:true}).click()
  await expect(orientation(page)).toContainText('FOV 100.0°')
  await page.getByRole('button',{name:'Reset View',exact:true}).click()
  await expect(orientation(page)).toContainText('Azimuth 0.0° · Elevation 10.0° · FOV 75.0°')
  await enable(page)
  const canvas=await ready(page);await canvas.scrollIntoViewIfNeeded();const b=(await canvas.boundingBox())!
  await page.mouse.move(b.x+b.width/2,b.y+b.height/2);await page.mouse.down();await page.mouse.move(b.x+b.width/2-80,b.y+b.height/2+25,{steps:8});await page.mouse.up()
  await expect(orientation(page)).not.toContainText('Azimuth 0.0°')
  await page.mouse.wheel(0,200);await expect(orientation(page)).toContainText('FOV 80.0°')
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
  expect(errors).toEqual([])
})

test('validated profiles render actual GPU points, switch metadata, preserve 2D and show quality',async({page},info)=>{
  await page.addInitScript(()=>{
    const original=WebGL2RenderingContext.prototype.drawArrays
    WebGL2RenderingContext.prototype.drawArrays=function(mode,first,count){if(mode===this.POINTS)(this.canvas as HTMLCanvasElement).dataset.angularPointCount=String(count);return original.call(this,mode,first,count)}
  })
  await result(page,r=>{const h=r.horizons as HorizonProfile[];h[1]!.points=[{azimuth_deg:0,elevation_deg:20},{azimuth_deg:90,elevation_deg:25}];return r})
  const canvas=await ready(page)
  await expect(local(page)).toContainText('TEST DATA — synthetic horizon profile')
  await expect(local(page)).toContainText('Incomplete terrain horizon coverage')
  await expect(local(page)).toContainText('Data quality: LIMITED')
  await expect(local(page)).toContainText('-85.000° latitude, 340.000° east longitude')
  await expect(canvas).toHaveAttribute('data-angular-point-count','3')
  await shot(page,info.outputPath('Backend-profile-low.png'))
  await page.getByLabel('3D horizon profile',{exact:true}).selectOption('controlled-horizon-high')
  await expect(local(page)).toContainText('Observer height: 2 m. Range: 1200 m.')
  await expect(canvas).toHaveAttribute('data-angular-point-count','2')
  await expect(local(page)).toContainText('2 known angular samples / 0 unknown elevations')
  await shot(page,info.outputPath('Backend-profile-high.png'))
  const panel=page.getByRole('region',{name:'Local Horizon',exact:true})
  await expect(panel.getByRole('img')).toHaveCount(2)
  await expect(panel.getByRole('table')).toHaveCount(2)
  await expect(panel.getByRole('table').nth(1)).toContainText('25')
  await page.getByRole('link',{name:'Edit scenario in Mission Setup'}).click()
  await expect(page.getByLabel('Interactive local horizon sky')).toHaveCount(0)
  await expect(page.getByRole('status',{name:'Camera view'})).toContainText('3D scene ready')
  await expect(page.getByText(/^Signed longitude:/)).toContainText('-20.000')
  await page.getByLabel('Latitude (degrees)',{exact:true}).fill('-84')
  await page.getByRole('navigation').getByRole('link',{name:'Mission Analysis',exact:true}).click()
  await ready(page)
  await expect(local(page)).toContainText('Orientation preview only')
  await expect(local(page)).not.toContainText('TEST DATA')
  await expect(local(page)).toContainText('-84.000° latitude')
})

test('missing, empty, invalid and all-unknown horizons never become terrain',async({page},info)=>{
  for(const horizons of [null,[],[{id:'invalid'}]]){
    await result(page,r=>({...r,horizons}));await ready(page)
    await expect(local(page)).toContainText('Backend celestial samples — no measured terrain horizon available.')
    await expect(local(page)).toContainText('Horizon profile unavailable for this sample.')
    await expect(local(page).getByRole('combobox')).toHaveCount(0)
  }
  await result(page,r=>{const h=r.horizons as HorizonProfile[];h[0]!.points=[{azimuth_deg:0,elevation_deg:null},{azimuth_deg:359,elevation_deg:null}];r.quality={status:'INSUFFICIENT',coverage_complete:false,limitations:[]};return r})
  await ready(page)
  await expect(local(page)).toContainText('0 known angular samples / 2 unknown elevations')
  await expect(local(page)).toContainText('Data quality: INSUFFICIENT')
  await shot(page,info.outputPath('Unknown-sectors.png'))
})

test('WebGL unavailable preserves scientific tables and other panels',async({page},info)=>{
  await page.addInitScript(()=>{
    const original=HTMLCanvasElement.prototype.getContext
    HTMLCanvasElement.prototype.getContext=function(this:HTMLCanvasElement,...args:Parameters<typeof original>){return String(args[0]).startsWith('webgl')?null:original.apply(this,args)} as typeof original
  })
  await result(page)
  await expect(local(page).getByRole('alert')).toContainText('3D view unavailable')
  await expect(local(page).getByRole('button',{name:'Look North',exact:true})).toBeDisabled()
  await expect(page.getByRole('region',{name:'Local Horizon',exact:true}).getByRole('table')).toHaveCount(2)
  await expect(page.getByRole('region',{name:'Sun Visibility',exact:true}).getByRole('img')).toHaveCount(2)
  await shot(page,info.outputPath('WebGL-unavailable.png'))
  await page.getByRole('navigation').getByRole('link',{name:'Alternative Explorer',exact:true}).click()
  await expect(page.getByRole('heading',{name:'Alternative Explorer',exact:true})).toBeVisible()
})

test('context loss disposes scene; explicit retry and route remount restore a fresh view',async({page})=>{
  const canvas=await preview(page)
  await canvas.evaluate(e=>{const gl=(e as HTMLCanvasElement).getContext('webgl2');const ext=gl?.getExtension('WEBGL_lose_context');if(!ext)throw Error('No context-loss extension');ext.loseContext()})
  await expect(local(page).getByRole('alert')).toContainText('WebGL context lost')
  await expect(page.locator('canvas')).toHaveCount(0)
  await page.getByRole('button',{name:'Retry 3D view',exact:true}).click();await ready(page)
  await page.getByRole('button',{name:'Look West',exact:true}).click()
  await page.getByRole('navigation').getByRole('link',{name:'Alternative Explorer',exact:true}).click()
  await expect(page.locator('canvas')).toHaveCount(0)
  await page.getByRole('navigation').getByRole('link',{name:'Mission Analysis',exact:true}).click();await ready(page)
  await expect(orientation(page)).toContainText('Azimuth 0.0°')
})

test('reduced motion and 200 percent text retain keyboard controls and 2D access',async({page},info)=>{
  await page.emulateMedia({reducedMotion:'reduce'});await result(page);await ready(page)
  await page.addStyleTag({content:'html{font-size:200%}'})
  await page.getByRole('button',{name:'Look East',exact:true}).focus();await page.keyboard.press('Enter')
  await expect(orientation(page)).toContainText('Azimuth 90.0°')
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
  const canvas=await ready(page);const box=(await canvas.boundingBox())!;expect(box.height).toBeGreaterThanOrEqual(340)
  await expect(local(page).getByText('TEST DATA — synthetic horizon profile',{exact:true})).toBeVisible()
  const region=(await page.getByRole('region',{name:'Local horizon view',exact:true}).boundingBox())!
  for(const button of await local(page).getByRole('button').all()){
    const bounds=(await button.boundingBox())!
    expect(bounds.x).toBeGreaterThanOrEqual(region.x)
    expect(bounds.x+bounds.width).toBeLessThanOrEqual(region.x+region.width+1)
  }
  await shot(page,info.outputPath('Horizon-200-percent.png'))
})

test('route unmount releases GPU buffers and generated label textures',async({page})=>{
  await page.addInitScript(()=>{
    const counters={buffers:0,textures:0};Object.assign(window,{localDisposals:counters})
    const buffers=WebGL2RenderingContext.prototype.deleteBuffer,textures=WebGL2RenderingContext.prototype.deleteTexture
    WebGL2RenderingContext.prototype.deleteBuffer=function(buffer){if(buffer)counters.buffers++;return buffers.call(this,buffer)}
    WebGL2RenderingContext.prototype.deleteTexture=function(texture){if(texture)counters.textures++;return textures.call(this,texture)}
  })
  const canvas=await preview(page)
  await canvas.screenshot() // Ensure an actual rendered frame allocated GPU resources.
  const read=()=>page.evaluate(()=>(window as unknown as {localDisposals:{buffers:number;textures:number}}).localDisposals)
  const before=await read()
  await page.getByRole('navigation').getByRole('link',{name:'Alternative Explorer',exact:true}).click()
  await expect(page.locator('canvas')).toHaveCount(0)
  await expect.poll(async()=>(await read()).textures).toBeGreaterThan(before.textures)
  await expect.poll(async()=>(await read()).buffers).toBeGreaterThan(before.buffers)
})
