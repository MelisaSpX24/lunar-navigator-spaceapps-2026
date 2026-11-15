import {expect,expectTypeOf,it} from 'vitest'
import {SITE_CATALOG} from './siteCatalog'
import {SOURCES} from './sourceEvidence'
import {analysisCoordinate,sourceLongitudeEast,transferReason,visualSiteCoordinate} from './siteValidation'
import type {AnalysisCoordinate,SourceReferenceCoordinate} from './siteTypes'
const ridge=SITE_CATALOG[0]!,rim=SITE_CATALOG[1]!,mouton=SITE_CATALOG[2]!,plateau=SITE_CATALOG[3]!,cr1=SITE_CATALOG[4]!
it('records external Data Book R01/R04 coordinates with exact source section and unknown latitude convention',()=>{
 expect(ridge.sourceCoordinate).toMatchObject({kind:'SOURCE_REFERENCE',objectId:'R01 / Site01',latitude:-89.4632,longitude:-137.49,latitudeType:'UNKNOWN',review:'NOT_REVERIFIED_IN_TASK'})
 expect(rim.sourceCoordinate).toMatchObject({objectId:'R04 / Site04',latitude:-89.7668,longitude:-171.87})
 for(const site of [ridge,rim]){
  expect(site.sourceCoordinate!.section).toContain('58–59')
  expect(site.sourceCoordinate!.frame).toBe('MOON_ME_DE421_REPORTED_VIA_DEM')
  expect(visualSiteCoordinate(site)).toBeNull();expect(analysisCoordinate(site)).toBeNull()
 }
})
it('does not equate source R01 centre with the CR1 research input',()=>{
 expect(ridge.id).not.toBe(cr1.id)
 expect(sourceLongitudeEast(ridge.sourceCoordinate!)).toBeCloseTo(222.51,10)
 expect(cr1.coordinate!.longitude).toBe(222.6)
 expect(cr1.coordinate!.latitude).not.toBe(ridge.sourceCoordinate!.latitude)
})
it.each([[-137.49,222.51],[-171.87,188.13],[-180,180],[180,180],[0,0],[31,31]])('converts signed east representation %s to %s only', (longitude,expected)=>{
 expect(sourceLongitudeEast({...ridge.sourceCoordinate!,longitude})).toBeCloseTo(expected,10)
})
it.each([-181,181,360,NaN,Infinity])('rejects invalid signed source longitude %s without normalization',longitude=>{
 expect(sourceLongitudeEast({...ridge.sourceCoordinate!,longitude})).toBeNull()
})
it('rejects 360 in positive-east source convention and unknown convention',()=>{
 expect(sourceLongitudeEast({...ridge.sourceCoordinate!,longitude:360,longitudeConvention:'EAST_0_360'})).toBeNull()
 expect(sourceLongitudeEast({...ridge.sourceCoordinate!,longitude:0,longitudeConvention:'EAST_0_360'})).toBe(0)
 expect(sourceLongitudeEast({...ridge.sourceCoordinate!,longitudeConvention:'UNKNOWN'})).toBeNull()
})
it('keeps planetographic Mons Mouton and LOLA 2011 source metadata out of planetocentric analysis',()=>{
 expect(mouton.sourceCoordinate).toMatchObject({latitude:-84.6,longitude:31,latitudeType:'PLANETOGRAPHIC',controlNetwork:'LOLA 2011 (user-reported)',frame:'UNKNOWN'})
 expect(analysisCoordinate(mouton)).toBeNull();expect(visualSiteCoordinate(mouton)).toBeNull()
 expectTypeOf<SourceReferenceCoordinate>().not.toMatchTypeOf<AnalysisCoordinate>()
})
it('a runtime source-coordinate substitution also fails the research-input gate',()=>{
 const bad={...mouton,coordinate:{...cr1.coordinate!,kind:'SOURCE_REFERENCE'}}
 // Deliberately malformed network-like input: compile-time rejection must also be guarded at runtime.
 expect(transferReason(bad)).not.toBeNull()
})
it('keeps historical membership per supplied dated announcement, without inventing Shackleton/CR1 membership',()=>{
 expect(ridge.historicalCandidate).toMatchObject({year:2022,date:'2022-08-19',review:'NOT_REVERIFIED_IN_TASK'})
 for(const site of [mouton,plateau])expect(site.historicalCandidate).toMatchObject({year:2024,date:'2024-10-28'})
 expect(rim.historicalCandidate).toBeNull();expect(cr1.historicalCandidate).toBeUndefined()
 expect(plateau.sourceCoordinate).toBeNull()
 expect(rim.context).toContain('Distinct from Shackleton Rim B and Peak Near Shackleton')
})
it('preserves previous 403 history and current failed review without promoting user findings',()=>{
 expect(SOURCES.book.history).toContain('Command 10: BLOCKED_403 (2026-11-15)')
 expect(SOURCES.pgda81.history[0]).toContain('first GET attempt')
 for(const source of Object.values(SOURCES)){
  expect(source.access).toBe('BLOCKED_403');expect(source.review).toBe('NOT_REVERIFIED_IN_TASK')
  expect(source.reviewedOn).toBe('2026-11-15')
 }
 expect(SITE_CATALOG.every(s=>analysisCoordinate(s)===null)).toBe(true)
 expect(SITE_CATALOG.every(s=>transferReason(s)!==null)).toBe(true)
})
it('only an independently evidence-verified research input can produce an analysis coordinate',()=>{
 const site={...cr1,coordinate:{...cr1.coordinate!,compatibility:'VERIFIED' as const,coordinateEvidence:{objectId:cr1.id,sourceUrl:cr1.sources[0]!.url,review:'DIRECTLY_REVIEWED' as const,latitudeTypeVerified:true as const,frameVerified:true as const}},sources:[{...cr1.sources[0]!,access:'VERIFIED' as const,review:'DIRECTLY_REVIEWED' as const}]}
 expect(analysisCoordinate(site)).toEqual({kind:'ANALYSIS_INPUT',latitude_deg:-89.468,longitude_deg_east:222.6,frame:'MOON_ME_DE421',latitude_type:'PLANETOCENTRIC'})
 site.coordinate.frame='UNKNOWN';expect(analysisCoordinate(site)).toBeNull()
})
it('requires directly reviewed evidence bound to the same object, source URL, latitude and frame',()=>{
 const site={...cr1,coordinate:{...cr1.coordinate!,compatibility:'VERIFIED' as const},sources:[{...cr1.sources[0]!,access:'VERIFIED' as const,review:'DIRECTLY_REVIEWED' as const}]}
 expect(analysisCoordinate(site)).toBeNull() // A flag is not an evidence chain.
 const proof={objectId:site.id,sourceUrl:site.sources[0]!.url,review:'DIRECTLY_REVIEWED' as const,latitudeTypeVerified:true as const,frameVerified:true as const}
 site.coordinate={...site.coordinate,coordinateEvidence:proof} as typeof site.coordinate
 expect(analysisCoordinate(site)).not.toBeNull()
 for(const patch of [{objectId:'different-feature'},{sourceUrl:SOURCES.usgs.url},{review:'NOT_REVERIFIED_IN_TASK'},{latitudeTypeVerified:false},{frameVerified:false}]){
  const bad={...site,coordinate:{...site.coordinate,coordinateEvidence:{...proof,...patch}}}
  expect(analysisCoordinate(bad)).toBeNull()
 }
})
