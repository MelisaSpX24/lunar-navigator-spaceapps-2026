import { analysisFixture, requestFixture } from './apiFixtures'
import type { AnalysisResponse } from '../services/api/responses'

// Deliberately synthetic, TEST_FIXTURE only. No NASA measurement or operation proof.
export function scientificFixture(): AnalysisResponse {
  const body = (state: string, fraction: number | null, condition: boolean | null, elevation: number | null) => ({
    azimuth_deg: 30, elevation_deg: elevation, angular_radius_deg: .25, horizon_id: 'controlled-horizon-low',
    center_clearance_deg: null, disk_visible_fraction: fraction, disk_state: state, condition_met: condition,
  })
  return analysisFixture({
    execution_status: 'COMPLETED', data_origin: 'TEST_FIXTURE', request: requestFixture(),
    resolved_site: {latitude_deg:-85,longitude_deg_east:340,frame:'MOON_ME_DE421',latitude_type:'PLANETOCENTRIC',surface_elevation_m:0,height_datum_id:null},
    series: [
      {time_utc:'2026-11-14T12:30:00Z',sun:body('NONE',0,false,0),earth:body('FULL',1,true,5),joint_condition_met:false},
      {time_utc:'2026-11-14T12:40:00+00:00',sun:body('UNKNOWN',null,null,null),earth:body('UNKNOWN',null,null,null),joint_condition_met:null},
      {time_utc:'2026-11-14T12:50:00Z',sun:body('PARTIAL',.25,true,2),earth:body('PARTIAL',.5,false,0),joint_condition_met:false},
    ],
    horizons: [1,2].map((height,index)=>({
      id:index===0?'controlled-horizon-low':'controlled-horizon-high',observer_height_m:height,range_m:1200,coverage_complete:false,dem_source_ids:['controlled-source'],
      points:[{azimuth_deg:0,elevation_deg:0},{azimuth_deg:90,elevation_deg:null},{azimuth_deg:180,elevation_deg:-2},{azimuth_deg:270,elevation_deg:3}],
    })),
    windows: {
      sun:[{start_utc:'2026-11-14T12:30:00Z',end_utc:'2026-11-14T12:45:00Z',definition_id:'controlled-sun-definition',start_censored:true,end_censored:false}],
      earth:[],joint:null,
    },
    decision:{status:'INCOMPLETE',reason_codes:['CONTROLLED_TEST_ONLY'],rules:[
      {code:'controlled-met',status:'MET',required:true,actual:true,message:'Synthetic rule for UI testing only.'},
      {code:'controlled-not-met',status:'NOT_MET',required:1,actual:0,message:'Values have no contract-specified unit.'},
      {code:'controlled-incomplete',status:'INCOMPLETE',required:null,actual:false,message:'Unknown requirement is not zero.'},
    ]},
    score:{value:0,model_version:'controlled-ui-test-v1',components:[{name:'Controlled component',raw_value:0,normalized_value:0,weight:1}]},
    quality:{status:'LIMITED',coverage_complete:false,limitations:['Synthetic data with an intentional unknown sample.']},
    limitations:['TEST DATA only; no scientific calculation or NASA measurement.'],
    sources:[{id:'controlled-source',kind:'REFERENCE',product:'Controlled UI test product',version:'test-v1',url:'https://example.invalid/controlled-test',sha256:'c'.repeat(64)}],
  })
}
