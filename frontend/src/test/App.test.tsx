import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { App } from '../app/App'

vi.mock('../visualization/local-horizon/HorizonScene', () => ({ default: () => <p>Local scene renderer mocked in jsdom</p> }))

// jsdom has no WebGL: real scene behavior is covered separately in Chromium.
vi.mock('../visualization/globe/LunarGlobe', () => ({ default: () => <p>NASA texture unavailable — geometric preview only</p> }))

function renderApp(path = '/') {
  return render(<MemoryRouter initialEntries={[path]}><App /></MemoryRouter>)
}

describe('mission screens', () => {
  it('opens Mission Setup with clearly unavailable controls', () => {
    renderApp()
    expect(screen.getByRole('heading', { level: 1, name: 'Mission Setup' })).toBeVisible()
    expect(screen.getByRole('region', { name: 'Global lunar view' })).toBeVisible()
    expect(screen.getByRole('button', { name: 'Run Analysis' })).toBeDisabled()
    expect(screen.getByText(/No analysis will be performed/)).toBeVisible()
    expect(screen.getByRole('textbox', { name: 'Latitude (degrees)' })).toBeVisible()
  })

  it('renders every analysis panel without scientific values', () => {
    renderApp('/analysis')
    for (const title of ['Local Horizon', 'Sun Visibility', 'Earth Visibility', 'Mission Timeline', 'Operation Assessment', 'Planning Score', 'Data Quality']) {
      expect(screen.getByRole('heading', { level: 2, name: title })).toBeVisible()
    }
    const score = screen.getByRole('region', { name: 'Planning Score' })
    expect(within(score).getByText('Not calculated')).toBeVisible()
    expect(score).not.toHaveTextContent(/\d/)
    expect(screen.getByText(/Scientific visualizations are not populated/)).toBeVisible()
  })

  it('renders supplied recorded alternatives separately from live scientific analysis', () => {
    renderApp('/alternatives')
    for(const title of ['Explore alternatives','Same Site. Better Time.','A/B Scenario Comparison','Data Quality and Source Evidence'])expect(screen.getByRole('region',{name:title})).toBeVisible()
    expect(screen.getByText('RECORDED EVIDENCE',{exact:true})).toBeVisible()
    expect(screen.getByText(/No new calculation was performed/)).toBeVisible()
    expect(screen.getByText(/Full horizon profile is not included/)).toBeVisible()
    expect(screen.queryByLabelText('Interactive local horizon sky')).not.toBeInTheDocument()
  })

  it('navigates between all screens and updates the active link and document title', async () => {
    const user = userEvent.setup()
    renderApp()
    const nav = screen.getByRole('navigation', { name: 'Main navigation' })
    expect(within(nav).getByRole('link', { name: 'Mission Setup' })).toHaveAttribute('aria-current', 'page')
    for (const name of ['Mission Analysis', 'Alternative Explorer', 'Mission Setup']) {
      await user.click(within(nav).getByRole('link', { name }))
      expect(screen.getByRole('heading', { level: 1, name })).toBeVisible()
      expect(within(nav).getByRole('link', { name })).toHaveAttribute('aria-current', 'page')
      expect(nav.querySelectorAll('[aria-current="page"]')).toHaveLength(1)
      expect(document.title).toBe(`${name} | 24&28 Lunar Navigator`)
      expect(screen.getByRole('main')).toHaveFocus()
    }
  })

  it('provides a recoverable unknown route', async () => {
    const user = userEvent.setup()
    renderApp('/unknown')
    expect(screen.getByRole('heading', { level: 1, name: 'Page not found' })).toBeVisible()
    await user.click(screen.getByRole('link', { name: 'Return to Mission Setup' }))
    expect(screen.getByRole('heading', { level: 1, name: 'Mission Setup' })).toBeVisible()
  })

  it('moves focus to the main content through the skip link', async () => {
    const user = userEvent.setup()
    renderApp()
    screen.getByRole('link', { name: 'Skip to main content' }).focus()
    await user.keyboard('{Enter}')
    expect(screen.getByRole('main')).toHaveFocus()
  })

  it('reports verified readiness without treating HTTP 200 as ready', async () => {
    renderApp()
    const connection = screen.getByRole('group', { name: 'Backend connection' })
    expect(await within(connection).findByText('Backend reachable — scientific engine not ready')).toBeVisible()
    expect(within(connection).queryByText('Backend reachable — scientific engine ready')).not.toBeInTheDocument()
  })
})
