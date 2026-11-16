import type {
  ApiEnvelope,
  BrandSettings,
  MimikaStatus,
  VoiceCloneSettings,
  ConnectionTestResult,
  CreateVideoRequest,
  DiagnosticsResult,
  GeneralSettings,
  LlmProviderId,
  LlmSettings,
  MaterialProviderId,
  MaterialSettings,
  TaskStatus,
  UpdateCheckResult,
  VoiceGroupDto,
  VoicePreviewResult,
} from './types'

// In dev, Vite proxies /api to the FastAPI backend (see vite.config.ts).
// In the packaged app, Electron's preload script exposes the backend's
// actual port (it can change if 8080 was already taken).
async function backendBaseUrl(): Promise<string> {
  if (window.desktopApi) {
    const port = await window.desktopApi.getBackendPort()
    return `http://127.0.0.1:${port}`
  }
  return ''
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const base = await backendBaseUrl()
  const response = await fetch(`${base}/api/v1${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })

  if (!response.ok && response.status !== 400) {
    throw new Error(`request_failed:${response.status}`)
  }

  const body = (await response.json()) as ApiEnvelope<T>
  return body.data
}

function post<T>(path: string, payload: unknown): Promise<T> {
  return request<T>(path, { method: 'POST', body: JSON.stringify(payload) })
}

async function upload<T>(path: string, file: File): Promise<T> {
  const base = await backendBaseUrl()
  const form = new FormData()
  form.append('file', file)
  // No JSON Content-Type here: the browser sets the multipart boundary.
  const response = await fetch(`${base}/api/v1${path}`, { method: 'POST', body: form })
  if (!response.ok && response.status !== 400) {
    throw new Error(`request_failed:${response.status}`)
  }
  const body = (await response.json()) as ApiEnvelope<T>
  return body.data
}

function del<T>(path: string): Promise<T> {
  return request<T>(path, { method: 'DELETE' })
}

function get<T>(path: string): Promise<T> {
  return request<T>(path)
}

export const api = {
  ping: () => get<{ ok: boolean }>('/system/ping'),
  diagnostics: () => get<DiagnosticsResult>('/system/diagnostics'),

  onboardingStatus: () => get<{ completed: boolean }>('/system/onboarding/status'),
  completeOnboarding: () => post<{ completed: boolean }>('/system/onboarding/complete', {}),

  testLlmProvider: (
    provider: LlmProviderId,
    api_key: string,
    model_name?: string,
    base_url?: string,
  ) =>
    post<ConnectionTestResult>('/system/settings/llm/test', {
      provider,
      api_key,
      model_name,
      base_url,
    }),
  saveLlmProvider: (
    provider: LlmProviderId,
    api_key: string,
    model_name?: string,
    base_url?: string,
  ) => post<{ saved: boolean }>('/system/settings/llm', { provider, api_key, model_name, base_url }),
  getLlmSettings: () => get<LlmSettings>('/system/settings/llm'),

  testMaterialProvider: (provider: MaterialProviderId, api_key: string) =>
    post<ConnectionTestResult>('/system/settings/material/test', { provider, api_key }),
  saveMaterialProvider: (provider: MaterialProviderId, api_key: string) =>
    post<{ saved: boolean }>('/system/settings/material', { provider, api_key }),
  getMaterialSettings: () => get<MaterialSettings>('/system/settings/material'),

  getVoices: () => get<{ groups: VoiceGroupDto[] }>('/system/voices'),
  previewVoice: (voice_id: string) =>
    post<VoicePreviewResult>('/system/voices/preview', { voice_id }),

  getGeneralSettings: () => get<GeneralSettings>('/system/settings/general'),
  saveGeneralSettings: (payload: Partial<GeneralSettings>) =>
    post<{ saved: boolean }>('/system/settings/general', payload),

  createVideo: (payload: CreateVideoRequest) =>
    post<{ task_id: string }>('/videos', payload),
  getTask: (taskId: string) => get<TaskStatus>(`/tasks/${taskId}`),

  checkForUpdates: () => get<UpdateCheckResult>('/system/updates/check'),

  getBrandSettings: () => get<BrandSettings>('/system/settings/brand'),
  saveBrandSettings: (payload: Partial<BrandSettings>) =>
    post<{ saved: boolean }>('/system/settings/brand', payload),
  uploadLogo: (file: File) =>
    upload<{ logo_filename: string }>('/system/settings/brand/logo', file),
  deleteLogo: () => del<{ removed: boolean }>('/system/settings/brand/logo'),

  listMaterials: () => get<{ materials: string[] }>('/system/materials'),
  uploadMaterial: (file: File) => upload<{ file: string }>('/system/materials', file),
  deleteMaterial: (filename: string) =>
    del<{ removed: boolean }>(`/system/materials/${encodeURIComponent(filename)}`),
  importMaterialsFolder: (folder: string) =>
    post<{ ok: boolean; imported: number; message_es: string }>(
      '/system/materials/import-folder',
      { folder },
    ),
  syncMaterialsFolder: () =>
    post<{ ok: boolean; imported: number; message_es: string }>(
      '/system/materials/sync-folder',
      {},
    ),

  getVoiceClone: () => get<VoiceCloneSettings>('/system/settings/voice-clone'),
  testFishKey: (api_key: string) =>
    post<{ ok: boolean; message_es: string }>('/system/settings/voice-clone/test', { api_key }),
  saveFishKey: (api_key: string) =>
    post<{ ok: boolean; message_es: string }>('/system/settings/voice-clone/key', { api_key }),
  cloneVoice: async (file: File, title: string) => {
    const base = await backendBaseUrl()
    const form = new FormData()
    form.append('file', file)
    const url = `${base}/api/v1/system/voices/clone?title=${encodeURIComponent(title)}`
    const response = await fetch(url, { method: 'POST', body: form })
    if (!response.ok && response.status !== 400) {
      throw new Error(`request_failed:${response.status}`)
    }
    const body = (await response.json()) as ApiEnvelope<{
      ok: boolean
      voice_name?: string
      message_es: string
    }>
    return body.data
  },

  getMimikaStatus: () => get<MimikaStatus>('/system/voices/mimika-status'),
  cloneVoiceLocal: async (file: File, name: string, engine: string) => {
    const base = await backendBaseUrl()
    const form = new FormData()
    form.append('file', file)
    const url = `${base}/api/v1/system/voices/clone-local?name=${encodeURIComponent(
      name,
    )}&engine=${encodeURIComponent(engine)}`
    const response = await fetch(url, { method: 'POST', body: form })
    if (!response.ok && response.status !== 400) {
      throw new Error(`request_failed:${response.status}`)
    }
    const body = (await response.json()) as ApiEnvelope<{
      ok: boolean
      voice_name?: string
      message_es: string
    }>
    return body.data
  },
}
