export type Point3 = { x: number; y: number; z: number }
export type VisualCoordinate = { latitude: number; longitude: number | null; radius: number }
const radians = Math.PI / 180

export function normalizeLongitude(longitude: number): number {
  if (!Number.isFinite(longitude)) throw new RangeError('Longitude must be finite')
  const wrapped = ((longitude + 180) % 360 + 360) % 360 - 180
  return Object.is(wrapped, -0) ? 0 : wrapped
}

export function toCartesian(latitude: number, longitude: number, radius = 1): Point3 {
  if (!Number.isFinite(latitude) || Math.abs(latitude) > 90) throw new RangeError('Latitude must be within ±90 degrees')
  if (!Number.isFinite(radius) || radius <= 0) throw new RangeError('Radius must be positive and finite')
  const phi = latitude * radians
  const lambda = normalizeLongitude(longitude) * radians
  return { x: radius * Math.cos(phi) * Math.cos(lambda), y: radius * Math.sin(phi), z: -radius * Math.cos(phi) * Math.sin(lambda) }
}

export function fromCartesian({ x, y, z }: Point3): VisualCoordinate {
  if (![x, y, z].every(Number.isFinite)) throw new RangeError('Position must be finite')
  const radius = Math.hypot(x, y, z)
  if (!Number.isFinite(radius) || radius === 0) throw new RangeError('Position must have a finite nonzero radius')
  return {
    latitude: Math.asin(Math.max(-1, Math.min(1, y / radius))) / radians,
    longitude: Math.hypot(x, z) / radius < 1e-10 ? null : normalizeLongitude(Math.atan2(-z, x) / radians),
    radius,
  }
}

/** Equirectangular map: west at left, 0° at centre, north at top. */
export function toMapUv(latitude: number, longitude: number) {
  toCartesian(latitude, longitude)
  return { u: (normalizeLongitude(longitude) + 180) / 360, v: (latitude + 90) / 180 }
}
