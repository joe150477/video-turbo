import { useState } from 'react'
import { api } from '../../api/client'
import { Button } from '../../components/Button'
import { VoicePicker } from '../../components/VoicePicker'

interface StepVoiceSelectionProps {
  onNext: () => void
}

export function StepVoiceSelection({ onNext }: StepVoiceSelectionProps) {
  const [selectedVoiceId, setSelectedVoiceId] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const handleNext = async () => {
    if (!selectedVoiceId) return
    setSaving(true)
    try {
      await api.saveGeneralSettings({ voice_name: selectedVoiceId })
      onNext()
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flex w-full max-w-md flex-col gap-4">
      <div>
        <h2 className="text-lg font-semibold">Elige una voz</h2>
        <p className="text-sm text-[var(--color-text-muted)]">
          Es la voz que narrará tus vídeos.
        </p>
      </div>

      <VoicePicker selectedVoiceId={selectedVoiceId} onSelect={setSelectedVoiceId} />

      <Button disabled={!selectedVoiceId} loading={saving} onClick={handleNext} className="self-end">
        Siguiente
      </Button>
    </div>
  )
}
