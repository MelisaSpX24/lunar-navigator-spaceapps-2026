import { useEffect, useRef } from 'react'
import { useThree } from '@react-three/fiber'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { toCartesian, type VisualCoordinate } from '../coordinates/lunarCoordinates'
import { Vector3 } from 'three'

export type SiteFocus = { kind: 'site'; coordinate: VisualCoordinate; sequence: number }
export type CameraCommand = { kind: 'south' | 'reset'; sequence: number } | SiteFocus
export type ViewState = { latitude: number; longitude: number; distance: number }
export const INITIAL_CAMERA: [number, number, number] = [3.2, 0.7, 0.8]

export function GlobeControls({ command, onView, interactive }: { command: CameraCommand; onView: (view: ViewState) => void; interactive: boolean }) {
  const { camera, gl, invalidate } = useThree()
  const controls = useRef<OrbitControls | null>(null)
  useEffect(() => {
    const orbit = new OrbitControls(camera, gl.domElement)
    controls.current = orbit
    orbit.enablePan = false
    orbit.enableDamping = false
    orbit.minDistance = 1.45
    orbit.maxDistance = 6
    orbit.minPolarAngle = 0.003
    orbit.maxPolarAngle = Math.PI - 0.003
    orbit.zoomSpeed = 0.7
    const update = () => invalidate()
    const report = () => onView({ latitude: Math.asin(camera.position.y / camera.position.length()) * 180 / Math.PI, longitude: Math.atan2(-camera.position.z, camera.position.x) * 180 / Math.PI, distance: camera.position.length() })
    orbit.addEventListener('change', update)
    orbit.addEventListener('end', report)
    orbit.update()
    report()
    return () => {
      orbit.removeEventListener('change', update)
      orbit.removeEventListener('end', report)
      orbit.dispose()
      controls.current = null
    }
  }, [camera, gl, invalidate, onView])
  useEffect(() => {
    if (controls.current) controls.current.enabled = interactive
    gl.domElement.style.touchAction = interactive ? 'none' : 'pan-y'
  }, [gl, interactive])
  useEffect(() => {
    // Instant changes respect reduced-motion users and avoid singular pole views.
    const p = command.kind === 'site' ? toCartesian(command.coordinate.latitude, command.coordinate.longitude ?? 0, 3.2) : null
    camera.position.copy(p ? new Vector3(p.x,p.y,p.z) : command.kind === 'south' ? new Vector3(0.18, -3.2, 0.18) : new Vector3(...INITIAL_CAMERA))
    camera.lookAt(0, 0, 0)
    controls.current?.update()
    onView({ latitude: Math.asin(camera.position.y / camera.position.length()) * 180 / Math.PI, longitude: Math.atan2(-camera.position.z, camera.position.x) * 180 / Math.PI, distance: camera.position.length() })
    invalidate()
  }, [command, camera, invalidate, onView])
  return null
}
