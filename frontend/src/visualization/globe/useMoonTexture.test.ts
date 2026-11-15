import { act, renderHook, waitFor } from '@testing-library/react'
import { Texture } from 'three'
import { afterEach, expect, it, vi } from 'vitest'
import { useMoonTexture } from './useMoonTexture'
import { loadMoonTexture } from './moonTexture'

vi.mock('./moonTexture', () => ({ loadMoonTexture: vi.fn() }))
afterEach(() => vi.resetAllMocks())

it('reports an unavailable asset without attempting a network request', () => {
  const { result } = renderHook(() => useMoonTexture(null))
  expect(result.current.status).toBe('unavailable')
  expect(loadMoonTexture).not.toHaveBeenCalled()
})

it('shows loading, accepts a synthetic test texture and disposes it on unmount', async () => {
  let resolve!: (texture: Texture) => void
  vi.mocked(loadMoonTexture).mockReturnValue(new Promise<Texture>(done => { resolve = done }))
  const texture = new Texture()
  const dispose = vi.spyOn(texture, 'dispose')
  const { result, unmount } = renderHook(() => useMoonTexture('/synthetic-test-only.jpg'))
  expect(result.current.status).toBe('loading')
  await act(async () => resolve(texture))
  expect(result.current.status).toBe('ready')
  unmount()
  expect(dispose).toHaveBeenCalledOnce()
})

it('falls back after a rejected texture load', async () => {
  vi.mocked(loadMoonTexture).mockRejectedValue(new Error('blocked'))
  const { result } = renderHook(() => useMoonTexture('/synthetic-test-only.jpg'))
  await waitFor(() => expect(result.current.status).toBe('unavailable'))
  expect(result.current.texture).toBeNull()
})

it('disposes a texture that arrives after unmount', async () => {
  let resolve!: (texture: Texture) => void
  vi.mocked(loadMoonTexture).mockReturnValue(new Promise<Texture>(done => { resolve = done }))
  const texture = new Texture()
  const dispose = vi.spyOn(texture, 'dispose')
  const { unmount } = renderHook(() => useMoonTexture('/synthetic-test-only.jpg'))
  unmount()
  await act(async () => resolve(texture))
  expect(dispose).toHaveBeenCalledOnce()
})
