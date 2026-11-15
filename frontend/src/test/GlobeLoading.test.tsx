import { render, screen } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import LunarGlobe from '../visualization/globe/LunarGlobe'
import { loadMoonTexture } from '../visualization/globe/moonTexture'

vi.mock('@react-three/fiber', () => ({ Canvas: () => null }))
vi.mock('../visualization/globe/moonTexture', async importOriginal => ({
  ...await importOriginal<typeof import('../visualization/globe/moonTexture')>(),
  loadMoonTexture: vi.fn(() => new Promise(() => {})),
}))

it('shows scene and texture loading without falsely announcing texture success', () => {
  render(<LunarGlobe selected={null} onSelect={() => {}} />)
  expect(screen.getByRole('heading', { name: 'Loading 3D scene' })).toBeVisible()
  expect(screen.getByText('Loading NASA texture…')).toBeVisible()
  expect(screen.queryByText('NASA color texture loaded — visual imagery only')).not.toBeInTheDocument()
  expect(loadMoonTexture).toHaveBeenCalledWith('/assets/moon/lroc_color_2k.jpg')
  expect(screen.getByRole('button', { name: 'Focus South Pole' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Reset View' })).toBeDisabled()
})
