import type { FormErrors, FormField } from '../../features/mission-input/missionState'
import type { ValidationIssue } from './responses'

const fields: Record<string, FormField[]> = {
  'site.latitude_deg': ['latitude'], 'site.longitude_deg_east': ['longitude'],
  'time.start_utc': ['utcDate','utcTime'], 'time.duration_s': ['hours','minutes','seconds'],
  'operation.profile': ['profile'],
  'operation.requirements.min_solar_disk_visible_fraction': ['solarFraction'],
  'operation.requirements.min_sun_visible_s': ['minSun'], 'operation.requirements.max_dark_gap_s': ['maxDark'],
  'operation.requirements.min_earth_continuous_s': ['minEarth'], 'operation.requirements.earth_clearance_margin_deg': ['clearance'],
  'operation.requirements.require_simultaneous': ['simultaneous'], 'operation.requirements.min_joint_continuous_s': ['minJoint'],
  'observer.solar_height_above_surface_m': ['solarHeight'], 'observer.earth_height_above_surface_m': ['earthHeight'],
  'options.include_full_horizon': ['fullHorizon'], 'options.include_earth_disk_fraction': ['earthDisk'], 'options.event_lookahead_s': ['lookahead'],
}
export function mapFieldErrors(issues: ValidationIssue[]): { fields: FormErrors; general: string[] } {
  const result: { fields: FormErrors; general: string[] } = { fields: {}, general: [] }
  for (const issue of issues) {
    const path = issue.loc[0] === 'body' ? issue.loc.slice(1) : []
    // CoordinateSite's discriminator branch may appear in Pydantic locations.
    if (path[0] === 'site' && path[1] === 'COORDINATES') path.splice(1, 1)
    const key = path.join('.')
    const targets = Object.hasOwn(fields, key) ? fields[key] : undefined
    if (targets) for (const field of targets) result.fields[field] = [result.fields[field], issue.msg].filter(Boolean).join(' ')
    else result.general.push(issue.msg)
  }
  return result
}
