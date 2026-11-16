import { useState, type MouseEvent } from 'react'
import type { ConnectionTestResult } from '../api/types'
import { Button } from './Button'

export interface ApiKeyExtras {
  model?: string
  baseUrl?: string
}

interface ApiKeyTesterProps {
  needsKey?: boolean
  // Optional extra fields for OpenAI-compatible providers (e.g. z.ai/GLM).
  needsModel?: boolean
  needsBaseUrl?: boolean
  modelPlaceholder?: string
  baseUrlPlaceholder?: string
  onTest: (apiKey: string, extras: ApiKeyExtras) => Promise<ConnectionTestResult>
  onSuccess: (apiKey: string, extras: ApiKeyExtras) => Promise<void> | void
  helpUrl?: string
  helpLabel?: string
}

// Shared by the LLM provider step and the stock-video provider step: paste
// a key (or nothing, for Ollama), press "Probar conexión", and only once
// the backend confirms it works do we consider the provider configured.
export function ApiKeyTester({
  needsKey = true,
  needsModel = false,
  needsBaseUrl = false,
  modelPlaceholder,
  baseUrlPlaceholder,
  onTest,
  onSuccess,
  helpUrl,
  helpLabel,
}: ApiKeyTesterProps) {
  const [apiKey, setApiKey] = useState('')
  const [model, setModel] = useState('')
  const [baseUrl, setBaseUrl] = useState('')
  const [status, setStatus] = useState<'idle' | 'testing' | 'ok' | 'error'>('idle')
  const [message, setMessage] = useState('')

  const extras: ApiKeyExtras = {
    model: model.trim() || undefined,
    baseUrl: baseUrl.trim() || undefined,
  }

  const handleTest = async () => {
    setStatus('testing')
    setMessage('')
    try {
      const result = await onTest(apiKey, extras)
      if (result.ok) {
        setStatus('ok')
        await onSuccess(apiKey, extras)
      } else {
        setStatus('error')
        setMessage(result.message_es)
      }
    } catch {
      setStatus('error')
      setMessage('No se pudo comprobar la conexión. Revisa tu conexión a internet.')
    }
  }

  const handleHelpClick = (event: MouseEvent<HTMLAnchorElement>) => {
    if (window.desktopApi && helpUrl) {
      event.preventDefault()
      window.desktopApi.openExternalLink(helpUrl)
    }
  }

  const inputClass =
    'w-full rounded-lg border border-[var(--color-border)] bg-transparent px-3 py-2 text-sm outline-none focus:border-[var(--color-primary)]'
  const missingRequired =
    (needsKey && apiKey.trim().length === 0) ||
    (needsBaseUrl && baseUrl.trim().length === 0) ||
    (needsModel && model.trim().length === 0)

  return (
    <div className="flex flex-col gap-2">
      {needsKey && (
        <input
          type="password"
          value={apiKey}
          onChange={(event) => {
            setApiKey(event.target.value)
            setStatus('idle')
          }}
          placeholder="Pega aquí tu clave de API"
          className={inputClass}
        />
      )}
      {needsBaseUrl && (
        <input
          type="text"
          value={baseUrl}
          onChange={(event) => {
            setBaseUrl(event.target.value)
            setStatus('idle')
          }}
          placeholder={baseUrlPlaceholder ?? 'Dirección de la API'}
          className={inputClass}
        />
      )}
      {needsModel && (
        <input
          type="text"
          value={model}
          onChange={(event) => {
            setModel(event.target.value)
            setStatus('idle')
          }}
          placeholder={modelPlaceholder ?? 'Nombre del modelo'}
          className={inputClass}
        />
      )}
      {helpUrl && (
        <a
          href={helpUrl}
          target="_blank"
          rel="noreferrer noopener"
          onClick={handleHelpClick}
          className="self-start text-xs text-[var(--color-primary)] underline"
        >
          {helpLabel ?? 'Obtener clave'}
        </a>
      )}
      <div className="flex items-center gap-3">
        <Button
          variant="secondary"
          onClick={handleTest}
          disabled={missingRequired}
          loading={status === 'testing'}
        >
          Probar conexión
        </Button>
        {status === 'ok' && (
          <span className="text-sm text-[var(--color-success)]">✓ Conectado correctamente</span>
        )}
      </div>
      {status === 'error' && <p className="text-sm text-[var(--color-danger)]">{message}</p>}
    </div>
  )
}
