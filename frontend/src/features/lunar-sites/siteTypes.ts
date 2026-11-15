export type SiteSource = { name: string; url: string; referenceYear: number | null; publicationDate: string | null; access: 'BLOCKED_403' | 'REPOSITORY_REVIEWED' | 'VERIFIED'; section: string; documentId?: string; version?: string; provenance?: 'EXTERNAL_RESEARCH_REFERENCED' | 'DIRECTLY_REVIEWED'; review?: 'NOT_REVERIFIED_IN_TASK' | 'DIRECTLY_REVIEWED'; reviewedOn?: string; history?: readonly string[] }
export type SiteCoordinate = {
  kind: 'RESEARCH_INPUT'
  latitude: number; longitude: number
  latitudeType: 'PLANETOCENTRIC' | 'PLANETOGRAPHIC' | 'UNKNOWN'
  longitudeConvention: 'EAST_0_360' | 'SIGNED_EAST' | 'UNKNOWN'
  frame: 'MOON_ME_DE421' | 'UNKNOWN'
  compatibility: 'VERIFIED' | 'NOT_VERIFIED'
  evidence: string | null
  coordinateEvidence?: { objectId: string; sourceUrl: string; review: 'DIRECTLY_REVIEWED'; latitudeTypeVerified: true; frameVerified: true }
  visualReference: boolean
}
export type LunarSite = {
  id: string; name: string; kind: 'REGION' | 'RESEARCH_POINT'; description: string
  coordinate: SiteCoordinate | null; sources: readonly SiteSource[]
  sourceCoordinate?: SourceReferenceCoordinate | null
  historicalCandidate?: {year:2022|2024;date:string;sourceUrl:string;review:'NOT_REVERIFIED_IN_TASK'|'DIRECTLY_REVIEWED'} | null
  unlockRequirements?: readonly string[]
  context: string; coverage: 'UNKNOWN' | 'LOCAL_EVIDENCE_LIMITED'; limitations: readonly string[]
}

/** Source values must not be assigned to analysis input fields without evidence. */
export type SourceReferenceCoordinate = {
  kind: 'SOURCE_REFERENCE'; objectId: string; latitude: number; longitude: number
  latitudeType: 'PLANETOCENTRIC' | 'PLANETOGRAPHIC' | 'UNKNOWN'
  longitudeConvention: 'SIGNED_EAST' | 'EAST_0_360' | 'UNKNOWN'
  frame: 'MOON_ME_DE421' | 'MOON_ME_DE421_REPORTED_VIA_DEM' | 'UNKNOWN'
  controlNetwork: string | null; sourceUrl: string; section: string
  review: 'NOT_REVERIFIED_IN_TASK' | 'DIRECTLY_REVIEWED'
  precisionNote: string
}
export type AnalysisCoordinate = {
  kind: 'ANALYSIS_INPUT'; latitude_deg: number; longitude_deg_east: number
  frame: 'MOON_ME_DE421'; latitude_type: 'PLANETOCENTRIC'
}
