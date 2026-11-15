import styles from './Layout.module.css'
import { ConnectionStatus } from '../features/scenario/ConnectionStatus'

export function Header() {
  return <header className={styles.header}>
    <a className={styles.brand} href="#/" aria-label="24&28 — Lunar Landing Site Navigator home">
      <span className={styles.brandMark} aria-hidden="true">24<span>&</span>28</span>
      <span className={styles.brandText}>LUNAR NAVIGATOR<span>LUNAR LANDING SITE NAVIGATOR</span></span>
    </a>
    <ConnectionStatus />
  </header>
}
