# Personalizaciones sobre MoneyPrinterTurbo

Este documento explica **qué partes de este proyecto son originales** del
proyecto oficial [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo)
y **cuáles se añadieron** para convertirlo en una aplicación de escritorio
amigable para usuarios no técnicos.

El objetivo es que, cuando salga una nueva versión del proyecto oficial,
sea **fácil incorporarla sin rehacer este trabajo**. Para ello, casi todo lo
personalizado vive en **archivos nuevos y separados**, y los archivos del
núcleo original se tocaron lo mínimo posible (solo cambios aditivos).

---

## 1. Archivos NUEVOS (100 % personalizados)

Estos archivos no existen en el proyecto oficial. Una actualización del
upstream **nunca los tocará**, así que se pueden conservar tal cual.

### Backend (Python)
- `app/services/setup.py` — lógica del asistente de configuración: probar
  conexión de cada proveedor de IA/vídeo, guardar ajustes, diagnóstico del
  sistema. **No hay que pedir API keys durante el desarrollo**: todo se
  configura desde la app final.
- `app/services/voice_catalog.py` — catálogo de voces con nombres amigables
  ("Español (Colombia) — Mujer") en vez de los técnicos ("es-CO-...").
- `app/services/updates.py` — comprobar e instalar nuevas versiones del
  proyecto oficial, con copia de seguridad y restauración automática.
- `app/services/branding.py` — superposición del logo de marca sobre el
  vídeo (contexto de IA y materiales propios reutilizan funciones ya
  existentes del núcleo; ver tabla 2 para el enganche de 1 línea).
- `app/controllers/v1/system.py` — endpoints `/api/v1/system/*` que consume
  la interfaz nueva (onboarding, ajustes, voces, diagnóstico, updates).
- `app/utils/error_messages.py` — traduce cualquier excepción a un mensaje
  claro en español (nunca se muestra un traceback de Python al usuario).

### Frontend y escritorio (nuevo, reemplaza a la WebUI de Streamlit)
- `desktop/frontend/` — interfaz nueva en React + Vite + TypeScript.
- `desktop/electron/` — envoltorio de escritorio (Electron) que arranca el
  backend y muestra la interfaz como una app nativa.
- `desktop/build/backend.spec` — receta de PyInstaller para empaquetar el
  backend como ejecutable (el usuario final no necesita instalar Python).

### Tests nuevos
- `test/services/test_setup.py`
- `test/services/test_voice_catalog.py`
- `test/utils/test_error_messages.py`
- `test/controllers/test_system.py`
- `test/config/test_config_secrets.py`

---

## 2. Archivos del núcleo ORIGINAL modificados (cambios mínimos y aditivos)

Estos SÍ existen en el proyecto oficial y se editaron un poco. Si una
actualización toca alguno, puede haber que resolver un pequeño conflicto.
La app avisa de esto en "Buscar actualizaciones". Cada cambio es aditivo
(no borra ni reescribe lógica original):

| Archivo | Qué se añadió | Por qué |
|---|---|---|
| `app/router.py` | registra el router `system` | exponer los endpoints nuevos |
| `app/asgi.py` | manejador global de excepciones + servir el frontend por HTTP (`MPT_FRONTEND_DIR`) | traducir errores; que la ventana cargue la interfaz sin `file://` |
| `app/models/schema.py` | modelos Pydantic nuevos (al final) + campos de logo en `VideoParams` | validar peticiones del asistente y la superposición del logo |
| `app/services/task.py` | campo `stage` + captura de errores del pipeline | mostrar el checklist de progreso y no dejar tareas "colgadas" |
| `app/services/video.py` | 1 línea: llama a `branding.apply_logo_overlay` | superponer el logo de marca (no-op si no hay logo) |
| `app/services/material.py` | `_get_tls_verify` → `get_tls_verify` (público) | reutilizar la verificación TLS al probar Pexels/Pixabay/Coverr |
| `app/config/config.py` | rutas en `MPT_USER_DATA_DIR`, puerto/host por env var, migración de claves antiguas | funcionar empaquetado; las claves se guardan en el config.toml del usuario (el llavero colgaba la app sin firmar) |
| `app/utils/utils.py` | rutas compatibles con PyInstaller y carpeta de datos del usuario | funcionar como app instalada, no como proyecto de GitHub |
| `pyproject.toml` | grupos de dependencias `dev` y `build`, config de ruff/black/mypy | herramientas de calidad y empaquetado |
| `.github/workflows/ci.yml` | añade los tests nuevos y lint/typecheck | CI del código personalizado |

---

## 3. Todo lo demás = proyecto ORIGINAL sin tocar

El resto de `app/` (services de LLM, voz, vídeo, subtítulos, materiales…),
`webui/` (la interfaz Streamlit original, que queda como herramienta
legacy), `cli.py`, `docs/`, etc., son del proyecto oficial y **no se
modificaron**. Toda la generación de vídeo real sigue usando ese código.

---

## 4. Cómo actualizar desde el proyecto oficial

**Opción fácil (recomendada):** desde la app, pestaña **Configuración →
Buscar actualizaciones**. Comprueba si hay versión nueva, muestra los
cambios, avisa si afecta a algún archivo modificado, hace copia de
seguridad y, si algo falla, restaura la versión anterior automáticamente.

**Opción manual (para desarrolladores):**
```bash
git fetch origin
git merge origin/main   # resolver conflictos solo en los archivos de la tabla 2
uv sync                 # actualizar dependencias
cd desktop/frontend && npm install && npm run build
```
Los archivos de la sección 1 no dan conflictos porque el upstream no los
conoce.
