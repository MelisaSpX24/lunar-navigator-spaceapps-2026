import { useId, type ReactNode } from 'react'
import styles from './Panel.module.css'

type PanelProps = {
  title: string
  eyebrow?: string
  children: ReactNode
  className?: string | undefined
}

export function Panel({ title, eyebrow, children, className = '' }: PanelProps) {
  const id = useId()
  return (
    <section className={`${styles.panel} ${className}`} aria-labelledby={id}>
      <header className={styles.header}>
        <div>
          {eyebrow && <p className="eyebrow">{eyebrow}</p>}
          <h2 id={id}>{title}</h2>
        </div>
      </header>
      {children}
    </section>
  )
}
