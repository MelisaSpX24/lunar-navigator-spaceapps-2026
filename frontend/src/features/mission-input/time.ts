import type { FormErrors, MissionFormState } from './missionState'

const MAX_UTC_MS = Date.parse('9999-12-31T23:59:59Z')

export function parseUtc(date: string, time: string): { value: string | null; errors: FormErrors } {
  const errors: FormErrors = {}
  const d = /^(\d{4})-(\d{2})-(\d{2})$/.exec(date)
  if (!d) errors.utcDate = 'Enter a UTC date in YYYY-MM-DD format.'
  else {
    const year = Number(d[1]), month = Number(d[2]), day = Number(d[3])
    const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0)
    const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if (year < 1 || month < 1 || month > 12 || day < 1 || day > (days[month - 1] ?? 0)) errors.utcDate = 'Enter a real calendar date, year 0001–9999.'
  }
  const t = /^(\d{2}):(\d{2})(?::(\d{2}))?$/.exec(time)
  if (!t || Number(t[1]) > 23 || Number(t[2]) > 59 || Number(t[3] ?? 0) > 59) errors.utcTime = 'Enter a UTC time from 00:00:00 to 23:59:59.'
  if (Object.keys(errors).length) return { value: null, errors }
  // Never construct a local Date or let Date roll an invalid calendar input.
  return { value: `${date}T${t![1]}:${t![2]}:${t![3] ?? '00'}Z`, errors }
}

export function parseDuration(state: Pick<MissionFormState, 'hours' | 'minutes' | 'seconds'>) {
  const errors: FormErrors = {}
  const values: number[] = []
  for (const field of ['hours', 'minutes', 'seconds'] as const) {
    const raw = state[field].trim(), value = Number(raw)
    if (!/^\d+$/.test(raw) || !Number.isSafeInteger(value) || (field !== 'hours' && value > 59)) {
      errors[field] = field === 'hours' ? 'Enter nonnegative whole hours within the safe integer range.' : 'Enter whole values from 0 to 59.'
    }
    values.push(value)
  }
  const total = values[0]! * 3600 + values[1]! * 60 + values[2]!
  if (!Object.keys(errors).length && (!Number.isSafeInteger(total) || total <= 0)) errors.hours = 'Total duration must be positive whole seconds within the safe integer range.'
  return { value: Object.keys(errors).length ? null : total, errors }
}

export function endWithinBackendRange(startUtc: string, durationSeconds: number): boolean {
  const start = Date.parse(startUtc)
  return Number.isFinite(start) && Number.isSafeInteger(durationSeconds) && durationSeconds > 0
    && durationSeconds <= Math.floor((MAX_UTC_MS - start) / 1000)
}
