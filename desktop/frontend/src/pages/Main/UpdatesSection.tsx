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
      // The Electron shell downloads the .dmg and swaps the installed app;
      // the backend only told us where to get it (result.download_url).
      if (!window.desktopApi?.applyUpdate || !result?.download_url) {
        setApplyMessage('Abre la app instalada para poder actualizar automáticamente.')
        return
      }
      const applyResult = await window.desktopApi.applyUpdate(result.download_url)
      setApplyMessage(applyResult.message_es)
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
              {result.notes && (
                <div className="mt-2">
                  <p className="text-xs font-medium text-[var(--color-text-muted)]">
                    Novedades de esta versión:
                  </p>
                  <p className="mt-1 whitespace-pre-line text-xs text-[var(--color-text-muted)]">
                    {result.notes}
                  </p>
                </div>
              )}

              {!confirming ? (
                <Button className="mt-3" onClick={() => setConfirming(true)} disabled={applying}>
                  Actualizar ahora
                </Button>
              ) : (
                <div className="mt-3 flex flex-col gap-2">
                  <p className="text-xs text-[var(--color-text-muted)]">
                    Se descargará e instalará la nueva versión. La app se cerrará y volverá a abrir
                    sola. ¿Continuar?
                  </p>
                  <div className="flex gap-2">
                    <Button onClick={apply} loading={applying}>
                      Sí, actualizar
                    </Button>
                    <Button variant="ghost" onClick={() => setConfirming(false)} disabled={applying}>
                      Cancelar
                    </Button>
                  </div>
                </div>
              )}
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
