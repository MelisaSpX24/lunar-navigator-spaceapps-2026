import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import { LocalHorizon } from './LocalHorizon'
import { scientificFixture } from '../../test/scientificFixtures'
import type { HorizonProfile } from '../../features/analysis-results/types'

// Renderer boundaries only; real WebGL, camera and cleanup tested in Chromium.
vi.mock('./HorizonScene',()=>({default:({profile}:{profile:HorizonProfile|null})=><p data-testid="rendered-profile">{profile?.id??'No terrain samples'}</p>}))
it('offers orientation only, without a valid observation site',async()=>{
  render(<LocalHorizon response={null} selected={null}/>);
  expect(screen.getByText(/Orientation preview only/)).toBeVisible()
  expect(screen.getByText(/No valid observer coordinate/)).toBeVisible()
  expect(await screen.findByTestId('rendered-profile')).toHaveTextContent('No terrain samples')
  expect(screen.queryByRole('combobox')).toBeNull()
})
it('preserves selected coordinate while preview is independent of scientific analysis',()=>{
  render(<LocalHorizon response={null} selected={{latitude:-85,longitude:-20,radius:1}}/>);
  expect(screen.getByText(/Selected observer coordinate/)).toHaveTextContent('-85.000° latitude, 340.000° east longitude')
})
it('does not label exact poles as valid backend observer sites',()=>{
  render(<LocalHorizon response={null} selected={{latitude:-90,longitude:null,radius:1}}/>);
  expect(screen.getByText(/No valid observer coordinate/)).toBeVisible()
})
it('selects each independent profile and resets safely on a replacement response',async()=>{
  const user=userEvent.setup(),response=scientificFixture()
  const {rerender}=render(<LocalHorizon response={response} selected={null}/>)
  expect(await screen.findByTestId('rendered-profile')).toHaveTextContent('controlled-horizon-low')
  expect(screen.getByText('TEST DATA — synthetic horizon profile')).toBeVisible()
  expect(screen.getByText('Incomplete terrain horizon coverage')).toBeVisible()
  expect(screen.getByText(/Data quality: LIMITED/)).toBeVisible()
  await user.selectOptions(screen.getByRole('combobox'),'controlled-horizon-high')
  expect(screen.getByTestId('rendered-profile')).toHaveTextContent('controlled-horizon-high')
  expect(screen.getByText(/Active profile:/)).toHaveTextContent('Observer height: 2 m. Range: 1200 m.')
  rerender(<LocalHorizon response={scientificFixture()} selected={null}/>)
  expect(screen.getByTestId('rendered-profile')).toHaveTextContent('controlled-horizon-low')
  rerender(<LocalHorizon response={null} selected={null}/>)
  expect(screen.getByTestId('rendered-profile')).toHaveTextContent('No terrain samples')
  expect(screen.queryByText('TEST DATA — synthetic horizon profile')).toBeNull()
})
it.each([null,[],[{id:'bad'}]])('withholds unusable profiles %j',async horizons=>{
  render(<LocalHorizon response={{...scientificFixture(),horizons}} selected={null}/>)
  expect(await screen.findByTestId('rendered-profile')).toHaveTextContent('No terrain samples')
  expect(screen.queryByRole('combobox')).toBeNull()
})
it('shows insufficient quality and all-null sample count without inventing clear terrain',async()=>{
  const r=scientificFixture();r.quality={status:'INSUFFICIENT',coverage_complete:false,limitations:[]}
  const h=r.horizons as HorizonProfile[];h[0]!.points=[{azimuth_deg:0,elevation_deg:null}]
  render(<LocalHorizon response={r} selected={null}/>);
  expect(await screen.findByTestId('rendered-profile')).toHaveTextContent('controlled-horizon-low')
  expect(screen.getByText(/0 known angular samples \/ 1 unknown/)).toBeVisible()
  expect(screen.getByText(/Data quality: INSUFFICIENT/)).toBeVisible()
})
