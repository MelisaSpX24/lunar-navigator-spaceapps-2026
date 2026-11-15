import { useEffect, useMemo } from 'react'
import { BufferAttribute, BufferGeometry } from 'three'
import type { HorizonProfile } from '../../features/analysis-results/types'
import { traceSegments } from './trace'

export function HorizonTrace({ profile }: { profile: HorizonProfile | null }) {
  const geometry = useMemo(() => new BufferGeometry().setAttribute('position', new BufferAttribute(traceSegments(profile), 3)), [profile])
  useEffect(() => () => geometry.dispose(), [geometry])
  if (!geometry.getAttribute('position').count) return null
  return <lineSegments name="visual-horizon-trace" geometry={geometry}><lineBasicMaterial color="#8cc7b4" transparent opacity={.6} /></lineSegments>
}
