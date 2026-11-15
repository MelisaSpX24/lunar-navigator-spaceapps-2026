import type { ReactNode } from 'react'
import styles from './StatusBadge.module.css'

/** A static label, not a connection indicator or a live-region announcement. */
export function StatusBadge({ children }: { children: ReactNode }) {
  return <span className={styles.badge}>{children}</span>
}
