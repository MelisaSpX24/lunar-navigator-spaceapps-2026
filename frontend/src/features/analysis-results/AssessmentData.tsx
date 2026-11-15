import { useMemo } from 'react'
import type { AnalysisResponse } from '../../services/api/responses'
import { checkDecision, checkQuality, checkScore, TABLE_ROWS } from './validation'
import { DataMessage, DataTable, DisplayCount, show, QualityNotice } from './Presentation'
import styles from './Results.module.css'

export function DecisionData({ response }: { response: AnalysisResponse }) {
  const data = useMemo(() => checkDecision(response.decision), [response.decision])
  if (data.kind !== 'valid') return <div className={styles.content}><DataMessage data={data} /></div>
  const d = data.value
  return <div className={styles.content}>
    <QualityNotice value={response.quality} />
    <p>Server decision: <strong>{d.status}</strong></p>
    <p>MET reports a requirement outcome, not NASA approval or landing safety certification. INCOMPLETE is an unfinished evaluation.</p>
    <p>Reason codes: {d.reason_codes.length ? d.reason_codes.join(', ') : 'None supplied; this is not automatic approval.'}</p>
    {d.rules.length === 0 ? <p>No rule records supplied (empty array). No successful operation is inferred.</p> : <>
      <DisplayCount total={d.rules.length} shown={Math.min(d.rules.length, TABLE_ROWS)} />
      <DataTable caption="Operation rules — units are not specified by this contract" headings={['Code','Status','Required','Actual','Message']}>
        {d.rules.slice(0, TABLE_ROWS).map((r, index) => <tr key={index}><th scope="row">{r.code}</th><td className={styles.literal}>{r.status}</td><td>{show(r.required)}</td><td>{show(r.actual)}</td><td>{r.message}</td></tr>)}
      </DataTable>
    </>}
  </div>
}
export function ScoreData({ response }: { response: AnalysisResponse }) {
  const score = useMemo(() => checkScore(response.score), [response.score])
  const quality = useMemo(() => checkQuality(response.quality), [response.quality])
  if (score.kind !== 'valid') return <div className={styles.content}><DataMessage data={score} /></div>
  const s = score.value
  return <div className={styles.content}>
    <p>Planning Score is not landing safety certification. No score or weight is calculated here.</p>
    {(quality.kind !== 'valid' || quality.value.status !== 'SUFFICIENT' || quality.value.coverage_complete !== true) && <p className={styles.warning}>Data quality limitation: {quality.kind === 'valid' ? `${quality.value.status}; coverage ${show(quality.value.coverage_complete)}` : 'Invalid or unknown quality metadata'}. A score does not repair missing scientific evidence.</p>}
    {s.value === null ? <h3>Not calculated</h3> : s.model_version === null ? <><h3>Score withheld</h3><p>Model version not provided; no verified scoring model can be claimed.</p></> : <p className={styles.score} aria-label="Backend planning score">{s.value} / 100</p>}
    <p>Model version: {s.model_version ?? 'Not provided (null)'}. Version text is supplied by the backend, not independently certified.</p>
    {s.components === null ? <p>Score components not provided (null). No weights are inferred.</p> : s.components.length === 0 ? <p>No score components supplied (empty array).</p> : <>
      <DisplayCount total={s.components.length} shown={Math.min(s.components.length, TABLE_ROWS)} />
      <DataTable caption="Score components — server values, no frontend aggregation" headings={['Name','Raw value (unit unspecified)','Normalized (0–1)','Weight (0–1)']}>
        {s.components.slice(0, TABLE_ROWS).map((c, index) => <tr key={index}><th scope="row">{c.name}</th><td>{c.raw_value}</td><td>{c.normalized_value}</td><td>{c.weight}</td></tr>)}
      </DataTable>
    </>}
  </div>
}
