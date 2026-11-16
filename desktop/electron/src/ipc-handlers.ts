import { spawn } from 'node:child_process'
import { createWriteStream, promises as fs } from 'node:fs'
import https from 'node:https'
import os from 'node:os'
import path from 'node:path'
import { type BrowserWindow, app, dialog, ipcMain, shell } from 'electron'
import type { BackendManager } from './backend-manager'

const APP_NAME = 'MoneyPrinterTurbo.app'

// Download a URL to a local file, following GitHub's redirect to its CDN.
function downloadFile(url: string, dest: string, redirectsLeft = 5): Promise<void> {
  return new Promise((resolve, reject) => {
    https
      .get(url, { headers: { 'User-Agent': 'VideoTurbo-Updater' } }, (response) => {
        const status = response.statusCode ?? 0
        if (status >= 300 && status < 400 && response.headers.location) {
          response.resume()
          if (redirectsLeft <= 0) return reject(new Error('too many redirects'))
          return resolve(downloadFile(response.headers.location, dest, redirectsLeft - 1))
        }
        if (status !== 200) {
          response.resume()
          return reject(new Error(`download failed: HTTP ${status}`))
        }
        const file = createWriteStream(dest)
        response.pipe(file)
        file.on('finish', () => file.close(() => resolve()))
        file.on('error', reject)
      })
      .on('error', reject)
  })
}

// Swap the running /Applications bundle for a freshly downloaded one. macOS
// can't replace an app while it runs, so a detached helper script waits for
// this process to quit, swaps the bundle, clears quarantine, and relaunches.
async function applyDownloadedUpdate(dmgPath: string): Promise<void> {
  const mountPoint = path.join(os.tmpdir(), `vt-update-${Date.now()}`)
  const scriptPath = path.join(os.tmpdir(), `vt-update-${Date.now()}.sh`)
  const appPath = `/Applications/${APP_NAME}`

  const script = `#!/bin/bash
set -e
# wait until this app has fully quit
for i in $(seq 1 60); do
  pgrep -f "${APP_NAME}/Contents/MacOS/MoneyPrinterTurbo" >/dev/null || break
  sleep 1
done
hdiutil attach "${dmgPath}" -nobrowse -mountpoint "${mountPoint}"
rm -rf "${appPath}"
ditto "${mountPoint}/${APP_NAME}" "${appPath}"
xattr -cr "${appPath}" 2>/dev/null || true
hdiutil detach "${mountPoint}" 2>/dev/null || true
rm -f "${dmgPath}" "${scriptPath}" 2>/dev/null || true
open "${appPath}"
`
  await fs.writeFile(scriptPath, script, { mode: 0o755 })
  const child = spawn('/bin/bash', [scriptPath], { detached: true, stdio: 'ignore' })
  child.unref()
}

export function registerIpcHandlers(
  backendManager: BackendManager,
  getWindow: () => BrowserWindow | null,
): void {
  ipcMain.handle('dialog:selectOutputFolder', async (): Promise<string | null> => {
    const window = getWindow()
    if (!window) return null
    const result = await dialog.showOpenDialog(window, {
      properties: ['openDirectory', 'createDirectory'],
    })
    if (result.canceled || result.filePaths.length === 0) return null
    return result.filePaths[0]
  })

  // Pick an existing folder (e.g. a synced Google Drive folder) to import
  // its photos/videos from. Separate from the output-folder picker so their
  // intents stay clear even though both open a directory dialog.
  ipcMain.handle('dialog:selectFolder', async (): Promise<string | null> => {
    const window = getWindow()
    if (!window) return null
    const result = await dialog.showOpenDialog(window, { properties: ['openDirectory'] })
    if (result.canceled || result.filePaths.length === 0) return null
    return result.filePaths[0]
  })

  ipcMain.handle(
    'dialog:saveFileAs',
    async (_event, defaultName: string): Promise<string | null> => {
      const window = getWindow()
      if (!window) return null
      const result = await dialog.showSaveDialog(window, { defaultPath: defaultName })
      if (result.canceled || !result.filePath) return null
      return result.filePath
    },
  )

  ipcMain.handle('backend:getPort', (): number => backendManager.port)

  ipcMain.handle('shell:openExternal', (_event, url: string): void => {
    if (url.startsWith('https://') || url.startsWith('http://')) {
      shell.openExternal(url)
    }
  })

  ipcMain.handle('app:quit', (): void => {
    app.quit()
  })

  // Download the new .dmg and install it: swap the /Applications bundle and
  // relaunch. Only accepts https URLs from the user's own GitHub release.
  ipcMain.handle(
    'update:apply',
    async (_event, downloadUrl: string): Promise<{ ok: boolean; message_es: string }> => {
      try {
        if (
          !downloadUrl.startsWith('https://github.com/') &&
          !downloadUrl.startsWith('https://objects.githubusercontent.com/')
        ) {
          return { ok: false, message_es: 'Enlace de descarga no válido.' }
        }
        const dmgPath = path.join(os.tmpdir(), `vt-update-${Date.now()}.dmg`)
        await downloadFile(downloadUrl, dmgPath)
        await applyDownloadedUpdate(dmgPath)
        // Give the helper script a moment to start, then quit so it can swap.
        setTimeout(() => app.quit(), 800)
        return {
          ok: true,
          message_es: 'Descarga lista. La app se cerrará y volverá a abrir ya actualizada…',
        }
      } catch (error) {
        return {
          ok: false,
          message_es: 'No se pudo descargar la actualización. Revisa tu conexión e inténtalo de nuevo.',
        }
      }
    },
  )
}
