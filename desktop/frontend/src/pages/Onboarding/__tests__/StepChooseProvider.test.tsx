import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { HttpResponse, http } from 'msw'
import { describe, expect, it, vi } from 'vitest'
import { server } from '../../../test/mswServer'
import { StepChooseProvider } from '../StepChooseProvider'

describe('StepChooseProvider', () => {
  it('disables Siguiente until a provider connection test succeeds', async () => {
    const onNext = vi.fn()
    render(<StepChooseProvider onNext={onNext} />)

    expect(screen.getByRole('button', { name: 'Siguiente' })).toBeDisabled()

    // Ollama needs no API key, so it is the simplest path to a real success.
    await userEvent.click(screen.getByRole('radio', { name: /Ollama/ }))
    await userEvent.click(screen.getByRole('button', { name: 'Probar conexión' }))

    expect(await screen.findByText('✓ Conectado correctamente')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Siguiente' })).toBeEnabled()

    await userEvent.click(screen.getByRole('button', { name: 'Siguiente' }))
    expect(onNext).toHaveBeenCalledTimes(1)
  })

  it('keeps Siguiente disabled and shows the translated error when the test fails', async () => {
    server.use(
      http.post('/api/v1/system/settings/llm/test', () =>
        HttpResponse.json({
          status: 200,
          data: { ok: false, message_es: 'La clave de API no es válida.' },
        }),
      ),
    )

    render(<StepChooseProvider onNext={vi.fn()} />)

    await userEvent.click(screen.getByRole('radio', { name: /Gemini/ }))
    await userEvent.type(screen.getByPlaceholderText('Pega aquí tu clave de API'), 'bad-key')
    await userEvent.click(screen.getByRole('button', { name: 'Probar conexión' }))

    expect(await screen.findByText('La clave de API no es válida.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Siguiente' })).toBeDisabled()
  })

  it('switching provider resets the previous test result', async () => {
    render(<StepChooseProvider onNext={vi.fn()} />)

    await userEvent.click(screen.getByRole('radio', { name: /Ollama/ }))
    await userEvent.click(screen.getByRole('button', { name: 'Probar conexión' }))
    expect(await screen.findByText('✓ Conectado correctamente')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('radio', { name: 'OpenAI' }))
    expect(screen.queryByText('✓ Conectado correctamente')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Siguiente' })).toBeDisabled()
  })
})
