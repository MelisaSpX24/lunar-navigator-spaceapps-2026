import { test,expect,type Page } from '@playwright/test'
import { celestialFixture } from '../src/test/celestialFixture'
import { healthFixture } from '../src/test/apiFixtures'
const region=(p:Page,n:string)=>p.getByRole('region',{name:n,exact:true})
async function open(p:Page,origin:'TEST_FIXTURE'|'PRECOMPUTED'|'LIVE_COMPUTED'='TEST_FIXTURE'){
 await p.route('**/api/v1/health',r=>r.fulfill({json:healthFixture(true)}))
 await p.route('**/api/v1/analyses',r=>{
  const data=celestialFixture();data.request=r.request().postDataJSON();data.data_origin=origin
  const profiles=data.horizons as {points:{azimuth_deg:number;elevation_deg:number|null}[]}[]
  profiles[0]!.points=[[0,2],[1,3],[2,null],[3,4],[4,3],[90,1]].map(([a,e])=>({azimuth_deg:a!,elevation_deg:e!}))
  profiles[1]!.points=[[0,1],[2,2],[4,1]].map(([a,e])=>({azimuth_deg:a!,elevation_deg:e!}))
  return r.fulfill({json:data})
 })
 await p.goto('/')
 for(const [label,value] of [['Latitude (degrees)','-85'],['Longitude (degrees east)','340'],['UTC date','2026-11-14'],['UTC time','12:30']])await p.getByLabel(label!,{exact:true}).fill(value!)
 await p.getByRole('button',{name:'Run Analysis',exact:true}).click()
 await p.getByRole('navigation').getByRole('link',{name:'Mission Analysis',exact:true}).click()
 await expect(p.getByLabel('Local camera orientation')).toContainText('ready')
}
test('panorama trace toggles preserve points, metadata, celestial motion and 2D tables',async({page},info)=>{
 let posts=0;page.on('request',r=>{if(r.method()==='POST')posts++})
 await open(page)
 await expect(page.getByLabel('Panoramic Trace',{exact:true})).not.toBeChecked()
 await region(page,'Local horizon view').screenshot({path:info.outputPath('Panorama-points.png')})
 await page.getByLabel('Panoramic Trace',{exact:true}).check()
 await expect(page.getByText('Visual trace connects nearby supplied samples.',{exact:false})).toBeVisible()
 await region(page,'Local horizon view').screenshot({path:info.outputPath('Panorama-trace.png')})
 await page.getByLabel('Smooth visual preview',{exact:true}).check()
 await page.getByLabel('Selected UTC time',{exact:true}).fill('500')
 await expect(region(page,'Sun Selected UTC Sample')).toContainText('VISUAL INTERPOLATION')
 await page.getByLabel('3D horizon profile',{exact:true}).selectOption('controlled-horizon-high')
 await expect(region(page,'Interactive 3D Horizon')).toContainText('Observer height: 2 m')
 await expect(page.getByLabel('Celestial horizon relationships')).toContainText('different horizon profile')
 await region(page,'Local horizon view').screenshot({path:info.outputPath('Panorama-high-profile.png')})
 await page.clock.install();await page.clock.pauseAt(new Date())
 await page.getByRole('button',{name:'Play',exact:true}).click();await page.clock.runFor(100)
 await expect(page.getByRole('button',{name:'Pause',exact:true})).toBeEnabled()
 await region(page,'Local horizon view').screenshot({path:info.outputPath('Panorama-playback.png')})
 await page.getByRole('button',{name:'Pause',exact:true}).click()
 await page.getByLabel('Panoramic Trace',{exact:true}).uncheck()
 await expect(region(page,'Local Horizon').getByRole('table')).toHaveCount(2)
 await page.addStyleTag({content:'html{font-size:200%}'})
 await region(page,'Local horizon view').screenshot({path:info.outputPath('Panorama-200.png')})
 expect(posts).toBe(1)
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
})
test('trace buffer is reused across time/camera changes and disposed on profile switch',async({page})=>{
 await page.addInitScript(()=>{
  const state={uploads:0,deletes:0},buffers=new Set<WebGLBuffer>();Object.assign(window,{traceGPU:state})
  const upload=WebGL2RenderingContext.prototype.bufferData,del=WebGL2RenderingContext.prototype.deleteBuffer
  WebGL2RenderingContext.prototype.bufferData=function(...args:unknown[]){if(args[1] instanceof Float32Array&&args[1].length===12){const b=this.getParameter(this.ARRAY_BUFFER_BINDING) as WebGLBuffer;buffers.add(b);state.uploads++}return Reflect.apply(upload,this,args)}
  WebGL2RenderingContext.prototype.deleteBuffer=function(b){if(b&&buffers.has(b)){state.deletes++;buffers.delete(b)}return del.call(this,b)}
 })
 await open(page);await page.getByLabel('Panoramic Trace',{exact:true}).check()
 const read=()=>page.evaluate(()=>(window as unknown as {traceGPU:{uploads:number;deletes:number}}).traceGPU)
 await region(page,'Local horizon view').screenshot();expect((await read()).uploads).toBe(1)
 await page.getByLabel('Selected UTC time',{exact:true}).fill('500')
 await page.getByRole('button',{name:'Look East',exact:true}).click();await region(page,'Local horizon view').screenshot()
 expect((await read()).uploads).toBe(1)
 await page.getByLabel('3D horizon profile',{exact:true}).selectOption('controlled-horizon-high')
 await expect.poll(async()=>(await read()).deletes).toBe(1)
})
for(const origin of ['PRECOMPUTED','LIVE_COMPUTED'] as const) test(`preserves ${origin} origin without claiming independent NASA certification`,async({page})=>{
 await open(page,origin)
 await expect(region(page,'Interactive 3D Horizon')).toContainText(`Data origin: ${origin}`)
})
