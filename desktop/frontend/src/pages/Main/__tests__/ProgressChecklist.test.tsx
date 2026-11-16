import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { HttpResponse, http } from 'msw'
import { describe, expect, it, vi } from 'vitest'
import { server } from '../../../test/mswServer'
import { renderWithClient } from '../../../test/renderWithClient'
import { ProgressChecklist } from '../ProgressChecklist'

describe('ProgressChecklist', () => {
  it('marks earlier stages done and the current stage active, later ones pending', async () => {
    // Default MSW handler returns state=PROCESSING, progress=20, stage="audio".
    renderWithClient(
      <ProgressChecklist taskId="task-123" onRetry={vi.fn()} onCreateAnother={vi.fn()} />,
    )

    expect(await screen.findByText('Generando voz')).toBeInTheDocument()

    const items = screen.getAllByRole('listitem')
    const textFor = (label: string) => items.find((item) => item.textContent?.includes(label))

    expect(textFor('Generando guion')?.textContent).toContain('✓')
    expect(textFor('Buscando ideas para las imágenes')?.textContent).toContain('✓')
    expect(textFor('Generando voz')?.textContent).toContain('●')
    expect(textFor('Creando subtítulos')?.textContent).toContain('○')
    expect(textFor('Descargando vídeos')?.textContent).toContain('○')
    expect(textFor('Exportando vídeo')?.textContent).toContain('○')

    expect(screen.getByText('20%')).toBeInTheDocument()
  })

  it('shows the translated error and a working Reintentar button when the task fails', async () => {
    server.use(
      http.get('/api/v1/tasks/:taskId', () =>
        HttpResponse.json({
          status: 200,
          data: {
            task_id: 'task-123',
            state: -1,
            progress: 40,
            error_message: 'No se pudieron descargar los vídeos. Revisa tu conexión.',
            error_code: 'materials_download_failed',
          },
        }),
      ),
    )
    const onRetry = vi.fn()
    renderWithClient(
      <ProgressChecklist taskId="task-123" onRetry={onRetry} onCreateAnother={vi.fn()} />,
    )

    expect(
      await screen.findByText('No se pudieron descargar los vídeos. Revisa tu conexión.'),
    ).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Reintentar' }))
    expect(onRetry).toHaveBeenCalledTimes(1)
  })

  it('shows the finished video and lets the user start another one', async () => {
    server.use(
      http.get('/api/v1/tasks/:taskId', () =>
        HttpResponse.json({
          status: 200,
          data: {
            task_id: 'task-123',
            state: 1,
            progress: 100,
            stage: 'done',
            videos: ['/tasks/task-123/final-1.mp4'],
          },
        }),
      ),
    )
    const onCreateAnother = vi.fn()
    renderWithClient(
      <ProgressChecklist taskId="task-123" onRetry={vi.fn()} onCreateAnother={onCreateAnother} />,
    )

    expect(await screen.findByText('¡Tu vídeo está listo!')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Crear otro' }))
    expect(onCreateAnother).toHaveBeenCalledTimes(1)
  })
})
