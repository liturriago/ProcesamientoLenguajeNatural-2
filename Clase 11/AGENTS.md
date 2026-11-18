# Clase 11 — Interfaz agéntica para el agente logístico (Clase 10)

Spec-Driven Development con orquestador + subagentes + skills.
Frontend: **Streamlit en Codespace**.

## Contrato con la Clase 10 (no romper)

- Chat: `POST {N8N_CHAT_URL}` default `http://n8n:5678/webhook/agente-logistica-unal`
- Payload: `{"sessionId": "<id estable por usuario>", "chatInput": "<pregunta>"}`
- Respuesta: `[{"output": "..."}]` o `{"output": "..."}`
- Memoria: `Window Buffer Memory` por `sessionId`. Mismo `sessionId` = misma conversación.
- Workflow en n8n en `Publish/Active`. Probar antes con:
  `python "Clase 10/Peticion.py" --url http://n8n:5678/webhook/agente-logistica-unal`

## Cómo correr (estudiante: starter; profesor: referencia)

```bash
cd .devcontainer && docker compose up -d          # n8n en :5678
pip install -r "Clase 11/starter/requirements.txt"
python "Clase 11/starter/check.py"                # juez: 3/9 -> 9/9
streamlit run "Clase 11/starter/app.py"           # UI en :8501
```

> `Clase 11/solucion-referencia/app/` es la solucion del profesor: mirarla
> invalida el ejercicio del estudiante. El estudiante solo toca `starter/`.

Variables (ver `Clase 11/app/.env.example`, nunca commitear valores reales):

- `N8N_CHAT_URL` (default localhost chat)
- `N8N_INGEST_URL` (default `http://n8n:5678/webhook/ingesta-reporte-pdf`)

## Reglas para agentes

1. `SPEC.md` manda. Si el código contradice al SPEC, se cambia el código.
2. Nada de secretos en repo: keys de OpenRouter/Google/Ngrok solo en Credentials de n8n o env local.
3. Un cambio = una tarea de `TASKS.md`. Marcar `[x]` solo con evidencia (comando + output).
4. Streamlit es thin-client: parseo de PDF y generación de PDF se hacen en `app/`, n8n solo razona y persiste.
5. Escritura en Sheets siempre con confirmación explícita en UI + `toolDescription` restrictivo en n8n. Nunca borrar sin `ID` exacto.
6. Verificación mínima antes de dar por hecha una tarea:
   `python -m py_compile "Clase 11/app/app.py"` + una petición real al webhook con `curl` o `Peticion.py`.
7. Skills en `Clase 11/skills/*/SKILL.md` son el contexto reutilizable: citarlos, no duplicarlos.
