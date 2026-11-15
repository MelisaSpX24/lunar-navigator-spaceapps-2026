import { test, expect, type Page } from '@playwright/test'
import { scientificFixture } from '../src/test/scientificFixtures'
import { analysisFixture, healthFixture } from '../src/test/apiFixtures'
import type { AnalysisResponse } from '../src/services/api/responses'

const panel=(page:Page,name:string)=>page.getByRole('region',{name,exact:true})
async function openResponse(page:Page,change:(r:AnalysisResponse)=>AnalysisResponse=(r=>r),status=200) {
  await page.route('**/api/v1/health',route=>route.fulfill({json:healthFixture(true)}))
  await page.route('**/api/v1/analyses',route=>{
    const r=scientificFixture();r.request=route.request().postDataJSON()
    return route.fulfill({status,json:change(r)})
  })
  await page.goto('/')
  await page.getByLabel('Latitude (degrees)',{exact:true}).fill('-85')
  await page.getByLabel('Longitude (degrees east)',{exact:true}).fill('340')
  await page.getByLabel('UTC date',{exact:true}).fill('2026-11-14')
  await page.getByLabel('UTC time',{exact:true}).fill('12:30')
  await expect(page.getByRole('button',{name:'Run Analysis',exact:true})).toBeEnabled()
  await page.getByRole('button',{name:'Run Analysis',exact:true}).click()
  await page.getByRole('navigation').getByRole('link',{name:'Mission Analysis',exact:true}).click()
  await expect(page.getByRole('heading',{name:'Mission Analysis',exact:true})).toBeVisible()
}
const fixtureNotice=(page:Page)=>page.getByText('TEST DATA — This response is not a live scientific assessment.',{exact:true})

test('matched completed TEST_FIXTURE populates all seven panels with explicit units, source and gaps',async({page},info)=>{
  const errors:string[]=[];page.on('pageerror',error=>errors.push(error.message))
  await openResponse(page)
  await expect(fixtureNotice(page)).toBeVisible()
  await expect(panel(page,'Local Horizon')).toContainText('Observer height: 1 m. Analysis range: 1200 m.')
  await expect(panel(page,'Local Horizon')).toContainText('Observer height: 2 m. Analysis range: 1200 m.')
  await expect(panel(page,'Local Horizon').getByRole('img')).toHaveCount(2)
  expect(await panel(page,'Local Horizon').locator('circle').count()).toBe(6)
  expect(await panel(page,'Local Horizon').locator('polyline').count()).toBe(0)
  for(const body of ['Sun','Earth']) {
    await expect(panel(page,`${body} Visibility`).getByRole('img',{name:new RegExp(`${body} elevation over UTC`)})).toBeVisible()
    await expect(panel(page,`${body} Visibility`).getByRole('table')).toHaveAccessibleName(new RegExp(`${body} samples`))
    await expect(panel(page,`${body} Visibility`)).toContainText('UNKNOWN')
    await expect(panel(page,`${body} Visibility`)).toContainText('PARTIAL')
    expect(await panel(page,`${body} Visibility`).locator('circle').count()).toBe(4)
  }
  await expect(panel(page,'Sun Visibility')).toContainText('NONE')
  await expect(panel(page,'Mission Timeline')).toContainText('Start included; end excluded.')
  await expect(panel(page,'Mission Timeline')).toContainText('Windows not calculated (null).')
  await expect(panel(page,'Mission Timeline')).toContainText('Calculated — no matching windows (empty array).')
  await expect(panel(page,'Mission Timeline').getByRole('table')).toContainText('true')
  await expect(panel(page,'Operation Assessment').getByRole('table')).toContainText('NOT_MET')
  await expect(panel(page,'Operation Assessment').getByRole('table')).toContainText('Unknown (null)')
  await expect(page.getByLabel('Backend planning score')).toHaveText('0 / 100')
  await expect(panel(page,'Planning Score')).toContainText('Data quality limitation: LIMITED')
  await expect(panel(page,'Data Quality')).toContainText('Controlled UI test product')
  await expect(panel(page,'Data Quality')).toContainText('c'.repeat(64))
  await expect(panel(page,'Data Quality').getByRole('link')).toHaveAttribute('href','https://example.invalid/controlled-test')
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
  await page.evaluate(()=>scrollTo(0,0))
  await page.screenshot({path:info.outputPath('Analysis-controlled-complete.png'),fullPage:true})
  expect(errors).toEqual([])
})

test('partial completed result preserves null versus empty arrays and unknown quality',async({page},info)=>{
  await openResponse(page,r=>({...r,series:null,horizons:[],windows:{sun:null,earth:[],joint:[]},score:{value:null,model_version:null,components:null},quality:{status:'NOT_ASSESSED',coverage_complete:null,limitations:[]},sources:[]}))
  await expect(fixtureNotice(page)).toBeVisible()
  await expect(panel(page,'Sun Visibility')).toContainText('Sun time samples not calculated or not provided (null).')
  await expect(panel(page,'Local Horizon')).toContainText('Calculated — no horizon profiles supplied (empty array).')
  await expect(panel(page,'Planning Score').getByRole('heading',{name:'Not calculated',exact:true})).toBeVisible()
  await expect(page.getByLabel('Backend planning score')).toHaveCount(0)
  await expect(panel(page,'Data Quality')).toContainText('Coverage complete: Unknown (null)')
  await expect(panel(page,'Data Quality')).toContainText('No source records supplied (empty array).')
  await page.evaluate(()=>scrollTo(0,0))
  await page.screenshot({path:info.outputPath('Analysis-partial.png'),fullPage:true})
})

test('invalid panel data stays isolated and unsafe source URLs remain plain text',async({page},info)=>{
  await openResponse(page,r=>{
    const rows=r.series as {sun:object}[],h=r.horizons as {points:unknown[]}[],sources=r.sources as object[]
    rows[0]!.sun={...rows[0]!.sun,disk_visible_fraction:2}
    h[0]!.points=[{azimuth_deg:360,elevation_deg:0}]
    r.score={...r.score,components:[{name:'invalid controlled component',raw_value:0,normalized_value:2,weight:1}]}
    r.sources=[{...sources[0],url:'javascript:alert(1)'}]
    return r
  })
  await expect(fixtureNotice(page)).toBeVisible()
  for(const name of ['Sun Visibility','Local Horizon','Planning Score']) await expect(panel(page,name).getByRole('alert')).toContainText('Invalid scientific response data')
  await expect(panel(page,'Earth Visibility').getByRole('img')).toHaveCount(2)
  await expect(panel(page,'Mission Timeline').getByRole('table')).toHaveCount(1)
  await expect(panel(page,'Operation Assessment').getByRole('table')).toBeVisible()
  await expect(panel(page,'Data Quality')).toContainText('unsupported or unsafe URL; not a link.')
  await expect(panel(page,'Data Quality').getByRole('link')).toHaveCount(0)
  await page.evaluate(()=>scrollTo(0,0))
  await page.screenshot({path:info.outputPath('Analysis-invalid-panels.png'),fullPage:true})
})

test('unordered UTC and reversed window intervals are rejected without hiding independent panels',async({page})=>{
  await openResponse(page,r=>{
    const rows=r.series as {time_utc:string}[];rows[1]!.time_utc='2026-11-14T12:29:00Z'
    r.windows.sun=[{start_utc:'2026-11-14T12:45:00Z',end_utc:'2026-11-14T12:30:00Z',definition_id:'controlled-invalid',start_censored:false,end_censored:false}]
    return r
  })
  await expect(panel(page,'Sun Visibility').getByRole('alert')).toContainText('strictly increasing')
  await expect(panel(page,'Earth Visibility').getByRole('alert')).toContainText('strictly increasing')
  await expect(panel(page,'Mission Timeline').getByRole('alert')).toContainText('No interval was sorted or clipped.')
  await expect(page.getByLabel('Backend planning score')).toHaveText('0 / 100')
  await expect(panel(page,'Local Horizon').getByRole('img')).toHaveCount(2)
})

test('mismatched echoed request is rejected even with the same analysis ID',async({page})=>{
  await openResponse(page,r=>({...r,request:{...r.request,observer:{surface_elevation_mode:'DEM',solar_height_above_surface_m:2,earth_height_above_surface_m:1}}}))
  await expect(panel(page,'Analysis Connection / Response Status').getByRole('alert')).toContainText('Response request does not match the submitted scenario.')
  await expect(fixtureNotice(page)).toHaveCount(0)
  await expect(panel(page,'Local Horizon')).toContainText('Orientation preview only')
  await expect(page.getByLabel('3D horizon profile',{exact:true})).toHaveCount(0)
  await expect(panel(page,'Sun Visibility')).toContainText('No visibility data')
  await expect(page.getByLabel('Backend planning score')).toHaveCount(0)
})

test('non-completed and 503 responses leave all seven panels without scientific values',async({page})=>{
  for(const execution_status of ['NOT_RUN','RUNNING','FAILED'] as const) {
    await openResponse(page,r=>({...r,execution_status}))
    await expect(panel(page,'Analysis Connection / Response Status')).toContainText('Response received; the server has not reported a completed analysis.')
    await expect(fixtureNotice(page)).toHaveCount(0)
    await expect(panel(page,'Local Horizon')).toContainText('Orientation preview only')
    await expect(page.getByLabel('3D horizon profile',{exact:true})).toHaveCount(0)
    await expect(panel(page,'Sun Visibility')).toContainText('No visibility data')
    await expect(panel(page,'Planning Score')).toContainText('Not calculated')
  }
  await openResponse(page,r=>analysisFixture({request:r.request}),503)
  await expect(panel(page,'Analysis Connection / Response Status')).toContainText('Scientific analysis is currently unavailable.')
  await expect(panel(page,'Local Horizon')).toContainText('Orientation preview only')
  await expect(page.getByLabel('3D horizon profile',{exact:true})).toHaveCount(0)
  for(const name of ['Sun Visibility','Earth Visibility','Mission Timeline','Operation Assessment','Planning Score','Data Quality']) {
    await expect(panel(page,name).getByRole('img')).toHaveCount(0)
    await expect(panel(page,name).getByRole('table')).toHaveCount(0)
  }
})

test('navigation retains scenario and marker; editing or reset clears old scientific charts',async({page})=>{
  await openResponse(page);await expect(fixtureNotice(page)).toBeVisible()
  await page.getByRole('navigation').getByRole('link',{name:'Alternative Explorer',exact:true}).click()
  await page.getByRole('navigation').getByRole('link',{name:'Mission Setup',exact:true}).click()
  await expect(page.getByLabel('Latitude (degrees)',{exact:true})).toHaveValue('-85')
  await expect(page.getByText(/^Signed longitude:/)).toContainText('-20.000')
  await page.getByLabel('Latitude (degrees)',{exact:true}).fill('-84')
  await page.getByRole('navigation').getByRole('link',{name:'Mission Analysis',exact:true}).click()
  await expect(fixtureNotice(page)).toHaveCount(0)
  await expect(panel(page,'Local Horizon')).toContainText('Orientation preview only')
  await expect(page.getByLabel('3D horizon profile',{exact:true})).toHaveCount(0)
  await expect(panel(page,'Sun Visibility')).toContainText('No visibility data')
  await page.getByRole('link',{name:'Edit scenario in Mission Setup'}).click()
  await page.getByRole('button',{name:'Reset scenario',exact:true}).click()
  await expect(page.getByLabel('Latitude (degrees)',{exact:true})).toHaveValue('')
})

test('200% text, accessible graph summaries and keyboard-scrollable tables do not overflow the page',async({page},info)=>{
  await openResponse(page);await expect(fixtureNotice(page)).toBeVisible()
  await page.addStyleTag({content:'html {font-size:200%;}'})
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
  const tableRegion=panel(page,'Sun Visibility').getByRole('region',{name:/Sun samples/})
  await tableRegion.focus();await expect(tableRegion).toBeFocused()
  await page.keyboard.press('ArrowRight')
  await expect.poll(()=>tableRegion.evaluate(e=>e.scrollLeft)).toBeGreaterThan(0)
  const graph=panel(page,'Sun Visibility').getByRole('img',{name:/Sun elevation over UTC/})
  await expect(graph).toHaveAccessibleName(/unknown values omitted/)
  await page.evaluate(()=>scrollTo(0,0))
  await page.screenshot({path:info.outputPath('Analysis-200-percent.png'),fullPage:true})
})
