import { useState } from 'react'
import { api } from '../../api/client'
import { Button } from '../../components/Button'
import type { UpdateCheckResult } from '../../api/types'

// "Buscar actualizaciones": checks the upstream MoneyPrinterTurbo project,
// shows what's new and whether it's compatible, and applies it with one
// click (after an explicit confirmation). The backend always backs up
// first and rolls back on failure — this component never auto-updates.
export function UpdatesSection() {
  const [checking, setChecking] = useState(false)
  const [applying, setApplying] = useState(false)
  const [result, setResult] = useState<UpdateCheckResult | null>(null)
  const [applyMessage, setApplyMessage] = useState<string | null>(null)
  const [confirming, setConfirming] = useState(false)

  const check = async () => {
    setChecking(true)
    setApplyMessage(null)
    setConfirming(false)
    try {
      setResult(await api.checkForUpdates())
    } catch {
      setResult({
        update_available: false,
        message_es: 'No se pudo comprobar si hay actualizaciones. Revisa tu conexión.',
      })
    } finally {
      setChecking(false)
    }
  }

  const apply = async () => {
    setApplying(true)
    setConfirming(false)
    try {
      const applyResult = await api.applyUpdate()
      setApplyMessage(applyResult.message_es)
      if (applyResult.ok) setResult(null)
    } catch {
      setApplyMessage('No se pudo completar la actualización. Inténtalo de nuevo.')
    } finally {
      setApplying(false)
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <p className="text-xs text-[var(--color-text-muted)]">
        Comprueba si hay una versión más reciente del motor de MoneyPrinterTurbo.
      </p>

      <div>
        <Button variant="secondary" onClick={check} loading={checking}>
          Buscar actualizaciones
        </Button>
      </div>

      {result && (
        <div className="rounded-xl border border-[var(--color-border)] p-3 text-sm">
          <p>{result.message_es}</p>

          {result.update_available && (
            <>
              {result.changes && result.changes.length > 0 && (
                <div className="mt-2">
                  <p className="text-xs font-medium text-[var(--color-text-muted)]">
                    Cambios incluidos:
                  </p>
                  <ul className="mt-1 list-disc pl-5 text-xs text-[var(--color-text-muted)]">
                    {result.changes.slice(0, 8).map((change, index) => (
                      <li key={index}>{change}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* A packaged app (can_auto_apply === false) can detect a new
                  version but can't rewrite its own files, so it only guides
                  the user to download the new installer — no apply button. */}
              {result.can_auto_apply !== false &&
                (!confirming ? (
                  <Button className="mt-3" onClick={() => setConfirming(true)} disabled={applying}>
                    Actualizar ahora
                  </Button>
                ) : (
                  <div className="mt-3 flex flex-col gap-2">
                    <p className="text-xs text-[var(--color-text-muted)]">
                      Se creará una copia de seguridad automática antes de actualizar. ¿Continuar?
                    </p>
                    <div className="flex gap-2">
                      <Button onClick={apply} loading={applying}>
                        Sí, actualizar
                      </Button>
                      <Button
                        variant="ghost"
                        onClick={() => setConfirming(false)}
                        disabled={applying}
                      >
                        Cancelar
                      </Button>
                    </div>
                  </div>
                ))}
            </>
          )}
        </div>
      )}

      {applyMessage && (
        <div className="rounded-xl border border-[var(--color-border)] p-3 text-sm">
          {applyMessage}
        </div>
      )}
    </div>
  )
}
