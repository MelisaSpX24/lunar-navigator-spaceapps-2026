import { useState, type FormEvent } from 'react'
import { PROFILES, type Profile } from './analysisRequest'
import type { RequestValidation } from './buildAnalysisRequest'
import type { FormErrors, FormField, MissionFormState, TextFieldName } from './missionState'
import styles from './MissionForm.module.css'

type Change = <K extends FormField>(field: K, value: MissionFormState[K]) => void
type Props = { state: MissionFormState; onChange: Change; validation: RequestValidation; onShowGlobe: () => void
  runEnabled: boolean; runReason: string; onRun: () => void; onReset: () => void; serverErrors: FormErrors }

function Field({ name, label, value, onChange, onBlur, error, hint, type = 'text' }: {
  name: TextFieldName; label: string; value: string; onChange: (value: string) => void; onBlur: () => void
  error: string | undefined; hint: string | undefined; type?: 'text' | 'date' | 'time'
}) {
  const id = `mission-${name}`
  const described = [hint && `${id}-hint`, error && `${id}-error`].filter(Boolean).join(' ') || undefined
  return <div className={styles.field}>
    <label htmlFor={id}>{label}</label>
    <input id={id} name={name} type={type} inputMode={type === 'text' ? 'decimal' : undefined}
      value={value} onChange={event => onChange(event.target.value)} onBlur={onBlur}
      step={type === 'time' ? '1' : undefined} min={type === 'date' ? '0001-01-01' : undefined}
      max={type === 'date' ? '9999-12-31' : undefined} aria-invalid={!!error} aria-describedby={described} />
    {hint && <p id={`${id}-hint`} className={styles.hint}>{hint}</p>}
    {error && <p id={`${id}-error`} className={styles.error}>{error}</p>}
  </div>
}

export function MissionForm({ state, onChange, validation, onShowGlobe, runEnabled, runReason, onRun, onReset, serverErrors }: Props) {
  const [touched, setTouched] = useState<Partial<Record<FormField, boolean>>>({})
  const [attempted, setAttempted] = useState(false)
  function field(name: TextFieldName, label: string, hint?: string, type?: 'date' | 'time') {
    const error = serverErrors[name] ?? (attempted || touched[name] || state[name] !== '' ? validation.errors[name] : undefined)
    return <Field name={name} label={label} value={state[name]} hint={hint} error={error} type={type ?? 'text'}
      onChange={value => onChange(name, value)} onBlur={() => setTouched(previous => ({ ...previous, [name]: true }))} />
  }
  function checkbox(name: 'simultaneous' | 'fullHorizon' | 'earthDisk', label: string) {
    return <label className={styles.checkbox} htmlFor={`mission-${name}`}>
      <input id={`mission-${name}`} name={name} type="checkbox" checked={state[name]} onChange={event => onChange(name, event.target.checked)}
        aria-invalid={!!serverErrors[name]} aria-describedby={serverErrors[name] ? `mission-${name}-server-error` : undefined} />
      <span>{label}{serverErrors[name] && <span id={`mission-${name}-server-error`} className={styles.error}>{serverErrors[name]}</span>}</span>
    </label>
  }
  function submit(event: FormEvent) {
    event.preventDefault()
    setAttempted(true)
    const input = Array.from(event.currentTarget.querySelectorAll<HTMLInputElement | HTMLSelectElement>('input,select'))
      .find(element => validation.errors[element.name as FormField] || serverErrors[element.name as FormField])
    if (input) {
      const details = input?.closest('details')
      if (details) details.open = true
      input?.focus()
    }
  }

  return <form className={styles.form} aria-label="Mission scenario inputs" noValidate onSubmit={submit}>
    <p className={styles.hint}>Prepare scenario inputs. Scientific readiness is reported separately.</p>
    <fieldset>
      <legend>Landing Site</legend>
      <div className={styles.pair}>
        {field('latitude', 'Latitude (degrees)', 'Planetocentric; south is negative. Exact ±90° poles are unsupported.')}
        {field('longitude', 'Longitude (degrees east)', 'East-positive [0°, 360°). 360° is excluded; use 0° for that meridian.')}
      </div>
      <button type="button" onClick={onShowGlobe}>Show lunar globe</button>
      <p className={styles.hint}>Pick on the globe or edit coordinates here. Frame: MOON_ME_DE421.</p>
      <p className={styles.siteSummary} aria-label="Selected site summary">
        {state.latitude && state.longitude ? `Site input: latitude ${state.latitude}°, longitude ${state.longitude}° E. See field validation before use.` : 'Select a surface point or enter both coordinates.'}
      </p>
    </fieldset>
    <fieldset>
      <legend>Operation Profile</legend>
      <div className={styles.field}>
        <label htmlFor="mission-profile">Operation profile</label>
        <select id="mission-profile" name="profile" value={state.profile} onChange={event => onChange('profile', event.target.value as Profile)} aria-invalid={!!serverErrors.profile} aria-describedby={`profile-description${serverErrors.profile ? ' mission-profile-error' : ''}`}>
          {PROFILES.map(profile => <option key={profile.value} value={profile.value}>{profile.label}</option>)}
        </select>
        <p id="profile-description" className={styles.hint}><strong>{PROFILES.find(profile => profile.value === state.profile)?.label}.</strong> {PROFILES.find(profile => profile.value === state.profile)?.description} Changing profile does not change your requirements.</p>
        {serverErrors.profile && <p id="mission-profile-error" className={styles.error}>{serverErrors.profile}</p>}
      </div>
    </fieldset>
    <fieldset>
      <legend>Time Window</legend>
      <div className={styles.pair}>
        {field('utcDate', 'UTC date', undefined, 'date')}
        {field('utcTime', 'UTC time', 'UTC throughout; no local-time conversion.', 'time')}
      </div>
      <p className={styles.hint}>Operation duration — whole hours, minutes and seconds.</p>
      <div className={styles.duration}>
        {field('hours', 'Hours')}{field('minutes', 'Minutes')}{field('seconds', 'Seconds')}
      </div>
      <output aria-label="Total operation duration" className={styles.total}>
        {validation.durationSeconds === null ? 'Total duration unavailable — correct the duration fields.' : `Total duration: ${validation.durationSeconds} seconds`}
      </output>
    </fieldset>
    <fieldset>
      <legend>Operation Requirements</legend>
      <p className={styles.hint}>Initial values are backend draft defaults, not NASA-approved mission limits. Blank optional thresholds remain null; zero is an explicit value.</p>
      {field('solarFraction', 'Minimum solar disk visible fraction', 'Fraction from 0 to 1, inclusive.')}
      <div className={styles.pair}>
        {field('minSun', 'Minimum Sun visibility (seconds)', 'Optional; cannot exceed operation duration.')}
        {field('minEarth', 'Minimum continuous Earth visibility (seconds)', 'Optional; cannot exceed operation duration.')}
      </div>
      {checkbox('simultaneous', 'Require simultaneous Sun and Earth visibility')}
      {field('minJoint', 'Minimum joint visibility (seconds)', 'Optional; requires simultaneous visibility and cannot exceed duration.')}
    </fieldset>
    <details className={styles.advanced}>
      <summary>Advanced settings</summary>
      <fieldset>
        <legend>Visibility settings</legend>
        <div className={styles.pair}>
          {field('maxDark', 'Maximum dark gap (seconds)', 'Optional; nonnegative.')}
          {field('clearance', 'Earth clearance margin (degrees)', 'From 0° to 90°, inclusive.')}
        </div>
      </fieldset>
      <fieldset>
        <legend>Observer</legend>
        <p className={styles.hint}>Surface elevation mode: DEM. These are device heights above the surface, not measured DEM elevation. Backend draft default: 1 metre.</p>
        <div className={styles.pair}>
          {field('solarHeight', 'Solar device height (metres)')}
          {field('earthHeight', 'Earth device height (metres)')}
        </div>
      </fieldset>
      <fieldset>
        <legend>Analysis options</legend>
        {checkbox('fullHorizon', 'Include full horizon profile')}
        {checkbox('earthDisk', 'Include Earth disk fraction')}
        {field('lookahead', 'Event lookahead (seconds)', 'Nonnegative whole seconds. Backend draft default: 86400.')}
      </fieldset>
    </details>
    <section className={styles.summary} aria-labelledby="scenario-summary-title">
      <h3 id="scenario-summary-title">Scenario Summary</h3>
      <p role="status">{validation.valid ? 'Scenario inputs valid — check backend readiness before running analysis.' : 'Scenario inputs incomplete or invalid — no request is prepared.'}</p>
      <p>{PROFILES.find(profile => profile.value === state.profile)?.label}</p>
      <p>UTC start: {validation.startUtc ?? 'Not specified or invalid'}</p>
      <p>Duration: {validation.durationSeconds === null ? 'Invalid' : `${validation.durationSeconds} seconds`}</p>
    </section>
    <details className={styles.preview}>
      <summary>Request Preview</summary>
      <p className={styles.hint}>Request preview only — this preview does not perform scientific analysis.</p>
      {validation.request ? <pre tabIndex={0} aria-label="AnalysisRequest JSON">{JSON.stringify(validation.request, null, 2)}</pre>
        : <p className={styles.hint}>Complete or correct the inputs to prepare a request.</p>}
    </details>
    <div className={styles.actions}>
      <button type="submit">Validate inputs</button>
      <button type="button" disabled={!runEnabled} onClick={onRun} aria-describedby="analysis-unavailable">Run Analysis</button>
    </div>
    <p id="analysis-unavailable" className={styles.hint}>{runReason}</p>
    <button type="button" onClick={() => { setTouched({}); setAttempted(false); onReset() }}>Reset scenario</button>
  </form>
}
