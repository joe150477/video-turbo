import type { LlmProviderId, MaterialProviderId } from '../../api/types'

export interface LlmProviderMeta {
  id: LlmProviderId
  label: string
  recommended?: boolean
  needsKey: boolean
  helpUrl?: string
  helpLabel?: string
  // OpenAI-compatible providers (e.g. z.ai / GLM) where the user supplies
  // the endpoint and model name from their own dashboard.
  needsBaseUrl?: boolean
  needsModel?: boolean
  baseUrlPlaceholder?: string
  modelPlaceholder?: string
}

export const LLM_PROVIDERS: LlmProviderMeta[] = [
  {
    id: 'gemini',
    label: 'Gemini',
    recommended: true,
    needsKey: true,
    helpUrl: 'https://aistudio.google.com/apikey',
    helpLabel: 'Obtener clave gratis de Gemini',
  },
  {
    id: 'openai',
    label: 'OpenAI',
    needsKey: true,
    helpUrl: 'https://platform.openai.com/api-keys',
    helpLabel: 'Obtener clave de OpenAI',
  },
  {
    id: 'ollama',
    label: 'Ollama (local)',
    needsKey: false,
  },
  {
    id: 'groq',
    label: 'Groq',
    needsKey: true,
    helpUrl: 'https://console.groq.com/keys',
    helpLabel: 'Obtener clave de Groq',
  },
  {
    id: 'claude',
    label: 'Claude',
    needsKey: true,
    helpUrl: 'https://console.anthropic.com/settings/keys',
    helpLabel: 'Obtener clave de Claude',
  },
  {
    id: 'moonshot',
    label: 'Kimi (Moonshot)',
    needsKey: true,
    helpUrl: 'https://platform.moonshot.cn/console/api-keys',
    helpLabel: 'Obtener clave de Kimi',
  },
  {
    id: 'deepseek',
    label: 'DeepSeek',
    needsKey: true,
    helpUrl: 'https://platform.deepseek.com/api_keys',
    helpLabel: 'Obtener clave de DeepSeek',
  },
  {
    id: 'qwen',
    label: 'Qwen (Alibaba)',
    needsKey: true,
    helpUrl: 'https://dashscope.console.aliyun.com/apiKey',
    helpLabel: 'Obtener clave de Qwen',
  },
  {
    id: 'zai',
    label: 'z.ai (GLM)',
    needsKey: true,
    needsBaseUrl: true,
    needsModel: true,
    baseUrlPlaceholder: 'Dirección de la API (ej. https://api.z.ai/api/paas/v4)',
    modelPlaceholder: 'Nombre del modelo (ej. glm-4.6)',
    helpUrl: 'https://z.ai',
    helpLabel: 'Abrir z.ai',
  },
]

export interface MaterialProviderMeta {
  id: MaterialProviderId
  label: string
  helpUrl: string
}

export const MATERIAL_PROVIDERS: MaterialProviderMeta[] = [
  { id: 'pexels', label: 'Pexels', helpUrl: 'https://www.pexels.com/api/' },
  { id: 'pixabay', label: 'Pixabay', helpUrl: 'https://pixabay.com/api/docs/' },
  { id: 'coverr', label: 'Coverr', helpUrl: 'https://coverr.co' },
]
