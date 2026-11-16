import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useRef, useState } from 'react'
import { api } from '../../api/client'
import { Button } from '../../components/Button'

const AUDIO_ACCEPT = 'audio/mpeg,audio/wav,audio/x-m4a,audio/mp4,audio/ogg,audio/flac'
const ENGINE_LABELS: Record<string, string> = {
  chatterbox: 'Chatterbox (multilingüe)',
  qwen3: 'Qwen3',
}

// "Clonar mi propia voz": two ways —
//  1) Local & free via MimikaStudio (runs on the user's Mac, no cost, private).
//  2) Fish Audio in the cloud (pennies per video) as an alternative.
export function VoiceCloneSection() {
  const queryClient = useQueryClient()
  const localInputRef = useRef<HTMLInputElement>(null)
  const fishInputRef = useRef<HTMLInputElement>(null)

  const { data } = useQuery({ queryKey: ['voice-clone'], queryFn: () => api.getVoiceClone() })
  const { data: mimika } = useQuery({
    queryKey: ['mimika-status'],
    queryFn: () => api.getMimikaStatus(),
    refetchInterval: 15000, // pick up when the user opens MimikaStudio
  })

  const [localName, setLocalName] = useState('Mi voz')
  const [engine, setEngine] = useState('chatterbox')
  const [localMsg, setLocalMsg] = useState<string | null>(null)
  const [localBusy, setLocalBusy] = useState(false)

  const [apiKey, setApiKey] = useState('')
  const [keyMsg, setKeyMsg] = useState<string | null>(null)
  const [savingKey, setSavingKey] = useState(false)
  const [fishTitle, setFishTitle] = useState('Mi voz')
  const [fishMsg, setFishMsg] = useState<string | null>(null)
  const [fishBusy, setFishBusy] = useState(false)

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['voice-clone'] })
    queryClient.invalidateQueries({ queryKey: ['general-settings'] })
  }

  const engines = mimika?.engines ?? []
  const currentEngine = engines.includes(engine) ? engine : engines[0] || 'chatterbox'
  const usingClone = (data?.current_voice ?? '').startsWith('mimika:')
    ? 'local'
    : (data?.current_voice ?? '').startsWith('fish:')
      ? 'fish'
      : null

  const onPickLocal = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return
    setLocalBusy(true)
    setLocalMsg(null)
    try {
      const result = await api.cloneVoiceLocal(file, localName.trim() || 'Mi voz', currentEngine)
      setLocalMsg(result.message_es)
      if (result.ok) refresh()
    } catch {
      setLocalMsg('No se pudo crear tu voz local. ¿Está MimikaStudio abierto?')
    } finally {
      setLocalBusy(false)
      if (localInputRef.current) localInputRef.current.value = ''
    }
  }

  const saveKey = async () => {
    setSavingKey(true)
    setKeyMsg(null)
    try {
      const result = await api.saveFishKey(apiKey.trim())
      setKeyMsg(result.message_es)
      if (result.ok) {
        setApiKey('')
        refresh()
      }
    } catch {
      setKeyMsg('No se pudo guardar la clave. Revisa tu conexión.')
    } finally {
      setSavingKey(false)
    }
  }

  const onPickFish = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return
    setFishBusy(true)
    setFishMsg(null)
    try {
      const result = await api.cloneVoice(file, fishTitle.trim() || 'Mi voz')
      setFishMsg(result.message_es)
      if (result.ok) refresh()
    } catch {
      setFishMsg('No se pudo crear tu voz. Inténtalo de nuevo.')
    } finally {
      setFishBusy(false)
      if (fishInputRef.current) fishInputRef.current.value = ''
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <p className="text-sm font-medium">Clonar mi propia voz</p>
        <p className="text-xs text-[var(--color-text-muted)]">
          Graba una muestra corta (10-30 s, voz clara, sin ruido) y todas las narraciones sonarán
          con tu voz.
        </p>
      </div>

      {/* Option 1: local & free (MimikaStudio) */}
      <div className="flex flex-col gap-2 rounded-xl border border-[var(--color-border)] p-3">
        <p className="text-sm font-medium">
          🖥️ Local y gratis (MimikaStudio){' '}
          {usingClone === 'local' && (
            <span className="text-xs text-[var(--color-success)]">Usando tu voz ✓</span>
          )}
        </p>
        {mimika?.reachable && engines.length > 0 ? (
          <>
            <p className="text-xs text-[var(--color-text-muted)]">
              MimikaStudio detectado ✓ — tu voz se genera en tu Mac, sin costo.
            </p>
            {engines.length > 1 && (
              <label className="flex flex-col gap-1 text-xs">
                Modelo de voz
                <select
                  value={currentEngine}
                  onChange={(event) => setEngine(event.target.value)}
                  className="rounded-lg border border-[var(--color-border)] bg-transparent px-3 py-2 text-sm"
                >
                  {engines.map((e) => (
                    <option key={e} value={e}>
                      {ENGINE_LABELS[e] ?? e}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <label className="flex flex-col gap-1 text-xs">
              Nombre de la voz
              <input
                value={localName}
                onChange={(event) => setLocalName(event.target.value)}
                maxLength={80}
                className="rounded-lg border border-[var(--color-border)] bg-transparent px-3 py-2 text-sm"
              />
            </label>
            <input
              ref={localInputRef}
              type="file"
              accept={AUDIO_ACCEPT}
              onChange={onPickLocal}
              className="hidden"
            />
            <div>
              <Button
                variant="secondary"
                loading={localBusy}
                onClick={() => localInputRef.current?.click()}
              >
                Subir muestra y crear mi voz
              </Button>
            </div>
            {localBusy && (
              <p className="text-xs text-[var(--color-text-muted)]">
                Generando en tu Mac… puede tardar un poco la primera vez.
              </p>
            )}
            {localMsg && <p className="text-xs text-[var(--color-text-muted)]">{localMsg}</p>}
          </>
        ) : (
          <p className="text-xs text-[var(--color-text-muted)]">
            Abre la app <strong>MimikaStudio</strong> (y descarga un modelo de voz) para clonar tu
            voz gratis aquí. En cuanto esté abierta, esta opción se activará sola.
          </p>
        )}
      </div>

      {/* Option 2: Fish Audio (cloud) */}
      <details className="rounded-xl border border-[var(--color-border)] p-3">
        <summary className="cursor-pointer text-sm font-medium">
          ☁️ Alternativa en la nube: Fish Audio{' '}
          {usingClone === 'fish' && (
            <span className="text-xs text-[var(--color-success)]">Usando tu voz ✓</span>
          )}
        </summary>
        <div className="mt-3 flex flex-col gap-2">
          {!data?.fish_configured ? (
            <>
              <label htmlFor="fish-key" className="text-xs font-medium">
                Clave de Fish Audio
              </label>
              <input
                id="fish-key"
                type="password"
                value={apiKey}
                onChange={(event) => setApiKey(event.target.value)}
                placeholder="Pega aquí tu clave de fish.audio"
                className="w-full rounded-lg border border-[var(--color-border)] bg-transparent px-3 py-2 text-sm"
              />
              <a
                href="https://fish.audio/go-api/"
                target="_blank"
                rel="noreferrer"
                className="text-xs text-[var(--color-primary)] underline"
              >
                ¿Dónde consigo mi clave?
              </a>
              <div>
                <Button
                  variant="secondary"
                  onClick={saveKey}
                  loading={savingKey}
                  disabled={!apiKey.trim()}
                >
                  Guardar clave
                </Button>
              </div>
              {keyMsg && <p className="text-xs text-[var(--color-text-muted)]">{keyMsg}</p>}
            </>
          ) : (
            <>
              <p className="text-xs text-[var(--color-text-muted)]">
                Clave configurada ({data.fish_masked_key}).
              </p>
              <label className="flex flex-col gap-1 text-xs">
                Nombre de la voz
                <input
                  value={fishTitle}
                  onChange={(event) => setFishTitle(event.target.value)}
                  maxLength={80}
                  className="rounded-lg border border-[var(--color-border)] bg-transparent px-3 py-2 text-sm"
                />
              </label>
              <input
                ref={fishInputRef}
                type="file"
                accept={AUDIO_ACCEPT}
                onChange={onPickFish}
                className="hidden"
              />
              <div>
                <Button
                  variant="secondary"
                  loading={fishBusy}
                  onClick={() => fishInputRef.current?.click()}
                >
                  Subir muestra y crear mi voz
                </Button>
              </div>
              {fishMsg && <p className="text-xs text-[var(--color-text-muted)]">{fishMsg}</p>}
            </>
          )}
        </div>
      </details>
    </div>
  )
}
