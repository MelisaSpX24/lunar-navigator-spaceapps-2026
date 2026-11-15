import { Component, type ReactNode } from 'react'
import { ErrorState } from '../../components/States'

export class GlobeBoundary extends Component<{ children: ReactNode; onError?: () => void }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  componentDidCatch() { this.props.onError?.() }
  render() {
    return this.state.failed
      ? <ErrorState title="3D view unavailable">WebGL could not render this scene. Other mission screens remain available. Reload to try again.</ErrorState>
      : this.props.children
  }
}
