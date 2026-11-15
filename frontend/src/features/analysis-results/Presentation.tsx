import { useId, type ReactNode } from 'react'
import { EmptyState } from '../../components/States'
import type { Checked } from './types'
import { checkQuality } from './validation'
import styles from './Results.module.css'

export const show = (value: number | boolean | string | null) => value === null ? 'Unknown (null)' : String(value)
export function QualityNotice({ value }: { value: unknown }) {
  const data = checkQuality(value)
  if (data.kind === 'valid' && data.value.status === 'SUFFICIENT' && data.value.coverage_complete === true) return null
  return <p className={styles.warning}>Data quality: {data.kind === 'valid' ? `${data.value.status}; coverage complete: ${show(data.value.coverage_complete)}` : 'invalid metadata'}. These values may be limited, incomplete or unassessed.</p>
}
export function DataMessage({ data, missing = 'Not calculated or not provided (null).' }: { data: Checked<unknown>; missing?: string }) {
  if (data.kind === 'missing') return <EmptyState title="Data not provided">{missing}</EmptyState>
  if (data.kind === 'valid') return null
  return <div className={styles.warning} role={data.kind === 'invalid' ? 'alert' : 'status'}><h3>{data.kind === 'invalid' ? 'Invalid scientific response data' : 'Display limit reached'}</h3><p>{data.message}</p></div>
}
export function DataTable({ caption, headings, children }: { caption: string; headings: string[]; children: ReactNode }) {
  return <div className={styles.tableBlock}>
    <p className={styles.tableCaption}>{caption}</p>
    <div className={styles.tableScroll} role="region" aria-label={caption} tabIndex={0}>
      <table><caption className={styles.visuallyHidden}>{caption}</caption><thead><tr>{headings.map(h => <th key={h} scope="col">{h}</th>)}</tr></thead><tbody>{children}</tbody></table>
    </div>
  </div>
}
export function DisplayCount({ total, shown }: { total: number; shown: number }) {
  return <p>{shown < total ? `Showing the first ${shown} of ${total} validated records. Later records are not shown; no values were interpolated.` : `${total} validated records shown.`}</p>
}
export function SamplePlot({ title, yLabel, minimum, maximum, points, xDescription }: {
  title: string; yLabel: string; minimum: number; maximum: number; points: { x: number; y: number | null }[]; xDescription: string
}) {
  const id = useId(), known = points.filter(p => p.y !== null)
  return <figure className={styles.plot}>
    <figcaption>{title}</figcaption>
    <p>Y: {yLabel} ({minimum} to {maximum}). X: {xDescription}</p>
    <svg viewBox="0 0 400 180" role="img" aria-labelledby={`${id}-title ${id}-desc`}>
      <title id={`${id}-title`}>{title}</title><desc id={`${id}-desc`}>{known.length} known samples; {points.length - known.length} unknown values omitted. Separate points only, with no interpolation. Values are available in the accompanying table.</desc>
      <path d="M16 8V164H392 M16 86H392" className={styles.axes} />
      {known.map((p, i) => <circle key={i} cx={16 + p.x * 376} cy={164 - (p.y! - minimum) / (maximum - minimum) * 156} r="3" className={styles.sample} />)}
    </svg>
    <p>{known.length} known / {points.length - known.length} unknown. Server samples only; gaps are not interpolated.</p>
  </figure>
}
