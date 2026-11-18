# SPEC — Clase 11: Interfaz del agente logístico UNAL

## 1. Objetivo
Construir con SDD una interfaz Streamlit que opere el agente de la Clase 10
(`Webhook → AI Agent → OpenRouter + Memory + Google Sheets + Clima`) y demostrar
el ciclo completo: consulta con grounding, escritura controlada y reportes PDF.

## 2. Alcance (mínimo aprobatorio)
1. **Chat + memoria:** enviar `chatInput` con `sessionId` estable, mostrar `output`,
   mantener historial en `st.session_state`. Cambiar `sessionId` = conversación nueva.
2. **Evidencia de grounding:** botones/atajos que disparan `¿Hay osciloscopios?`,
   `¿Hay Raspberry Pi?`, `¿Clima en Manizales?` y muestran respuesta + JSON crudo.
3. **Lectura y escritura de inventario:** consultar y, con confirmación explícita en UI
   (checkbox "Confirmo escritura" + mostrar JSON a enviar), registrar/actualizar
   (`ID, Componente, Cantidad, Ubicacion, Estado`). Prohibido borrar sin `ID` exacto.
4. **Subir PDF:** `st.file_uploader` PDF → extraer texto con `pypdf` en Streamlit →
   `POST {N8N_INGEST_URL}` con `{"sessionId","filename","text"}` → mostrar resumen
   devuelto por el workflow B. Límite 10 MB, solo `.pdf`.
5. **Generar PDF:** botón "Generar reporte" que arma un PDF con historial + snapshot
   de respuestas usando `fpdf2` y lo ofrece en `st.download_button`.

Fuera de alcance: autenticación de usuarios, despliegue permanente de n8n,
túnel Ngrok (era de la versión anterior con Colab; en Codespaces se usa
`localhost` + port-forward).

## 3. Contratos API

### 3.1 Rama A — chat (evolución del agente de la Clase 10, mismo `path`)
- `POST {N8N_CHAT_URL}` `Content-Type: application/json`
- Request: `{"sessionId": "demo-01", "chatInput": "¿Hay osciloscopios?"}`
- Response 200: `[{"output": "..."}]` (aceptar también `{"output": "..."}`)
- Errores: `404` = workflow no publicado o path mal (`/webhook/` vs `/webhook-test/`);
  `401` con body vacío = se usó la URL `https://...app.github.dev` en código
  interno. El código usa siempre `http://n8n:5678` (no `localhost`: no llega
  al contenedor n8n); la URL `https` es solo para el navegador.

### 3.2 Rama B — ingesta de reporte (mismo workflow, `Clase11 - Agente Logistica UNAL.json`)
- `POST {N8N_INGEST_URL}` `Content-Type: application/json`
- Request: `{"sessionId": "demo-01", "filename": "reporte.pdf", "text": "<texto 1..20000 chars>"}`
- Response 200: `{"ok": true, "filename": "...", "summary": "...", "chars": 1234}`
- El workflow B NO recibe binarios en esta versión (decisión: parseo en Streamlit).
  Extensión futura: aceptar `multipart/form-data` con `Binary Data` en el Webhook.

### 3.3 Herramienta de escritura (mismo agente, Workflow A)
- Nuevo `Google Sheets Tool` `Inventario_Write` con `Operation: Append` (o `Update`),
  `Document: Inventario Laboratorio UNAL`, `Sheet: Hoja 1`.
- `toolDescription` restrictiva (ver `PLAN.md`). El Agent decide Read vs Write por intención.

## 4. Criterios de aceptación
- [ ] `streamlit run app/app.py` levanta sin errores y cada sección tiene estado
      vacío/cargando/error en español.
- [ ] Chat responde contra n8n local y conserva contexto al cambiar de pregunta
      con mismo `sessionId`.
- [ ] Escritura exige confirmación y muestra el payload antes de enviar; sin
      confirmación no hay POST.
- [ ] Subir `poema_test.pdf` y `reporte_planta.pdf` devuelve `summary` del workflow B.
- [ ] "Generar reporte" descarga un PDF que incluye al menos 1 intercambio de chat.
- [ ] `python -m py_compile app/app.py` pasa y ninguna key queda en el repo
      (`grep -ri "sk-\|client_secret\|authtoken" Clase\ 11/app` vacío).
