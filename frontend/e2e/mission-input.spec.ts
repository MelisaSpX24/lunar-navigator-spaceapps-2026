import { test, expect, type Page } from '@playwright/test'

// Regression coverage uses a controlled health response; live integration is checked separately.
test.beforeEach(async ({ page }) => {
  await page.route('**/api/v1/health', route => route.fulfill({ json: {status:'ok',science_ready:false,dem_ready:false,kernels_ready:false,reason_codes:['SCIENCE_ENGINE_NOT_READY']} }))
})

async function validInputs(page: Page) {
  await page.goto('/')
  await page.getByLabel('Latitude (degrees)', {exact:true}).fill('10')
  await page.getByLabel('Longitude (degrees east)', {exact:true}).fill('340')
  await page.getByLabel('UTC date', {exact:true}).fill('2026-11-14')
  await page.getByLabel('UTC time', {exact:true}).fill('12:30')
  await page.getByLabel('Hours', {exact:true}).fill('2')
  await page.getByLabel('Minutes', {exact:true}).fill('30')
  await expect(page.getByText('Scenario inputs valid — check backend readiness before running analysis.')).toBeVisible()
  await page.getByText('Request Preview', {exact:true}).click()
}
async function request(page: Page) { return JSON.parse((await page.getByLabel('AnalysisRequest JSON').textContent())!) }

test('manual coordinates, four profiles and a real request preview never start analysis', async ({page}, info) => {
  const posts: string[] = []
  page.on('request', req => { if(req.method()==='POST') posts.push(req.url()) })
  await validInputs(page)
  for(const profile of ['SOLAR_POWERED_EXPERIMENT','EARTH_DATA_TRANSMISSION','SHORT_SURFACE_OBSERVATION','CUSTOM_OPERATION']) {
    await page.getByLabel('Operation profile', {exact:true}).selectOption(profile)
    const json = await request(page)
    expect(json.operation.profile).toBe(profile)
    expect(json.operation.requirements.min_solar_disk_visible_fraction).toBe(.5)
    expect(json.operation.requirements.min_joint_continuous_s).toBeNull()
  }
  const json = await request(page)
  expect(json.site).toEqual({kind:'COORDINATES',latitude_deg:10,longitude_deg_east:340,frame:'MOON_ME_DE421',latitude_type:'PLANETOCENTRIC'})
  expect(json.time).toEqual({start_utc:'2026-11-14T12:30:00Z',duration_s:9000})
  await expect(page.getByRole('status',{name:'Total operation duration'})).toContainText('9000 seconds')
  await expect(page.getByRole('button',{name:'Run Analysis'})).toBeDisabled()
  await page.getByRole('button',{name:'Validate inputs'}).click()
  await expect(page.getByRole('heading',{name:'Selected visual coordinate'})).toBeVisible()
  await expect(page.getByText(/^Signed longitude:/)).toContainText('-20.000°')
  await expect(page.getByText('NASA color texture loaded — visual imagery only')).toBeVisible()
  await page.evaluate(() => scrollTo(0, 0))
  await page.screenshot({path:info.outputPath('Mission-form-valid.png'),fullPage:true})
  expect(posts).toEqual([])
})

test('real globe picking updates the form and camera controls preserve the shared point', async ({page}) => {
  await page.goto('/')
  await expect(page.getByRole('status',{name:'Camera view'})).toContainText('3D scene ready')
  const enable=page.getByRole('button',{name:'Enable globe interaction'})
  if(await enable.isVisible()) await enable.click()
  const canvas=page.locator('canvas')
  await canvas.scrollIntoViewIfNeeded()
  await canvas.click()
  const lat=await page.getByLabel('Latitude (degrees)',{exact:true}).inputValue()
  const lon=await page.getByLabel('Longitude (degrees east)',{exact:true}).inputValue()
  expect(Number(lat)).toBeGreaterThan(-90)
  expect(Number(lat)).toBeLessThan(90)
  expect(Number(lon)).toBeGreaterThan(180)
  expect(Number(lon)).toBeLessThan(360)
  await expect(page.getByText(/^Signed longitude:/)).toContainText((Number(lon)-360).toFixed(3))
  for(const name of ['Focus South Pole','Reset View']) {
    await page.getByRole('button',{name}).click()
    await expect(page.getByLabel('Latitude (degrees)',{exact:true})).toHaveValue(lat)
    await expect(page.getByLabel('Longitude (degrees east)',{exact:true})).toHaveValue(lon)
  }
})

test('invalid coordinates, thresholds and poles retain user input and hide request JSON', async ({page},info) => {
  await validInputs(page)
  await page.getByLabel('Longitude (degrees east)',{exact:true}).fill('360')
  await expect(page.getByLabel('AnalysisRequest JSON')).toHaveCount(0)
  await expect(page.getByLabel('Longitude (degrees east)',{exact:true})).toHaveValue('360')
  await expect(page.getByLabel('Longitude (degrees east)',{exact:true})).toHaveAttribute('aria-invalid','true')
  await expect(page.locator('#mission-longitude-error')).toBeVisible()
  await expect(page.locator('#mission-longitude-error')).toContainText('360° is excluded')
  await page.getByLabel('Latitude (degrees)',{exact:true}).fill('-90')
  await expect(page.getByText(/Exact ±90° poles are not supported/)).toBeVisible()
  await expect(page.getByLabel('Latitude (degrees)',{exact:true})).toHaveValue('-90')
  await page.getByLabel('Latitude (degrees)',{exact:true}).fill('-85')
  await page.getByLabel('Longitude (degrees east)',{exact:true}).fill('270')
  await page.getByLabel('Minimum continuous Earth visibility (seconds)',{exact:true}).fill('9001')
  await expect(page.getByText('This requirement cannot exceed the total operation duration.')).toBeVisible()
  await expect(page.getByLabel('AnalysisRequest JSON')).toHaveCount(0)
  await page.evaluate(() => scrollTo(0, 0))
  await page.screenshot({path:info.outputPath('Mission-form-invalid.png'),fullPage:true})
  await page.getByLabel('Minimum continuous Earth visibility (seconds)',{exact:true}).fill('0')
  await page.getByLabel('Minimum joint visibility (seconds)',{exact:true}).fill('0')
  await expect(page.getByText(/Enable simultaneous visibility when/)).toBeVisible()
  await page.getByLabel('Require simultaneous Sun and Earth visibility',{exact:true}).check()
  expect((await request(page)).operation.requirements.min_joint_continuous_s).toBe(0)
})

test('advanced observer/options preserve null versus zero and respect the backend schema', async ({page}) => {
  await validInputs(page)
  await page.getByText('Advanced settings',{exact:true}).click()
  await page.getByLabel('Minimum Sun visibility (seconds)',{exact:true}).fill('0')
  await page.getByLabel('Solar device height (metres)',{exact:true}).fill('0')
  await page.getByLabel('Earth device height (metres)',{exact:true}).fill('2.5')
  await page.getByLabel('Event lookahead (seconds)',{exact:true}).fill('0')
  await page.getByLabel('Include full horizon profile',{exact:true}).uncheck()
  await page.getByLabel('Include Earth disk fraction',{exact:true}).uncheck()
  const json=await request(page)
  expect(json.observer).toEqual({surface_elevation_mode:'DEM',solar_height_above_surface_m:0,earth_height_above_surface_m:2.5})
  expect(json.options).toEqual({include_full_horizon:false,include_earth_disk_fraction:false,event_lookahead_s:0})
  expect(json.operation.requirements.min_sun_visible_s).toBe(0)
  expect(json.operation.requirements.min_earth_continuous_s).toBeNull()
  expect(Object.keys(json).sort()).toEqual(['observer','operation','options','schema_version','site','time'])
})

test('enlarged text, field errors and JSON remain keyboard-accessible without overflow', async ({page},info) => {
  await page.emulateMedia({reducedMotion:'reduce'})
  await validInputs(page)
  await page.addStyleTag({content:'html { font-size: 200%; }'})
  await page.getByLabel('Operation profile',{exact:true}).selectOption('SOLAR_POWERED_EXPERIMENT')
  await expect(page.locator('#profile-description')).toContainText('Solar-Powered Experiment.')
  await page.getByText('Advanced settings',{exact:true}).click()
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
  await expect(page.getByLabel('AnalysisRequest JSON')).toBeVisible()
  await page.getByLabel('Longitude (degrees east)',{exact:true}).fill('360')
  await page.getByRole('button',{name:'Validate inputs'}).click()
  const field=page.getByLabel('Longitude (degrees east)',{exact:true})
  await expect(field).toBeFocused()
  await expect(field).toHaveAttribute('aria-invalid','true')
  expect(await field.getAttribute('aria-describedby')).toContain('mission-longitude-error')
  const clipped=await page.locator('h1,h2,h3,p,label,legend').evaluateAll(elements=>elements.filter(e=>e.scrollWidth>e.clientWidth+1).map(e=>e.textContent))
  expect(clipped).toEqual([])
  await page.evaluate(() => scrollTo(0, 0))
  await page.screenshot({path:info.outputPath('Mission-form-enlarged.png'),fullPage:true})
})

test('UTC preview remains identical across browser time zones and DST transitions', async ({browser,baseURL}) => {
  for(const timezoneId of ['UTC','Europe/Istanbul','America/New_York']) {
    const context=await browser.newContext({timezoneId,baseURL:baseURL!})
    try {
      const page=await context.newPage()
      await validInputs(page)
      for(const [date,time,expected] of [
        ['2026-03-08','02:30','2026-03-08T02:30:00Z'],
        ['2026-11-01','01:30','2026-11-01T01:30:00Z'],
        ['2026-12-31','23:59:59','2026-12-31T23:59:59Z'],
        ['2027-01-01','00:00','2027-01-01T00:00:00Z'],
      ]) {
        await page.getByLabel('UTC date',{exact:true}).fill(date!)
        await page.getByLabel('UTC time',{exact:true}).fill(time!)
        expect((await request(page)).time.start_utc).toBe(expected)
        await expect(page.getByLabel('UTC date',{exact:true})).toHaveValue(date!)
      }
    } finally { await context.close() }
  }
})
