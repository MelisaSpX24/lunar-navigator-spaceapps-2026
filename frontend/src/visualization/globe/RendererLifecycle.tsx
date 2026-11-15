import { useEffect } from 'react'
import { useThree } from '@react-three/fiber'

export function RendererLifecycle({ onReady, onLost }: { onReady: () => void; onLost: () => void }) {
  const canvas = useThree(state => state.gl.domElement)
  useEffect(() => {
    onReady()
    canvas.addEventListener('webglcontextlost', onLost)
    return () => canvas.removeEventListener('webglcontextlost', onLost)
  }, [canvas, onReady, onLost])
  return null
}
