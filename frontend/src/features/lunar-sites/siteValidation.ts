import { eastLongitudeToVisual, visualLongitudeToEast } from '../mission-input/coordinates'
import { finiteDecimal } from '../mission-input/missionState'
import { safeSourceUrl } from '../analysis-results/validation'
import type { AnalysisCoordinate, LunarSite, SiteCoordinate, SourceReferenceCoordinate } from './siteTypes'
import type { VisualCoordinate } from '../../visualization/coordinates/lunarCoordinates'
const record=(value:unknown):value is Record<string,unknown>=>typeof value==='object'&&value!==null&&!Array.isArray(value)
const nonempty=(value:unknown):value is string=>typeof value==='string'&&value.trim().length>0
function researchInput(site:unknown):SiteCoordinate|null {
 if(!record(site)||!record(site.coordinate))return null
 const c=site.coordinate
 if(c.kind!=='RESEARCH_INPUT'||typeof c.latitude!=='number'||!Number.isFinite(c.latitude)||c.latitude<=-90||c.latitude>=90||typeof c.longitude!=='number'||!Number.isFinite(c.longitude)||c.longitude<0||c.longitude>=360)return null
 if(c.latitudeType!=='PLANETOCENTRIC'||c.longitudeConvention!=='EAST_0_360'||c.frame!=='MOON_ME_DE421'||c.visualReference!==true||!nonempty(c.evidence))return null
 if(c.compatibility!=='VERIFIED'&&c.compatibility!=='NOT_VERIFIED')return null
 return c as SiteCoordinate
}
export function validNumericCoordinate(site:unknown) {
 if(!record(site)||!record(site.coordinate))return false
 const c=site.coordinate
 return typeof c.latitude==='number'&&typeof c.longitude==='number'&&Number.isFinite(c.latitude)&&c.latitude>-90&&c.latitude<90&&Number.isFinite(c.longitude)&&c.longitude>=0&&c.longitude<360
}
export function visualSiteCoordinate(site:unknown):VisualCoordinate|null {
 const c=researchInput(site)
 return c?{latitude:c.latitude,longitude:eastLongitudeToVisual(c.longitude),radius:1}:null
}
export function transferReason(site:unknown):string|null {
 const c=researchInput(site)
 if(!c)return 'Source coordinates are not yet verified for the required lunar reference frame.'
 if(c.compatibility!=='VERIFIED')return 'Independent coordinate provenance and frame registration are NOT VERIFIED. Visual exploration only.'
 const proof:unknown=c.coordinateEvidence
 if(!record(site)||!nonempty(site.id)||!record(proof)||proof.objectId!==site.id||proof.review!=='DIRECTLY_REVIEWED'||proof.latitudeTypeVerified!==true||proof.frameVerified!==true||!Array.isArray(site.sources)||!site.sources.some((s:unknown)=>record(s)&&s.url===proof.sourceUrl&&s.access==='VERIFIED'&&s.review==='DIRECTLY_REVIEWED'&&typeof s.url==='string'&&safeSourceUrl(s.url)&&nonempty(s.section)))return 'Verified primary-source coordinate evidence tied to this object, latitude type and frame is required before transfer.'
 return null
}
export function matchesSite(site:LunarSite,latitude:string,longitude:string) {
 if(transferReason(site)!==null)return false
 const a=finiteDecimal(latitude),b=finiteDecimal(longitude)
 // Only adapter roundoff, never a geographic search radius or snapping.
 return a!==null&&b!==null&&Math.abs(a-site.coordinate!.latitude)<=1e-12&&Math.abs(b-site.coordinate!.longitude)<=1e-12
}
/** Representation only. Never a latitude/frame transformation. */
export function sourceLongitudeEast(c:SourceReferenceCoordinate):number|null {
 if(!record(c)||c.kind!=='SOURCE_REFERENCE'||typeof c.longitude!=='number'||!Number.isFinite(c.longitude))return null
 if(c.longitudeConvention==='EAST_0_360')return c.longitude>=0&&c.longitude<360?c.longitude:null
 if(c.longitudeConvention==='SIGNED_EAST'&&c.longitude>=-180&&c.longitude<=180)return visualLongitudeToEast(c.longitude)
 return null
}
export function analysisCoordinate(site:unknown):AnalysisCoordinate|null {
 if(transferReason(site)!==null)return null
 const c=researchInput(site)!
 return {kind:'ANALYSIS_INPUT',latitude_deg:c.latitude,longitude_deg_east:c.longitude,frame:'MOON_ME_DE421',latitude_type:'PLANETOCENTRIC'}
}
