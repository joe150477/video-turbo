import { useState } from 'react'
import { api } from '../../api/client'
import { Button } from '../../components/Button'
import { ApiKeyTester } from '../../components/ApiKeyTester'
import type { LlmProviderId } from '../../api/types'
import { LLM_PROVIDERS } from './providers'

interface StepChooseProviderProps {
  onNext: () => void
}

export function StepChooseProvider({ onNext }: StepChooseProviderProps) {
  const [selected, setSelected] = useState<LlmProviderId | null>(null)
  const [configured, setConfigured] = useState(false)

  const selectedMeta = LLM_PROVIDERS.find((provider) => provider.id === selected)

  return (
    <div className="flex w-full max-w-md flex-col gap-5">
      <div>
        <h2 className="text-lg font-semibold">¿Qué IA deseas utilizar?</h2>
        <p className="text-sm text-[var(--color-text-muted)]">
          Escribe el guion y las ideas de tus vídeos.
        </p>
      </div>

      <div className="flex flex-col gap-2">
        {LLM_PROVIDERS.map((provider) => (
          <label
            key={provider.id}
            className={`flex cursor-pointer items-center justify-between rounded-xl border p-3 text-left transition-colors ${
              selected === provider.id
                ? 'border-[var(--color-primary)] bg-[var(--color-primary)]/5'
                : 'border-[var(--color-border)] hover:bg-black/5 dark:hover:bg-white/5'
            }`}
          >
            <span className="flex items-center gap-2">
              <input
                type="radio"
                name="llm-provider"
                checked={selected === provider.id}
                onChange={() => {
                  setSelected(provider.id)
                  setConfigured(false)
                }}
              />
              {provider.label}
            </span>
            {provider.recommended && (
              <span className="rounded-full bg-[var(--color-primary)]/10 px-2 py-0.5 text-xs font-medium text-[var(--color-primary)]">
                Recomendado
              </span>
            )}
          </label>
        ))}
      </div>

      {selectedMeta && (
        <ApiKeyTester
          key={selectedMeta.id}
          needsKey={selectedMeta.needsKey}
          needsModel={selectedMeta.needsModel}
          needsBaseUrl={selectedMeta.needsBaseUrl}
          modelPlaceholder={selectedMeta.modelPlaceholder}
          baseUrlPlaceholder={selectedMeta.baseUrlPlaceholder}
          helpUrl={selectedMeta.helpUrl}
          helpLabel={selectedMeta.helpLabel}
          onTest={(apiKey, extras) =>
            api.testLlmProvider(selectedMeta.id, apiKey, extras.model, extras.baseUrl)
          }
          onSuccess={async (apiKey, extras) => {
            await api.saveLlmProvider(selectedMeta.id, apiKey, extras.model, extras.baseUrl)
            setConfigured(true)
          }}
        />
      )}

      <Button disabled={!configured} onClick={onNext} className="self-end">
        Siguiente
      </Button>
    </div>
  )
}
