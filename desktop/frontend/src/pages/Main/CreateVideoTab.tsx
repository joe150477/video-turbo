import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../../api/client'
import { Button } from '../../components/Button'
import { ErrorBanner } from '../../components/ErrorBanner'
import {
  DURATION_TO_PARAGRAPHS,
  FORMAT_TO_ASPECT,
  type VideoDuration,
  type VideoFormat,
} from '../../api/types'
import { ProgressChecklist } from './ProgressChecklist'

const DURATIONS: VideoDuration[] = [30, 60, 90]
const FORMATS: { id: VideoFormat; label: string }[] = [
  { id: 'tiktok', label: 'TikTok' },
  { id: 'youtube_shorts', label: 'YouTube Shorts' },
  { id: 'instagram_reels', label: 'Instagram Reels' },
]

export function CreateVideoTab() {
  const [subject, setSubject] = useState('')
  const [keywords, setKeywords] = useState('')
  const [duration, setDuration] = useState<VideoDuration>(30)
  const [format, setFormat] = useState<VideoFormat>('tiktok')
  const [taskId, setTaskId] = useState<string | null>(null)
  const [starting, setStarting] = useState(false)
  const [startError, setStartError] = useState<string | null>(null)

  const { data: generalSettings } = useQuery({
    queryKey: ['general-settings'],
    queryFn: () => api.getGeneralSettings(),
  })
  const { data: materialSettings } = useQuery({
    queryKey: ['material-settings'],
    queryFn: () => api.getMaterialSettings(),
  })
  const { data: brandSettings } = useQuery({
    queryKey: ['brand'],
    queryFn: () => api.getBrandSettings(),
  })
  const { data: ownMaterials } = useQuery({
    queryKey: ['materials'],
    queryFn: () => api.listMaterials(),
  })

  const handleGenerate = async () => {
    setStarting(true)
    setStartError(null)
    try {
      const stockSource = materialSettings?.pexels
        ? 'pexels'
        : materialSettings?.pixabay
          ? 'pixabay'
          : materialSettings?.coverr
            ? 'coverr'
            : 'pexels'

      // If a "live" folder (e.g. Google Photos) is configured, re-sync it first
      // so newly added photos/videos are picked up before this video is built.
      let materials = ownMaterials?.materials ?? []
      if (brandSettings?.materials_folder) {
        try {
          await api.syncMaterialsFolder()
          materials = (await api.listMaterials()).materials
        } catch {
          // A sync hiccup shouldn't block generation; use whatever is already there.
        }
      }

      // Build from the user's own footage when they have a folder configured or
      // explicitly turned on "use my own materials" and some exist.
      const useOwn =
        (Boolean(brandSettings?.materials_folder) || Boolean(brandSettings?.use_own_materials)) &&
        materials.length > 0

      const { task_id } = await api.createVideo({
        video_subject: subject,
        video_aspect: FORMAT_TO_ASPECT[format],
        paragraph_number: DURATION_TO_PARAGRAPHS[duration],
        video_source: useOwn ? 'local' : stockSource,
        voice_name: generalSettings?.voice_name ?? '',
        // Brand context is applied by the backend on both script paths (the
        // persuasive chain reads it internally; the classic path falls back to
        // it). Sending it here as a manual prompt would suppress the persuasive
        // brain, so we intentionally don't pass it.
        // Keep scripts and voice local (Spanish/Colombia by default).
        video_language: brandSettings?.content_language || undefined,
        // Your own keywords steer stock search toward local footage
        // (e.g. "Barranquilla, estudiantes, Caribe colombiano").
        video_terms: keywords.trim() || undefined,
        logo_path: brandSettings?.logo_filename || undefined,
        logo_position: brandSettings?.logo_position,
        logo_size: brandSettings?.logo_size,
        video_materials: useOwn
          ? materials.map((name) => ({ provider: 'local', url: name }))
          : undefined,
        // When using own clips, optionally top them up with local stock.
        supplement_with_stock: useOwn ? brandSettings?.supplement_with_stock : undefined,
        fallback_source: useOwn && brandSettings?.supplement_with_stock ? stockSource : undefined,
      })
      setTaskId(task_id)
    } catch {
      setStartError('No se pudo iniciar la generación del vídeo. Inténtalo de nuevo.')
    } finally {
      setStarting(false)
    }
  }

  if (taskId) {
    return (
      <ProgressChecklist
        taskId={taskId}
        onRetry={handleGenerate}
        onCreateAnother={() => setTaskId(null)}
      />
    )
  }

  return (
    <div className="mx-auto flex max-w-lg flex-col gap-6 p-6">
      <div>
        <label htmlFor="video-subject" className="mb-1 block text-sm font-medium">
          Tema
        </label>
        <input
          id="video-subject"
          value={subject}
          onChange={(event) => setSubject(event.target.value)}
          placeholder="Ej: Curiosidades del espacio"
          className="w-full rounded-lg border border-[var(--color-border)] bg-transparent px-3 py-2 text-sm outline-none focus:border-[var(--color-primary)]"
        />
      </div>

      <div>
        <label htmlFor="video-keywords" className="mb-1 block text-sm font-medium">
          Palabras clave para las imágenes <span className="font-normal text-[var(--color-text-muted)]">(opcional)</span>
        </label>
        <input
          id="video-keywords"
          value={keywords}
          onChange={(event) => setKeywords(event.target.value)}
          placeholder="Ej: Barranquilla, estudiantes, familia colombiana, Caribe"
          className="w-full rounded-lg border border-[var(--color-border)] bg-transparent px-3 py-2 text-sm outline-none focus:border-[var(--color-primary)]"
        />
        <p className="mt-1 text-xs text-[var(--color-text-muted)]">
          Escribe lugares/temas locales y el vídeo buscará imágenes acordes (más realistas). Déjalo
          vacío para que la IA elija.
        </p>
      </div>

      <div>
        <p className="mb-1 text-sm font-medium">Duración</p>
        <div className="flex gap-2">
          {DURATIONS.map((option) => (
            <button
              key={option}
              type="button"
              onClick={() => setDuration(option)}
              className={`rounded-lg border px-4 py-2 text-sm ${
                duration === option
                  ? 'border-[var(--color-primary)] bg-[var(--color-primary)]/10'
                  : 'border-[var(--color-border)]'
              }`}
            >
              {option} segundos
            </button>
          ))}
        </div>
      </div>

      <div>
        <p className="mb-1 text-sm font-medium">Formato</p>
        <div className="flex flex-wrap gap-2">
          {FORMATS.map((option) => (
            <button
              key={option.id}
              type="button"
              onClick={() => setFormat(option.id)}
              className={`rounded-lg border px-4 py-2 text-sm ${
                format === option.id
                  ? 'border-[var(--color-primary)] bg-[var(--color-primary)]/10'
                  : 'border-[var(--color-border)]'
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {startError && <ErrorBanner message={startError} onRetry={handleGenerate} />}

      <Button
        onClick={handleGenerate}
        loading={starting}
        disabled={subject.trim().length === 0}
        className="py-4 text-base"
      >
        Generar vídeo
      </Button>
    </div>
  )
}
