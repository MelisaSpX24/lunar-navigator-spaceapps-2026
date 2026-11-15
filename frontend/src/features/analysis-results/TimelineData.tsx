import { useCelestialTime } from '../celestial-timeline/CelestialTime'
import { useMemo, useId } from 'react'
import type { AnalysisResponse } from '../../services/api/responses'
import { checkWindows, TABLE_ROWS } from './validation'
import { timePosition, type TimeBounds } from './utc'
import { DataMessage, DataTable, DisplayCount, QualityNotice } from './Presentation'
import styles from './Results.module.css'

function WindowLane({ label, raw, bounds }: { label: string; raw: unknown; bounds: TimeBounds }) {
  const time = useCelestialTime()
  const id = useId(), data = useMemo(() => checkWindows(raw, bounds), [raw, bounds])
  if (data.kind !== 'valid') return <section><h3>{label} windows</h3><DataMessage data={data} missing="Windows not calculated (null)." /></section>
  const windows = data.value.slice(0, TABLE_ROWS)
  return <section>
    <h3>{label} windows</h3>
    {windows.length === 0 ? <p>Calculated — no matching windows (empty array).</p> : <>
      <DisplayCount total={data.value.length} shown={windows.length} />
      <figure className={styles.plot}>
        <figcaption>{label} visibility windows — server intervals</figcaption>
        <svg viewBox={`0 0 400 ${Math.max(40, windows.length * 20 + 10)}`} role="img" aria-labelledby={`${id}-title ${id}-desc`}>
          <title id={`${id}-title`}>{label} window timeline (UTC)</title><desc id={`${id}-desc`}>One labelled bar per server interval, starting inclusive and ending exclusive. Censored boundaries are listed in the table. No new windows are calculated.</desc>
          {time?.selected && <line aria-label="Selected UTC playhead" x1={timePosition(time.selected, bounds) * 400} x2={timePosition(time.selected, bounds) * 400} y1="0" y2={Math.max(40, windows.length * 20 + 10)} stroke="white" strokeWidth="2" />}
          {windows.map((w, index) => <rect key={index} x={timePosition(w.start, bounds) * 400} width={(timePosition(w.end, bounds) - timePosition(w.start, bounds)) * 400} y={index * 20 + 5} height="10" className={styles.window}><title>{w.definition_id}: [{w.start.text}, {w.end.text}); censored start {String(w.start_censored)}, end {String(w.end_censored)}</title></rect>)}
        </svg>
        <p>X: UTC from {bounds.start.text} to {bounds.end.text}. Each bar is a separate server record.</p>
      </figure>
      <DataTable caption={`${label} half-open intervals [start UTC, end UTC)`} headings={['Definition ID','Start (UTC, inclusive)','End (UTC, exclusive)','Start censored','End censored']}>
        {windows.map((w, index) => <tr key={index}><th scope="row">{w.definition_id}</th><td className={styles.literal}>{w.start.text}</td><td className={styles.literal}>{w.end.text}</td><td>{String(w.start_censored)}</td><td>{String(w.end_censored)}</td></tr>)}
      </DataTable>
      <p>Censored true means that boundary is not fully observed within the analysis window.</p>
    </>}
  </section>
}
export function TimelineData({ response, bounds }: { response: AnalysisResponse; bounds: TimeBounds }) {
  const time = useCelestialTime()
  return <div className={styles.content}>
    {time?.selected && <output aria-label="Timeline selected UTC" aria-live={time.playing ? 'off' : 'polite'}>Selected UTC: {time.selected.text}</output>}
    <QualityNotice value={response.quality} />
    <p>Server-provided half-open intervals: [start UTC, end UTC). Start included; end excluded.</p>
    {(['sun','earth','joint'] as const).map(key => <WindowLane key={key} label={key === 'joint' ? 'Joint' : key === 'sun' ? 'Sun' : 'Earth'} raw={response.windows[key]} bounds={bounds} />)}
  </div>
}
