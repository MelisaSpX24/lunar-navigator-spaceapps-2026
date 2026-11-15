import { normalizeLongitude, type VisualCoordinate } from '../../visualization/coordinates/lunarCoordinates'
import { finiteDecimal } from './missionState'

export function visualLongitudeToEast(longitude: number): number {
  const signed = normalizeLongitude(longitude)
  return signed < 0 ? signed + 360 : signed
}

export function eastLongitudeToVisual(longitude: number): number {
  if (!Number.isFinite(longitude) || longitude < 0 || longitude >= 360) throw new RangeError('East longitude must be in [0, 360)')
  return normalizeLongitude(longitude)
}

export function coordinateFields(point: VisualCoordinate) {
  return { latitude: String(point.latitude), longitude: point.longitude === null ? '' : String(visualLongitudeToEast(point.longitude)) }
}

/** Derived from the same raw fields as the form. Invalid edits hide the marker;
 * exact poles retain their visual marker while request validation rejects them.
 */
export function visualCoordinate(latitudeText: string, longitudeText: string): VisualCoordinate | null {
  const latitude = finiteDecimal(latitudeText), longitude = finiteDecimal(longitudeText)
  if (latitude === null || Math.abs(latitude) > 90) return null
  if (Math.abs(latitude) === 90) return { latitude, longitude: null, radius: 1 }
  if (longitude === null || longitude < 0 || longitude >= 360) return null
  return { latitude, longitude: eastLongitudeToVisual(longitude), radius: 1 }
}
