import { useEffect, useMemo } from 'react'
import { CanvasTexture, SRGBColorSpace } from 'three'
import { renderDirection, samplePositions } from './directions'
import type { HorizonProfile } from '../../features/analysis-results/types'

function referenceSegments() {
  const values: number[] = []
  const segment = (a: number[], b: number[]) => values.push(...a, ...b)
  // Coordinate guides only: not a measured terrain silhouette.
  for (const elevation of [-60, -30, 0, 30, 60]) {
    for (let az = 0; az < 360; az += 5) segment(renderDirection(az, elevation), renderDirection((az + 5) % 360, elevation))
  }
  for (let az = 0; az < 360; az += 30) {
    for (let el = -85; el < 85; el += 5) segment(renderDirection(az, el), renderDirection(az, el + 5))
    segment(renderDirection(az, -2), renderDirection(az, 2))
  }
  return new Float32Array(values)
}
function Label({ text, azimuth, elevation }: { text: string; azimuth: number; elevation: number }) {
  const texture = useMemo(() => {
    const canvas = document.createElement('canvas'); canvas.width = 256; canvas.height = 96
    const ctx = canvas.getContext('2d')
    if (ctx) { ctx.fillStyle = '#d9f5ff'; ctx.font = 'bold 48px sans-serif'; ctx.textAlign = 'center'; ctx.fillText(text, 128, 65) }
    const map = new CanvasTexture(canvas); map.colorSpace = SRGBColorSpace; return map
  }, [text])
  useEffect(() => () => texture.dispose(), [texture])
  return <sprite position={renderDirection(azimuth, elevation, 9.8)} scale={[3.6, 1.35, 1]}><spriteMaterial map={texture} transparent depthTest={false} /></sprite>
}
export function SkyReferences() {
  const positions = useMemo(referenceSegments, [])
  return <group name="coordinate-guides-not-terrain">
    <lineSegments><bufferGeometry><bufferAttribute attach="attributes-position" args={[positions, 3]} /></bufferGeometry><lineBasicMaterial color="#34576b" /></lineSegments>
    {['N · 0°', 'E · 90°', 'S · 180°', 'W · 270°'].map((text, i) => <Label key={text} text={text} azimuth={i * 90} elevation={6} />)}
    {[-60, -30, 30, 60].map(e => <Label key={e} text={`${e > 0 ? '+' : ''}${e}°`} azimuth={0} elevation={e} />)}
  </group>
}
export function HorizonSamples({ profile }: { profile: HorizonProfile | null }) {
  const positions = useMemo(() => samplePositions(profile), [profile])
  if (!positions.length) return null
  return <points name="backend-angular-samples"><bufferGeometry><bufferAttribute attach="attributes-position" args={[positions, 3]} /></bufferGeometry><pointsMaterial color="#b5ecd0" size={8} sizeAttenuation={false} /></points>
}
