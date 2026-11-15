import { render, screen, within } from '@testing-library/react'
import { expect, it } from 'vitest'
import { scientificFixture } from '../../test/scientificFixtures'
import { HorizonData, BodyData } from './VisibilityPanels'
import { TimelineData } from './TimelineData'
import { DecisionData, ScoreData } from './AssessmentData'
import { QualityData } from './QualityData'
import { timeBounds } from './utc'

const bounds=timeBounds('2026-11-14T12:30:00Z',3600)
it('plots actual horizon samples with no line across null elevations and explicit incomplete coverage',()=>{
  const {container}=render(<HorizonData response={scientificFixture()} />)
  expect(screen.getAllByText(/Incomplete horizon coverage/)).toHaveLength(2)
  expect(screen.getByText('Observer height: 1 m. Analysis range: 1200 m.')).toBeVisible()
  expect(screen.getByText('Observer height: 2 m. Analysis range: 1200 m.')).toBeVisible()
  expect(container.querySelectorAll('circle')).toHaveLength(6)
  expect(container.querySelectorAll('polyline')).toHaveLength(0)
  expect(screen.getAllByText('Unknown (null)')).toHaveLength(2)
  expect(screen.getAllByRole('img')).toHaveLength(2)
})
it('provides accessible Sun charts and exact UNKNOWN/NONE/PARTIAL, false and zero table cells',()=>{
  const {container}=render(<BodyData response={scientificFixture()} body="sun" bounds={bounds} />)
  expect(screen.getByRole('img',{name:/Sun elevation over UTC/})).toBeVisible()
  expect(screen.getByRole('img',{name:/Sun disk visible fraction over UTC/})).toBeVisible()
  expect(container.querySelectorAll('circle')).toHaveLength(4)
  for(const text of ['NONE','UNKNOWN','PARTIAL','false','0']) expect(screen.getAllByRole('cell',{name:text}).length).toBeGreaterThan(0)
  expect(screen.getByRole('table')).toHaveAccessibleName(/Sun samples/)
})
it('handles malformed Sun data independently of a valid Earth panel',()=>{
  const response=scientificFixture(),series=response.series as {sun:object}[]
  series[0]!.sun={...series[0]!.sun,disk_visible_fraction:2}
  render(<><section aria-label="Sun test"><BodyData response={response} body="sun" bounds={bounds} /></section><section aria-label="Earth test"><BodyData response={response} body="earth" bounds={bounds} /></section></>)
  expect(within(screen.getByRole('region',{name:'Sun test'})).getByRole('alert')).toHaveTextContent('Invalid scientific response data')
  expect(within(screen.getByRole('region',{name:'Earth test'})).getAllByRole('img')).toHaveLength(2)
  expect(screen.getByText('Geometric Earth visibility does not establish a verified radio link or data transfer rate.')).toBeVisible()
})
it('announces bounded rendering instead of silently sampling a large validated series',()=>{
  const response=scientificFixture(),sample=response.series![0] as {sun:unknown;earth:unknown;joint_condition_met:unknown}
  response.series=Array.from({length:101},(_,i)=>({...sample,time_utc:new Date(Date.parse('2026-11-14T12:30:00Z')+i*1000).toISOString()}))
  const {container}=render(<BodyData response={response} body="sun" bounds={bounds} />)
  expect(screen.getByText('Showing the first 100 of 101 validated records. Later records are not shown; no values were interpolated.')).toBeVisible()
  expect(container.querySelectorAll('tbody tr')).toHaveLength(100)
  expect(container.querySelectorAll('circle')).toHaveLength(200)
})
it('separates null, calculated-empty, half-open intervals and censored boundaries',()=>{
  render(<TimelineData response={scientificFixture()} bounds={bounds} />)
  expect(screen.getByText('Windows not calculated (null).')).toBeVisible()
  expect(screen.getByText('Calculated — no matching windows (empty array).')).toBeVisible()
  expect(screen.getByRole('table')).toHaveAccessibleName('Sun half-open intervals [start UTC, end UTC)')
  expect(screen.getByRole('cell',{name:'true'})).toBeVisible()
  expect(screen.getByRole('cell',{name:'false'})).toBeVisible()
})
it('keeps decision null/boolean/zero values without invented units or automatic approval',()=>{
  render(<DecisionData response={scientificFixture()} />)
  expect(screen.getByRole('table')).toHaveAccessibleName(/units are not specified/)
  expect(screen.getByRole('cell',{name:'0'})).toBeVisible()
  expect(screen.getByRole('cell',{name:'Unknown (null)'})).toBeVisible()
  expect(screen.getByRole('cell',{name:'false'})).toBeVisible()
})
it('renders actual zero score with quality warning, but distinguishes null and unknown model version',()=>{
  const response=scientificFixture()
  const {rerender}=render(<ScoreData response={response} />)
  expect(screen.getByLabelText('Backend planning score')).toHaveTextContent('0 / 100')
  expect(screen.getByText(/Data quality limitation: LIMITED/)).toBeVisible()
  rerender(<ScoreData response={{...response,score:{...response.score,value:null}}} />)
  expect(screen.getByRole('heading',{name:'Not calculated'})).toBeVisible()
  expect(screen.queryByLabelText('Backend planning score')).not.toBeInTheDocument()
  rerender(<ScoreData response={{...response,score:{...response.score,model_version:null,value:75}}} />)
  expect(screen.getByRole('heading',{name:'Score withheld'})).toBeVisible()
  expect(screen.queryByLabelText('Backend planning score')).not.toBeInTheDocument()
})
it('shows quality/provenance, preserves unknown coverage and never links an unsafe source URL',()=>{
  const response=scientificFixture(),source=(response.sources as object[])[0]!
  response.sources=[{...source,url:'javascript:alert(1)'}]
  response.quality={...response.quality,status:'INSUFFICIENT',coverage_complete:null}
  render(<QualityData response={response} />)
  expect(screen.getByText('Coverage complete: Unknown (null)')).toBeVisible()
  expect(screen.getByText('INSUFFICIENT')).toBeVisible()
  expect(screen.getByText('c'.repeat(64))).toBeVisible()
  expect(screen.queryByRole('link')).not.toBeInTheDocument()
  expect(screen.getByText(/unsupported or unsafe URL; not a link/)).toBeVisible()
})
