import type { ReactNode } from 'react'
import styles from './SceneViewport.module.css'

type Props = { label: string; caption: string; footer: string; children: ReactNode; interactive?: boolean }

/** Layout only. A future renderer can occupy surface; overlays stay independent. */
export function SceneViewport({ label, caption, footer, children, interactive = false }: Props) {
  return <section className={styles.viewport} aria-label={label}>
    <div className={styles.grid} aria-hidden="true" />
    <div className={styles.overlay}>
      <span>{caption}</span><span className={styles.reserved}>{interactive ? 'VISUAL EXPLORATION' : 'VIEWPORT RESERVED'}</span>
    </div>
    <div className={`${styles.surface} ${interactive ? styles.interactive : ''}`}>{children}</div>
    <div className={`${styles.overlay} ${styles.bottom}`}>
      <span>{footer}</span>{!interactive && <span>Camera controls unavailable</span>}
    </div>
  </section>
}
