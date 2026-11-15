import { test, expect, type Page } from '@playwright/test'

// Regression coverage uses a controlled health response; live integration is checked separately.
test.beforeEach(async ({ page }) => {
  await page.route('**/api/v1/health', route => route.fulfill({ json: {status:'ok',science_ready:false,dem_ready:false,kernels_ready:false,reason_codes:['SCIENCE_ENGINE_NOT_READY']} }))
})

async function distance(page: Page) {
  const text = await page.getByRole('status', { name: 'Camera view' }).innerText()
  return Number(text.match(/Camera distance ([\d.]+)/)?.[1])
}

test('touch mode lets page scrolling resume after interaction is paused', async ({ page, browserName }) => {
  expect(browserName).toBe('chromium')
  await page.goto('/')
  await expect(page.getByRole('status', { name: 'Camera view' })).toContainText('3D scene ready')
  await page.getByRole('button', { name: 'Enable globe interaction' }).click()
  const canvas = page.locator('canvas')
  await canvas.scrollIntoViewIfNeeded()
  const bounds = (await canvas.boundingBox())!
  const x = bounds.x + bounds.width / 2, y = bounds.y + bounds.height / 2
  const before = await page.getByRole('status', { name: 'Camera view' }).innerText()
  const cdp = await page.context().newCDPSession(page)
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x, y, id: 0 }] })
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x: x + 50, y: y + 20, id: 0 }] })
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] })
  await expect(page.getByRole('status', { name: 'Camera view' })).not.toHaveText(before)
  const beforePinch = await distance(page)
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: x - 20, y, id: 0 }, { x: x + 20, y, id: 1 }] })
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x: x - 55, y, id: 0 }, { x: x + 55, y, id: 1 }] })
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] })
  await expect.poll(() => distance(page)).toBeLessThan(beforePinch)
  await page.getByRole('button', { name: 'Reset View' }).click()
  await canvas.tap()
  await expect(page.getByRole('heading', { name: 'Selected visual coordinate' })).toBeVisible()
  await page.getByRole('button', { name: 'Pause globe interaction' }).click()
  await canvas.scrollIntoViewIfNeeded()
  const position = (await canvas.boundingBox())!
  const scroll = await page.evaluate(() => scrollY)
  const startY = position.y + 200
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x, y: startY, id: 0 }] })
  // Allow compositor frames between moves, as a real swipe does. An instant
  // start/move/end sequence is insufficient to exercise native page scrolling.
  for (let step = 1; step <= 8; step++) {
    await page.evaluate(() => new Promise(resolve => requestAnimationFrame(resolve)))
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x, y: startY - step * 20, id: 0 }] })
  }
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] })
  await expect.poll(() => page.evaluate(() => scrollY)).toBeGreaterThan(scroll)
  await cdp.detach()
})

test('local horizon touch rotation and pinch work; pause restores page swipes', async ({page}) => {
  await page.goto('/#/analysis')
  const readout=page.getByRole('status',{name:'Local camera orientation'})
  await expect(readout).toContainText('Local 3D scene ready')
  await page.getByRole('button',{name:'Enable 3D interaction',exact:true}).click()
  const canvas=page.getByLabel('Interactive local horizon sky',{exact:true}).locator('canvas')
  await canvas.scrollIntoViewIfNeeded();const b=(await canvas.boundingBox())!,x=b.x+b.width/2,y=b.y+b.height/2
  const cdp=await page.context().newCDPSession(page)
  await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x,y,id:0}]})
  await cdp.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:x+40,y:y+20,id:0}]})
  await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]})
  await expect(readout).not.toContainText('Azimuth 0.0°')
  await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:x-20,y,id:0},{x:x+20,y,id:1}]})
  await cdp.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:x-50,y,id:0},{x:x+50,y,id:1}]})
  await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]})
  await expect.poll(async()=>Number((await readout.innerText()).match(/FOV ([\d.]+)/)?.[1])).toBeLessThan(75)
  await page.getByRole('button',{name:'Pause 3D interaction',exact:true}).click()
  await canvas.scrollIntoViewIfNeeded();const box=(await canvas.boundingBox())!,scroll=await page.evaluate(()=>scrollY),startY=box.y+200
  await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x,y:startY,id:0}]})
  for(let step=1;step<=8;step++){
    await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(resolve)))
    await cdp.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x,y:startY-step*20,id:0}]})
  }
  await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]})
  await expect.poll(()=>page.evaluate(()=>scrollY)).toBeGreaterThan(scroll)
  await cdp.detach()
})
