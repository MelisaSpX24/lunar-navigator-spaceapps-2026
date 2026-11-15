import { useEffect, useState } from 'react'
import type { Texture } from 'three'
import { loadMoonTexture } from './moonTexture'

export type TextureState = { status: 'loading' | 'ready' | 'unavailable'; texture: Texture | null }

export function useMoonTexture(url: string | null): TextureState {
  const [state, setState] = useState<TextureState>({ status: url ? 'loading' : 'unavailable', texture: null })
  useEffect(() => {
    let active = true
    let owned: Texture | null = null
    if (!url) { setState({ status: 'unavailable', texture: null }); return }
    setState({ status: 'loading', texture: null })
    void loadMoonTexture(url).then(texture => {
      if (!active) { texture.dispose(); return }
      owned = texture
      setState({ status: 'ready', texture })
    }).catch(() => {
      if (active) setState({ status: 'unavailable', texture: null })
    })
    return () => { active = false; owned?.dispose() }
  }, [url])
  return state
}
