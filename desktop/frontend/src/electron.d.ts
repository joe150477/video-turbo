export interface DesktopApi {
  selectOutputFolder(): Promise<string | null>
  selectFolder(): Promise<string | null>
  saveFileAs(defaultName: string): Promise<string | null>
  getBackendPort(): Promise<number>
  openExternalLink(url: string): void
  quitApp(): void
}

declare global {
  interface Window {
    // Only present when running inside the Electron shell (see
    // desktop/electron/src/preload.ts). Absent in the plain browser dev
    // server, where the app falls back to browser-native equivalents.
    desktopApi?: DesktopApi
  }
}
