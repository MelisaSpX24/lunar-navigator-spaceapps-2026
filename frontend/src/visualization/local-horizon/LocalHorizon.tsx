import { useCelestialTime } from '../../features/celestial-timeline/CelestialTime'
import { hasDirection, horizonRelation } from '../../features/celestial-timeline/selection'
import type { CelestialView } from './CelestialLayer'
import { lazy, Suspense, useMemo, useState } from 'react'
import { GlobeBoundary } from '../globe/GlobeBoundary'
import { SceneViewport } from '../../components/SceneViewport'
import { checkHorizons } from '../../features/analysis-results/validation'
import { QualityNotice } from '../../features/analysis-results/Presentation'
import type { AnalysisResponse } from '../../services/api/responses'
import type { VisualCoordinate } from '../coordinates/lunarCoordinates'
import { visualLongitudeToEast } from '../../features/mission-input/coordinates'
import styles from './LocalHorizon.module.css'

const HorizonScene = lazy(() => import('./HorizonScene'))
/** response must come through completedResult: this component never fetches or
 * synthesizes scientific content. checkHorizons is the same gate used by 2D. */
export function LocalHorizon({ response, selected }: { response: AnalysisResponse | null; selected: VisualCoordinate | null }) {
  const time = useCelestialTime()
  const data = useMemo(() => checkHorizons(response?.horizons ?? null), [response])
  const [selection, setSelection] = useState<{ response: AnalysisResponse; id: string } | null>(null)
  const profiles = data.kind === 'valid' ? data.value : []
  const profile = profiles.find(p => selection?.response === response && p.id === selection.id) ?? profiles[0] ?? null
  const celestial = useMemo<CelestialView | null>(() => time?.result ? ({ sun: time.sunSample, earth: time.earthSample, sunPosition: time.sunPosition, earthPosition: time.earthPosition, sunRows: time.sun.kind === 'valid' ? time.sun.value : [], earthRows: time.earth.kind === 'valid' ? time.earth.value : [], utc: time.selected?.text ?? null, testData: time.result.response.data_origin === 'TEST_FIXTURE' }) : null, [time])
  const hasBodies = celestial?.sunRows.some(row => hasDirection(row.body)) || celestial?.earthRows.some(row => hasDirection(row.body))
  const known = profile?.points.filter(p => p.elevation_deg !== null).length ?? 0
  return <section className={styles.wrapper} aria-label="Interactive 3D Horizon">
    <h3>Interactive 3D Horizon</h3>
    <p>{selected && selected.longitude !== null && Math.abs(selected.latitude) < 90
      ? `Selected observer coordinate: ${selected.latitude.toFixed(3)}° latitude, ${visualLongitudeToEast(selected.longitude).toFixed(3)}° east longitude. Camera motion does not change this location.`
      : 'No valid observer coordinate — this orientation scene is not tied to a scientific observation site.'}</p>
    <p className={styles.notice}>{profile ? 'Backend Horizon View — backend-provided angular samples; not a physical DEM terrain mesh.' : hasBodies ? 'Backend celestial samples — no measured terrain horizon available. Celestial directions are labeled as backend samples or visual previews.' : 'Orientation preview only — no measured terrain horizon or celestial positions are available.'}</p>
    {response?.data_origin === 'TEST_FIXTURE' && profile && <p className={styles.testNotice}>TEST DATA — synthetic horizon profile</p>}
    {celestial?.testData && <p className={styles.testNotice}>TEST DATA — synthetic celestial positions</p>}

    {response && <QualityNotice value={response.quality} />}
    {data.kind === 'invalid' || data.kind === 'limited' ? <p>3D horizon withheld: {data.message} No terrain is inferred; see the 2D validation message below.</p> : null}
    {response && <p>Data origin: {response.data_origin ?? 'Unknown — no independently verified provenance'}</p>}
    {profile && <>
      <label htmlFor="horizon-profile">3D horizon profile</label>
      <select id="horizon-profile" value={profile.id} onChange={e => { if (response) setSelection({ response, id: e.target.value }) }}>
        {profiles.map(p => <option key={p.id} value={p.id}>{p.id} · {p.observer_height_m} m observer · {p.range_m} m range</option>)}
      </select>

    </>}
    {profile && <p>Observer height: {profile.observer_height_m} m · Range: {profile.range_m} m · {profile.coverage_complete ? 'Coverage reported complete' : 'Incomplete terrain horizon coverage'}</p>}
    <SceneViewport label="Local horizon view" caption={profile ? 'BACKEND ANGULAR HORIZON' : hasBodies ? 'BACKEND CELESTIAL SAMPLES' : 'ORIENTATION PREVIEW'} footer="Observer-centred directions only — not landing safety evidence" interactive>
      <GlobeBoundary><Suspense fallback={<p role="status">Loading local 3D module…</p>}><HorizonScene onUnavailable={time?.pause} playing={time?.playing ?? false} celestial={celestial} profile={profile} testData={!!profile && response?.data_origin === 'TEST_FIXTURE'} /></Suspense></GlobeBoundary>
    </SceneViewport>
    {profile && <>
      <div aria-live="polite" className={styles.metadata}>
        <p>Active profile: {profile.id}. Observer height: {profile.observer_height_m} m. Range: {profile.range_m} m.</p>
        <p>{profile.coverage_complete ? 'Backend reports complete horizon coverage.' : 'Incomplete terrain horizon coverage'}</p>
        <p>{known} known angular samples / {profile.points.length - known} unknown elevations. Sample points remain visible; optional visual guides do not fill sectors or close the seam. Unsampled directions remain unknown.</p>
        <p>DEM source IDs: {profile.dem_source_ids.join(', ') || 'None supplied'}. Source IDs are not independent source verification.</p>
      </div>
    </>}
    {celestial && <div aria-label="Celestial horizon relationships">
      {(['sun','earth'] as const).map(body => {
        const position = body === 'sun' ? celestial.sunPosition : celestial.earthPosition
        const sample = celestial[body]
        const relation = sample ? horizonRelation(sample.body, profiles, profile?.id ?? null)
          : position.kind === 'interpolated' ? horizonRelation({ horizon_id: position.horizonId }, profiles, profile?.id ?? null) : 'No sample at selected time.'
        return <p key={body}>{body === 'sun' ? 'Sun' : 'Earth'}: {relation}</p>
      })}
      <p>Position above plotted horizon points does not prove visibility. Only backend disk state and conditions describe visibility. Celestial markers are illustrative and not to angular scale.</p>
    </div>}
    <p>Numeric horizon samples remain available in the 2D section below. Missing elevations are never interpreted as clear sky.</p>
  </section>
}
