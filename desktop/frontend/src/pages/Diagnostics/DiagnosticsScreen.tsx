import { useCallback, useEffect, useState } from 'react'
import { api } from '../../api/client'
import type { DiagnosticCheck } from '../../api/types'
import { Button } from '../../components/Button'
import { ErrorBanner } from '../../components/ErrorBanner'
import { Spinner } from '../../components/Spinner'

type Phase = 'connecting' | 'checking' | 'issues' | 'backend_unreachable'

const PING_RETRIES = 20
const PING_INTERVAL_MS = 600

// The LLM/material provider checks are expected to fail before the user has
// completed the wizard — that is what the wizard is for, not a system
// problem worth blocking the app over.
const NON_BLOCKING_CHECKS = new Set(['llm_provider'])

interface DiagnosticsScreenProps {
  onReady: () => void
}

export function DiagnosticsScreen({ onReady }: DiagnosticsScreenProps) {
  const [phase, setPhase] = useState<Phase>('connecting')
  const [checks, setChecks] = useState<DiagnosticCheck[]>([])
  const [attempt, setAttempt] = useState(0)

  const runChecks = useCallback(async () => {
    setPhase('connecting')

    let connected = false
    for (let i = 0; i < PING_RETRIES; i += 1) {
      try {
        await api.ping()
        connected = true
        break
      } catch {
        await new Promise((resolve) => setTimeout(resolve, PING_INTERVAL_MS))
      }
    }

    if (!connected) {
      setPhase('backend_unreachable')
      return
    }

    setPhase('checking')
    try {
      const result = await api.diagnostics()
      setChecks(result.checks)
      const blockingFailures = result.checks.filter(
        (check) => !check.ok && !NON_BLOCKING_CHECKS.has(check.name),
      )
      if (blockingFailures.length === 0) {
        onReady()
      } else {
        setPhase('issues')
      }
    } catch {
      setPhase('backend_unreachable')
    }
  }, [onReady])

  useEffect(() => {
    runChecks()
  }, [runChecks, attempt])

  const retry = () => setAttempt((current) => current + 1)

  return (
    <div className="mx-auto flex min-h-full max-w-md flex-col items-center justify-center gap-6 p-8 text-center">
      <h1 className="text-xl font-semibold">MoneyPrinterTurbo</h1>

      {phase === 'connecting' && <Spinner label="Iniciando la aplicación…" />}
      {phase === 'checking' && <Spinner label="Comprobando tu sistema…" />}

      {phase === 'backend_unreachable' && (
        <ErrorBanner
          message="No se pudo iniciar la aplicación. Vuelve a intentarlo."
          onRetry={retry}
        />
      )}

      {phase === 'issues' && (
        <div className="flex w-full flex-col gap-3">
          {checks
            .filter((check) => !check.ok)
            .map((check) => (
              <div
                key={check.name}
                className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-left dark:border-amber-900 dark:bg-amber-950"
              >
                <p className="text-sm font-medium text-amber-800 dark:text-amber-200">
                  {check.message_es}
                </p>
                {check.fix_hint_es && (
                  <p className="mt-1 text-xs text-amber-700 dark:text-amber-300">
                    {check.fix_hint_es}
                  </p>
                )}
              </div>
            ))}
          <div className="mt-2 flex justify-center gap-3">
            <Button variant="secondary" onClick={retry}>
              Reintentar
            </Button>
            <Button variant="ghost" onClick={onReady}>
              Continuar de todos modos
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
