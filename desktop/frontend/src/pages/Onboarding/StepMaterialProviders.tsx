import { useState } from 'react'
import { api } from '../../api/client'
import { ApiKeyTester } from '../../components/ApiKeyTester'
import { Button } from '../../components/Button'
import { MATERIAL_PROVIDERS } from './providers'

interface StepMaterialProvidersProps {
  onNext: () => void
}

export function StepMaterialProviders({ onNext }: StepMaterialProvidersProps) {
  const [wantsFreeVideos, setWantsFreeVideos] = useState<boolean | null>(null)
  const [configuredProviders, setConfiguredProviders] = useState<Set<string>>(new Set())

  return (
    <div className="flex w-full max-w-md flex-col gap-5">
      <div>
        <h2 className="text-lg font-semibold">¿Quieres usar vídeos gratuitos?</h2>
        <p className="text-sm text-[var(--color-text-muted)]">
          Se usarán para ilustrar tus vídeos automáticamente.
        </p>
      </div>

      <div className="flex gap-3">
        <Button
          variant={wantsFreeVideos === true ? 'primary' : 'secondary'}
          onClick={() => setWantsFreeVideos(true)}
        >
          Sí
        </Button>
        <Button
          variant={wantsFreeVideos === false ? 'primary' : 'secondary'}
          onClick={() => setWantsFreeVideos(false)}
        >
          No
        </Button>
      </div>

      {wantsFreeVideos && (
        <div className="flex flex-col gap-4">
          {MATERIAL_PROVIDERS.map((provider) => (
            <div key={provider.id} className="rounded-xl border border-[var(--color-border)] p-3">
              <p className="mb-2 text-sm font-medium">{provider.label}</p>
              <ApiKeyTester
                helpUrl={provider.helpUrl}
                helpLabel={`Obtener clave gratis de ${provider.label}`}
                onTest={(apiKey) => api.testMaterialProvider(provider.id, apiKey)}
                onSuccess={async (apiKey) => {
                  await api.saveMaterialProvider(provider.id, apiKey)
                  setConfiguredProviders((current) => new Set(current).add(provider.id))
                }}
              />
            </div>
          ))}
          {configuredProviders.size === 0 && (
            <p className="text-xs text-[var(--color-text-muted)]">
              Puedes configurar esto más tarde desde Configuración.
            </p>
          )}
        </div>
      )}

      <Button disabled={wantsFreeVideos === null} onClick={onNext} className="self-end">
        Siguiente
      </Button>
    </div>
  )
}
