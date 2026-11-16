import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { HttpResponse, http } from 'msw'
import { describe, expect, it } from 'vitest'
import { server } from '../../../test/mswServer'
import { renderWithClient } from '../../../test/renderWithClient'
import { CreateVideoTab } from '../CreateVideoTab'

describe('CreateVideoTab', () => {
  it('disables "Generar vídeo" until a subject is entered', () => {
    renderWithClient(<CreateVideoTab />)
    expect(screen.getByRole('button', { name: 'Generar vídeo' })).toBeDisabled()
  })

  it('maps duration and format to the real API fields and starts the task', async () => {
    let capturedBody: unknown = null
    server.use(
      http.post('/api/v1/videos', async ({ request }) => {
        capturedBody = await request.json()
        return HttpResponse.json({ status: 200, data: { task_id: 'task-999' } })
      }),
    )

    renderWithClient(<CreateVideoTab />)

    await userEvent.type(screen.getByLabelText('Tema'), 'Curiosidades del espacio')
    await userEvent.click(screen.getByRole('button', { name: '60 segundos' }))
    await userEvent.click(screen.getByRole('button', { name: 'YouTube Shorts' }))
    await userEvent.click(screen.getByRole('button', { name: 'Generar vídeo' }))

    await waitFor(() => {
      expect(capturedBody).toMatchObject({
        video_subject: 'Curiosidades del espacio',
        video_aspect: '9:16',
        paragraph_number: 2,
      })
    })

    // Once a task starts, the form is replaced by the progress checklist.
    expect(await screen.findByText('20%')).toBeInTheDocument()
  })
})
