import { readFileSync } from 'node:fs'
import {expect,it} from 'vitest'
import {SOURCES,DATA_BOOK_COMPARISON} from './sourceEvidence'
import {SITE_CATALOG} from './siteCatalog'
import {analysisCoordinate,transferReason,visualSiteCoordinate,validNumericCoordinate,matchesSite} from './siteValidation'
const requests=JSON.parse(readFileSync('evidence/command-10-final-retrieval.json','utf8')) as {id:string;url:string;origin_status:number|null;tunnel_status?:number;bytes:number}[]
it('evaluates actual retrieval records as NOT VERIFIED rather than successful NASA inspection',()=>{
 expect(requests).toHaveLength(13)
 expect(new Set(requests.map(r=>r.url)).size).toBe(13)
 for(const r of requests){expect(r.bytes).toBe(0);expect(r.origin_status).toBeNull();expect(r.tunnel_status).toBe(403)}
 for(const source of Object.values(SOURCES)){
  expect(requests.some(r=>r.url===source.url)).toBe(true)
  expect(source.review).toBe('NOT_REVERIFIED_IN_TASK')
  expect(source.provenance).toBe('EXTERNAL_RESEARCH_REFERENCED')
 }
})
it('records all eleven official source groups and precise external versions/sections without upgrading proof',()=>{
 expect(Object.keys(SOURCES)).toHaveLength(11)
 expect(SOURCES.book).toMatchObject({documentId:'20230007818',version:'ACD-50044 Revision A (2023)'})
 expect(SOURCES.book.section).toContain('58–59')
 expect(SOURCES.book2025).toMatchObject({documentId:'20250002845',version:'M2M-30044 Baseline (2025)'})
 expect(SOURCES.book2025.section).toContain('A2.1-1, page 75')
 expect(SOURCES.lro.version).toContain('14 May 2008')
 expect(SOURCES.lro.section).toContain('5.0, 6.0, 6.1')
 expect(SOURCES.book2022.documentId).toBe('20220015275')
 expect(SOURCES.book2022.section).toContain('C1 / CR1')
 expect(DATA_BOOK_COMPARISON.directComparison).toBe('NOT_VERIFIED')
 expect(DATA_BOOK_COMPARISON.numericalDifference).toBe('NOT_VERIFIED')
 expect(DATA_BOOK_COMPARISON.authoritativeSourceForTransfer).toBe('UNRESOLVED')
})
it('provides object-specific unlock instructions for all five current locked production records',()=>{
 for(const site of SITE_CATALOG){
  expect(site.unlockRequirements!.length).toBeGreaterThanOrEqual(2)
  expect(site.unlockRequirements!.join(' ')).toMatch(/latitude|frame/)
  expect(transferReason(site)).not.toBeNull();expect(analysisCoordinate(site)).toBeNull()
 }
 expect(SITE_CATALOG[0]!.unlockRequirements!.join(' ')).toContain('R01')
 expect(SITE_CATALOG[1]!.unlockRequirements!.join(' ')).toContain('R04')
 expect(SITE_CATALOG[2]!.unlockRequirements!.join(' ')).toContain('planetographic')
 expect(SITE_CATALOG[4]!.sources.some(s=>s.documentId==='20220015275')).toBe(true)
})
it.each([null,undefined,{},[],{coordinate:{}},{coordinate:{evidence:55}},{coordinate:'bad'},{coordinate:{kind:'SOURCE_REFERENCE'}}])('rejects malformed untyped input %j without crashing',bad=>{
 expect(()=>transferReason(bad)).not.toThrow()
 expect(transferReason(bad)).not.toBeNull();expect(analysisCoordinate(bad)).toBeNull();expect(visualSiteCoordinate(bad)).toBeNull();expect(validNumericCoordinate(bad)).toBe(false)
})
it.each(['IAU_MOON','MOON_PA_DE421','EPSG:4326','UNKNOWN'])('rejects incompatible frame %s even with a forged verification flag',frame=>{
 const site=SITE_CATALOG[4]!,bad={...site,coordinate:{...site.coordinate!,compatibility:'VERIFIED',frame}}
 expect(analysisCoordinate(bad)).toBeNull();expect(visualSiteCoordinate(bad)).toBeNull()
})
it('rejects malformed proof/source values and non-string evidence safely',()=>{
 const s=SITE_CATALOG[4]!
 const base={...s,coordinate:{...s.coordinate!,compatibility:'VERIFIED',coordinateEvidence:{objectId:s.id,sourceUrl:s.sources[0]!.url,review:'DIRECTLY_REVIEWED',latitudeTypeVerified:true,frameVerified:true}}}
 for(const sources of [null,{},[null],[{section:12,url:[]}]])expect(analysisCoordinate({...base,sources})).toBeNull()
 expect(analysisCoordinate({...base,coordinate:{...base.coordinate,evidence:13}})).toBeNull()
 expect(matchesSite(s,'-89.468','0xde.9')).toBe(false)
})
