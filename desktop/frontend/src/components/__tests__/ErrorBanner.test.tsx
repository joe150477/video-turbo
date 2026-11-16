import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { ErrorBanner } from '../ErrorBanner'

describe('ErrorBanner', () => {
  it('renders the given Spanish message', () => {
    render(<ErrorBanner message="No se pudo conectar a internet." />)
    expect(screen.getByRole('alert')).toHaveTextContent('No se pudo conectar a internet.')
  })

  it('calls onRetry when the button is clicked', async () => {
    const onRetry = vi.fn()
    render(<ErrorBanner message="Algo falló." onRetry={onRetry} />)

    await userEvent.click(screen.getByRole('button', { name: 'Reintentar' }))

    expect(onRetry).toHaveBeenCalledTimes(1)
  })

  it('does not render a retry button when onRetry is not provided', () => {
    render(<ErrorBanner message="Algo falló." />)
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  it('never renders text that looks like a Python traceback', () => {
    // This is the desktop app's core promise: whatever reaches ErrorBanner
    // must already be a short, translated sentence — never leaked internals.
    render(<ErrorBanner message="No se pudo conectar a internet. Revisa tu conexión." />)
    const text = screen.getByRole('alert').textContent ?? ''
    expect(text).not.toMatch(/Traceback/i)
    expect(text).not.toMatch(/\.py/)
    expect(text).not.toMatch(/Exception/i)
  })
})
