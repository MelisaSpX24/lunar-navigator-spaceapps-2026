import { HorizonTrace } from './HorizonTrace'
import { traceSegments } from './trace'
import { PositionStatus } from '../../features/celestial-timeline/PositionStatus'
import { hasDirection } from '../../features/celestial-timeline/selection'
import { CelestialLayer, type CelestialView } from './CelestialLayer'
import { Canvas } from '@react-three/fiber'
import { useCallback, useEffect, useMemo, useState } from 'react'
import type { HorizonProfile } from '../../features/analysis-results/types'
import { GlobeBoundary } from '../globe/GlobeBoundary'
import { RendererLifecycle } from '../globe/RendererLifecycle'
import { ObserverControls } from './ObserverControls'
import { HorizonSamples, SkyReferences } from './SkyReferences'
import { INITIAL_VIEW, boundedView, type View } from './directions'
import styles from './LocalHorizon.module.css'

export default function HorizonScene({ profile, testData, celestial = null, playing = false, onUnavailable }: { profile: HorizonProfile | null; testData: boolean; celestial?: CelestialView | null; playing?: boolean; onUnavailable?: (() => void) | undefined }) {
  const [trace, setTrace] = useState(false)
  const traceCount = useMemo(() => traceSegments(profile).length / 6, [profile])
  const [sunPath, setSunPath] = useState(false), [earthPath, setEarthPath] = useState(false)
  const [view, setView] = useState<View>(INITIAL_VIEW)
  const [ready, setReady] = useState(false)
  const [failure, setFailure] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(0)
  const [interactive, setInteractive] = useState(() => !window.matchMedia?.('(pointer: coarse)').matches)
  const onReady = useCallback(() => setReady(true), [])
  const onLost = useCallback(() => setFailure('WebGL context lost'), [])
  const onError = useCallback(() => setFailure('WebGL unavailable'), [])
  useEffect(() => { if (failure) onUnavailable?.() }, [failure, onUnavailable])
  const disabled = !ready || !!failure
  return <div className={styles.scene}>
    {failure ? <div role="alert"><h4>{failure}</h4><p>3D view unavailable. Scientific horizon data remains accessible in the 2D chart below when provided.</p><button onClick={() => { setReady(false); setFailure(null); setAttempt(v => v + 1) }}>Retry 3D view</button></div> :
      <div className={styles.frame} style={{ pointerEvents: interactive ? 'auto' : 'none' }}>
        <span className={styles.sceneLabel}>{celestial?.testData ? 'TEST DATA — synthetic celestial positions' : testData ? 'TEST DATA · synthetic samples' : profile ? 'Backend angular samples' : celestial && (celestial.sunRows.some(row => hasDirection(row.body)) || celestial.earthRows.some(row => hasDirection(row.body))) ? 'Backend celestial samples · No measured terrain horizon' : 'Orientation guides only'}{profile && !profile.coverage_complete ? ' · Incomplete coverage' : ''}</span>
        <GlobeBoundary key={attempt} onError={onError}>
          <Canvas role="group" aria-label="Interactive local horizon sky" aria-describedby="horizon-help" frameloop="demand" dpr={[1, 1.5]} camera={{ position: [0, 0, 0], fov: INITIAL_VIEW.fov, near: .1, far: 20 }} gl={{ antialias: true }}>
            <color attach="background" args={['#07121e']} />
            <RendererLifecycle onReady={onReady} onLost={onLost} />
            <ObserverControls view={view} onView={setView} interactive={interactive} />
            <SkyReferences /><HorizonSamples profile={profile} />{trace && <HorizonTrace profile={profile} />}{celestial && <CelestialLayer data={celestial} sunPath={sunPath} earthPath={earthPath} />}
          </Canvas>
        </GlobeBoundary>
      </div>}
    <div className={styles.display} aria-label="Horizon display options">
      <label><input type="checkbox" checked={trace} onChange={e => setTrace(e.target.checked)} disabled={!profile} /> Panoramic Trace</label>
      <span>Sample Points always visible · {trace ? 'Panoramic Trace' : 'Sample Points'} mode</span>
      {trace && <p>Visual trace connects nearby supplied samples. Terrain between samples has not been independently measured by this view.</p>}
      {trace && traceCount === 0 && <p>Insufficient sampled coverage for panoramic trace.</p>}
    </div>
    <div className={styles.controls} role="group" aria-label="Local horizon camera controls">
      {(['North','East','South','West'] as const).map((name, i) => <button key={name} disabled={disabled} onClick={() => setView(v => ({ ...v, azimuth: i * 90 }))}>Look {name}</button>)}
      <button disabled={disabled} onClick={() => setView(v => ({ ...v, elevation: 0 }))}>Horizon level</button>
      <button disabled={disabled} onClick={() => setView(INITIAL_VIEW)}>Reset View</button>
      <button disabled={disabled} onClick={() => setView(v => boundedView({ ...v, elevation: v.elevation + 10 }))}>Look up</button>
      <button disabled={disabled} onClick={() => setView(v => boundedView({ ...v, elevation: v.elevation - 10 }))}>Look down</button>
      <button disabled={disabled} onClick={() => setView(v => boundedView({ ...v, fov: v.fov - 10 }))}>Zoom in</button>
      <button disabled={disabled} onClick={() => setView(v => boundedView({ ...v, fov: v.fov + 10 }))}>Zoom out</button>
      <button disabled={disabled} aria-pressed={interactive} onClick={() => setInteractive(v => !v)}>{interactive ? 'Pause 3D interaction' : 'Enable 3D interaction'}</button>
    </div>
    {celestial && <div className={styles.controls} role="group" aria-label="Celestial sample paths">
      <label><input type="checkbox" checked={sunPath} disabled={!celestial.sunRows.length} onChange={e => setSunPath(e.target.checked)} /> Show Sun path</label>
      <label><input type="checkbox" checked={earthPath} disabled={!celestial.earthRows.length} onChange={e => setEarthPath(e.target.checked)} /> Show Earth path</label>
      <p>Paths show discrete backend directions only. No lines bridge unknown or unsampled times.</p>
      <output aria-label="Scene UTC" aria-live={playing ? 'off' : 'polite'}>{celestial.utc ?? 'No validated samples'}</output>
    </div>}
    {celestial && <div aria-label="3D celestial position status"><PositionStatus compact name="Sun" position={celestial.sunPosition} /><PositionStatus compact name="Earth" position={celestial.earthPosition} />
      {(celestial.sunPosition.kind === 'interpolated' || celestial.earthPosition.kind === 'interpolated') && <p className={styles.testNotice}>VISUAL INTERPOLATION — not a computed science sample</p>}
    </div>}
    <p id="horizon-help">Drag to look around; scroll or pinch to change field of view. Camera stays at the observer origin. On touch screens, enable interaction first; pause to scroll the page. Direction buttons work with a keyboard.</p>
    {!ready && !failure && <p role="status">Loading local 3D scene…</p>}
    <output className={styles.orientation} aria-label="Local camera orientation" aria-live="polite">{failure ? '3D scene unavailable' : `${ready ? 'Local 3D scene ready' : 'Starting'} · Azimuth ${view.azimuth.toFixed(1)}° · Elevation ${view.elevation.toFixed(1)}° · FOV ${view.fov.toFixed(1)}°`}</output>
    <p>Coordinate guides: N 0°, E 90°, S 180°, W 270°. The 0° ring is a horizontal reference, not a measured terrain horizon. Display radius is angular presentation scale, not physical distance. Celestial directions, when available, are labeled as backend samples or guarded visual interpolation; marker sizes are illustrative, not to angular scale.</p>
  </div>
}
