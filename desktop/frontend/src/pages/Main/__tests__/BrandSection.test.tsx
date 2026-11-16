import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { HttpResponse, http } from 'msw'
import { describe, expect, it } from 'vitest'
import { server } from '../../../test/mswServer'
import { renderWithClient } from '../../../test/renderWithClient'
import { BrandSection } from '../BrandSection'

describe('BrandSection', () => {
  it('saves the brand context', async () => {
    let savedBody: unknown = null
    server.use(
      http.post('/api/v1/system/settings/brand', async ({ request }) => {
        savedBody = await request.json()
        return HttpResponse.json({ status: 200, data: { saved: true } })
      }),
    )

    renderWithClient(<BrandSection />)

    const textarea = await screen.findByLabelText(/Contexto de tu marca/)
    await userEvent.type(textarea, 'Cafetería artesanal, tono cercano')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar contexto' }))

    await waitFor(() =>
      expect(savedBody).toMatchObject({ brand_context: 'Cafetería artesanal, tono cercano' }),
    )
  })

  it('shows logo position/size controls only once a logo is uploaded', async () => {
    server.use(
      http.get('/api/v1/system/settings/brand', () =>
        HttpResponse.json({
          status: 200,
          data: {
            brand_context: '',
            logo_filename: 'logo.png',
            logo_position: 'top-left',
            logo_size: 15,
            use_own_materials: false,
          },
        }),
      ),
    )

    renderWithClient(<BrandSection />)

    expect(await screen.findByText('Posición')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Quitar logo' })).toBeInTheDocument()
  })

  it('lets the user enable their own materials once some are uploaded', async () => {
    server.use(
      http.get('/api/v1/system/materials', () =>
        HttpResponse.json({ status: 200, data: { materials: ['clip1.mp4', 'foto.png'] } }),
      ),
    )

    renderWithClient(<BrandSection />)

    expect(await screen.findByText('clip1.mp4')).toBeInTheDocument()
    expect(screen.getByText(/Usar mis archivos en los vídeos/)).toBeInTheDocument()
  })
})
