import type { ReactNode } from 'react'
import styles from './States.module.css'

type StateProps = { title?: string; children: ReactNode }

function StateContent({ symbol, title, children }: StateProps & { symbol: string }) {
  return <>
    <span className={styles.symbol} aria-hidden="true">{symbol}</span>
    <div><h3>{title}</h3><p>{children}</p></div>
  </>
}

export function LoadingState({ title = 'Loading', children }: StateProps) {
  return <div className={`${styles.state} ${styles.loading}`} role="status" aria-live="polite" aria-busy="true">
    <StateContent symbol="…" title={title}>{children}</StateContent>
  </div>
}

export function EmptyState({ title = 'No data available', children }: StateProps) {
  return <div className={styles.state}>
    <StateContent symbol="—" title={title}>{children}</StateContent>
  </div>
}

export function ErrorState({ title = 'Something went wrong', children, onRetry }: StateProps & { onRetry?: () => void }) {
  return <div className={`${styles.state} ${styles.error}`} role="alert">
    <StateContent symbol="!" title={title}>{children}</StateContent>
    {onRetry && <button type="button" onClick={onRetry}>Try again</button>}
  </div>
}

export function UnsupportedDataState({ title = 'Data not supported', children }: StateProps) {
  return <div className={`${styles.state} ${styles.unsupported}`} role="status">
    <StateContent symbol="?" title={title}>{children}</StateContent>
  </div>
}
