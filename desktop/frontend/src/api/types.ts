export interface ApiEnvelope<T> {
  status: number
  message?: string
  data: T
}

export type LlmProviderId =
  | 'gemini'
  | 'openai'
  | 'groq'
  | 'ollama'
  | 'claude'
  | 'moonshot'
  | 'deepseek'
  | 'qwen'
  | 'zai'
export type MaterialProviderId = 'pexels' | 'pixabay' | 'coverr'

export interface ConnectionTestResult {
  ok: boolean
  message_es: string
}

export interface LlmSettings {
  provider: string
  masked_api_key: string
}

export interface MaterialSettings {
  pexels: boolean
  pixabay: boolean
  coverr: boolean
}

export interface FriendlyVoiceDto {
  id: string
  label_es: string
  gender: string
  provider: string
}

export interface VoiceGroupDto {
  language_label_es: string
  voices: FriendlyVoiceDto[]
}

export interface VoicePreviewResult {
  ok: boolean
  message_es?: string
  audio_base64?: string
  mime_type?: string
}

export interface GeneralSettings {
  output_directory: string
  video_aspect: string
  voice_name: string
  max_concurrent_tasks: number
}

export interface DiagnosticCheck {
  name: string
  ok: boolean
  message_es: string
  fix_hint_es?: string
}

export interface DiagnosticsResult {
  checks: DiagnosticCheck[]
  all_ok: boolean
}

export type VideoFormat = 'tiktok' | 'youtube_shorts' | 'instagram_reels'
export type VideoDuration = 30 | 60 | 90

// Mirrors app/models/const.py TASK_STATE_*
export const TASK_STATE_FAILED = -1
export const TASK_STATE_COMPLETE = 1
export const TASK_STATE_PROCESSING = 4

export type TaskStage =
  | 'script'
  | 'terms'
  | 'audio'
  | 'subtitle'
  | 'materials'
  | 'video'
  | 'done'

export interface TaskStatus {
  task_id: string
  state: number
  progress: number
  stage?: TaskStage
  error_message?: string
  error_code?: string
  videos?: string[]
  combined_videos?: string[]
}

export interface UpdateCheckResult {
  update_available: boolean
  message_es: string
  version?: string
  installed_version?: string
  latest_version?: string
  notes?: string
  download_url?: string
}

export interface UpdateApplyResult {
  ok: boolean
  message_es: string
}

export interface BrandSettings {
  brand_context: string
  logo_filename: string
  logo_position: string
  logo_size: number
  use_own_materials: boolean
  supplement_with_stock: boolean
  content_language: string
  persuasive_mode: boolean
  target_audience: string
  role_models: Record<string, string>
  materials_folder: string
  enhance_media: boolean
}

export interface ClonedVoice {
  id: string
  title: string
  voice_name: string
}

export interface VoiceCloneSettings {
  fish_configured: boolean
  fish_masked_key: string
  cloned_voices: ClonedVoice[]
  current_voice: string
}

export interface MimikaStatus {
  reachable: boolean
  engines: string[]
  base_url: string
}

export interface CreateVideoRequest {
  video_subject: string
  video_aspect: string
  paragraph_number: number
  video_source: string
  voice_name: string
  // Brand / localization additions (all optional; empty = default behavior)
  video_script_prompt?: string
  video_language?: string
  video_terms?: string
  logo_path?: string
  logo_position?: string
  logo_size?: number
  video_materials?: { provider: string; url: string }[]
  supplement_with_stock?: boolean
  fallback_source?: string
}

// The underlying engine has no "make it exactly N seconds" knob: length is
// a side effect of how much narration the LLM writes. paragraph_number is
// the closest real lever, so duration options map to a rough paragraph
// count rather than a literal seconds value.
export const DURATION_TO_PARAGRAPHS: Record<VideoDuration, number> = {
  30: 1,
  60: 2,
  90: 4,
}

// TikTok, YouTube Shorts and Instagram Reels are all vertical 9:16 video —
// the "format" choice only exists so the user can pick the platform they
// have in mind, it does not change the technical output.
export const FORMAT_TO_ASPECT: Record<VideoFormat, string> = {
  tiktok: '9:16',
  youtube_shorts: '9:16',
  instagram_reels: '9:16',
}
