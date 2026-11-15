import { expect,it } from 'vitest'
import { SITE_CATALOG } from './siteCatalog'
import { matchesSite, transferReason, validNumericCoordinate, visualSiteCoordinate } from './siteValidation'
import type { LunarSite } from './siteTypes'
import { safeSourceUrl } from '../analysis-results/validation'
import { toCartesian,fromCartesian } from '../../visualization/coordinates/lunarCoordinates'
const cr1=SITE_CATALOG[4]!
const verified=():LunarSite=>({...cr1,coordinate:{...cr1.coordinate!,compatibility:'VERIFIED',coordinateEvidence:{objectId:cr1.id,sourceUrl:cr1.sources[0]!.url,review:'DIRECTLY_REVIEWED',latitudeTypeVerified:true,frameVerified:true}},sources:[{...cr1.sources[0]!,access:'VERIFIED',review:'DIRECTLY_REVIEWED'}]}) // Test-only policy evidence; never a production site.
it('retains unique regions and a separate research point, with no unsupported analysis-ready claim',()=>{
 expect(new Set(SITE_CATALOG.map(s=>s.id)).size).toBe(5)
 expect(SITE_CATALOG.filter(s=>s.kind==='REGION')).toHaveLength(4)
 expect(cr1.kind).toBe('RESEARCH_POINT')
 expect(SITE_CATALOG.every(s=>transferReason(s)!==null)).toBe(true)
 expect(SITE_CATALOG.slice(0,4).every(s=>s.coordinate===null)).toBe(true)
})
it('keeps blocked retrieval history distinct from externally reported publication dates',()=>{
 for(const site of SITE_CATALOG){
  for(const source of site.sources){expect(safeSourceUrl(source.url)).toBe(source.url);expect(source.access).toBe('BLOCKED_403');expect(source.review).toBe('NOT_REVERIFIED_IN_TASK');expect(source.history?.some(h=>h.includes('403'))).toBe(true)}
 }
 expect(SITE_CATALOG[0]!.historicalCandidate?.date).toBe('2022-08-19')
 expect(SITE_CATALOG[0]!.context).toContain('No 2024 membership')
})
it('permits a documented visual reference without promoting unverified registration to coordinate transfer',()=>{
 expect(visualSiteCoordinate(cr1)).toEqual({latitude:-89.468,longitude:-137.39999999999998,radius:1})
 expect(transferReason(cr1)).toContain('NOT VERIFIED')
 const v=visualSiteCoordinate(cr1)!,p=toCartesian(v.latitude,v.longitude!)
 expect(fromCartesian(p).latitude).toBeCloseTo(-89.468,8)
 expect(p.y).toBeLessThan(0);expect(p.z).toBeGreaterThan(0)
})
it.each([-90,90,NaN,Infinity])('rejects latitude %s',latitude=>{
 const s=verified();s.coordinate!.latitude=latitude
 expect(validNumericCoordinate(s)).toBe(false);expect(transferReason(s)).not.toBeNull();expect(visualSiteCoordinate(s)).toBeNull()
})
it.each([-20,360,Infinity,NaN])('rejects rather than silently normalizing catalog longitude %s',longitude=>{
 const s=verified();s.coordinate!.longitude=longitude
 expect(validNumericCoordinate(s)).toBe(false);expect(visualSiteCoordinate(s)).toBeNull()
})
it.each([0,30,180,270,359.9])('uses east-positive longitude %s through the existing adapter',longitude=>{
 const s=verified();s.coordinate!.longitude=longitude
 expect(transferReason(s)).toBeNull()
 const c=visualSiteCoordinate(s)!
 expect(((c.longitude!%360)+360)%360).toBeCloseTo(longitude)
})
it.each(['PLANETOGRAPHIC','UNKNOWN'] as const)('blocks %s latitude even with positive east longitude',latitudeType=>{
 const s=verified();s.coordinate!.latitudeType=latitudeType
 expect(visualSiteCoordinate(s)).toBeNull();expect(transferReason(s)).not.toBeNull()
})
it('requires frame, convention, actual evidence and reviewed primary source',()=>{
 for(const update of [{frame:'UNKNOWN'},{longitudeConvention:'SIGNED_EAST'},{longitudeConvention:'UNKNOWN'},{evidence:null}] as const){
  const s=verified();s.coordinate={...s.coordinate!,...update};expect(transferReason(s)).not.toBeNull()
 }
 const s=verified();s.sources=[];expect(transferReason(s)).toContain('primary-source')
 s.sources=[{...cr1.sources[0]!,access:'VERIFIED',url:'javascript:alert(1)'}];expect(transferReason(s)).not.toBeNull()
})
it('clears exact catalog association on manual edit/reset and never associates unverified CR1',()=>{
 const s=verified();expect(matchesSite(s,'-89.468','222.6')).toBe(true)
 for(const [a,b] of [['-89','222.6'],['',''],['-89.468','-137.4']])expect(matchesSite(s,a!,b!)).toBe(false)
 expect(matchesSite(cr1,'-89.468','222.6')).toBe(false)
})
