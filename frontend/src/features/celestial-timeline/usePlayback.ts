import { useCallback, useEffect, useState } from 'react'
import type { Stamp, TimeBounds } from '../analysis-results/utc'
import { stampAt } from './selection'

export const PLAYBACK_SECONDS = [30, 60, 120] as const
export function useReducedMotion() {
  const [reduced, setReduced] = useState(() => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false)
  useEffect(() => {
    const media = window.matchMedia?.('(prefers-reduced-motion: reduce)')
    if (!media) return
    const update = () => setReduced(media.matches)
    update(); media.addEventListener('change', update)
    return () => media.removeEventListener('change', update)
  }, [])
  return reduced
}
/** One clock; no data fetching, science updates or persistent animation outside this hook. */
export function usePlayback(identity: object | null, bounds: TimeBounds | null, enabled: boolean, selected: Stamp | null, write: (value: Stamp) => void) {
  const [run, setRun] = useState<{ identity: object; start: Stamp } | null>(null)
  const [seconds, setSeconds] = useState<number>(60)
  const [message, setMessage] = useState('Playback paused.')
  const pause = useCallback(() => { setRun(null); setMessage('Playback paused.') }, [])
  const playing = !!run && run.identity === identity && enabled
  useEffect(() => { setRun(null); setMessage('Playback paused.') }, [identity])
  useEffect(() => { if (!enabled) pause() }, [enabled, pause])
  useEffect(() => {
    if (!playing || !run || !bounds) return
    let frame = 0, alive = true, previous = performance.now(), elapsed = 0, lastPaint = 0
    const stop = (reason: string) => { alive = false; cancelAnimationFrame(frame); setRun(null); setMessage(reason) }
    const visibility = () => { if (document.hidden) stop('Playback paused because the tab is hidden. Press Play to resume.') }
    const advance = (now: number) => {
      if (!alive) return
      const delta = now - previous; previous = now
      if (document.hidden || delta > 250 || delta < 0) { stop('Playback paused after a timing interruption. Press Play to resume.'); return }
      elapsed += delta
      // Integer microsecond arithmetic keeps UTC within exact operation bounds.
      const tick = run.start.tick + (bounds.end.tick - bounds.start.tick) * BigInt(Math.floor(elapsed * 1000)) / BigInt(seconds * 1e6)
      if (tick >= bounds.end.tick) { write(bounds.end); stop('Playback ended at the operation boundary.'); return }
      if (elapsed - lastPaint >= 1000 / 30) { write(stampAt(tick)); lastPaint = elapsed }
      frame = requestAnimationFrame(advance)
    }
    document.addEventListener('visibilitychange', visibility)
    frame = requestAnimationFrame(advance)
    return () => { alive = false; cancelAnimationFrame(frame); document.removeEventListener('visibilitychange', visibility) }
  }, [playing, run, bounds, seconds, write])
  const play = (replay = false) => {
    if (!enabled || !identity || !bounds || !selected || document.hidden) return
    const start = replay ? bounds.start : selected
    if (start.tick >= bounds.end.tick) return
    write(start); setMessage('Playback playing. Scientific values are available only at exact samples.'); setRun({ identity, start })
  }
  const setSpeed = (value: number) => { if (PLAYBACK_SECONDS.some(s => s === value)) { pause(); setSeconds(value) } }
  return { playing, seconds, message, pause, play, setSpeed }
}
