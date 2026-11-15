import type { AnalysisRequestV1 } from '../mission-input/analysisRequest'
import { record } from '../../services/api/responses'
import { utcStamp } from './utc'

/** All explicitly sent fields must match; ordering/UTC zero-offset spelling may differ.
 * No coercion of numbers, booleans, null or extra fields. No ID-based correlation.
 */
export function requestMatches(expected: AnalysisRequestV1, echoed: unknown): boolean {
  function equal(a: unknown, b: unknown, path: string): boolean {
    if (path === 'time.start_utc') {
      const left = utcStamp(a), right = utcStamp(b)
      return !!left && !!right && left.tick === right.tick
    }
    if (record(a) && record(b)) {
      const keys = Object.keys(a)
      return keys.length === Object.keys(b).length && keys.every(key => Object.hasOwn(b, key) && equal(a[key], b[key], path ? `${path}.${key}` : key))
    }
    return a === b
  }
  return equal(expected, echoed, '')
}
