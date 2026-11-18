# TASKS — Clase 11 (orquestador: tomar en orden, una a la vez)

> Rol estudiante: se trabaja en `Clase 11/starter/` (ver `starter/README.md`).
> `solucion-referencia/` es del profesor: mirarla invalida el ejercicio.
> `python "Clase 11/starter/check.py"` es el juez: arranca en 3/9 y debe llegar a 9/9.

- [x] **T0 Fork + starter.** Fork propio, Codespace propio, `docker compose up -d`,
      importar `Clase11 - Agente Logistica UNAL.json` (las 2 ramas), `Publish`,
      y desactivar el workflow de la Clase 10 (mismo path de chat: si quedan
      los dos activos, el webhook dispara doble).
      en ambos. `pip install -r "Clase 11/starter/requirements.txt"`.
- [x] **T1 Contrato vivo.** Verificar `docker compose ps` (n8n Up), workflow A en
      `Publish`, `POST n8n:5678/webhook/agente-logistica-unal` con
      `Peticion.py` responde `output`. Evidencia: comando + `Status: 200`.
- [x] **T2 Chat + memoria.** En `starter/app.py`: sidebar (`N8N_CHAT_URL`, `session_id`),
      historial en `st.session_state`, parseo `[{output}]/{output}`, timeout 120 s,
      estados vacío/error. Evidencia: `check.py` suma cliente+chat UI + 2 turnos mismo `sessionId`.
- [x] **T3 Panel grounding.** Botones `Osciloscopios / Raspberry Pi / Clima Manizales`
      que envían el `chatInput` correspondiente y muestran respuesta + JSON crudo
      colapsable. Evidencia: 3 respuestas reales.
- [x] **T4 Escritura con confirmación.** Formulario `ID/Componente/Cantidad/Ubicacion/Estado`
      + checkbox `Confirmo` + preview del `chatInput` generado
      (`Registra: ID=... Componente=...`). Sin check no hay POST. Documentar alta del
      tool `Inventario_Write` en n8n. Evidencia: ejecución que devuelve confirmación.
- [x] **T5 Subir PDF.** `file_uploader` PDF ≤10 MB, extracción con `pypdf`, preview
      1000 chars, `POST {N8N_INGEST_URL}` con `{"sessionId","filename","text"}`,
      render de `summary`. Probar con `poema_test.pdf` y `reporte_planta.pdf`.
- [x] **T6 Generar reporte.** Botón que arma PDF con `fpdf2` (sesión, fecha, intercambios,
      último resumen) y `download_button`. Evidencia: PDF descargado con ≥1 intercambio.
- [x] **T7 Rama de ingesta.** Probar la rama B del mismo workflow (ya importado
      en T0) con `curl` JSON `{"sessionId","filename","text"}` → `{"ok":true,"summary":...}`.
- [x] **T8 QA + demo.** `check.py` 9/9, `grep` de secretos vacío, T2–T6 contra
      n8n real, demo en vivo (chat con memoria, escritura con/sin check, ingesta,
      reporte). Evidencia: checklist SPEC §4 en verde.

Reparto sugerido: orquestador → `explore` (T1), `frontend` (T2–T6), `qa` (T7–T8).
Cada tarea cierra con comando + output pegado en el resumen.
