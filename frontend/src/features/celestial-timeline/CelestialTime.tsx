import { useCallback, useEffect, createContext, useContext, useMemo, useState, type ReactNode } from 'react'
import type { completedResult } from '../analysis-results/resultContext'
import { checkHorizons, checkSeries } from '../analysis-results/validation'
import type { BodyRow, Checked } from '../analysis-results/types'
import { timePosition, type Stamp } from '../analysis-results/utc'
import { exactSample, sliderStamp } from './selection'
import { lowerBound, prepareMotion, visualPosition } from './motion'
import { PLAYBACK_SECONDS, usePlayback, useReducedMotion } from './usePlayback'
import styles from './Celestial.module.css'

type Result = ReturnType<typeof completedResult>
function useTimeState(result: Result) {
  const [choice, setChoice] = useState<{ response: NonNullable<Result>['response']; time: Stamp } | null>(null)
  const [smoothChoice, setSmoothChoice] = useState(false)
  const reduced = useReducedMotion()
  useEffect(() => { setChoice(null); setSmoothChoice(false) }, [result?.response])
  const data = useMemo(() => {
    const missing: Checked<BodyRow[]> = { kind: 'missing' }
    const sun = result ? checkSeries(result.response.series, 'sun', result.bounds) : missing
    const earth = result ? checkSeries(result.response.series, 'earth', result.bounds) : missing
    const times = (sun.kind === 'valid' ? sun.value : earth.kind === 'valid' ? earth.value : []).map(row => row.time)
    const profiles = checkHorizons(result?.response.horizons ?? null)
    const ids = new Set(profiles.kind === 'valid' ? profiles.value.map(p => p.id) : [])
    return { sun, earth, times, sunTrack: prepareMotion(sun, ids), earthTrack: prepareMotion(earth, ids) }
  }, [result])
  const selected = result && data.times.length ? choice?.response === result.response ? choice.time : data.times[0]! : null
  const write = useCallback((time: Stamp) => {
    if (result && time.tick >= result.bounds.start.tick && time.tick <= result.bounds.end.tick) setChoice({ response: result.response, time })
  }, [result])
  const smooth = smoothChoice && !reduced
  const supported = smooth ? data.sunTrack.supportedSegments + data.earthTrack.supportedSegments > 0 : Math.max(data.sunTrack.known, data.earthTrack.known) >= 2
  const canPlay = !!result && !!selected && supported && !reduced
  const playback = usePlayback(result?.response ?? null, result?.bounds ?? null, canPlay, selected, write)
  const select = (time: Stamp) => { playback.pause(); write(time) }
  const setSmooth = (value: boolean) => { playback.pause(); setSmoothChoice(value) }
  return { ...data, ...playback, result, selected, select, smooth, setSmooth, reduced, canPlay,
    sunSample: exactSample(data.sun, selected), earthSample: exactSample(data.earth, selected),
    sunPosition: visualPosition(data.sunTrack, selected, smooth), earthPosition: visualPosition(data.earthTrack, selected, smooth) }
}
const TimeContext = createContext<ReturnType<typeof useTimeState> | null>(null)
export function CelestialTimeProvider({ result, children }: { result: Result; children: ReactNode }) {
  const state = useTimeState(result)
  return <TimeContext.Provider value={state}>{children}</TimeContext.Provider>
}
export const useCelestialTime = () => useContext(TimeContext)
export function TimeSelector() {
  const time = useCelestialTime()
  const { selected, times = [], result } = time ?? {}
  const index = selected ? lowerBound(times, selected.tick) : 0
  const exact = !!selected && times[index]?.tick === selected.tick
  const previous = times[index - 1], next = times[index + (exact ? 1 : 0)]
  return <section className={styles.block} aria-label="UTC time selection">
    <h3>UTC time selection</h3>
    {result && <p>Operation range: {result.bounds.start.text} → {result.bounds.end.text}</p>}
    <label htmlFor="utc-selection">Selected UTC time</label>
    <input id="utc-selection" type="range" min="0" max="10000" step="1" disabled={!selected || !result} value={selected && result ? Math.round(timePosition(selected, result.bounds) * 10000) : 0}
      aria-valuetext={selected?.text ?? 'No validated samples'} onChange={e => { if (result) time?.select(sliderStamp(Number(e.target.value), result.bounds)) }} />
    <output aria-label="Selected UTC" aria-live={time?.playing ? 'off' : 'polite'}>{selected?.text ?? 'No validated time samples available.'}</output>
    <p>{selected ? exact ? 'Backend sample selected — no interpolation.' : time?.smooth ? 'No exact backend sample at this time. Visual directions require accepted neighboring samples; visibility has not been evaluated.' : 'No sample at selected time. Celestial markers and sample values are withheld; no interpolation.' : 'Scientific time selection is disabled.'}</p>
    <div className={styles.buttons}>{[['First sample', times[0]],['Previous sample',previous],['Next sample',next],['Last sample',times.at(-1)]].map(([label, stamp]) => <button key={String(label)} disabled={!stamp || times.length === 0} onClick={() => { if (typeof stamp === 'object') time?.select(stamp) }}>{String(label)}</button>)}</div>
    <label className={styles.option}><input type="checkbox" checked={time?.smooth ?? false} disabled={!selected || time?.reduced} onChange={e => time?.setSmooth(e.target.checked)} /> Smooth visual preview</label>
    <p>{time?.smooth ? 'Smooth Visual Preview: direction-only interpolation, not SPICE or a computed science sample.' : 'Exact Samples: only backend sample positions are shown.'}</p>
    <label htmlFor="playback-speed">Playback duration</label>
    <select id="playback-speed" value={time?.seconds ?? 60} onChange={e => time?.setSpeed(Number(e.target.value))}>
      {PLAYBACK_SECONDS.map(s => <option key={s} value={s}>Full operation in {s} seconds</option>)}
    </select>
    <p>Visual playback speed only; the operation duration and backend results do not change. Manual selection or a speed/mode change pauses playback.</p>
    <div className={styles.buttons}>
      <button disabled={!time?.canPlay || time.playing || selected?.tick === result?.bounds.end.tick} onClick={() => time?.play()}>Play</button>
      <button disabled={!time?.playing} onClick={time?.pause}>Pause</button>
      <button disabled={!time?.canPlay || time.playing} onClick={() => time?.play(true)}>Replay</button>
    </div>
    <p role="status" aria-label="Playback status">{time?.message ?? 'Playback paused.'}</p>
    {time?.reduced ? <p>Reduced motion: smooth preview and playback are disabled. Manual sample selection remains available.</p> : !time?.canPlay && <p>Playback needs at least two supported directions; Smooth Visual Preview also needs an accepted interpolation interval.</p>}
    <p>The range spans the full operation; sample buttons select exact backend UTC stamps, including sub-second values. No API requests or new scientific calculations are triggered.</p>
  </section>
}
