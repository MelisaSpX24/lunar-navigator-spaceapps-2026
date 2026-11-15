import { useEffect, useMemo, useRef } from 'react'
import type { ThreeEvent } from '@react-three/fiber'
import type { Texture } from 'three'
import { fromCartesian, toCartesian, type VisualCoordinate } from '../coordinates/lunarCoordinates'
import { createMoonGeometry } from './moonGeometry'

type Props = { texture: Texture | null; selected: VisualCoordinate | null; onSelect: (point: VisualCoordinate) => void }

export function MoonMesh({ texture, selected, onSelect }: Props) {
  const geometry = useMemo(createMoonGeometry, [])
  const start = useRef<{ x: number; y: number; moved: boolean } | null>(null)
  useEffect(() => () => geometry.dispose(), [geometry])
  const equator = useMemo(() => new Float32Array(Array.from({ length: 96 }, (_, i) => {
    const p = toCartesian(0, i * 360 / 96, 1.003)
    return [p.x, p.y, p.z]
  }).flat()), [])
  const meridian = useMemo(() => new Float32Array(Array.from({ length: 96 }, (_, i) => {
    const t = i * 2 * Math.PI / 96
    return [1.003 * Math.cos(t), 1.003 * Math.sin(t), 0]
  }).flat()), [])
  function select(event: ThreeEvent<MouseEvent>) {
    const gesture = start.current
    start.current = null
    if (!gesture || gesture.moved || Math.hypot(event.clientX - gesture.x, event.clientY - gesture.y) > 5 || event.delta > 5) return
    onSelect(fromCartesian(event.point))
  }
  const marker = selected ? toCartesian(selected.latitude, selected.longitude ?? 0, 1.016) : null
  return <>
    <mesh geometry={geometry}
      onPointerDown={e => { start.current = { x: e.clientX, y: e.clientY, moved: false } }}
      onPointerMove={e => {
        if (start.current && Math.hypot(e.clientX - start.current.x, e.clientY - start.current.y) > 5) start.current.moved = true
      }}
      onPointerOut={() => { if (start.current) start.current.moved = true }}
      onClick={select}>
      {/* A map arriving after the first draw needs a new shader variant. R3F
          disposes the replaced material; texture ownership stays with the hook. */}
      <meshStandardMaterial key={texture?.uuid ?? 'geometric-preview'} map={texture} color={texture ? '#ffffff' : '#a5adb6'} roughness={1} metalness={0} />
    </mesh>
    {!texture && [equator, meridian].map((points, index) => <lineLoop key={index} raycast={() => null}>
      <bufferGeometry><bufferAttribute attach="attributes-position" args={[points, 3]} /></bufferGeometry>
      <lineBasicMaterial color="#657f92" transparent opacity={0.7} />
    </lineLoop>)}
    {marker && <mesh position={[marker.x, marker.y, marker.z]} raycast={() => null}>
      <sphereGeometry args={[0.022, 12, 8]} /><meshBasicMaterial color="#8cdee6" />
    </mesh>}
  </>
}
