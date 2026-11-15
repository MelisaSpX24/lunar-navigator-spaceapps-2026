import { positionLabel, type VisualPosition } from './motion'
import styles from './Celestial.module.css'

export function PositionStatus({ name, position, compact = false }: { name: string; position: VisualPosition; compact?: boolean }) {
  return <div aria-label={`${name} visual position`}>
    <p><strong>{name}: {positionLabel(position)}</strong></p>
    {position.kind === 'unavailable' && <p>{position.reason}</p>}
    {position.kind === 'interpolated' && !compact && <>
      <p className={styles.warning}>VISUAL INTERPOLATION — not a computed science sample</p>
      <p>Visual position preview between validated samples: {position.from.text} → {position.to.text}. Visibility at this UTC has not been evaluated.</p>
    </>}
  </div>
}
