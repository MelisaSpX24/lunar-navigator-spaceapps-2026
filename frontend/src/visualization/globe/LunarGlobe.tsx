import { CandidateMarkers,type GlobeCandidate } from './CandidateMarkers'
import { memo, useCallback, useEffect, useState } from 'react'
import { Canvas } from '@react-three/fiber'
import { EmptyState, LoadingState, UnsupportedDataState } from '../../components/States'
import { GlobeBoundary } from './GlobeBoundary'
import { GlobeControls, INITIAL_CAMERA, type CameraCommand, type ViewState } from './GlobeControls'
import { SiteMarkers } from './SiteMarkers'
import type { SiteFocus } from './GlobeControls'
import { MoonMesh } from './MoonMesh'
import { NASA_PAGE, TEXTURE_UNAVAILABLE, VERIFIED_TEXTURE_URL } from './moonTexture'
import { useMoonTexture } from './useMoonTexture'
import { RendererLifecycle } from './RendererLifecycle'
import type { VisualCoordinate } from '../coordinates/lunarCoordinates'
import styles from './LunarGlobe.module.css'

export default memo(function LunarGlobe({ selected, onSelect, siteFocus, onInspectSite, candidates, selectedCandidate, onSelectCandidate }: { selected: VisualCoordinate | null; onSelect: (coordinate: VisualCoordinate) => void; siteFocus?: SiteFocus | null; onInspectSite?: (id:string)=>void; candidates?:GlobeCandidate[];selectedCandidate?:string|null;onSelectCandidate?:(id:string)=>void }) {
  const [ready, setReady] = useState(false)
  const [failure, setFailure] = useState<'lost' | 'unavailable' | null>(null)
  const [interactive, setInteractive] = useState(() => !window.matchMedia?.('(pointer: coarse)').matches)
  const [command, setCommand] = useState<CameraCommand>({ kind: 'reset', sequence: 0 })
  const [view, setView] = useState<ViewState | null>(null)
  const texture = useMoonTexture(VERIFIED_TEXTURE_URL)
  const onReady = useCallback(() => setReady(true), [])
  const onLost = useCallback(() => setFailure('lost'), [])
  const onUnavailable = useCallback(() => setFailure('unavailable'), [])
  useEffect(() => { if(siteFocus) setCommand(siteFocus) }, [siteFocus])
  function move(kind: 'south' | 'reset') { setCommand(previous => ({ kind, sequence: previous.sequence + 1 })) }

  return <div className={styles.globe}>
    <p className={`${styles.textureNotice} ${texture.status === 'ready' ? styles.textureReady : ''}`} role="status">{texture.status === 'ready' ? 'NASA color texture loaded — visual imagery only' : texture.status === 'loading' ? 'Loading NASA texture…' : TEXTURE_UNAVAILABLE}</p>
    <div className={styles.toolbar} role="group" aria-label="Globe camera controls">
      <button type="button" disabled={!ready || !!failure} onClick={() => move('south')}>Focus South Pole</button>
      <button type="button" disabled={!ready || !!failure} onClick={() => move('reset')}>Reset View</button>
      <button type="button" disabled={!ready || !!failure} aria-pressed={interactive} onClick={() => setInteractive(value => !value)}>{interactive ? 'Pause globe interaction' : 'Enable globe interaction'}</button>
    </div>
    {onInspectSite && <p className={styles.help}>Amber diamond: catalog research reference, absolute registration not verified. Marker size is illustrative. Click to inspect sources; use the list for keyboard access. It does not select mission coordinates.</p>}
    <p id="globe-help" className={styles.help}>Drag to rotate. Scroll or pinch to zoom. On touch screens, enable globe interaction first; pause it to scroll the page normally. Selection is visual only. Use the mission form for numeric coordinate entry.</p>
    {!ready && !failure && <LoadingState title="Loading 3D scene">Starting the WebGL renderer.</LoadingState>}
    <div className={styles.frame} style={{ pointerEvents: interactive ? 'auto' : 'none' }}>
      {failure ? <UnsupportedDataState title={failure === 'lost' ? 'WebGL context lost' : 'WebGL unavailable'}>The 3D view stopped. Reload to try again; other screens remain available.</UnsupportedDataState> :
        <GlobeBoundary onError={onUnavailable}><Canvas
          aria-label="Interactive 3D lunar sphere" aria-describedby="globe-help"
          frameloop="demand" dpr={[1, 1.5]}
          style={{ pointerEvents: interactive ? 'auto' : 'none' }}
          camera={{ position: INITIAL_CAMERA, fov: 45, near: 0.05, far: 30 }}
          fallback={<UnsupportedDataState title="WebGL unavailable">Other mission screens remain available.</UnsupportedDataState>}
        >
          <RendererLifecycle onReady={onReady} onLost={onLost} />
          <ambientLight intensity={1.2} />
          <directionalLight position={[4, 3, 5]} intensity={2} />
          <GlobeControls command={command} onView={setView} interactive={interactive} />
          <MoonMesh texture={texture.texture} selected={selected} onSelect={onSelect} />
          {candidates&&onSelectCandidate&&<CandidateMarkers candidates={candidates} selected={selectedCandidate??null} onSelect={onSelectCandidate}/>}
          {onInspectSite && <SiteMarkers onInspect={onInspectSite} />}
        </Canvas></GlobeBoundary>}
    </div>
    <div className={styles.readouts}>
      <output aria-label="Camera view">{ready && !failure && view ? `3D scene ready · View latitude ${view.latitude.toFixed(1)}° · View longitude ${view.longitude.toFixed(1)}° · Camera distance ${view.distance.toFixed(2)} R` : failure ? '3D scene unavailable' : '3D scene starting'}</output>
      <div aria-live="polite" aria-atomic="true">
        {selected ? <div className={styles.selection}>
          <h3>Selected visual coordinate</h3>
          <dl><div><dt>Latitude</dt><dd>{selected.latitude.toFixed(3)}°</dd></div>
            <div><dt>Longitude</dt><dd>{selected.longitude === null ? 'Undefined at pole' : `${Math.abs(selected.longitude).toFixed(3)}° ${selected.longitude < 0 ? 'W' : 'E'}`}</dd></div></dl>
          <p>Signed longitude: {selected.longitude === null ? 'undefined' : `${selected.longitude.toFixed(3)}°`} (−180° to +180°).</p>
        </div> : <EmptyState title="No surface point selected">Click or tap the sphere to inspect a visual coordinate.</EmptyState>}
      </div>
    </div>
    <p className={styles.help}>Illustrative lighting — not the Moon’s illumination at a selected UTC time. The reference grid marks the equator and prime meridian in geometric preview mode. No elevation or visibility can be inferred.</p>
    <p className={styles.credit}>Imagery source: <a href={NASA_PAGE} target="_blank" rel="noreferrer">NASA Scientific Visualization Studio / Lunar Reconnaissance Orbiter</a>. {texture.status === 'ready' ? 'Imagery: NASA Scientific Visualization Studio / Lunar Reconnaissance Orbiter. Served locally from the user-supplied, checksum-verified JPEG.' : 'NASA imagery is not displayed while the local asset is loading or unavailable.'} Color imagery is not elevation data; polar image gaps may contain supplementary imagery.</p>
  </div>
})
