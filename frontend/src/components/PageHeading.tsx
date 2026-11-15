import { StatusBadge } from './StatusBadge'
import styles from './PageHeading.module.css'

type Props = { title: string; workspace: string; subtitle: string; status: string }

export function PageHeading({ title, workspace, subtitle, status }: Props) {
  return <div className={styles.heading}>
    <div>
      <p className="eyebrow">LUNAR SURFACE OPERATIONS / {workspace}</p>
      <h1>{title}</h1>
      <p className={styles.subtitle}>{subtitle}</p>
    </div>
    <StatusBadge>{status}</StatusBadge>
  </div>
}
