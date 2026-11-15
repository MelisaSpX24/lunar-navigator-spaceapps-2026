import { useMemo } from 'react'
import type { AnalysisResponse } from '../../services/api/responses'
import { checkQuality, checkSources, safeSourceUrl, TABLE_ROWS } from './validation'
import { DataMessage, DisplayCount, show } from './Presentation'
import styles from './Results.module.css'

export function QualityData({ response }: { response: AnalysisResponse }) {
  const quality = useMemo(() => checkQuality(response.quality), [response.quality])
  const sources = useMemo(() => checkSources(response.sources), [response.sources])
  return <div className={styles.content}>
    {quality.kind !== 'valid' ? <DataMessage data={quality} /> : <>
      <p>Quality status: <strong>{quality.value.status}</strong></p>
      <p>Coverage complete: {show(quality.value.coverage_complete)}</p>
      {(quality.value.status !== 'SUFFICIENT' || quality.value.coverage_complete !== true) && <p className={styles.warning}>Coverage or scientific evidence is limited, incomplete or unassessed. Missing coverage is not complete coverage.</p>}
      {quality.value.limitations.map((v, i) => <p key={i}>Quality limitation: {v}</p>)}
    </>}
    {response.limitations.map((v, i) => <p key={i}>Response limitation: {v}</p>)}
    <h3>Source evidence</h3>
    <p>Metadata and SHA-256 values are supplied by the backend. Their presence does not independently verify NASA origin, authenticity or scientific accuracy.</p>
    {sources.kind !== 'valid' ? <DataMessage data={sources} /> : sources.value.length === 0 ? <p>No source records supplied (empty array). No verified NASA source list can be claimed.</p> : <>
      <DisplayCount total={sources.value.length} shown={Math.min(sources.value.length, TABLE_ROWS)} />
      {sources.value.slice(0, TABLE_ROWS).map((s, i) => <section key={i} className={styles.source} aria-label={`Source ${s.id}`}>
        <h4>{s.id} — {s.kind}</h4><p>Product: {s.product}</p><p>Version: {s.version}</p>
        <p>URL: {safeSourceUrl(s.url) ? <a href={safeSourceUrl(s.url)!} target="_blank" rel="noopener noreferrer">{s.url}</a> : <><span>{s.url}</span> — unsupported or unsafe URL; not a link.</>}</p>
        <p>Provided SHA-256: <code>{s.sha256}</code></p>
      </section>)}
    </>}
  </div>
}
