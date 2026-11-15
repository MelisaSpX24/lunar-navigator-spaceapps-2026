import { capabilitiesFixture } from '../src/test/jobFixtures'
import { test, expect, type Page } from '@playwright/test'

// Regression coverage uses a controlled health response; live integration is checked separately.
test.beforeEach(async ({ page }) => {
  await page.route('**/api/v1/capabilities',r=>r.fulfill({json:capabilitiesFixture(false)}))
  await page.route('**/api/v1/health', route => route.fulfill({ json: {status:'ok',science_ready:false,dem_ready:false,kernels_ready:false,reason_codes:['SCIENCE_ENGINE_NOT_READY']} }))
})

async function expectNoClippedText(page: Page) {
  const clipped = await page.locator('h1, h2, h3, p, dt, dd').evaluateAll(elements =>
    elements.filter(element => element.scrollWidth > element.clientWidth + 1).map(element => element.textContent),
  )
  expect(clipped).toEqual([])
}

test('all screens render without overflow, page errors or scientific requests', async ({ page }, testInfo) => {
  const errors: string[] = []
  const requests: string[] = []
  let capabilityChecks=0
  page.on('pageerror', error => errors.push(error.message))
  page.on('request', request => {
    const path=new URL(request.url()).pathname
    if(path==='/api/v1/capabilities'&&request.method()==='GET')capabilityChecks++
    if (['fetch', 'xhr'].includes(request.resourceType()) && !(['/api/v1/health','/api/v1/capabilities'].includes(path) && request.method() === 'GET')) requests.push(request.url())
  })
  await page.goto('/')
  for (const title of ['Mission Setup', 'Mission Analysis', 'Alternative Explorer']) {
    await page.getByRole('navigation').getByRole('link', { name: title, exact: true }).click()
    await expect(page.getByRole('heading', { level: 1, name: title })).toBeVisible()
    await expect(page.getByRole('navigation').getByRole('link', { name: title, exact: true })).toHaveAttribute('aria-current', 'page')
    if (title === 'Mission Setup') {
      await expect(page.getByRole('status', { name: 'Camera view' })).toContainText('3D scene ready')
      await expect(page.getByText('NASA color texture loaded — visual imagery only')).toBeVisible()
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
    await expectNoClippedText(page)
    await page.screenshot({ path: testInfo.outputPath(`${title.replaceAll(' ', '-')}.png`), fullPage: true })
  }
  expect(errors).toEqual([])
  expect(requests).toEqual([])
  expect(capabilityChecks).toBe(1)
})

test('hash links, reload and browser back/forward preserve the current screen', async ({ page }) => {
  await page.goto('/#/analysis')
  await expect(page.getByRole('heading', { level: 1, name: 'Mission Analysis' })).toBeVisible()
  await page.reload()
  await expect(page.getByRole('heading', { level: 1, name: 'Mission Analysis' })).toBeVisible()
  await page.getByRole('navigation').getByRole('link', { name: 'Alternative Explorer' }).click()
  await page.goBack()
  await expect(page.getByRole('heading', { level: 1, name: 'Mission Analysis' })).toBeVisible()
  await page.goForward()
  await expect(page.getByRole('heading', { level: 1, name: 'Alternative Explorer' })).toBeVisible()
  await page.goto('/#/alternatives')
  await expect(page.getByRole('heading', { level: 1, name: 'Alternative Explorer' })).toBeVisible()
})

test('keyboard navigation and skip link transfer focus correctly', async ({ page }) => {
  await page.goto('/')
  const analysisLink = page.getByRole('navigation').getByRole('link', { name: 'Mission Analysis' })
  await page.getByRole('navigation').getByRole('link', { name: 'Mission Setup' }).focus()
  await page.keyboard.press('Tab')
  await expect(analysisLink).toBeFocused()
  await expect(analysisLink).toHaveCSS('outline-style', 'solid')
  await expect(analysisLink).toHaveCSS('outline-width', '2px')
  await page.keyboard.press('Enter')
  await expect(page.getByRole('heading', { level: 1, name: 'Mission Analysis' })).toBeVisible()
  await expect(page.getByRole('main')).toBeFocused()
  const skip = page.getByRole('link', { name: 'Skip to main content' })
  await skip.focus()
  await expect(skip).toBeInViewport()
  await page.keyboard.press('Enter')
  await expect(page.getByRole('main')).toBeFocused()
  await expect(page).toHaveURL(/#\/analysis$/)
})

test('unknown routes offer a working recovery link', async ({ page }) => {
  await page.goto('/#/unknown')
  await expect(page.getByRole('heading', { name: 'Page not found' })).toBeVisible()
  await page.getByRole('link', { name: 'Return to Mission Setup' }).click()
  await expect(page.getByRole('heading', { level: 1, name: 'Mission Setup' })).toBeVisible()
})

test('scene areas, touch targets and panel order support the viewport', async ({ page }) => {
  await page.goto('/')
  const globe = await page.getByRole('region', { name: 'Global lunar view' }).boundingBox()
  expect(globe).not.toBeNull()
  expect(globe!.height).toBeGreaterThanOrEqual(380)
  expect(globe!.width).toBeGreaterThan(260)
  for (const link of await page.getByRole('navigation').getByRole('link').all()) {
    const bounds = await link.boundingBox()
    expect(bounds!.width).toBeGreaterThanOrEqual(44)
    expect(bounds!.height).toBeGreaterThanOrEqual(44)
  }
  const run = await page.getByRole('button', { name: 'Run Analysis' }).boundingBox()
  expect(run!.height).toBeGreaterThanOrEqual(44)
  if (page.viewportSize()!.width >= 1100) {
    const parameters = await page.getByRole('region', { name: 'Mission parameters' }).boundingBox()
    expect(globe!.width).toBeGreaterThan(parameters!.width * 1.5)
  }
  await page.goto('/#/analysis')
  await expect(page.getByLabel('Local camera orientation')).toContainText('Local 3D scene ready')
  const horizon = await page.getByRole('region', { name: 'Local horizon view' }).boundingBox()
  expect(horizon!.height).toBeGreaterThanOrEqual(380)
  if (page.viewportSize()!.width <= 700) {
    const titles = ['Local Horizon', 'Sun Visibility', 'Earth Visibility', 'Mission Timeline', 'Operation Assessment', 'Planning Score', 'Data Quality']
    // Read all rectangles in one layout snapshot; lazy scene startup can otherwise
    // change document height between individual boundingBox calls.
    const rectangles = await page.evaluate(names => names.map(name => {
      const element = [...document.querySelectorAll('section')].find(e => e.getAttribute('aria-label') === name || e.querySelector('h2')?.textContent === name)
      if (!element) throw new Error(`Missing panel ${name}`)
      const box = element.getBoundingClientRect()
      return { top: box.top, bottom: box.bottom }
    }), titles)
    for (let i = 1; i < rectangles.length; i++) expect(rectangles[i]!.top).toBeGreaterThanOrEqual(rectangles[i - 1]!.bottom)
  }
})

test('reduced motion and enlarged text preserve access to each screen', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.goto('/')
  await expect(page.getByRole('button', { name: 'Run Analysis' })).toHaveCSS('transition-duration', '0s')
  await page.addStyleTag({ content: 'html { font-size: 200%; }' })
  for (const title of ['Mission Setup', 'Mission Analysis', 'Alternative Explorer']) {
    await page.getByRole('navigation').getByRole('link', { name: title, exact: true }).click()
    await expect(page.getByRole('heading', { level: 1, name: title })).toBeVisible()
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    await expectNoClippedText(page)
  }
})
