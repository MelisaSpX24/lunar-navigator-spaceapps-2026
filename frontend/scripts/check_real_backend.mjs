// Unmocked HTTP + Chromium evidence. Requires the documented isolated backend
// and Vite development proxy; never supplies a runner or source/test data.
import { chromium, expect } from '@playwright/test'
import { mkdir, writeFile } from 'node:fs/promises'
const base=process.env.LUNAR_FRONTEND_URL||'http://127.0.0.1:5174'
const browser=await chromium.launch({executablePath:process.env.TEST_BROWSER_PATH||'/usr/bin/chromium'})
const output='.validation/command11-real-browser';await mkdir(output,{recursive:true})
const report=[]
try {
for(const [name,width,height] of [['desktop',1440,1000],['tablet',820,1180],['mobile',390,844]]){
 const context=await browser.newContext({viewport:{width,height},isMobile:name==='mobile',hasTouch:name==='mobile'})
 const page=await context.newPage(), errors=[];page.setDefaultTimeout(15000);page.on('pageerror',e=>errors.push(e.message))
 await page.goto(base)
 const backend=page.getByRole('region',{name:'Scientific Backend',exact:true})
 await expect(backend).toContainText('SCIENCE_SOURCES_NOT_CONFIGURED')
 await page.getByLabel('Latitude (degrees)',{exact:true}).fill('-89.468')
 await page.getByLabel('Longitude (degrees east)',{exact:true}).fill('222.6')
 await page.getByLabel('UTC date',{exact:true}).fill('2026-11-20')
 await page.getByLabel('UTC time',{exact:true}).fill('08:00')
 await page.getByLabel('Hours',{exact:true}).fill('6')
 await page.getByLabel('Minimum Sun visibility (seconds)',{exact:true}).fill('600')
 await page.getByText('Advanced settings',{exact:true}).click()
 await page.getByLabel('Include full horizon profile',{exact:true}).uncheck()
 await page.getByLabel('Research execution mode',{exact:true}).selectOption('recorded')
 await expect(page.getByRole('button',{name:'Run Analysis',exact:true})).toBeDisabled()
 await expect(page.getByRole('button',{name:'Run Research Prototype',exact:true})).toBeEnabled()
 const response=page.waitForResponse(r=>r.url().includes('/analyses?mode=recorded'))
 await page.getByRole('button',{name:'Run Research Prototype',exact:true}).click()
 const raw=await response;expect(raw.status()).toBe(200)
 const data=await raw.json();expect(data.data_origin).toBe('PRECOMPUTED')
 await expect(backend).toContainText('PRECOMPUTED — exact-match recorded research response')
 await page.getByRole('link',{name:'View research results in Mission Analysis',exact:true}).click()
 await expect(page.getByLabel('Backend planning score')).toContainText('/ 100')
 await expect(page.getByRole('region',{name:'Local Horizon',exact:true})).toContainText('not calculated')
 for(const body of ['Sun Visibility','Earth Visibility'])await expect(page.getByRole('region',{name:body,exact:true}).getByRole('table')).toBeVisible()
 await expect(page.locator('#prototype-limitations')).toContainText('independent astronomical validation remain incomplete')
 await expect(page.getByLabel('Local camera orientation',{exact:true})).toContainText('Local 3D scene ready')
 await page.getByRole('button',{name:'Look South',exact:true}).click()
 await page.getByRole('region',{name:'Interactive 3D Horizon',exact:true}).screenshot({path:`${output}/${name}-recorded-3d.png`})
 await page.screenshot({path:`${output}/${name}-recorded-analysis.png`,fullPage:true})
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
 if(name==='mobile'){await page.evaluate(()=>document.documentElement.style.fontSize='200%');expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await backend.screenshot({path:`${output}/mobile-200percent.png`})}
 expect(errors).toEqual([])
 report.push({viewport:name,recorded_status:raw.status(),data_origin:data.data_origin,execution:data.execution_status,score:data.score.value,series:data.series.length,horizons:data.horizons,page_errors:errors,network:'unmocked isolated backend + Vite proxy'})
 await context.close()
}
await writeFile(`${output}/report.json`,JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2))
}finally{await browser.close()}
