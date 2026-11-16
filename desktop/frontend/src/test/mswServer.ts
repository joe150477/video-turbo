import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'

// Default happy-path handlers for every endpoint the app calls. Individual
// tests override specific routes with server.use(...) to exercise error
// paths, without having to restate the entire API surface each time.
export const handlers = [
  http.get('/api/v1/system/ping', () => HttpResponse.json({ status: 200, data: { ok: true } })),
  http.get('/api/v1/system/diagnostics', () =>
    HttpResponse.json({
      status: 200,
      data: {
        checks: [
          { name: 'ffmpeg', ok: true, message_es: 'FFmpeg funciona correctamente.' },
          { name: 'disk_space', ok: true, message_es: 'Espacio suficiente.' },
          { name: 'internet', ok: true, message_es: 'Conexión detectada.' },
          { name: 'output_folder', ok: true, message_es: 'Carpeta usable.' },
          { name: 'llm_provider', ok: false, message_es: 'Falta configurar IA.' },
        ],
        all_ok: false,
      },
    }),
  ),
  http.get('/api/v1/system/onboarding/status', () =>
    HttpResponse.json({ status: 200, data: { completed: false } }),
  ),
  http.post('/api/v1/system/onboarding/complete', () =>
    HttpResponse.json({ status: 200, data: { completed: true } }),
  ),
  http.post('/api/v1/system/settings/llm/test', () =>
    HttpResponse.json({ status: 200, data: { ok: true, message_es: 'Conectado correctamente.' } }),
  ),
  http.post('/api/v1/system/settings/llm', () =>
    HttpResponse.json({ status: 200, data: { saved: true } }),
  ),
  http.get('/api/v1/system/settings/llm', () =>
    HttpResponse.json({ status: 200, data: { provider: 'gemini', masked_api_key: '****1234' } }),
  ),
  http.post('/api/v1/system/settings/material/test', () =>
    HttpResponse.json({ status: 200, data: { ok: true, message_es: 'Conectado correctamente.' } }),
  ),
  http.post('/api/v1/system/settings/material', () =>
    HttpResponse.json({ status: 200, data: { saved: true } }),
  ),
  http.get('/api/v1/system/settings/material', () =>
    HttpResponse.json({ status: 200, data: { pexels: true, pixabay: false, coverr: false } }),
  ),
  http.get('/api/v1/system/voices', () =>
    HttpResponse.json({
      status: 200,
      data: {
        groups: [
          {
            language_label_es: 'Español',
            voices: [
              { id: 'es-CO-SalomeNeural-Female', label_es: 'Español (Colombia) — Mujer', gender: 'Female', provider: 'edge' },
              { id: 'es-MX-JorgeNeural-Male', label_es: 'Español (México) — Hombre', gender: 'Male', provider: 'edge' },
            ],
          },
          {
            language_label_es: 'Inglés',
            voices: [
              { id: 'en-US-AriaNeural-Female', label_es: 'Inglés (EE. UU.) — Mujer', gender: 'Female', provider: 'edge' },
            ],
          },
        ],
      },
    }),
  ),
  http.post('/api/v1/system/voices/preview', () =>
    HttpResponse.json({ status: 200, data: { ok: true, audio_base64: 'ZmFrZS1hdWRpbw==', mime_type: 'audio/mpeg' } }),
  ),
  http.get('/api/v1/system/settings/voice-clone', () =>
    HttpResponse.json({
      status: 200,
      data: { fish_configured: false, fish_masked_key: '', cloned_voices: [], current_voice: '' },
    }),
  ),
  http.get('/api/v1/system/voices/mimika-status', () =>
    HttpResponse.json({
      status: 200,
      data: { reachable: false, engines: [], base_url: 'http://127.0.0.1:7693' },
    }),
  ),
  http.get('/api/v1/system/settings/general', () =>
    HttpResponse.json({
      status: 200,
      data: { output_directory: '', video_aspect: '9:16', voice_name: '', max_concurrent_tasks: 5 },
    }),
  ),
  http.post('/api/v1/system/settings/general', () =>
    HttpResponse.json({ status: 200, data: { saved: true } }),
  ),
  http.post('/api/v1/videos', () =>
    HttpResponse.json({ status: 200, data: { task_id: 'task-123' } }),
  ),
  http.get('/api/v1/tasks/:taskId', () =>
    HttpResponse.json({
      status: 200,
      data: { task_id: 'task-123', state: 4, progress: 20, stage: 'audio' },
    }),
  ),
  http.get('/api/v1/system/updates/check', () =>
    HttpResponse.json({
      status: 200,
      data: { update_available: false, message_es: 'Ya tienes la versión más reciente.' },
    }),
  ),
  http.post('/api/v1/system/updates/apply', () =>
    HttpResponse.json({ status: 200, data: { ok: true, message_es: 'Actualización instalada.' } }),
  ),
  http.get('/api/v1/system/settings/brand', () =>
    HttpResponse.json({
      status: 200,
      data: {
        brand_context: '',
        logo_filename: '',
        logo_position: 'bottom-right',
        logo_size: 12,
        use_own_materials: false,
        supplement_with_stock: false,
        content_language: 'Español (Colombia)',
        persuasive_mode: true,
        target_audience: '',
        role_models: {},
        materials_folder: '',
        enhance_media: true,
      },
    }),
  ),
  http.post('/api/v1/system/settings/brand', () =>
    HttpResponse.json({ status: 200, data: { saved: true } }),
  ),
  http.post('/api/v1/system/settings/brand/logo', () =>
    HttpResponse.json({ status: 200, data: { logo_filename: 'logo.png' } }),
  ),
  http.delete('/api/v1/system/settings/brand/logo', () =>
    HttpResponse.json({ status: 200, data: { removed: true } }),
  ),
  http.get('/api/v1/system/materials', () =>
    HttpResponse.json({ status: 200, data: { materials: [] } }),
  ),
  http.post('/api/v1/system/materials', () =>
    HttpResponse.json({ status: 200, data: { file: 'clip.mp4' } }),
  ),
  http.delete('/api/v1/system/materials/:name', () =>
    HttpResponse.json({ status: 200, data: { removed: true } }),
  ),
  http.post('/api/v1/system/materials/import-folder', () =>
    HttpResponse.json({
      status: 200,
      data: { ok: true, imported: 5, message_es: 'Se importaron 5 archivo(s).' },
    }),
  ),
]

export const server = setupServer(...handlers)
