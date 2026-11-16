import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { api } from '../../api/client'
import { Button } from '../../components/Button'

const LOGO_POSITIONS = [
  { value: 'bottom-right', label: 'Abajo derecha' },
  { value: 'bottom-left', label: 'Abajo izquierda' },
  { value: 'top-right', label: 'Arriba derecha' },
  { value: 'top-left', label: 'Arriba izquierda' },
  { value: 'center', label: 'Centro' },
]

function SavedBadge({ show }: { show: boolean }) {
  return show ? <span className="text-xs text-[var(--color-success)]">Guardado ✓</span> : null
}

// The "Marca" settings section: brand context for the AI, a logo overlay,
// and the user's own image/video materials. Everything here is optional —
// leaving it empty keeps the default behavior.
export function BrandSection() {
  const queryClient = useQueryClient()
  const logoInputRef = useRef<HTMLInputElement>(null)
  const materialInputRef = useRef<HTMLInputElement>(null)

  const { data: brand } = useQuery({ queryKey: ['brand'], queryFn: () => api.getBrandSettings() })
  const { data: materialsData } = useQuery({
    queryKey: ['materials'],
    queryFn: () => api.listMaterials(),
  })

  const [context, setContext] = useState('')
  const [logoPosition, setLogoPosition] = useState('bottom-right')
  const [logoSize, setLogoSize] = useState(12)
  const [useOwnMaterials, setUseOwnMaterials] = useState(false)
  const [supplementWithStock, setSupplementWithStock] = useState(false)
  const [contentLanguage, setContentLanguage] = useState('Español (Colombia)')
  const [persuasiveMode, setPersuasiveMode] = useState(true)
  const [targetAudience, setTargetAudience] = useState('')
  const [enhanceMedia, setEnhanceMedia] = useState(true)
  const [saved, setSaved] = useState(false)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (brand) {
      setContext(brand.brand_context)
      setLogoPosition(brand.logo_position || 'bottom-right')
      setLogoSize(brand.logo_size || 12)
      setUseOwnMaterials(brand.use_own_materials)
      setSupplementWithStock(brand.supplement_with_stock)
      setContentLanguage(brand.content_language || 'Español (Colombia)')
      setPersuasiveMode(brand.persuasive_mode ?? true)
      setTargetAudience(brand.target_audience || '')
      setEnhanceMedia(brand.enhance_media ?? true)
    }
  }, [brand])

  const flashSaved = () => {
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['brand'] })
    queryClient.invalidateQueries({ queryKey: ['materials'] })
  }

  const saveSettings = async (patch: Record<string, unknown>) => {
    await api.saveBrandSettings(patch)
    flashSaved()
    refresh()
  }

  const onPickLogo = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return
    setBusy(true)
    try {
      await api.uploadLogo(file)
      refresh()
    } finally {
      setBusy(false)
      if (logoInputRef.current) logoInputRef.current.value = ''
    }
  }

  const onPickMaterials = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? [])
    if (files.length === 0) return
    setBusy(true)
    try {
      for (const file of files) await api.uploadMaterial(file)
      refresh()
    } finally {
      setBusy(false)
      if (materialInputRef.current) materialInputRef.current.value = ''
    }
  }

  const [importMessage, setImportMessage] = useState<string | null>(null)

  const onImportFolder = async () => {
    if (!window.desktopApi) return
    const folder = await window.desktopApi.selectFolder()
    if (!folder) return
    setBusy(true)
    setImportMessage(null)
    try {
      const result = await api.importMaterialsFolder(folder)
      setImportMessage(result.message_es)
      refresh()
    } catch {
      setImportMessage('No se pudo importar desde esa carpeta.')
    } finally {
      setBusy(false)
    }
  }

  const LANGUAGE_OPTIONS = [
    'Español (Colombia)',
    'Español (España)',
    'Español (México)',
    'Español neutro',
    'Inglés',
  ]

  return (
    <div className="flex flex-col gap-5">
      {/* 0. Persuasive brain: multi-agent script chain */}
      <div className="flex flex-col gap-2">
        <label className="flex items-start gap-2 text-sm font-medium">
          <input
            type="checkbox"
            className="mt-0.5"
            checked={persuasiveMode}
            onChange={(event) => {
              setPersuasiveMode(event.target.checked)
              saveSettings({ persuasive_mode: event.target.checked })
            }}
          />
          <span>
            Modo persuasivo (recomendado)
            <span className="block text-xs font-normal text-[var(--color-text-muted)]">
              La IA investiga tu público, elige el gancho y la llamada a la acción, escribe el
              guion y lo revisa antes de usarlo — para vender, no solo describir.
            </span>
          </span>
        </label>
        {persuasiveMode && (
          <div className="flex flex-col gap-1 pl-6">
            <label htmlFor="target-audience" className="text-xs font-medium">
              ¿A quién le hablas? (público objetivo)
            </label>
            <input
              id="target-audience"
              value={targetAudience}
              onChange={(event) => setTargetAudience(event.target.value)}
              onBlur={() => saveSettings({ target_audience: targetAudience })}
              maxLength={500}
              placeholder="Ej: Padres de familia en Barranquilla, estrato 4-6, que buscan un colegio bilingüe."
              className="w-full rounded-lg border border-[var(--color-border)] bg-transparent px-3 py-2 text-sm outline-none focus:border-[var(--color-primary)]"
            />
          </div>
        )}
      </div>

      {/* 0b. Content language */}
      <div className="flex flex-col gap-2 border-t border-[var(--color-border)] pt-4">
        <label htmlFor="content-language" className="text-sm font-medium">
          Idioma y acento del guion
        </label>
        <p className="text-xs text-[var(--color-text-muted)]">
          La IA escribirá el guion en este idioma. Recomendado: Español (Colombia) para tu público.
        </p>
        <select
          id="content-language"
          value={contentLanguage}
          onChange={(event) => {
            setContentLanguage(event.target.value)
            saveSettings({ content_language: event.target.value })
          }}
          className="w-full rounded-lg border border-[var(--color-border)] bg-transparent px-3 py-2 text-sm"
        >
          {LANGUAGE_OPTIONS.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </div>

      {/* 1. Brand context for the AI */}
      <div className="flex flex-col gap-2 border-t border-[var(--color-border)] pt-4">
        <label htmlFor="brand-context" className="text-sm font-medium">
          Contexto de tu marca (para la IA)
        </label>
        <p className="text-xs text-[var(--color-text-muted)]">
          Describe tu marca, tono y público. La IA lo usará para que los guiones suenen a ti.
        </p>
        <textarea
          id="brand-context"
          value={context}
          onChange={(event) => setContext(event.target.value)}
          rows={4}
          maxLength={2000}
          placeholder="Ej: Somos una cafetería artesanal. Tono cercano y alegre. Público joven que valora lo natural."
          className="w-full rounded-lg border border-[var(--color-border)] bg-transparent px-3 py-2 text-sm outline-none focus:border-[var(--color-primary)]"
        />
        <div className="flex items-center gap-3">
          <Button variant="secondary" onClick={() => saveSettings({ brand_context: context })}>
            Guardar contexto
          </Button>
          <SavedBadge show={saved} />
        </div>
      </div>

      {/* 2. Logo overlay */}
      <div className="flex flex-col gap-2 border-t border-[var(--color-border)] pt-4">
        <p className="text-sm font-medium">Logo sobre el vídeo</p>
        <p className="text-xs text-[var(--color-text-muted)]">
          {brand?.logo_filename
            ? 'Tu logo aparecerá en todos los vídeos.'
            : 'Sube un PNG (preferiblemente con fondo transparente).'}
        </p>
        <div className="flex items-center gap-3">
          <input
            ref={logoInputRef}
            type="file"
            accept="image/png,image/jpeg,image/webp"
            onChange={onPickLogo}
            className="hidden"
          />
          <Button variant="secondary" loading={busy} onClick={() => logoInputRef.current?.click()}>
            {brand?.logo_filename ? 'Cambiar logo' : 'Subir logo'}
          </Button>
          {brand?.logo_filename && (
            <Button
              variant="ghost"
              onClick={async () => {
                await api.deleteLogo()
                refresh()
              }}
            >
              Quitar logo
            </Button>
          )}
        </div>
        {brand?.logo_filename && (
          <div className="mt-2 flex flex-wrap items-end gap-4">
            <label className="flex flex-col gap-1 text-xs">
              Posición
              <select
                value={logoPosition}
                onChange={(event) => {
                  setLogoPosition(event.target.value)
                  saveSettings({ logo_position: event.target.value })
                }}
                className="rounded-lg border border-[var(--color-border)] bg-transparent px-3 py-2 text-sm"
              >
                {LOGO_POSITIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1 text-xs">
              Tamaño: {logoSize}%
              <input
                type="range"
                min={3}
                max={40}
                value={logoSize}
                onChange={(event) => setLogoSize(Number(event.target.value))}
                onMouseUp={() => saveSettings({ logo_size: logoSize })}
                onTouchEnd={() => saveSettings({ logo_size: logoSize })}
              />
            </label>
          </div>
        )}
      </div>

      {/* 3. Own materials */}
      <div className="flex flex-col gap-2 border-t border-[var(--color-border)] pt-4">
        <p className="text-sm font-medium">Tus propias imágenes y vídeos</p>
        <p className="text-xs text-[var(--color-text-muted)]">
          Súbelos o impórtalos desde una carpeta (por ejemplo tu Google Drive sincronizado).
          Mínimo 480×480 píxeles.
        </p>
        <input
          ref={materialInputRef}
          type="file"
          accept="video/mp4,video/quicktime,image/jpeg,image/png,image/webp"
          multiple
          onChange={onPickMaterials}
          className="hidden"
        />
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" loading={busy} onClick={() => materialInputRef.current?.click()}>
            Subir archivos
          </Button>
          {window.desktopApi && (
            <Button variant="secondary" loading={busy} onClick={onImportFolder}>
              {brand?.materials_folder ? 'Cambiar carpeta' : 'Elegir carpeta (Google Photos)'}
            </Button>
          )}
        </div>
        {brand?.materials_folder && (
          <p className="text-xs text-[var(--color-text-muted)]">
            📁 Tu carpeta: <span className="break-all">{brand.materials_folder}</span>
            <br />
            La app tomará de aquí tus fotos y vídeos, y buscará archivos nuevos automáticamente
            cada vez que generes un vídeo.
          </p>
        )}
        {importMessage && (
          <p className="text-xs text-[var(--color-text-muted)]">{importMessage}</p>
        )}
        <label className="flex items-start gap-2 text-sm">
          <input
            type="checkbox"
            className="mt-0.5"
            checked={enhanceMedia}
            onChange={(event) => {
              setEnhanceMedia(event.target.checked)
              saveSettings({ enhance_media: event.target.checked })
            }}
          />
          <span>
            Mejorar mis fotos automáticamente
            <span className="block text-xs font-normal text-[var(--color-text-muted)]">
              Ajusta color, contraste y nitidez, y corrige fotos giradas — para que se vean mejor
              aunque no sean perfectas.
            </span>
          </span>
        </label>
        {materialsData && materialsData.materials.length > 0 && (
          <>
            <ul className="mt-1 flex flex-col gap-1 text-xs">
              {materialsData.materials.map((name) => (
                <li key={name} className="flex items-center justify-between gap-2">
                  <span className="truncate">{name}</span>
                  <button
                    type="button"
                    className="text-[var(--color-danger)]"
                    onClick={async () => {
                      await api.deleteMaterial(name)
                      refresh()
                    }}
                  >
                    Quitar
                  </button>
                </li>
              ))}
            </ul>
            <label className="mt-2 flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={useOwnMaterials}
                onChange={(event) => {
                  setUseOwnMaterials(event.target.checked)
                  saveSettings({ use_own_materials: event.target.checked })
                }}
              />
              Usar mis archivos en los vídeos (en lugar de vídeos de stock)
            </label>
            {useOwnMaterials && (
              <label className="flex items-center gap-2 pl-6 text-sm text-[var(--color-text-muted)]">
                <input
                  type="checkbox"
                  checked={supplementWithStock}
                  onChange={(event) => {
                    setSupplementWithStock(event.target.checked)
                    saveSettings({ supplement_with_stock: event.target.checked })
                  }}
                />
                Completar con vídeos de stock si mis archivos no alcanzan
              </label>
            )}
          </>
        )}
      </div>
    </div>
  )
}
