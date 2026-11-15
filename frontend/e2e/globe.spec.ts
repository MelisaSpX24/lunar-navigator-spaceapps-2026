import { capabilitiesFixture } from '../src/test/jobFixtures'
import { test, expect, type Page } from '@playwright/test'

// Regression coverage uses a controlled health response; live integration is checked separately.
test.beforeEach(async ({ page }) => {
  await page.route('**/api/v1/health', route => route.fulfill({ json: {status:'ok',science_ready:false,dem_ready:false,kernels_ready:false,reason_codes:['SCIENCE_ENGINE_NOT_READY']} }))
})
import { createHash } from 'node:crypto'
import { PerspectiveCamera, Vector3 } from 'three'

async function observeMoonUploads(page: Page) {
  // Observe genuine GPU uploads from the browser, without adding production
  // globals or replacing Three.js, the JPEG or the rendering context.
  await page.addInitScript(() => {
    const observed = window as typeof window & { __moonUploads: number[][] }
    observed.__moonUploads = []
    const prototype = WebGL2RenderingContext.prototype as unknown as Record<string, (...args: unknown[]) => unknown>
    for (const method of ['texImage2D', 'texSubImage2D']) {
      const original = prototype[method]!
      prototype[method] = function (this: WebGL2RenderingContext, ...args: unknown[]) {
        const value = Reflect.apply(original, this, args)
        for (const source of args) {
          if (source instanceof HTMLImageElement && source.src.endsWith('/assets/moon/lroc_color_2k.jpg')) {
            observed.__moonUploads.push([source.naturalWidth, source.naturalHeight])
          }
        }
        return value
      }
    }
  })
}

async function ready(page: Page) {
  await page.goto('/')
  await expect(page.getByRole('status', { name: 'Camera view' })).toContainText('3D scene ready')
  await expect(page.getByText('NASA color texture loaded — visual imagery only')).toBeVisible()
  const enable = page.getByRole('button', { name: 'Enable globe interaction' })
  if (await enable.isVisible()) await enable.click()
  const canvas = page.locator('canvas')
  await canvas.scrollIntoViewIfNeeded()
  return canvas
}

async function distance(page: Page) {
  const text = await page.getByRole('status', { name: 'Camera view' }).innerText()
  return Number(text.match(/Camera distance ([\d.]+)/)?.[1])
}

test.beforeEach(async({page})=>{await page.route('**/api/v1/capabilities',r=>r.fulfill({json:capabilitiesFixture(false)}))})

test('real WebGL sphere with local NASA texture, camera focus and reset', async ({ page }, info) => {
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()) })
  const canvas = await ready(page)
  await expect(canvas).toBeVisible()
  const renderer = await canvas.evaluate(element => {
    const gl = (element as HTMLCanvasElement).getContext('webgl2')
    return gl ? { version: gl.getParameter(gl.VERSION) as string, lost: gl.isContextLost() } : null
  })
  expect(renderer?.version).toContain('WebGL 2')
  expect(renderer?.lost).toBe(false)
  await expect(page.getByText('NASA texture unavailable — geometric preview only')).toHaveCount(0)
  await page.screenshot({ path: info.outputPath('Globe-equatorial.png'), fullPage: true })
  const initial = await page.getByRole('status', { name: 'Camera view' }).innerText()
  await page.getByRole('button', { name: 'Focus South Pole' }).focus()
  await page.keyboard.press('Enter')
  await expect(page.getByRole('status', { name: 'Camera view' })).toContainText('View latitude -85.5°')
  await page.screenshot({ path: info.outputPath('Globe-south.png'), fullPage: true })
  await page.getByRole('button', { name: 'Reset View' }).focus()
  await page.keyboard.press('Enter')
  await expect(page.getByRole('status', { name: 'Camera view' })).toHaveText(initial)
  expect(errors).toEqual([])
})

test('local JPEG is HTTP 200, byte-identical and browser-decodable', async ({ page, request }) => {
  const remoteRequests: string[] = []
  page.on('request', r => { if (new URL(r.url()).hostname.endsWith('nasa.gov')) remoteRequests.push(r.url()) })
  const response = await request.get('/assets/moon/lroc_color_2k.jpg')
  expect(response.status()).toBe(200)
  expect(response.headers()['content-type']).toContain('image/jpeg')
  const bytes = await response.body()
  expect(bytes.length).toBe(457942)
  expect(createHash('sha256').update(bytes).digest('hex')).toBe('f7130a1822681fa7512d7dcfd40db8c10b9ba4f06777910348698260ed7a2170')
  await ready(page)
  expect(await page.evaluate(async () => {
    const image = new Image()
    image.src = new URL('assets/moon/lroc_color_2k.jpg', document.baseURI).href
    await image.decode()
    return [image.naturalWidth, image.naturalHeight]
  })).toEqual([2048, 1024])
  expect(remoteRequests).toEqual([])
})

test('the decoded local JPEG is uploaded to the WebGL texture used by the scene', async ({ page }) => {
  await observeMoonUploads(page)
  await ready(page)
  await expect.poll(() => page.evaluate(() => (window as typeof window & { __moonUploads: number[][] }).__moonUploads)).toContainEqual([2048, 1024])
})

test('landmark selections and cardinal views support geographic visual review', async ({ page }, info) => {
  const canvas = await ready(page)
  const bounds = (await canvas.boundingBox())!
  const camera = new PerspectiveCamera(45, bounds.width / bounds.height, 0.05, 30)
  camera.position.set(3.2, 0.7, 0.8)
  camera.lookAt(0, 0, 0)
  camera.updateMatrixWorld()
  // Approximate recognizable feature locations, used for qualitative image
  // review, not an independently certified cartographic registration.
  for (const [name, latitude, longitude] of [
    ['Copernicus', 9.62, -20.08], ['Tycho', -43.31, -11.36], ['Mare-Crisium', 17, 59.1],
  ] as const) {
    if (name === 'Mare-Crisium') {
      // Bring the feature away from the perspective limb before selecting it.
      const box = (await canvas.boundingBox())!
      const current = Math.atan2(-camera.position.z, camera.position.x) * 180 / Math.PI
      const change = 30 - current
      await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2)
      await page.mouse.down()
      await page.mouse.move(box.x + box.width / 2 - change * box.height / 360, box.y + box.height / 2, { steps: 12 })
      await page.mouse.up()
      await expect(page.getByRole('status', { name: 'Camera view' })).toContainText('View longitude 30.0°')
      camera.position.applyAxisAngle(new Vector3(0, 1, 0), change * Math.PI / 180)
      camera.lookAt(0, 0, 0)
      camera.updateMatrixWorld()
    }
    const phi = latitude * Math.PI / 180, lambda = longitude * Math.PI / 180
    const point = new Vector3(Math.cos(phi) * Math.cos(lambda), Math.sin(phi), -Math.cos(phi) * Math.sin(lambda)).project(camera)
    const box = (await canvas.boundingBox())!
    await page.mouse.click(box.x + (point.x + 1) * box.width / 2, box.y + (1 - point.y) * box.height / 2)
    await expect(page.getByRole('heading', { name: 'Selected visual coordinate' })).toBeVisible()
    const actualLatitude = Number.parseFloat(await page.locator('dd').filter({ hasText: /^-?\d+\.\d{3}°$/ }).innerText())
    const signed = await page.getByText(/^Signed longitude:/).innerText()
    expect(actualLatitude).toBeCloseTo(latitude, 0)
    expect(Number(signed.match(/Signed longitude: (-?[\d.]+)/)?.[1])).toBeCloseTo(longitude, 0)
    await canvas.screenshot({ path: info.outputPath(`Landmark-${name}.png`) })
  }
  for (const longitude of [90, -90, 180]) {
    await page.getByRole('button', { name: 'Reset View' }).click()
    await canvas.scrollIntoViewIfNeeded()
    const box = (await canvas.boundingBox())!
    const current = Number((await page.getByRole('status', { name: 'Camera view' }).innerText()).match(/View longitude (-?[\d.]+)/)?.[1])
    const delta = ((longitude - current + 540) % 360) - 180
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2)
    await page.mouse.down()
    await page.mouse.move(box.x + box.width / 2 - delta * box.height / 360, box.y + box.height / 2, { steps: 16 })
    await page.mouse.up()
    await expect.poll(async () => {
      const actual = Number((await page.getByRole('status', { name: 'Camera view' }).innerText()).match(/View longitude (-?[\d.]+)/)?.[1])
      return Math.abs(((actual - longitude + 540) % 360) - 180)
    }).toBeLessThan(1)
    await canvas.screenshot({ path: info.outputPath(`Longitude-${longitude}.png`) })
  }
})

test('failed JPEG load retains a working neutral sphere and honest fallback', async ({ page }, info) => {
  await page.route('**/assets/moon/lroc_color_2k.jpg', route => route.fulfill({ status: 404, body: 'missing test asset' }))
  await page.goto('/')
  await expect(page.getByRole('status', { name: 'Camera view' })).toContainText('3D scene ready')
  await expect(page.getByText('NASA texture unavailable — geometric preview only')).toBeVisible()
  await expect(page.getByText('NASA color texture loaded — visual imagery only')).toHaveCount(0)
  await page.getByRole('button', { name: 'Focus South Pole' }).click()
  await expect(page.getByRole('status', { name: 'Camera view' })).toContainText('View latitude -85.5°')
  await page.getByRole('button', { name: 'Reset View' }).click()
  await expect(page.getByRole('status', { name: 'Camera view' })).toContainText('View latitude 12.0°')
  await page.screenshot({ path: info.outputPath('Globe-missing-texture.png'), fullPage: true })
})

test('loading texture never announces success prematurely', async ({ page }) => {
  await observeMoonUploads(page)
  let release!: () => void
  const gate = new Promise<void>(resolve => { release = resolve })
  await page.route('**/assets/moon/lroc_color_2k.jpg', async route => {
    await gate
    await route.continue()
  })
  try {
    await page.goto('/')
    await expect(page.getByText('Loading NASA texture…')).toBeVisible()
    await expect(page.getByRole('status', { name: 'Camera view' })).toContainText('3D scene ready')
    // Force an actual first draw with the neutral material before releasing the JPEG.
    await page.locator('canvas').screenshot()
    await expect(page.getByText('NASA color texture loaded — visual imagery only')).toHaveCount(0)
  } finally { release() }
  await expect(page.getByText('NASA color texture loaded — visual imagery only')).toBeVisible()
  await expect.poll(() => page.evaluate(() => (window as typeof window & { __moonUploads: number[][] }).__moonUploads)).toContainEqual([2048, 1024])
})

test('drag rotates without selecting and wheel zoom remains outside the sphere', async ({ page }) => {
  const canvas = await ready(page)
  const bounds = (await canvas.boundingBox())!
  const initial = await page.getByRole('status', { name: 'Camera view' }).innerText()
  await page.mouse.move(bounds.x + bounds.width / 2, bounds.y + bounds.height / 2)
  await page.mouse.down()
  await page.mouse.move(bounds.x + bounds.width / 2 + 70, bounds.y + bounds.height / 2 + 15, { steps: 12 })
  await page.mouse.up()
  await expect(page.getByRole('status', { name: 'Camera view' })).not.toHaveText(initial)
  await expect(page.getByText('No surface point selected')).toBeVisible()
  // A drag returning to its start is still a drag, not a surface click.
  await page.mouse.move(bounds.x + bounds.width / 2, bounds.y + bounds.height / 2)
  await page.mouse.down()
  await page.mouse.move(bounds.x + bounds.width / 2 + 50, bounds.y + bounds.height / 2, { steps: 8 })
  await page.mouse.move(bounds.x + bounds.width / 2, bounds.y + bounds.height / 2, { steps: 8 })
  await page.mouse.up()
  await expect(page.getByText('No surface point selected')).toBeVisible()
  const beforeZoom = await distance(page)
  await page.mouse.wheel(0, -500)
  await expect.poll(() => distance(page)).toBeLessThan(beforeZoom)
  await page.mouse.wheel(0, -12000)
  await expect.poll(() => distance(page)).toBe(1.45)
  await page.mouse.wheel(0, 20000)
  await expect.poll(() => distance(page)).toBe(6)
})

test('raycasting selects a finite coordinate and marker persists through camera changes', async ({ page }, info) => {
  const canvas = await ready(page)
  const bounds = (await canvas.boundingBox())!
  await page.mouse.click(bounds.x + bounds.width / 2, bounds.y + bounds.height / 2)
  await expect(page.getByRole('heading', { name: 'Selected visual coordinate' })).toBeVisible()
  const latitude = page.locator('dd').filter({ hasText: /^-?\d+\.\d{3}°$/ })
  await expect(latitude).toHaveCount(1)
  const selected = await latitude.innerText()
  expect(Number.parseFloat(selected)).toBeGreaterThan(-90)
  expect(Number.parseFloat(selected)).toBeLessThan(90)
  await page.screenshot({ path: info.outputPath('Globe-selection.png'), fullPage: true })
  await page.getByRole('button', { name: 'Focus South Pole' }).click()
  await expect(latitude).toHaveText(selected)
  await page.getByRole('button', { name: 'Reset View' }).click()
  await expect(latitude).toHaveText(selected)
  await page.getByRole('navigation').getByRole('link', { name: 'Mission Analysis' }).click()
  await expect(page.getByLabel('Interactive 3D lunar sphere')).toHaveCount(0)
  await expect(page.getByLabel('Interactive local horizon sky')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Local Horizon', exact: true })).toBeVisible()
})

test('WebGL unavailability leaves navigation and scientific empty states usable', async ({ page }) => {
  await page.addInitScript(() => {
    const original = HTMLCanvasElement.prototype.getContext
    HTMLCanvasElement.prototype.getContext = function (this: HTMLCanvasElement, ...args: Parameters<typeof original>) {
      if (String(args[0]).startsWith('webgl')) return null
      return original.apply(this, args)
    } as typeof original
  })
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'WebGL unavailable' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Loading 3D scene' })).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Reset View' })).toBeDisabled()
  await page.getByRole('navigation').getByRole('link', { name: 'Alternative Explorer' }).click()
  await expect(page.getByRole('heading', { name: 'Alternative Explorer', level: 1 })).toBeVisible()
})

test('context loss is explicit and releases the Canvas', async ({ page }) => {
  const canvas = await ready(page)
  await canvas.evaluate(element => {
    const gl = (element as HTMLCanvasElement).getContext('webgl2')
    const extension = gl?.getExtension('WEBGL_lose_context')
    if (!extension) throw new Error('Context-loss extension unavailable')
    extension.loseContext()
  })
  await expect(page.getByRole('heading', { name: 'WebGL context lost' })).toBeVisible()
  await expect(page.locator('canvas')).toHaveCount(0)
})
