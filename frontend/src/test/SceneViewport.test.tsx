import { render, screen, within } from '@testing-library/react'
import { expect, it } from 'vitest'
import { SceneViewport } from '../components/SceneViewport'

it('keeps scene content and overlay information accessible without a renderer', () => {
  render(<SceneViewport label="Global lunar view" caption="Global view unavailable" footer="No imagery loaded.">
    <p>Interactive lunar globe is not yet available.</p>
  </SceneViewport>)
  const view = screen.getByRole('region', { name: 'Global lunar view' })
  expect(within(view).getByText('Interactive lunar globe is not yet available.')).toBeVisible()
  expect(within(view).getByText('No imagery loaded.')).toBeVisible()
  expect(within(view).getByText('Camera controls unavailable')).toBeVisible()
  expect(view.querySelector('canvas')).toBeNull()
  expect(within(view).queryByRole('button')).not.toBeInTheDocument()
})
