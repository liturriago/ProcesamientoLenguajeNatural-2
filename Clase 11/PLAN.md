# PLAN — Clase 11

## 1. Arquitectura elegida

```
[Streamlit :8501] --requests--> [n8n :5678]
  app/app.py  ── POST n8n:5678/webhook/agente-logistica-unal (JSON chat)
              ── POST n8n:5678/webhook/ingesta-reporte-pdf (JSON texto PDF)
```

Streamlit corre en el mismo Codespace que n8n, por eso usa `http://n8n:5678`
(DNS interno de Compose, estable entre reinicios): evita CORS + auth del proxy
`*.app.github.dev` (causa del `401` y del `Connection lost 1008` vistos en la
Clase 10). OJO: `localhost:5678` NO sirve desde la terminal del dev container
(con `docker-outside-of-docker` cada contenedor tiene su propio `localhost`;
el puerto publicado vive en el host). Regla: navegador → URL `https` de PORTS;
código dentro del Codespace → `http://n8n:5678`.

## 2. Decisiones

1. **Interfaz en el mismo Codespace.** Streamlit corre junto a n8n y llama por
   `http://n8n:5678` (DNS interno, no `localhost`: con docker-outside-of-docker
   cada contenedor tiene su propio loopback), evitando el proxy
   `*.app.github.dev` (causa del `401` y del `Connection lost 1008` vistos en la
   Clase 10) y las URLs efímeras por Codespace.
2. **Híbrido n8n: A chat R/W + B ingesta.** El chat JSON ya funciona; mezclarle
   binarios lo rompe. B recibe texto ya extraído (límite 20k chars) y responde resumen.
   La escritura en Sheets es un segundo `ai_tool` en el mismo agente A, no otro workflow,
   para conservar una sola memoria por `sessionId`.
3. **Parseo y PDF en Streamlit, no en n8n.** `pypdf` extrae, `fpdf2` genera. n8n solo
   razona/persiste. Menos nodos binarios que explicar y menos puntos de fallo.
4. **Confirmación en dos capas para escritura:** checkbox en UI + `toolDescription`
   que exige confirmación y `ID` exacto. Sin esto el ReAct puede inventar IDs.

## 3. Componentes

- `app/app.py`: 4 secciones (Chat / Inventario y clima / Subir PDF / Reporte).
  Estado en `st.session_state` (`messages`, `session_id`). Timeout 120 s a n8n.
- `app/requirements.txt`: `streamlit, requests, pypdf, fpdf2`.
- El workflow único `Clase11 - Agente Logistica UNAL.json` trae las dos ramas:
  `Webhook (POST ingesta-reporte-pdf, respond lastNode) → Code (resume:
  filename + chars + preview 500)`. Respuesta del último nodo = HTTP response.
  Importar, `Publish` y **desactivar el workflow de la Clase 10** (mismo `path`
  de chat: dos activos = doble disparo).
- Escritura en A (manual en n8n, 5 min): duplicar el `Google Sheets Tool`,
  `Operation: Append`, renombrar `Inventario_Write`, pegar el `toolDescription`
  de abajo, `Disable` nada (conviven Read + Write).

`toolDescription` para `Inventario_Write`:
```
Usa SOLO cuando el usuario pide registrar, actualizar o mover inventario.
Exige ID, Componente, Cantidad, Ubicacion y Estado; pide confirmacion explicita
antes de escribir. Nunca borres ni actualices sin ID exacto. Responde con lo escrito.
```

## 4. Riesgos y mitigación

- n8n dormido / workflow no publicado → `404`: la UI muestra "Publica el workflow
  y verifica `docker compose ps`", con comando copiable.
- Puerto `5678` en `Private` + URL `https` desde el navegador → `401`: la UI usa
  `localhost` por defecto; la guía explica el switch a `Public`.
- LLM inventa existencias → system prompt de la Clase 10 + confirmación obligatoria.
- PDF > 10 MB o escaneado sin texto → error legible, se sugiere PDF con texto.

## 5. Orden de construcción (ver TASKS.md)
Contrato → chat → paneles grounding → escritura con confirmación → subida PDF →
reporte PDF → workflow B → QA contra n8n real → demo en vivo.
