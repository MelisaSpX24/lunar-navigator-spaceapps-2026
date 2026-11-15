import type { VisualPosition } from '../../features/celestial-timeline/motion'
import { useEffect, useMemo } from 'react'
import { BufferAttribute, BufferGeometry, CanvasTexture, SRGBColorSpace } from 'three'
import type { BodyRow } from '../../features/analysis-results/types'
import { hasDirection } from '../../features/celestial-timeline/selection'
import { renderDirection } from './directions'

export type CelestialView = { sun: BodyRow | null; earth: BodyRow | null; sunPosition: VisualPosition; earthPosition: VisualPosition; sunRows: BodyRow[]; earthRows: BodyRow[]; utc: string | null; testData: boolean }
export function pathPositions(rows: BodyRow[]) {
  return new Float32Array(rows.flatMap(row => hasDirection(row.body) ? renderDirection(row.body.azimuth_deg, row.body.elevation_deg, 9) : []))
}
function Marker({ position, name }: { position: VisualPosition; name: 'SUN' | 'EARTH' }) {
  const texture = useMemo(() => {
    const canvas = document.createElement('canvas'); canvas.width = 512; canvas.height = 256
    const ctx = canvas.getContext('2d')
    if (ctx) {
      ctx.fillStyle = name === 'SUN' ? '#ffcf70' : '#83e9ff'; ctx.strokeStyle = ctx.fillStyle; ctx.lineWidth = 8
      ctx.beginPath()
      if (name === 'SUN') ctx.arc(256, 128, 24, 0, Math.PI * 2)
      else { ctx.moveTo(256, 103); ctx.lineTo(281, 128); ctx.lineTo(256, 153); ctx.lineTo(231, 128); ctx.closePath() }
      ctx.stroke()
      // Keep text readable when a cardinal guide or another direction lies behind it.
      ctx.fillStyle = '#07121e'; ctx.fillRect(130, name === 'SUN' ? 8 : 158, 252, 82)
      ctx.fillStyle = name === 'SUN' ? '#ffcf70' : '#83e9ff'
      ctx.font = 'bold 72px sans-serif'; ctx.textAlign = 'center'; ctx.fillText(name, 256, name === 'SUN' ? 75 : 225)
    }
    const map = new CanvasTexture(canvas); map.colorSpace = SRGBColorSpace; return map
  }, [name])
  useEffect(() => () => texture.dispose(), [texture])
  if (position.kind === 'unavailable') return null
  return <sprite name={`celestial-${name.toLowerCase()}`} position={position.direction.map(n => n * 9) as [number, number, number]} scale={[5, 2.5, 1]} renderOrder={2}>
    <spriteMaterial map={texture} transparent depthTest={false} depthWrite={false} />
  </sprite>
}
function Path({ rows, body }: { rows: BodyRow[]; body: 'sun' | 'earth' }) {
  const geometry = useMemo(() => new BufferGeometry().setAttribute('position', new BufferAttribute(pathPositions(rows), 3)), [rows])
  // Own the attribute with its geometry so it is still attached when disposed.
  useEffect(() => () => geometry.dispose(), [geometry])
  if (!geometry.getAttribute('position').count) return null
  return <points name={`${body}-sample-path`} geometry={geometry}><pointsMaterial color={body === 'sun' ? '#ffcf70' : '#83e9ff'} size={3} sizeAttenuation={false} /></points>
}
export function CelestialLayer({ data, sunPath, earthPath }: { data: CelestialView; sunPath: boolean; earthPath: boolean }) {
  return <group><Marker position={data.sunPosition} name="SUN" /><Marker position={data.earthPosition} name="EARTH" />{sunPath && <Path rows={data.sunRows} body="sun" />}{earthPath && <Path rows={data.earthRows} body="earth" />}</group>
}
