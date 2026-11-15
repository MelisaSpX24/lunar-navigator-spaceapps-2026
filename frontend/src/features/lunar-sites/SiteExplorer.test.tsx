import { render,screen,fireEvent,within,waitFor } from '@testing-library/react'
import { validForm,healthFixture,analysisFixture,jsonResponse } from '../../test/apiFixtures'
import type { MissionFormState } from '../mission-input/missionState'
import { SITE_CATALOG } from './siteCatalog'
import { ScenarioProvider,useScenario } from '../scenario/ScenarioProvider'
import { expect,it,vi } from 'vitest'
import { SiteExplorer } from './SiteExplorer'
function setup(){const onUse=vi.fn(),onView=vi.fn(),onInspect=vi.fn();render(<SiteExplorer latitude="" longitude="" inspected={null} onInspect={onInspect} onView={onView} onUse={onUse}/>);return {onUse,onView,onInspect}}
it('lists sources and disabled reasons with accessible actions, including a research visual reference',()=>{
 const {onUse,onView,onInspect}=setup()
 expect(screen.getAllByRole('article')).toHaveLength(5)
 const cr1=within(screen.getByRole('article',{name:'Site01 / CR1 Research Point'}))
 fireEvent.click(cr1.getByRole('button',{name:/Inspect/}));expect(onInspect).toHaveBeenCalledWith('site01-cr1-research')
 fireEvent.click(cr1.getByRole('button',{name:/View on Globe/}));expect(onView).toHaveBeenCalledOnce()
 expect(cr1.getByRole('button',{name:/Use These Coordinates/})).toBeDisabled()
 expect(screen.getAllByRole('button',{name:/Use These Coordinates/}).every(b=>(b as HTMLButtonElement).disabled)).toBe(true)
 expect(onUse).not.toHaveBeenCalled()
 const region=within(screen.getByRole('article',{name:'Mons Mouton'}))
 expect(region.getByRole('button',{name:/View on Globe/})).toBeDisabled()
 for(const link of screen.getAllByRole('link'))expect(link).toHaveAttribute('rel','noopener noreferrer')
})

it('a future evidence-verified coordinate uses shared scenario selection without changing operation inputs',()=>{
 const site={...SITE_CATALOG[4]!,coordinate:{...SITE_CATALOG[4]!.coordinate!,compatibility:'VERIFIED' as const,coordinateEvidence:{objectId:SITE_CATALOG[4]!.id,sourceUrl:SITE_CATALOG[4]!.sources[0]!.url,review:'DIRECTLY_REVIEWED' as const,latitudeTypeVerified:true as const,frameVerified:true as const}},sources:[{...SITE_CATALOG[4]!.sources[0]!,access:'VERIFIED' as const,review:'DIRECTLY_REVIEWED' as const}]}
 function Harness(){const s=useScenario();return <><SiteExplorer sites={[site]} latitude={s.state.latitude} longitude={s.state.longitude} inspected={null} onInspect={()=>{}} onView={()=>{}} onUse={s.select}/><button onClick={()=>{s.change('utcDate','2026-11-14');s.change('utcTime','12:30');s.change('profile','EARTH_DATA_TRANSMISSION')}}>Prepare inputs</button><output data-testid="scenario">{s.state.latitude}|{s.state.longitude}|{s.state.profile}|{s.state.utcDate}|{s.state.utcTime}|{s.analysis.kind}</output></>}
 render(<ScenarioProvider><Harness/></ScenarioProvider>)
 fireEvent.click(screen.getByText('Prepare inputs'))
 fireEvent.click(screen.getByRole('button',{name:/Use These Coordinates/}))
 const fields=screen.getByTestId('scenario').textContent!.split('|')
 expect(Number(fields[0])).toBe(-89.468);expect(Number(fields[1])).toBeCloseTo(222.6,10)
 expect(fields.slice(2)).toEqual(['EARTH_DATA_TRANSMISSION','2026-11-14','12:30','idle'])
 expect(screen.getByText('Current location:',{exact:false})).toHaveTextContent('Site01 / CR1')
})

it('verified test-only transfer preserves every non-coordinate field, clears a prior response and never auto-posts',async()=>{
 const site={...SITE_CATALOG[4]!,coordinate:{...SITE_CATALOG[4]!.coordinate!,compatibility:'VERIFIED' as const,coordinateEvidence:{objectId:SITE_CATALOG[4]!.id,sourceUrl:SITE_CATALOG[4]!.sources[0]!.url,review:'DIRECTLY_REVIEWED' as const,latitudeTypeVerified:true as const,frameVerified:true as const}},sources:[{...SITE_CATALOG[4]!.sources[0]!,access:'VERIFIED' as const,review:'DIRECTLY_REVIEWED' as const}]}
 const wanted:MissionFormState={...validForm(),profile:'EARTH_DATA_TRANSMISSION',hours:'2',minutes:'15',seconds:'30',solarFraction:'0.75',minSun:'120',maxDark:'300',minEarth:'30',clearance:'1',simultaneous:true,minJoint:'20',solarHeight:'2',earthHeight:'3',fullHorizon:false,earthDisk:true,lookahead:'3600'}
 const mock=vi.fn().mockImplementation(async(url:string,options?:RequestInit)=>url.endsWith('/health')?jsonResponse(healthFixture(true)):jsonResponse(analysisFixture({request:JSON.parse(String(options?.body))}),503))
 vi.stubGlobal('fetch',mock)
 function Harness(){const s=useScenario();return <><SiteExplorer sites={[site]} latitude={s.state.latitude} longitude={s.state.longitude} inspected={null} onInspect={()=>{}} onView={()=>{}} onUse={s.select}/><button onClick={()=>{for(const [key,value] of Object.entries(wanted))s.change(key as keyof MissionFormState,value as never)}}>Prepare full scenario</button><button onClick={()=>{void s.run()}}>Submit controlled request</button><output aria-label="Full scenario probe">{JSON.stringify({state:s.state,analysis:s.analysis.kind,health:s.health.kind,valid:s.validation.valid,request:s.validation.request})}</output></>}
 render(<ScenarioProvider><Harness/></ScenarioProvider>)
 const probe=()=>JSON.parse(screen.getByLabelText('Full scenario probe').textContent!)
 await waitFor(()=>expect(probe().health).toBe('ready'))
 fireEvent.click(screen.getByText('Prepare full scenario'));expect(probe().valid).toBe(true)
 fireEvent.click(screen.getByText('Submit controlled request'))
 await waitFor(()=>expect(probe().analysis).toBe('not_ready'))
 fireEvent.click(screen.getByRole('button',{name:/Use These Coordinates/}))
 const {latitude,longitude,...rest}=probe().state
 const {latitude:_oldLatitude,longitude:_oldLongitude,...expected}=wanted
 expect(latitude).toBe('-89.468');expect(Number(longitude)).toBeCloseTo(222.6,10)
 expect(rest).toEqual(expected);expect(probe().analysis).toBe('idle')
 expect(probe().request.site.kind).toBe('COORDINATES')
 expect(mock.mock.calls.filter(call=>call[1]?.method==='POST')).toHaveLength(1)
})
