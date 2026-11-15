import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it, vi } from 'vitest'
import { MissionSetup } from '../../screens/MissionSetup'
import type { VisualCoordinate } from '../../visualization/coordinates/lunarCoordinates'
import { ScenarioProvider } from '../scenario/ScenarioProvider'
import { PROFILES } from './analysisRequest'

vi.mock('../../visualization/globe/LunarGlobe', () => ({
  default: ({ selected, onSelect }: { selected: VisualCoordinate | null; onSelect: (p: VisualCoordinate) => void }) => <div>
    <button onClick={() => onSelect({latitude:-85,longitude:-20,radius:1})}>Pick west point</button>
    <button onClick={() => onSelect({latitude:-90,longitude:null,radius:1})}>Pick exact pole</button>
    <output aria-label="Mock globe marker">{selected ? `${selected.latitude}/${selected.longitude}` : 'No marker'}</output>
  </div>,
}))
afterEach(() => vi.unstubAllGlobals())

async function fillValid() {
  const user = userEvent.setup()
  await user.type(screen.getByLabelText('Latitude (degrees)'), '-85')
  await user.type(screen.getByLabelText('Longitude (degrees east)'), '340')
  fireEvent.change(screen.getByLabelText('UTC date'), {target:{value:'2026-11-14'}})
  fireEvent.change(screen.getByLabelText('UTC time'), {target:{value:'12:30'}})
  return user
}

it('shares globe selection and manual edits through the same coordinate fields', async () => {
  const user = userEvent.setup()
  render(<ScenarioProvider><MissionSetup /></ScenarioProvider>)
  await user.click(await screen.findByRole('button', {name:'Pick west point'}))
  expect(screen.getByLabelText('Latitude (degrees)')).toHaveValue('-85')
  expect(screen.getByLabelText('Longitude (degrees east)')).toHaveValue('340')
  expect(screen.getByLabelText('Mock globe marker')).toHaveTextContent('-85/-20')
  await user.clear(screen.getByLabelText('Longitude (degrees east)'))
  expect(screen.getByLabelText('Mock globe marker')).toHaveTextContent('No marker')
  await user.type(screen.getByLabelText('Longitude (degrees east)'), '270')
  expect(screen.getByLabelText('Mock globe marker')).toHaveTextContent('-85/-90')
})

it('keeps the selected pole without clamping and rejects its request', async () => {
  const user = userEvent.setup()
  render(<ScenarioProvider><MissionSetup /></ScenarioProvider>)
  await user.click(await screen.findByRole('button',{name:'Pick exact pole'}))
  expect(screen.getByLabelText('Latitude (degrees)')).toHaveValue('-90')
  expect(screen.getByLabelText('Longitude (degrees east)')).toHaveValue('')
  expect(screen.getByLabelText('Mock globe marker')).toHaveTextContent('-90/null')
  expect(screen.getByLabelText('Latitude (degrees)')).toHaveAttribute('aria-invalid','true')
  expect(screen.getByText(/Exact ±90° poles are not supported/)).toBeVisible()
  expect(screen.queryByLabelText('AnalysisRequest JSON')).not.toBeInTheDocument()
})

it('prepares only request JSON, preserves profile requirements, and never sends an analysis', async () => {
  const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({status:'ok',science_ready:false,dem_ready:false,kernels_ready:false,reason_codes:['SCIENCE_ENGINE_NOT_READY']})))
  vi.stubGlobal('fetch', fetch)
  render(<ScenarioProvider><MissionSetup /></ScenarioProvider>)
  const user = await fillValid()
  await user.type(screen.getByLabelText('Minimum continuous Earth visibility (seconds)'), '0')
  for (const profile of PROFILES) {
    await user.selectOptions(screen.getByLabelText('Operation profile'),profile.value)
    expect(screen.getByLabelText('Minimum continuous Earth visibility (seconds)')).toHaveValue('0')
  }
  await user.click(screen.getByText('Request Preview', {selector:'summary'}))
  const request = JSON.parse(screen.getByLabelText('AnalysisRequest JSON').textContent!)
  expect(request.operation.profile).toBe('CUSTOM_OPERATION')
  expect(request.operation.requirements.min_earth_continuous_s).toBe(0)
  expect(request.operation.requirements.min_sun_visible_s).toBeNull()
  expect(request.time.start_utc).toBe('2026-11-14T12:30:00Z')
  expect(screen.getByText('Scenario inputs valid — check backend readiness before running analysis.')).toBeVisible()
  expect(screen.getByRole('button',{name:'Run Analysis'})).toBeDisabled()
  await user.click(screen.getByRole('button',{name:'Validate inputs'}))
  expect(fetch.mock.calls.every(([, options]) => options?.method !== 'POST')).toBe(true)
  await user.clear(screen.getByLabelText('Longitude (degrees east)'))
  await user.type(screen.getByLabelText('Longitude (degrees east)'), '360')
  expect(screen.queryByLabelText('AnalysisRequest JSON')).not.toBeInTheDocument()
  expect(screen.getByLabelText('Longitude (degrees east)')).toHaveAttribute('aria-invalid','true')
})

it('links threshold errors to fields and focuses the first invalid input on validation', async () => {
  render(<ScenarioProvider><MissionSetup /></ScenarioProvider>)
  const user = userEvent.setup()
  await user.click(screen.getByRole('button',{name:'Validate inputs'}))
  expect(screen.getByLabelText('Latitude (degrees)')).toHaveFocus()
  await user.type(screen.getByLabelText('Minimum joint visibility (seconds)'), '0')
  const input = screen.getByLabelText('Minimum joint visibility (seconds)')
  expect(input).toHaveAttribute('aria-invalid','true')
  expect(input).toHaveAttribute('aria-describedby', expect.stringContaining('mission-minJoint-error'))
  await user.click(screen.getByLabelText('Require simultaneous Sun and Earth visibility'))
  await waitFor(() => expect(input).toHaveAttribute('aria-invalid','false'))
  expect(input).toHaveValue('0')
})
