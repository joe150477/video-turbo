# ESTADO — VIDEO TURBO
Fork de MoneyPrinterTurbo: app de escritorio macOS que crea videos cortos (guion IA, voz, subtítulos, stock o material propio). Memorias clave: `videoturbo-desktop-app`, `persuasive-brain-and-voice-roadmap`, `auto-update-plan`, `image-sources-and-script-field`.

## Archivos clave
- Backend FastAPI `app/`: services (llm, voice, script_studio, setup, task, video, material, branding, updates, voice_catalog), `controllers/v1/system.py`, `asgi.py`.
- `desktop/`: frontend React + electron; `build/backend.spec` (PyInstaller). `webui/` Streamlit legacy.
- App INSTALADA en `/Applications/MoneyPrinterTurbo.app` (sirve en 127.0.0.1:8081). Se puede actualizar en caliente copiando backend+frontend nuevos a `Contents/Resources/` (sin DMG).

## Hecho esta fase (verificado)
- Cerebro persuasivo: cadena Research→Marketing→Copywriter→QA (`script_studio.py`), multi-modelo por rol, memoria de marca. Empaquetado.
- Materiales reales: "carpeta viva" (re-sync al generar) + mejora automática de fotos (`enhance_image_file`).
- Voz clonada (dos opciones):
  - Fish Audio (nube): `fish_tts`/`create_fish_voice_clone`, API real verificada. Voz `fish:id:label`. Gratis prueba; comercial ~1-2¢/video.
  - MimikaStudio (LOCAL gratis, 127.0.0.1:7693): `mimika_tts`/`create_mimika_voice_clone`; motores chatterbox(es/en) y qwen3(Spanish/English). PROBADO EN VIVO (clonó+generó español). Voz `mimika:engine:name`.
  - UI Configuración→Voz→"Clonar mi propia voz" (local primero + Fish). Endpoints `/system/voices/mimika-status`, `/clone-local`, `/clone`.
- Fix caché: `asgi._SpaStaticFiles` sirve index.html con `no-store` (para que las mejoras se vean sin trucos).
- 16+ tests de voz OK; ruff/black/typecheck/lint limpios.

## Pendiente
- Usuario: con MimikaStudio ABIERTO, grabar voz (15-30s, M4A/WAV) y clonarla; textos de muestra ES/EN ya entregados. Luego rehacer videos NAS con su voz.
- Auto-actualización EN CURSO (2026-11-16): decisión = app se auto-actualiza con NUESTRAS versiones (GitHub Actions + Releases en repo `joe150477/video-turbo`) + yo traigo mejoras del original A MANO con pruebas. Pasos: usuario crea repo PÚBLICO vacío `video-turbo` → yo hago commit de todo (hoy sin confirmar) + workflow + actualizador 1-clic → push. Seguridad OK: sin claves en archivos rastreados (config.toml vacío). Ver `auto-update-plan`.
- Original (harry0703) va 201 commits ADELANTE (nuestro fork del 3-jul; original al 8-sep). Reescribió los mismos archivos que personalizamos (voice/task/material/llm/video) ⇒ merge automático ROMPERÍA lo nuestro; por eso cherry-pick manual. Mejoras a traer: subtítulos palabra-por-palabra, texto-a-imagen, Kokoro TTS, fix seguridad CORS. `origin/main` ya fetcheado.
- Regenerar `.dmg` cuando el disco esté libre (hoy electron-builder se colgó por `mediaanalysisd` saturando disco; se parcheó la app en caliente).
- Fase grande siguiente: modo ASISTENTE conversacional (chat que pregunta/razona + enrutador multi-modelo por cuota, estilo opencode) = el "Director General". Luego fuentes de imágenes (Unsplash/Wikimedia + legalidad) + campo de guion/storyboard.
- Defecto: `CreateVideoTab` mandaba brand_context como `video_script_prompt` y saltaba el cerebro persuasivo; corregido en frontend, verificar en próxima build.

## Reglas / riesgos
- La IA que genera los guiones NO es Claude Code ni gasta esos tokens: usa el proveedor LLM que el usuario configuró (hoy = Groq, gratis). Opciones gratis/local: Groq, Ollama, Gemini, OpenRouter :free, DeepSeek, Qwen. MimikaStudio (voz) = local gratis; Fish = centavos.
- Probar de verdad antes de declarar hecho; decir qué no se pudo probar. Botón `open` por entregable + carpeta.
- `~/Documents` en iCloud: lecturas de disco a veces se cuelgan (mediaanalysisd/iCloud) y los builds grandes fallan hasta que el disco se calme.
- Trabajo paralelo (otros proyectos, ver memorias): Phoînix (`phoinix-app`; IA local + Claude Code offline, en `~/Documents/Claude Code/Phoînix`), Whiteboard Ads NAS (`whiteboard-explainer-skill`), FootIQ (`footiq-app`; v5.56 lista (registro honesto) (Segura sin VIGILAR + check «Ya la anoté»), pendiente Commit+Push y reabrir app en iPhone; cuotas ESPN se guardan solas cada 3 h en `~/Developer/footiq-datos`), voz guardada Chatterbox (`voz-guardada-chatterbox`).
