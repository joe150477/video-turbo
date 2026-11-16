import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { HttpResponse, http } from 'msw'
import { describe, expect, it } from 'vitest'
import { server } from '../../../test/mswServer'
import { UpdatesSection } from '../UpdatesSection'

describe('UpdatesSection', () => {
  it('reports when the app is already up to date', async () => {
    render(<UpdatesSection />)
    await userEvent.click(screen.getByRole('button', { name: 'Buscar actualizaciones' }))
    expect(await screen.findByText('Ya tienes la versión más reciente.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Actualizar ahora' })).not.toBeInTheDocument()
  })

  it('requires explicit confirmation before applying an update', async () => {
    server.use(
      http.get('/api/v1/system/updates/check', () =>
        HttpResponse.json({
          status: 200,
          data: {
            update_available: true,
            can_auto_apply: true,
            changes: ['Arreglo de un error', 'Nueva función'],
            compatible: true,
            message_es: 'Esta actualización es compatible con tu configuración.',
          },
        }),
      ),
    )

    render(<UpdatesSection />)
    await userEvent.click(screen.getByRole('button', { name: 'Buscar actualizaciones' }))

    expect(await screen.findByText('Arreglo de un error')).toBeInTheDocument()

    // First click only reveals the confirmation, it does not apply yet.
    await userEvent.click(screen.getByRole('button', { name: 'Actualizar ahora' }))
    expect(screen.getByText(/copia de seguridad automática/)).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Sí, actualizar' }))
    expect(await screen.findByText('Actualización instalada.')).toBeInTheDocument()
  })

  it('offers no apply button in a packaged build (can_auto_apply false)', async () => {
    server.use(
      http.get('/api/v1/system/updates/check', () =>
        HttpResponse.json({
          status: 200,
          data: {
            update_available: true,
            can_auto_apply: false,
            changes: ['Nueva versión publicada'],
            message_es: 'Hay una versión más reciente disponible. Descarga el nuevo instalador.',
          },
        }),
      ),
    )

    render(<UpdatesSection />)
    await userEvent.click(screen.getByRole('button', { name: 'Buscar actualizaciones' }))

    expect(await screen.findByText(/Descarga el nuevo instalador/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Actualizar ahora' })).not.toBeInTheDocument()
  })
})
