import { PositionStatus } from './PositionStatus'
import { useCelestialTime } from './CelestialTime'
import { show } from '../analysis-results/Presentation'
import { hasDirection } from './selection'
import styles from './Celestial.module.css'

export function SelectedBody({ body }: { body: 'sun' | 'earth' }) {
  const time = useCelestialTime(), label = body === 'sun' ? 'Sun' : 'Earth'
  if (!time?.result) return null
  const sample = body === 'sun' ? time.sunSample : time.earthSample
  const data = time[body]
  return <section className={styles.block} aria-label={`${label} Selected UTC Sample`}>
    <h3>Selected UTC Sample — {label}</h3>
    {time.result.response.data_origin === 'TEST_FIXTURE' && <p className={styles.warning}>TEST DATA — synthetic celestial positions</p>}
    <p>Selected UTC: {time.selected?.text ?? 'Unavailable'}</p>
    <PositionStatus name={label} position={body === 'sun' ? time.sunPosition : time.earthPosition} />
    {data.kind !== 'valid' ? <p>Selected sample unavailable: {data.kind === 'missing' ? 'Data not provided (null).' : data.message}</p> : !sample ? <p>No sample at selected time. No exact backend sample at this time; disk state, fraction, clearance and condition are not evaluated.</p> : <>
      <p>Backend sample UTC: {sample.time.text}. No visual interpolation.</p>
      {!hasDirection(sample.body) && <p>Direction unavailable — marker hidden.</p>}
      <dl>{[['Azimuth (°)',sample.body.azimuth_deg],['Elevation (°)',sample.body.elevation_deg],['Angular radius (°), backend',sample.body.angular_radius_deg],['Disk state',sample.body.disk_state],['Disk visible fraction, backend',sample.body.disk_visible_fraction],['Condition met',sample.body.condition_met],['Horizon profile ID',sample.body.horizon_id],['Center clearance (°), backend',sample.body.center_clearance_deg]].map(([key,value]) => <div key={String(key)}><dt>{key}</dt><dd>{show(value ?? null)}</dd></div>)}</dl>
    </>}
  </section>
}
