import { useMemo } from 'react'
import type { AnalysisResponse } from '../../services/api/responses'
import { checkHorizons, checkSeries, TABLE_ROWS } from './validation'
import { timePosition, type TimeBounds } from './utc'
import { DataMessage, DataTable, DisplayCount, SamplePlot, show, QualityNotice } from './Presentation'
import styles from './Results.module.css'

export function HorizonData({ response }: { response: AnalysisResponse }) {
  const data = useMemo(() => checkHorizons(response.horizons), [response.horizons])
  if (data.kind !== 'valid') return <div className={styles.content}><DataMessage data={data} missing="Horizon profiles not calculated or not provided (null)." /></div>
  return <div className={styles.content}>
    <QualityNotice value={response.quality} />
    {data.value.length === 0 && <p>Calculated — no horizon profiles supplied (empty array).</p>}
    {data.value.map(h => <section key={h.id} className={styles.profile} aria-label={`Horizon ${h.id}`}>
      <h3>Profile: {h.id}</h3>
      <p>Observer height: {h.observer_height_m} m. Analysis range: {h.range_m} m.</p>
      <p>DEM source IDs: {h.dem_source_ids.length ? h.dem_source_ids.join(', ') : 'None supplied; source evidence is missing.'}</p>
      {!h.coverage_complete && <p className={styles.warning}>Incomplete horizon coverage — unknown terrain must not be treated as clear sky.</p>}
      {h.points.length === 0 ? <p>Calculated — no horizon points supplied.</p> : <SamplePlot title={`Horizon elevation — ${h.id}`} minimum={-90} maximum={90} yLabel="Horizon elevation (°)" xDescription="Azimuth (°), 0 inclusive to 360 exclusive"
        points={h.points.map(p => ({ x: p.azimuth_deg / 360, y: p.elevation_deg }))} />}
      <p>Chart covers all {h.points.length} validated records; unknown elevations have no marker. Table shows the first {Math.min(h.points.length, TABLE_ROWS)} rows.</p>
      <DataTable caption={`Horizon samples — ${h.id} (first ${TABLE_ROWS} at most)`} headings={['Azimuth (°)','Elevation (°)']}>
        {h.points.slice(0, TABLE_ROWS).map(p => <tr key={p.azimuth_deg}><th scope="row">{p.azimuth_deg}</th><td>{show(p.elevation_deg)}</td></tr>)}
      </DataTable>
    </section>)}
  </div>
}
export function BodyData({ response, body, bounds }: { response: AnalysisResponse; body: 'sun' | 'earth'; bounds: TimeBounds }) {
  const data = useMemo(() => checkSeries(response.series, body, bounds), [response.series, body, bounds])
  const label = body === 'sun' ? 'Sun' : 'Earth'
  if (data.kind !== 'valid') return <div className={styles.content}><DataMessage data={data} missing={`${label} time samples not calculated or not provided (null).`} /></div>
  const rows = data.value.slice(0, TABLE_ROWS)
  return <div className={styles.content}>
    <QualityNotice value={response.quality} />
    <p>{body === 'earth' ? 'Geometric Earth visibility does not establish a verified radio link or data transfer rate.' : 'Geometric Sun visibility does not establish electrical power output.'}</p>
    {data.value.length === 0 ? <p>Calculated — no {label} samples supplied (empty array).</p> : <>
      <DisplayCount total={data.value.length} shown={rows.length} />
      <SamplePlot title={`${label} elevation over UTC`} yLabel="Elevation (°)" minimum={-90} maximum={90} xDescription={`UTC from ${bounds.start.text} to ${bounds.end.text}`}
        points={rows.map(row => ({ x: timePosition(row.time, bounds), y: row.body.elevation_deg }))} />
      <SamplePlot title={`${label} disk visible fraction over UTC`} yLabel="Disk visible fraction" minimum={0} maximum={1} xDescription={`UTC from ${bounds.start.text} to ${bounds.end.text}`}
        points={rows.map(row => ({ x: timePosition(row.time, bounds), y: row.body.disk_visible_fraction }))} />
      <DataTable caption={`${label} samples — backend values (first ${TABLE_ROWS} at most)`} headings={['Time (UTC)','Azimuth (°)','Elevation (°)','Angular radius (°)','Center clearance (°)','Disk fraction (0–1)','Disk state','Condition met','Horizon ID']}>
        {rows.map(row => <tr key={row.time.text}><th scope="row" className={styles.literal}>{row.time.text}</th>{[row.body.azimuth_deg,row.body.elevation_deg,row.body.angular_radius_deg,row.body.center_clearance_deg,row.body.disk_visible_fraction,row.body.disk_state,row.body.condition_met,row.body.horizon_id].map((v, i) => <td key={i} className={i === 5 || i === 6 ? styles.literal : undefined}>{show(v)}</td>)}</tr>)}
      </DataTable>
    </>}
  </div>
}
