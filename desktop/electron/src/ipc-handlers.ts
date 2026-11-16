import { type BrowserWindow, app, dialog, ipcMain, shell } from 'electron'
import type { BackendManager } from './backend-manager'

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
}
