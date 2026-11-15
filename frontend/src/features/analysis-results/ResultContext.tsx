import { useMemo } from 'react'
import type { AnalysisResponse } from '../../services/api/responses'
import type { AnalysisRequestV1 } from '../mission-input/analysisRequest'
import type { TimeBounds } from './utc'
import { checkQuality, checkResolvedSite } from './validation'
import { DataMessage, show } from './Presentation'
import styles from './Results.module.css'

export function ResultContext({ response, request, bounds }: { response: AnalysisResponse; request: AnalysisRequestV1; bounds: TimeBounds }) {
  const quality = useMemo(() => checkQuality(response.quality), [response.quality])
  const site = useMemo(() => checkResolvedSite(response.resolved_site), [response.resolved_site])
  return <section className={styles.context} aria-labelledby="result-context-title">
    <h2 id="result-context-title">Scientific response context</h2>
    {response.data_origin === 'TEST_FIXTURE' && <p className={styles.warning} role="note"><strong>TEST DATA — This response is not a live scientific assessment.</strong></p>}
    <p>Execution: COMPLETED. Data origin: {response.data_origin ?? 'Not provided (null); provenance is unknown'}.</p>
    <p>Matched scenario: {request.site.latitude_deg}° latitude, {request.site.longitude_deg_east}° east longitude; {request.site.frame}, {request.site.latitude_type}.</p>
    <p>UTC interval: {bounds.start.text} to {bounds.end.text}; duration {request.time.duration_s} seconds.</p>
    {site.kind === 'valid' ? <p>Resolved site: {site.value.latitude_deg}°, {site.value.longitude_deg_east}° E. Surface elevation: {show(site.value.surface_elevation_m)}{site.value.surface_elevation_m !== null ? ' m' : ''}. Height datum: {site.value.height_datum_id ?? 'Not provided (null)'}.</p> : site.kind === 'missing' ? <p>Resolved site not provided (null); the input coordinate is not a measured DEM elevation.</p> : <DataMessage data={site} />}
    <p>Quality: {quality.kind === 'valid' ? `${quality.value.status}; coverage complete: ${show(quality.value.coverage_complete)}` : 'Invalid or missing quality metadata'}.</p>
    <p>Format validation is not scientific certification. Review each panel, source evidence and limitations before interpreting backend values.</p>
  </section>
}
