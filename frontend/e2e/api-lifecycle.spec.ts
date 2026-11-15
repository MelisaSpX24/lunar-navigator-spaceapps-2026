import { test, expect, type Page } from '@playwright/test'
import { analysisFixture, healthFixture, requestFixture } from '../src/test/apiFixtures'

const connection=(page:Page)=>page.getByRole('group',{name:'Backend connection'})
const responsePanel=(page:Page)=>page.getByRole('region',{name:'Analysis Connection / Response Status'})
async function health(page:Page,ready=false) {
  await page.route('**/api/v1/health',route=>route.fulfill({json:healthFixture(ready)}))
}
async function fill(page:Page) {
  await page.getByLabel('Latitude (degrees)',{exact:true}).fill('-85')
  await page.getByLabel('Longitude (degrees east)',{exact:true}).fill('340')
  await page.getByLabel('UTC date',{exact:true}).fill('2026-11-14')
  await page.getByLabel('UTC time',{exact:true}).fill('12:30')
}
async function start(page:Page) {await health(page,true);await page.goto('/');await fill(page);await expect(page.getByRole('button',{name:'Run Analysis',exact:true})).toBeEnabled()}

test('reachable is not ready; scenario, globe marker and health survive navigation until explicit reset',async({page},info)=>{
  let checks=0,posts=0
  await page.route('**/api/v1/health',route=>{checks++;return route.fulfill({json:healthFixture()})})
  await page.route('**/api/v1/analyses',route=>{posts++;return route.abort()})
  await page.goto('/');await fill(page)
  await expect(connection(page)).toContainText('Backend reachable — scientific engine not ready')
  await expect(page.getByRole('button',{name:'Run Analysis',exact:true})).toBeDisabled()
  const enable=page.getByRole('button',{name:'Enable globe interaction'})
  if(await enable.isVisible()) await enable.click()
  await expect(page.getByRole('status',{name:'Camera view'})).toContainText('3D scene ready')
  await page.locator('canvas').click()
  const latitude=await page.getByLabel('Latitude (degrees)',{exact:true}).inputValue()
  const longitude=await page.getByLabel('Longitude (degrees east)',{exact:true}).inputValue()
  const readout=await page.getByText(/^Signed longitude:/).innerText()
  await page.getByRole('navigation').getByRole('link',{name:'Mission Analysis',exact:true}).click()
  const scenario=page.getByRole('region',{name:'Current Scenario',exact:true})
  await expect(scenario).toContainText(latitude)
  await expect(scenario).toContainText(longitude)
  await expect(scenario).toContainText('2026-11-14T12:30:00Z')
  await page.screenshot({path:info.outputPath('Scenario-analysis-not-ready.png'),fullPage:true})
  await page.getByRole('navigation').getByRole('link',{name:'Alternative Explorer',exact:true}).click()
  await page.getByRole('navigation').getByRole('link',{name:'Mission Setup',exact:true}).click()
  await expect(page.getByLabel('Latitude (degrees)',{exact:true})).toHaveValue(latitude)
  await expect(page.getByLabel('Longitude (degrees east)',{exact:true})).toHaveValue(longitude)
  await expect(page.getByText(/^Signed longitude:/)).toHaveText(readout)
  expect(checks).toBe(1);expect(posts).toBe(0)
  await connection(page).getByRole('button',{name:'Check backend'}).click()
  await expect.poll(()=>checks).toBe(2)
  await page.getByRole('button',{name:'Reset scenario',exact:true}).click()
  await expect(page.getByLabel('Latitude (degrees)',{exact:true})).toHaveValue('')
  await expect(page.getByText('No surface point selected')).toBeVisible()
})

test('ready, valid input sends one exact POST; 503 is NOT_RUN and preserves inputs',async({page},info)=>{
  let posts=0;let body:unknown;let release!:()=>void
  const gate=new Promise<void>(resolve=>{release=resolve})
  await page.route('**/api/v1/analyses',async route=>{posts++;body=route.request().postDataJSON();await gate;await route.fulfill({status:503,json:analysisFixture()})})
  await health(page,true);await page.goto('/')
  await expect(page.getByRole('button',{name:'Run Analysis',exact:true})).toBeDisabled()
  await fill(page)
  const run=page.getByRole('button',{name:'Run Analysis',exact:true})
  await expect(run).toBeEnabled()
  // Two DOM clicks in one task prove the synchronous guard as well as the disabled UI.
  await run.evaluate(button=>{(button as HTMLButtonElement).click();(button as HTMLButtonElement).click()})
  await expect(responsePanel(page)).toContainText('Submitting scenario')
  await expect(run).toBeDisabled()
  await expect(connection(page).getByRole('button',{name:'Check backend'})).toBeDisabled()
  await expect.poll(()=>posts).toBe(1);expect(body).toEqual(requestFixture())
  release()
  await expect(responsePanel(page)).toContainText('Scientific analysis is currently unavailable. Your scenario inputs have been preserved.')
  await expect(responsePanel(page)).toContainText('NOT_RUN')
  await expect(responsePanel(page)).toContainText('SCIENCE_ENGINE_NOT_READY')
  await expect(responsePanel(page)).toContainText('unavailable (null); no zero has been inferred')
  await expect(page.getByLabel('Longitude (degrees east)',{exact:true})).toHaveValue('340')
  await expect(run).toBeDisabled()
  await page.evaluate(()=>scrollTo(0,0))
  await page.screenshot({path:info.outputPath('Scenario-503-preserved.png'),fullPage:true})
})

test('422 maps field errors and safely displays unknown locations without changing input',async({page},info)=>{
  await page.route('**/api/v1/analyses',route=>route.fulfill({status:422,json:{detail:[
    {loc:['body','site','COORDINATES','latitude_deg'],msg:'Backend rejected this latitude.'},
    {loc:['body','operation','requirements','min_sun_visible_s'],msg:'Backend threshold rule.'},
    {loc:['body','future_rule'],msg:'<b>Unmapped backend rule</b>'},
  ]}}))
  await start(page);await page.getByRole('button',{name:'Run Analysis',exact:true}).click()
  await expect(page.getByLabel('Latitude (degrees)',{exact:true})).toHaveAttribute('aria-invalid','true')
  await expect(page.locator('#mission-latitude-error')).toHaveText('Backend rejected this latitude.')
  await expect(page.getByLabel('Latitude (degrees)',{exact:true})).toHaveValue('-85')
  await expect(responsePanel(page).getByRole('alert')).toContainText('<b>Unmapped backend rule</b>')
  expect(await responsePanel(page).locator('b').count()).toBe(0)
  await page.getByRole('button',{name:'Validate inputs',exact:true}).click()
  await expect(page.getByLabel('Latitude (degrees)',{exact:true})).toBeFocused()
  await page.evaluate(()=>scrollTo(0,0))
  await page.screenshot({path:info.outputPath('Scenario-422-fields.png'),fullPage:true})
  await page.getByLabel('Latitude (degrees)',{exact:true}).fill('-84')
  await expect(page.locator('#mission-latitude-error')).toHaveCount(0)
})

test('unreachable and invalid health support explicit keyboard retry without POST',async({page},info)=>{
  let checks=0,posts=0
  await page.route('**/api/v1/health',route=>{checks++;return checks===1?route.abort('connectionrefused'):checks===2?route.fulfill({body:'invalid json',contentType:'application/json'}):route.fulfill({json:healthFixture()})})
  page.on('request',request=>{if(request.method()==='POST')posts++})
  await page.goto('/');await fill(page)
  await expect(connection(page)).toContainText('Backend unreachable')
  await connection(page).getByRole('button',{name:'Retry connection'}).focus()
  await page.keyboard.press('Enter')
  await expect(connection(page)).toContainText('Backend response invalid — readiness unknown')
  await page.addStyleTag({content:'html {font-size:200%;}'})
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
  await page.screenshot({path:info.outputPath('Backend-invalid-200-text.png'),fullPage:true})
  await connection(page).getByRole('button',{name:'Retry connection'}).click()
  await expect(connection(page)).toContainText('Backend reachable — scientific engine not ready')
  expect(checks).toBe(3);expect(posts).toBe(0)
})

test('cancellation and editing discard delayed responses; a new response survives an older one',async({page})=>{
  let posts=0,releaseOld!:()=>void,releaseCancelled!:()=>void
  const old=new Promise<void>(resolve=>{releaseOld=resolve}),cancelled=new Promise<void>(resolve=>{releaseCancelled=resolve})
  await page.route('**/api/v1/analyses',async route=>{
    const n=++posts
    if(n===1) await cancelled
    if(n===2) await old
    await route.fulfill({json:analysisFixture({analysis_id:`controlled-${n}`,execution_status:'RUNNING',data_origin:'TEST_FIXTURE',request:route.request().postDataJSON()})}).catch(()=>{})
  })
  await start(page);await page.getByRole('button',{name:'Run Analysis',exact:true}).click()
  await expect.poll(()=>posts).toBe(1)
  await responsePanel(page).getByRole('button',{name:'Cancel request'}).click()
  await expect(responsePanel(page)).toContainText('Analysis request cancelled')
  releaseCancelled()
  await page.getByRole('button',{name:'Run Analysis',exact:true}).click()
  await expect.poll(()=>posts).toBe(2)
  await page.getByLabel('Longitude (degrees east)',{exact:true}).fill('270')
  await expect(responsePanel(page)).toContainText('Scenario changed')
  await page.getByRole('button',{name:'Run Analysis',exact:true}).click()
  await expect(responsePanel(page)).toContainText('controlled-3')
  releaseOld()
  await expect(responsePanel(page)).not.toContainText('controlled-2')
  await expect(responsePanel(page)).toContainText('controlled-3')
})

test('HTTP 200 NOT_RUN and TEST_FIXTURE remain text status, never scientific success',async({page},info)=>{
  await page.route('**/api/v1/analyses',route=>route.fulfill({json:analysisFixture({data_origin:'TEST_FIXTURE'})}))
  await start(page);await page.getByRole('button',{name:'Run Analysis',exact:true}).click()
  await expect(responsePanel(page)).toContainText('server has not reported a completed analysis')
  await expect(responsePanel(page)).toContainText('Test fixture response — not a live NASA analysis.')
  await expect(responsePanel(page)).toContainText('not calculated or not provided (null)')
  await page.getByRole('navigation').getByRole('link',{name:'Mission Analysis',exact:true}).click()
  await expect(page.getByRole('region',{name:'Planning Score',exact:true})).toContainText('Not calculated')
  await expect(page.getByRole('region',{name:'Planning Score',exact:true})).not.toContainText(/\d/)
  await expect(page.getByRole('region',{name:'Sun Visibility',exact:true})).toContainText('No visibility data')
  await page.screenshot({path:info.outputPath('Response-test-fixture.png'),fullPage:true})
})

test('server and schema failures remain distinct from science-not-ready',async({page})=>{
  const replies=[{status:500,json:{}},{status:502,json:{}},{status:504,json:{}},{status:404,json:{}},
    {status:503,json:analysisFixture({decision:{status:'INCOMPLETE',reason_codes:[]}})},
    {status:200,json:{...analysisFixture(),schema_version:'2.0'}},{status:200,body:'not json',contentType:'application/json'}]
  let index=0
  await page.route('**/api/v1/analyses',route=>route.fulfill(replies[index++]!))
  await start(page)
  for(const reply of replies) {
    await page.getByRole('button',{name:'Run Analysis',exact:true}).click()
    await expect(responsePanel(page).getByRole('alert')).toContainText(`HTTP status: ${reply.status}`)
    await expect(responsePanel(page)).not.toContainText('Scientific analysis is currently unavailable.')
    await expect(page.getByLabel('Latitude (degrees)',{exact:true})).toHaveValue('-85')
  }
  await expect(responsePanel(page)).toContainText('Analysis response is not valid JSON.')
  await page.route('**/api/v1/analyses',route=>route.abort('failed'))
  await page.getByRole('button',{name:'Run Analysis',exact:true}).click()
  await expect(responsePanel(page).getByRole('alert')).toContainText('The backend could not be reached.')
})

test('COMPLETED fixture response stays labelled and does not populate scientific panels',async({page})=>{
  await page.route('**/api/v1/analyses',route=>route.fulfill({json:analysisFixture({execution_status:'COMPLETED',data_origin:'TEST_FIXTURE',score:{value:75}})}))
  await start(page);await page.getByRole('button',{name:'Run Analysis',exact:true}).click()
  await expect(responsePanel(page)).toContainText('Server reports COMPLETED.')
  await expect(responsePanel(page)).toContainText('Test fixture response — not a live NASA analysis.')
  await expect(responsePanel(page)).toContainText('field received; see Planning Score for validation.')
  await expect(responsePanel(page)).not.toContainText('75')
  await page.getByRole('navigation').getByRole('link',{name:'Mission Analysis',exact:true}).click()
  await expect(page.getByRole('region',{name:'Planning Score',exact:true})).toContainText('Score withheld')
})
