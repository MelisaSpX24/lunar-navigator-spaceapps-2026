import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { EmptyState, ErrorState, LoadingState, UnsupportedDataState } from '../components/States'

describe('reusable data states', () => {
  it('explains an empty result without a misleading error alert', () => {
    render(<EmptyState title="No samples">An analysis is required.</EmptyState>)
    expect(screen.getByRole('heading', { name: 'No samples' })).toBeVisible()
    expect(screen.getByText('An analysis is required.')).toBeVisible()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('announces a loading state', () => {
    render(<LoadingState>Waiting for a response.</LoadingState>)
    expect(screen.getByRole('status')).toHaveAttribute('aria-busy', 'true')
    expect(screen.getByRole('status')).toHaveTextContent('Waiting for a response.')
  })

  it('announces an error and lets the caller retry', async () => {
    const onRetry = vi.fn()
    const user = userEvent.setup()
    render(<ErrorState title="Request failed" onRetry={onRetry}>Please try again.</ErrorState>)
    expect(screen.getByRole('alert')).toHaveTextContent('Request failed')
    await user.click(screen.getByRole('button', { name: 'Try again' }))
    expect(onRetry).toHaveBeenCalledTimes(1)
  })

  it('does not offer an inert retry action without a handler', () => {
    render(<ErrorState>Cannot load this result.</ErrorState>)
    expect(screen.getByRole('alert')).toBeVisible()
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  it('distinguishes unsupported data from a scientific zero', () => {
    render(<UnsupportedDataState>Unsupported schema version.</UnsupportedDataState>)
    expect(screen.getByRole('status')).toHaveTextContent('Data not supported')
    expect(screen.getByRole('status')).toHaveTextContent('Unsupported schema version.')
  })
})
