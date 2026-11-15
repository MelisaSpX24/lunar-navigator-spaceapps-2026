import { useEffect, useRef } from 'react'
import { Link, Outlet, Route, Routes, useLocation } from 'react-router-dom'
import { EmptyState } from '../components/States'
import { MissionSetup } from '../screens/MissionSetup'
import { MissionAnalysis } from '../screens/MissionAnalysis'
import { AlternativeExplorer } from '../screens/AlternativeExplorer'
import { Header } from './Header'
import { Navigation } from './Navigation'
import styles from './Layout.module.css'
import { ScenarioProvider } from '../features/scenario/ScenarioProvider'

function AppLayout() {
  const location = useLocation()
  const main = useRef<HTMLElement>(null)
  useEffect(() => {
    const title = main.current?.querySelector('h1')?.textContent ?? 'Page not found'
    document.title = `${title} | 24&28 Lunar Navigator`
    main.current?.focus({ preventScroll: true })
  }, [location.pathname])

  return <div className={styles.shell}>
    <a href="#main-content" className={styles.skipLink} onClick={(event) => {
      event.preventDefault()
      main.current?.focus()
    }}>Skip to main content</a>
    <Header />
    <Navigation />
    <main id="main-content" ref={main} tabIndex={-1} className={styles.main}><Outlet /></main>
    <footer className={styles.footer}>
      <span>24&28 <span aria-hidden="true">/</span> NASA Space Apps Challenge 2026 project</span>
      <span>Planning support only. No landing, power or radio-link guarantees.</span>
    </footer>
  </div>
}

export function App() {
  return <ScenarioProvider><Routes>
    <Route element={<AppLayout />}>
      <Route index element={<MissionSetup />} />
      <Route path="analysis" element={<MissionAnalysis />} />
      <Route path="alternatives" element={<AlternativeExplorer />} />
      <Route path="*" element={<>
        <h1>Page not found</h1>
        <EmptyState title="This destination is unavailable">Choose a mission screen from the navigation.</EmptyState>
        <Link to="/">Return to Mission Setup</Link>
      </>} />
    </Route>
  </Routes></ScenarioProvider>
}
