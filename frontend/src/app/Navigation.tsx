import { NavLink } from 'react-router-dom'
import styles from './Layout.module.css'

const destinations = [
  { path: '/', title: 'Mission Setup', number: '01' },
  { path: '/analysis', title: 'Mission Analysis', number: '02' },
  { path: '/alternatives', title: 'Alternative Explorer', number: '03' },
]

export function Navigation() {
  return <nav className={styles.navigation} aria-label="Main navigation">
    {destinations.map(({ path, title, number }) =>
      <NavLink key={path} to={path} end className={({ isActive }) => `${styles.navLink} ${isActive ? styles.active : ''}`}>
        <span className={styles.navNumber} aria-hidden="true">{number}</span>{title}
      </NavLink>,
    )}
  </nav>
}
