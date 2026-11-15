import { useEffect, useRef } from 'react'
import { useThree } from '@react-three/fiber'
import { PerspectiveCamera } from 'three'
import { boundedView, renderDirection, type View } from './directions'

/** Fixed origin; changes only angular orientation/FOV, never observer location. */
export function ObserverControls({ view, onView, interactive }: { view: View; onView: (view: View) => void; interactive: boolean }) {
  const { camera, gl, invalidate } = useThree()
  const current = useRef(view)
  useEffect(() => {
    current.current = view
    camera.position.set(0, 0, 0)
    camera.up.set(0, 1, 0)
    camera.lookAt(...renderDirection(view.azimuth, view.elevation))
    if (camera instanceof PerspectiveCamera) { camera.fov = view.fov; camera.updateProjectionMatrix() }
    invalidate()
  }, [camera, invalidate, view])
  useEffect(() => {
    const canvas = gl.domElement
    canvas.style.touchAction = interactive ? 'none' : 'pan-y'
    if (!interactive) return
    const points = new Map<number, { x: number; y: number }>()
    const report = (next: View) => { current.current = boundedView(next); onView(current.current) }
    const distance = () => { const [a, b] = [...points.values()]; return a && b ? Math.hypot(a.x - b.x, a.y - b.y) : 0 }
    const down = (e: PointerEvent) => {
      if (e.button !== 0 || points.size >= 2) return
      points.set(e.pointerId, { x: e.clientX, y: e.clientY }); canvas.setPointerCapture(e.pointerId)
    }
    const move = (e: PointerEvent) => {
      const previous = points.get(e.pointerId)
      if (!previous) return
      const before = distance()
      points.set(e.pointerId, { x: e.clientX, y: e.clientY })
      if (points.size === 2) { const after = distance(); if (before > 0 && after > 0) report({ ...current.current, fov: current.current.fov * before / after }) }
      else report({ ...current.current, azimuth: current.current.azimuth - (e.clientX - previous.x) * current.current.fov / Math.max(canvas.clientHeight, 1), elevation: current.current.elevation + (e.clientY - previous.y) * current.current.fov / Math.max(canvas.clientHeight, 1) })
    }
    const up = (e: PointerEvent) => { points.delete(e.pointerId); if (canvas.hasPointerCapture(e.pointerId)) canvas.releasePointerCapture(e.pointerId) }
    const wheel = (e: WheelEvent) => { e.preventDefault(); report({ ...current.current, fov: current.current.fov + Math.sign(e.deltaY) * 5 }) }
    canvas.addEventListener('pointerdown', down); canvas.addEventListener('pointermove', move)
    canvas.addEventListener('pointerup', up); canvas.addEventListener('pointercancel', up); canvas.addEventListener('lostpointercapture', up)
    canvas.addEventListener('wheel', wheel, { passive: false })
    return () => {
      canvas.removeEventListener('pointerdown', down); canvas.removeEventListener('pointermove', move)
      canvas.removeEventListener('pointerup', up); canvas.removeEventListener('pointercancel', up); canvas.removeEventListener('lostpointercapture', up)
      canvas.removeEventListener('wheel', wheel)
      for (const id of points.keys()) if (canvas.hasPointerCapture(id)) canvas.releasePointerCapture(id)
    }
    // Keep pointer capture and pinch state across renders; external camera changes
    // are synchronized in the camera effect rather than reinstalling listeners on every move.
  }, [gl, interactive, onView])
  return null
}
