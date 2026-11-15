import { render, screen, fireEvent } from '@testing-library/react'
import { expect, it } from 'vitest'
import { scientificFixture } from '../../test/scientificFixtures'
import { timeBounds } from '../analysis-results/utc'
import { CelestialTimeProvider, TimeSelector } from './CelestialTime'
import { SelectedBody } from './SelectedBody'
import { TimelineData } from '../analysis-results/TimelineData'
import { requestFixture } from '../../test/apiFixtures'
const bounds=timeBounds('2026-11-14T12:30:00Z',3600)
const result=()=>({response:scientificFixture(),request:requestFixture(),bounds})
it('one UTC source synchronizes controls, sample values and timeline; resets on new response',()=>{
 const r=result()
 const view=(value:ReturnType<typeof result>|null)=><CelestialTimeProvider result={value}><TimeSelector/><SelectedBody body="sun"/><SelectedBody body="earth"/>{value&&<TimelineData response={value.response} bounds={bounds}/>}</CelestialTimeProvider>
 const {rerender}=render(view(r))
 expect(screen.getByLabelText('Selected UTC')).toHaveTextContent('12:30:00')
 fireEvent.click(screen.getByText('Next sample',{exact:true}))
 expect(screen.getByLabelText('Selected UTC')).toHaveTextContent('12:40:00')
 expect(screen.getByLabelText('Timeline selected UTC')).toHaveTextContent('12:40:00')
 expect(screen.getByLabelText('Sun Selected UTC Sample')).toHaveTextContent('UNKNOWN')
 fireEvent.click(screen.getByText('Last sample',{exact:true}))
 expect(screen.getByLabelText('Earth Selected UTC Sample')).toHaveTextContent('PARTIAL')
 fireEvent.change(screen.getByLabelText('Selected UTC time'),{target:{value:'1'}})
 expect(screen.getByLabelText('Sun Selected UTC Sample')).toHaveTextContent('No sample at selected time')
 fireEvent.click(screen.getByText('Previous sample',{exact:true}))
 expect(screen.getByLabelText('Sun Selected UTC Sample')).toHaveTextContent('false')
 rerender(view({...result()}));expect(screen.getByLabelText('Selected UTC')).toHaveTextContent('12:30:00')
 rerender(view(null));expect(screen.getByLabelText('Selected UTC time')).toBeDisabled()
 expect(screen.queryByLabelText('Sun Selected UTC Sample')).toBeNull()
})
it.each([null,[]])('disables scientific slider for %j series',series=>{
 const r=result();r.response.series=series
 render(<CelestialTimeProvider result={r}><TimeSelector/></CelestialTimeProvider>)
 expect(screen.getByLabelText('Selected UTC time')).toBeDisabled()
})
it('one sample permits exact inspection but no next/previous or fabricated motion',()=>{
 const r=result();r.response.series=r.response.series!.slice(0,1)
 render(<CelestialTimeProvider result={r}><TimeSelector/></CelestialTimeProvider>)
 expect(screen.getByText('Next sample',{exact:true})).toBeDisabled()
 expect(screen.getByText('Previous sample',{exact:true})).toBeDisabled()
 expect(screen.getByRole('button',{name:'Play'})).toBeDisabled()
})
