import { render } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import { PerspectiveCamera, Vector3 } from 'three'
import { ObserverControls } from './ObserverControls'
import { INITIAL_VIEW } from './directions'

const state=vi.hoisted(()=>({value:{} as unknown}))
vi.mock('@react-three/fiber',()=>({useThree:()=>state.value}))
it('keeps camera at origin, updates external direction, and cleans all input listeners on pause/unmount',()=>{
  const canvas=document.createElement('canvas'),camera=new PerspectiveCamera(),invalidate=vi.fn(),onView=vi.fn()
  canvas.hasPointerCapture=()=>false
  state.value={camera,gl:{domElement:canvas},invalidate}
  const add=vi.spyOn(canvas,'addEventListener'),remove=vi.spyOn(canvas,'removeEventListener')
  const {rerender,unmount}=render(<ObserverControls view={INITIAL_VIEW} onView={onView} interactive/>)
  expect(camera.position.toArray()).toEqual([0,0,0])
  expect(canvas.style.touchAction).toBe('none')
  const view={azimuth:90,elevation:0,fov:50}
  rerender(<ObserverControls view={view} onView={onView} interactive/>)
  const direction=camera.getWorldDirection(new Vector3());expect(direction.x).toBeCloseTo(1);expect(direction.y).toBeCloseTo(0)
  canvas.dispatchEvent(new WheelEvent('wheel',{deltaY:1,cancelable:true}))
  expect(onView).toHaveBeenLastCalledWith({...view,fov:55})
  rerender(<ObserverControls view={view} onView={onView} interactive={false}/>)
  expect(canvas.style.touchAction).toBe('pan-y')
  expect(remove.mock.calls.map(c=>c[0])).toEqual(add.mock.calls.map(c=>c[0]))
  onView.mockClear();canvas.dispatchEvent(new WheelEvent('wheel',{deltaY:1}));expect(onView).not.toHaveBeenCalled()
  rerender(<ObserverControls view={view} onView={onView} interactive/>);unmount()
  expect(remove.mock.calls.map(c=>c[0])).toEqual(add.mock.calls.map(c=>c[0]))
})
