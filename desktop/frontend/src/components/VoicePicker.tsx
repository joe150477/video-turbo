import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../api/client'
import { ErrorBanner } from './ErrorBanner'
import { Spinner } from './Spinner'

interface VoicePickerProps {
  selectedVoiceId: string | null
  onSelect: (voiceId: string) => void
}

const DEFAULT_EXPANDED_GROUPS = new Set(['Español'])

// Shared by the onboarding wizard's voice step and the Settings tab: fetch
// the friendly, grouped catalog, let the user preview a voice out loud, and
// report the selection up. Callers decide what happens once a voice is
// chosen (advance the wizard, or save immediately).
export function VoicePicker({ selectedVoiceId, onSelect }: VoicePickerProps) {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['voices'],
    queryFn: () => api.getVoices(),
  })
  const [expandedGroups, setExpandedGroups] = useState(DEFAULT_EXPANDED_GROUPS)
  const [previewingId, setPreviewingId] = useState<string | null>(null)

  const toggleGroup = (label: string) => {
    setExpandedGroups((current) => {
      const next = new Set(current)
      if (next.has(label)) next.delete(label)
      else next.add(label)
      return next
    })
  }

  const playPreview = async (voiceId: string) => {
    setPreviewingId(voiceId)
    try {
      const result = await api.previewVoice(voiceId)
      if (result.ok && result.audio_base64) {
        const audio = new Audio(
          `data:${result.mime_type ?? 'audio/mpeg'};base64,${result.audio_base64}`,
        )
        await audio.play()
      }
    } finally {
      setPreviewingId(null)
    }
  }

  if (isLoading) return <Spinner label="Cargando voces disponibles…" />
  if (isError || !data) {
    return (
      <ErrorBanner message="No se pudo cargar el catálogo de voces." onRetry={() => refetch()} />
    )
  }

  return (
    <div className="flex max-h-80 flex-col gap-3 overflow-y-auto pr-1">
      {data.groups.map((group) => (
        <div key={group.language_label_es} className="rounded-xl border border-[var(--color-border)]">
          <button
            type="button"
            onClick={() => toggleGroup(group.language_label_es)}
            className="flex w-full items-center justify-between px-3 py-2 text-sm font-medium"
          >
            {group.language_label_es}
            <span>{expandedGroups.has(group.language_label_es) ? '▲' : '▼'}</span>
          </button>
          {expandedGroups.has(group.language_label_es) && (
            <div className="flex flex-col gap-1 border-t border-[var(--color-border)] p-2">
              {group.voices.map((voice) => (
                <label
                  key={voice.id}
                  className={`flex items-center justify-between rounded-lg px-2 py-1.5 text-sm ${
                    selectedVoiceId === voice.id ? 'bg-[var(--color-primary)]/10' : ''
                  }`}
                >
                  <span className="flex items-center gap-2">
                    <input
                      type="radio"
                      name="voice"
                      checked={selectedVoiceId === voice.id}
                      onChange={() => onSelect(voice.id)}
                    />
                    {voice.label_es}
                  </span>
                  <button
                    type="button"
                    onClick={() => playPreview(voice.id)}
                    disabled={previewingId === voice.id}
                    className="text-xs text-[var(--color-primary)]"
                  >
                    {previewingId === voice.id ? 'Reproduciendo…' : '▶ Escuchar ejemplo'}
                  </button>
                </label>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
