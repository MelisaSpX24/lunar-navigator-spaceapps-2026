import { StrictMode } from 'react'
import { act, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { celestialFixture } from '../../test/celestialFixture'
import { requestFixture } from '../../test/apiFixtures'
import { timeBounds } from '../analysis-results/utc'
import { CelestialTimeProvider, TimeSelector, useCelestialTime } from './CelestialTime'
import { SelectedBody } from './SelectedBody'
import { TimelineData } from '../analysis-results/TimelineData'
let now=0, id=0, frames:Map<number,FrameRequestCallback>, media:EventTarget & {matches:boolean}, hidden=false
beforeEach(()=>{
 now=0;id=0;hidden=false;frames=new Map()
 vi.spyOn(performance,'now').mockImplementation(()=>now)
 vi.stubGlobal('requestAnimationFrame',vi.fn((cb:FrameRequestCallback)=>{frames.set(++id,cb);return id}))
 vi.stubGlobal('cancelAnimationFrame',vi.fn((key:number)=>frames.delete(key)))
 media=Object.assign(new EventTarget(),{matches:false})
 vi.stubGlobal('matchMedia',()=>media)
 vi.spyOn(document,'hidden','get').mockImplementation(()=>hidden)
})
afterEach(()=>vi.restoreAllMocks())
function advance(ms:number, step=50){for(let n=0;n<ms;n+=step){act(()=>{now+=Math.min(step,ms-n);const pending=[...frames.values()];frames.clear();pending.forEach(f=>f(now))})}}
const make=()=>({response:celestialFixture(),request:requestFixture(),bounds:timeBounds('2026-11-14T12:30:00Z',3600)})
function Probe(){const t=useCelestialTime()!;return <span data-testid="motion">{t.sunPosition.kind}/{t.earthPosition.kind}</span>}
function view(r:ReturnType<typeof make>|null){return <StrictMode><CelestialTimeProvider result={r}><TimeSelector/><Probe/><SelectedBody body="sun"/><SelectedBody body="earth"/>{r&&<TimelineData response={r.response} bounds={r.bounds}/>}</CelestialTimeProvider></StrictMode>}
const button=(name:string)=>screen.getByRole('button',{name})
const click=(name:string)=>fireEvent.click(button(name))
const stamp=()=>screen.getByLabelText('Selected UTC').textContent
it('keeps exact default, labels smooth directions and never invents visibility between samples',()=>{
 render(view(make()));expect(screen.getByLabelText('Smooth visual preview')).not.toBeChecked()
 fireEvent.change(screen.getByLabelText('Selected UTC time'),{target:{value:'833'}})
 expect(screen.getByTestId('motion')).toHaveTextContent('unavailable/unavailable')
 fireEvent.click(screen.getByLabelText('Smooth visual preview'))
 expect(screen.getByTestId('motion')).toHaveTextContent('interpolated/interpolated')
 const readout=within(screen.getByLabelText('Sun Selected UTC Sample'))
 expect(readout.getByText('VISUAL INTERPOLATION — not a computed science sample')).toBeVisible()
 expect(readout.queryByText('PARTIAL',{exact:true})).toBeNull()
 expect(readout.queryByText('false',{exact:true})).toBeNull()
 expect(readout.queryByText('0.25',{exact:true})).toBeNull()
 click('First sample');expect(screen.getByTestId('motion')).toHaveTextContent('sample/sample')
 expect(readout.getByText('PARTIAL',{exact:true})).toBeVisible()
})
it('plays a single StrictMode clock, pauses without losing UTC, resumes and replays',()=>{
 render(view(make()));expect(frames.size).toBe(0)
 click('Play');expect(frames.size).toBe(1);advance(1000)
 const saved=stamp();expect(saved).toContain('12:31:00')
 expect(screen.getByLabelText('Selected UTC')).toHaveAttribute('aria-live','off')
 click('Pause');expect(frames.size).toBe(0);advance(1000);expect(stamp()).toBe(saved)
 click('Play');advance(1000);expect(stamp()).toContain('12:32:00')
 click('Pause');click('Replay');expect(stamp()).toContain('12:30:00');expect(frames.size).toBe(1)
})
it('speed changes pause, end clamps exactly and Replay alone restarts',()=>{
 render(view(make()));click('Play');advance(100)
 fireEvent.change(screen.getByLabelText('Playback duration'),{target:{value:'30'}})
 expect(frames.size).toBe(0)
 click('Last sample');click('Play');advance(20000)
 expect(stamp()).toContain('13:30:00');expect(frames.size).toBe(0)
 expect(button('Play')).toBeDisabled();expect(button('Replay')).toBeEnabled()
 expect(screen.getByRole('status',{name:'Playback status'})).toHaveTextContent('Playback ended')
 advance(1000);expect(stamp()).toContain('13:30:00')
 click('Replay');advance(1000);expect(stamp()).toContain('12:32:00')
})
it('manual slider, sample buttons and mode changes cancel playback without racing',()=>{
 render(view(make()));click('Play');advance(100)
 fireEvent.change(screen.getByLabelText('Selected UTC time'),{target:{value:'1000'}})
 expect(frames.size).toBe(0);const saved=stamp();advance(100);expect(stamp()).toBe(saved)
 click('Play');click('Next sample');expect(frames.size).toBe(0);expect(stamp()).toContain('12:40:00')
 click('Play');fireEvent.click(screen.getByLabelText('Smooth visual preview'));expect(frames.size).toBe(0)
})
it('backgrounding and long frame stalls stop without resuming or jumping',()=>{
 render(view(make()));click('Play');advance(100);const saved=stamp()
 act(()=>{hidden=true;document.dispatchEvent(new Event('visibilitychange'))});expect(frames.size).toBe(0)
 act(()=>{hidden=false;document.dispatchEvent(new Event('visibilitychange'))});advance(100);expect(stamp()).toBe(saved)
 click('Play');advance(1000,1000);expect(frames.size).toBe(0);expect(stamp()).toBe(saved)
})
it('new response, invalidation and unmount remove pending frames and old choices',()=>{
 const r=make(),ui=render(view(r));click('Play');advance(1000)
 ui.rerender(view(make()));expect(frames.size).toBe(0);expect(stamp()).toContain('12:30:00')
 click('Play');ui.rerender(view(null));expect(frames.size).toBe(0);expect(button('Play')).toBeDisabled()
 expect(screen.getByTestId('motion')).toHaveTextContent('unavailable/unavailable')
 ui.rerender(view(make()));click('Play');ui.unmount();expect(frames.size).toBe(0)
})
it('reduced motion disables animation and retains manual sample access, including preference changes',()=>{
 render(view(make()));click('Play')
 act(()=>{media.matches=true;media.dispatchEvent(new Event('change'))})
 expect(frames.size).toBe(0);expect(button('Play')).toBeDisabled();expect(screen.getByLabelText('Smooth visual preview')).toBeDisabled()
 click('Next sample');expect(stamp()).toContain('12:40:00')
 act(()=>{media.matches=false;media.dispatchEvent(new Event('change'))});expect(frames.size).toBe(0)
})
it.each([null,[],[celestialFixture().series![0]]])('disables playback for missing/empty/single series',series=>{
 const r=make();r.response.series=series;render(view(r));expect(button('Play')).toBeDisabled();expect(button('Replay')).toBeDisabled();expect(frames.size).toBe(0)
})
it('smooth playback needs an accepted interval and never changes windows or makes network requests',()=>{
 const r=make(),original=JSON.stringify(r.response),ui=render(view(r))
 fireEvent.click(screen.getByLabelText('Smooth visual preview'));click('Play');advance(1000)
 expect(screen.getByTestId('motion')).toHaveTextContent('interpolated/interpolated')
 expect(screen.getByLabelText('Timeline selected UTC')).toHaveTextContent(stamp()!)
 expect(JSON.stringify(r.response)).toBe(original);expect(fetch).not.toHaveBeenCalled()
 const invalid=make();for(const row of invalid.response.series as {sun:{horizon_id:null};earth:{horizon_id:null}}[]){row.sun.horizon_id=null;row.earth.horizon_id=null}
 ui.rerender(view(invalid));fireEvent.click(screen.getByLabelText('Smooth visual preview'));expect(button('Play')).toBeDisabled()
})

it.each([30,60,120])('uses elapsed wall time at the %s-second full-operation speed',seconds=>{
 render(view(make()))
 fireEvent.change(screen.getByLabelText('Playback duration'),{target:{value:String(seconds)}})
 click('Play');advance(1000)
 const actual=Date.parse(stamp()!), start=Date.parse('2026-11-14T12:30:00Z')
 expect(actual-start).toBe(3600*1000/seconds)
})
