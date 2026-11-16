import { contextBridge, ipcRenderer } from 'electron'

// The only bridge between the sandboxed renderer (the React app) and the
// OS. Kept intentionally small: native folder/file dialogs, the backend's
// actual port, opening links in the real browser, and quitting — nothing
// that would let arbitrary web content reach the filesystem directly.
contextBridge.exposeInMainWorld('desktopApi', {
  selectOutputFolder: (): Promise<string | null> =>
    ipcRenderer.invoke('dialog:selectOutputFolder'),
  selectFolder: (): Promise<string | null> => ipcRenderer.invoke('dialog:selectFolder'),
  saveFileAs: (defaultName: string): Promise<string | null> =>
    ipcRenderer.invoke('dialog:saveFileAs', defaultName),
  getBackendPort: (): Promise<number> => ipcRenderer.invoke('backend:getPort'),
  openExternalLink: (url: string): void => {
    ipcRenderer.invoke('shell:openExternal', url)
  },
  quitApp: (): void => {
    ipcRenderer.invoke('app:quit')
  },
  applyUpdate: (downloadUrl: string): Promise<{ ok: boolean; message_es: string }> =>
    ipcRenderer.invoke('update:apply', downloadUrl),
})
