import { useState } from 'react'
import { api } from '../../api/client'
import { Button } from '../../components/Button'

interface StepSummaryProps {
  onFinished: () => void
}

export function StepSummary({ onFinished }: StepSummaryProps) {
  const [saving, setSaving] = useState(false)

  const handleFinish = async () => {
    setSaving(true)
    try {
      await api.completeOnboarding()
      onFinished()
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flex w-full max-w-md flex-col items-center gap-4 text-center">
      <span className="text-4xl">✅</span>
      <h2 className="text-lg font-semibold">¡Todo listo!</h2>
      <p className="text-sm text-[var(--color-text-muted)]">
        Ya puedes empezar a crear tus vídeos. Podrás cambiar cualquiera de estas opciones más
        tarde desde Configuración.
      </p>
      <Button loading={saving} onClick={handleFinish}>
        Empezar a usar la app
      </Button>
    </div>
  )
}
