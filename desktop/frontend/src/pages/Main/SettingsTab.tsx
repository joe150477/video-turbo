import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState, type ReactNode } from 'react'
import { api } from '../../api/client'
import { ApiKeyTester } from '../../components/ApiKeyTester'
import { Button } from '../../components/Button'
import { VoicePicker } from '../../components/VoicePicker'
import type { LlmProviderId } from '../../api/types'
import { LLM_PROVIDERS, MATERIAL_PROVIDERS } from '../Onboarding/providers'
import { UpdatesSection } from './UpdatesSection'
import { BrandSection } from './BrandSection'
import { VoiceCloneSection } from './VoiceCloneSection'

const ASPECT_OPTIONS = [
  { value: '9:16', label: 'Vertical (TikTok, Reels, Shorts)' },
  { value: '16:9', label: 'Horizontal' },
  { value: '1:1', label: 'Cuadrado' },
]

function SectionCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-3 rounded-xl border border-[var(--color-border)] p-4">
      <h3 className="text-sm font-semibold">{title}</h3>
      {children}
    </section>
  )
}

function SavedBadge({ show }: { show: boolean }) {
  if (!show) return null
  return <span className="text-xs text-[var(--color-success)]">Guardado ✓</span>
}

export function SettingsTab() {
  const queryClient = useQueryClient()
  const { data: llmSettings } = useQuery({
    queryKey: ['llm-settings'],
    queryFn: () => api.getLlmSettings(),
  })
  const { data: materialSettings } = useQuery({
    queryKey: ['material-settings'],
    queryFn: () => api.getMaterialSettings(),
  })
  const { data: generalSettings } = useQuery({
    queryKey: ['general-settings'],
    queryFn: () => api.getGeneralSettings(),
  })

  const [selectedProvider, setSelectedProvider] = useState<LlmProviderId | null>(null)
  const [voiceId, setVoiceId] = useState<string | null>(null)
  const [outputDirectory, setOutputDirectory] = useState('')
  const [videoAspect, setVideoAspect] = useState('9:16')
  const [maxConcurrentTasks, setMaxConcurrentTasks] = useState(5)
  const [savedField, setSavedField] = useState<string | null>(null)

  useEffect(() => {
    if (generalSettings) {
      setOutputDirectory(generalSettings.output_directory)
      setVideoAspect(generalSettings.video_aspect || '9:16')
      setMaxConcurrentTasks(generalSettings.max_concurrent_tasks)
      setVoiceId(generalSettings.voice_name || null)
    }
  }, [generalSettings])

  const flashSaved = (field: string) => {
    setSavedField(field)
    setTimeout(() => setSavedField((current) => (current === field ? null : current)), 2000)
  }

  const invalidateSettings = () => {
    queryClient.invalidateQueries({ queryKey: ['llm-settings'] })
    queryClient.invalidateQueries({ queryKey: ['material-settings'] })
    queryClient.invalidateQueries({ queryKey: ['general-settings'] })
  }

  const handleChooseFolder = async () => {
    if (!window.desktopApi) return
    const folder = await window.desktopApi.selectOutputFolder()
    if (folder) setOutputDirectory(folder)
  }

  const saveGeneral = async (patch: Record<string, unknown>, field: string) => {
    await api.saveGeneralSettings(patch)
    flashSaved(field)
    invalidateSettings()
  }

  return (
    <div className="mx-auto flex max-w-lg flex-col gap-5 p-6">
      <SectionCard title="Proveedor de IA">
        <p className="text-xs text-[var(--color-text-muted)]">
          Actual: <strong>{llmSettings?.provider ?? '—'}</strong>
          {llmSettings?.masked_api_key ? ` (clave ${llmSettings.masked_api_key})` : ''}
        </p>
        <div className="flex flex-col gap-1">
          {LLM_PROVIDERS.map((provider) => (
            <label key={provider.id} className="flex items-center gap-2 text-sm">
              <input
                type="radio"
                name="settings-llm-provider"
                checked={selectedProvider === provider.id}
                onChange={() => setSelectedProvider(provider.id)}
              />
              {provider.label}
            </label>
          ))}
        </div>
        {selectedProvider &&
          (() => {
            const meta = LLM_PROVIDERS.find((provider) => provider.id === selectedProvider)!
            return (
              <ApiKeyTester
                key={selectedProvider}
                needsKey={meta.needsKey}
                needsModel={meta.needsModel}
                needsBaseUrl={meta.needsBaseUrl}
                modelPlaceholder={meta.modelPlaceholder}
                baseUrlPlaceholder={meta.baseUrlPlaceholder}
                helpUrl={meta.helpUrl}
                helpLabel={meta.helpLabel}
                onTest={(apiKey, extras) =>
                  api.testLlmProvider(selectedProvider, apiKey, extras.model, extras.baseUrl)
                }
                onSuccess={async (apiKey, extras) => {
                  await api.saveLlmProvider(selectedProvider, apiKey, extras.model, extras.baseUrl)
                  flashSaved('llm')
                  invalidateSettings()
                }}
              />
            )
          })()}
        <SavedBadge show={savedField === 'llm'} />
      </SectionCard>

      <SectionCard title="Vídeos gratuitos">
        {MATERIAL_PROVIDERS.map((provider) => (
          <div key={provider.id} className="flex flex-col gap-2 border-t border-[var(--color-border)] pt-3 first:border-t-0 first:pt-0">
            <p className="text-sm">
              {provider.label}{' '}
              {materialSettings?.[provider.id] && (
                <span className="text-xs text-[var(--color-success)]">✓ Configurado</span>
              )}
            </p>
            <ApiKeyTester
              helpUrl={provider.helpUrl}
              onTest={(apiKey) => api.testMaterialProvider(provider.id, apiKey)}
              onSuccess={async (apiKey) => {
                await api.saveMaterialProvider(provider.id, apiKey)
                invalidateSettings()
              }}
            />
          </div>
        ))}
      </SectionCard>

      <SectionCard title="Voz">
        {/* Cloning first: it's the headline feature and must not be buried
            under the long library of stock voices. */}
        <VoiceCloneSection />
        <details className="mt-1">
          <summary className="cursor-pointer text-sm font-medium">
            O elegir una voz de la biblioteca
          </summary>
          <div className="mt-3 flex flex-col gap-3">
            <VoicePicker selectedVoiceId={voiceId} onSelect={setVoiceId} />
            <div className="flex items-center gap-3">
              <Button
                variant="secondary"
                onClick={() => voiceId && saveGeneral({ voice_name: voiceId }, 'voice')}
                disabled={!voiceId}
              >
                Guardar voz
              </Button>
              <SavedBadge show={savedField === 'voice'} />
            </div>
          </div>
        </details>
      </SectionCard>

      <SectionCard title="Carpeta de salida">
        <div className="flex items-center gap-2">
          <input
            value={outputDirectory}
            onChange={(event) => setOutputDirectory(event.target.value)}
            readOnly={Boolean(window.desktopApi)}
            placeholder="Carpeta donde se guardan tus vídeos"
            className="w-full rounded-lg border border-[var(--color-border)] bg-transparent px-3 py-2 text-sm"
          />
          {window.desktopApi && (
            <Button variant="secondary" onClick={handleChooseFolder}>
              Elegir…
            </Button>
          )}
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="secondary"
            onClick={() => saveGeneral({ output_directory: outputDirectory }, 'output')}
          >
            Guardar
          </Button>
          <SavedBadge show={savedField === 'output'} />
        </div>
      </SectionCard>

      <SectionCard title="Resolución">
        <select
          value={videoAspect}
          onChange={(event) => {
            setVideoAspect(event.target.value)
            saveGeneral({ video_aspect: event.target.value }, 'aspect')
          }}
          className="w-full rounded-lg border border-[var(--color-border)] bg-transparent px-3 py-2 text-sm"
        >
          {ASPECT_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <SavedBadge show={savedField === 'aspect'} />
      </SectionCard>

      <SectionCard title="Número máximo de vídeos a la vez">
        <input
          type="number"
          min={1}
          max={20}
          value={maxConcurrentTasks}
          onChange={(event) => setMaxConcurrentTasks(Number(event.target.value))}
          className="w-24 rounded-lg border border-[var(--color-border)] bg-transparent px-3 py-2 text-sm"
        />
        <div className="flex items-center gap-3">
          <Button
            variant="secondary"
            onClick={() => saveGeneral({ max_concurrent_tasks: maxConcurrentTasks }, 'concurrency')}
          >
            Guardar
          </Button>
          <SavedBadge show={savedField === 'concurrency'} />
        </div>
      </SectionCard>

      <SectionCard title="Marca (logo, contexto y tus archivos)">
        <BrandSection />
      </SectionCard>

      <SectionCard title="Buscar actualizaciones">
        <UpdatesSection />
      </SectionCard>
    </div>
  )
}
