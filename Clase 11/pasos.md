# Pasos — Clase 11 (rol estudiante)

Guía operativa paso a paso (completa: pasos 1 a 7). Cada paso termina con un
checkpoint: no avances al siguiente sin tenerlo en verde.

Flujo único: TODO ocurre dentro del Codespace, incluido OpenCode.
Abre dos pestañas de terminal en el Codespace: una para el agente (`opencode`)
y otra para docker/pruebas. Nada se instala en tu computador.

DÓNDE se hace cada cosa (etiqueta al inicio de cada sección):
- `[terminal-Codespace]` bash dentro del Codespace (opencode, git, docker, pruebas, `streamlit run`).
- `[n8n]` navegador, URL https de PORTS puerto 5678 (importar, Publish, credenciales, tools, Executions).
- `[Streamlit]` navegador, URL de PORTS puerto 8501 (probar la UI: chat, botones, upload, reporte).
- `[navegador: github.com]` solo gestión del Codespace (ver estado, Start, Delete, `gh codespace list` si tienes `gh`).

## Paso 1 — T0: entorno vivo (para hacer ANTES de codificar)

> Meta del paso: n8n `Up`, 1 workflow en `Publish`, contrato verificado con
> `Status: 200` y `check.py` en **3/9 en verde**. Sin esto, nada de T2.

## 1. Fork y Codespace [navegador: github.com]

1. En GitHub: `Fork` del repo (si no lo tienes) → en TU fork
   `Code > Codespaces > Create codespace on main`.
2. Todo (agente, código, git, n8n, Streamlit) vive dentro del Codespace.
   En tu computador no instalas nada: solo el navegador.

## 2. Actualiza y levanta SOLO el n8n [terminal-Codespace]

```bash
git pull
cd /workspaces/ProcesamientoLenguajeNatural/.devcontainer
docker pull n8nio/n8n:latest
docker compose up -d n8n
docker compose ps
docker compose logs --tail=20 n8n
```

Reglas que aprendimos a golpes:
- **NUNCA `docker compose up -d` completo**: el compose incluye el servicio
  `dev`, que es el contenedor donde estás parado. Recrearlo mata tu sesión
  y ves "the codespace is not available".
- **`pull` separado primero**: la imagen pesa cientos de MB; así ves el
  progreso en vez de una terminal congelada.
- **No mezcles descargas**: espera a que termine el "Setting up" del
  `postCreateCommand` antes del `docker pull` (2 cores no dan para todo a la vez).
- **Una cosa a la vez en 2 cores**: mientras el agente trabaja no levantes
  Streamlit; cuando pruebes la UI, el agente descansa. Turnos, no todo junto.

✅ Esperado: `pln-clase10-n8n-n8n-1 Up ... 0.0.0.0:5678->5678/tcp` y en los
logs `Editor is ready` / `n8n ready on ::, port 5678`.

### Si el Codespace muere ("not available") [navegador: github.com]
1. En otra pestaña abre `github.com/codespaces` y mira el estado:
   - `Running` → espera 3–5 min (estaba descargando) y reabre.
   - `Failed` → `Restart`; si no revive, `Delete` + `Create codespace on main`.
2. No pierdes nada commiteado: todo está en git. Solo reimportarías el workflow (punto 3)
   y recrearías credenciales OpenRouter/Google.

## 3. Importa el workflow único (2 ramas) y publícalo [n8n]

1. Abre n8n por la URL `https` de la pestaña `PORTS` (puerto 5678),
   **nunca** por `http://localhost:5678` en el navegador.
2. `Workflows → … → Import from file`:
   - `Clase 11/Clase11 - Agente Logistica UNAL.json` (rama chat + rama ingesta)
3. Pulsa **`Publish`** arriba a la derecha (eso es el `Active`) y **desactiva
   el workflow de la Clase 10** si lo tienes: comparten el `path`
   `agente-logistica-unal` y dos activos = doble disparo.
4. Copia sus Production URLs de los nodos Webhook:
   - `.../webhook/agente-logistica-unal`
   - `.../webhook/ingesta-reporte-pdf`

## 4. Verifica el contrato (Clase 10 manda) [terminal-Codespace]

```bash
cd /workspaces/ProcesamientoLenguajeNatural
python "Clase 11/Peticion.py" --url http://n8n:5678/webhook/agente-logistica-unal --mensaje "¿Hay osciloscopios?" --session-id paso01
```

- ✅ `Status: 200` + respuesta del agente → sigue al punto 5.
- ❌ `404` → el workflow no está publicado o usas `/webhook-test/`. Publica y usa `/webhook/`.
- ❌ `401` con body vacío → usaste la URL `https://...app.github.dev` en código
  interno. El código usa `http://n8n:5678/...` siempre (`localhost` no llega
  al contenedor n8n); la URL `https` es solo para el navegador.

## 5. Starter + juez [terminal-Codespace]

```bash
pip install -r "Clase 11/starter/requirements.txt"
python "Clase 11/starter/check.py"
```

✅ Esperado:
```
[PASS] py_compile app.py
[PASS] sin secretos en app.py
[FAIL] cliente chat ...
[FAIL] chat UI ...
[FAIL] grounding ...
[FAIL] escritura ...
[FAIL] PDF ...
[PASS] requirements ...
[SKIP/PASS] contrato vivo
3/9 en verde (4/9 si n8n responde).
```

## Checkpoint del paso 1 (listo si tienes esto)
1. `docker compose ps` → n8n `Up`.
2. `Status: 200` del punto 4.
3. `check.py` en 3/9 (4/9 si n8n respondió al contrato vivo).

## Paso 2 — T2 con OpenCode: el orquestador trabaja, tú diriges

> Meta: `check.py` enciende `cliente chat` + `chat UI` (5/9) SIN que tú escribas
> el código: lo implementan tus subagentes y tú verificas. Sentido del paso:
> practicar SDD — el SPEC manda, el orquestador delega, los skills dan contexto,
> TASKS + `check.py` son el juez. Trabajan SOLO en `Clase 11/starter/app.py`.
> La referencia (`solucion-referencia/`) no se mira ni se menciona.

## 6. Abre OpenCode en el Codespace y lánzale el T2 [terminal-Codespace]

Abre una SEGUNDA pestaña de terminal en el Codespace (la primera queda libre
para docker/pruebas) y verifica si `opencode` existe:
```bash
opencode --version
```
Si no lo tienes, instálalo (una sola vez por Codespace, comando oficial OpenCode 2):
```bash
curl -fsSL opencode.ai/v2/install | bash
source ~/.bashrc   # o abre terminal nueva: el instalador agrega ~/.opencode/bin al PATH
opencode --version
```
Luego entra a la raíz del repo y corre:
```bash
cd /workspaces/ProcesamientoLenguajeNatural
opencode
```
Al abrirlo la primera vez, con `/connect` vinculas tu proveedor de modelo
(API key). Sin eso el agente no responde: es el único secreto que cada uno pone
en SU Codespace, nunca en el repo.

Pega esto como primer mensaje (es tu contrato con el orquestador):
```text
Rol: orquestador de la Clase 11. Ejecuta SOLO la tarea T2 de TASKS.md.
Lee antes: Clase 11/SPEC.md (historias chat+memoria y criterios), Clase 11/PLAN.md
(decision Streamlit), Clase 11/TASKS.md (T2), Clase 11/AGENTS.md (las 7 reglas)
y los skills Clase 11/skills/n8n-webhook-client/SKILL.md +
Clase 11/skills/streamlit-chat-ui/SKILL.md.
Delega: explore verifica el contrato vivo con Peticion.py (Status: 200);
frontend implementa UNICAMENTE T2 en Clase 11/starter/app.py
(parse_output, post_chat con timeout 120 y errores 404/401 en espanol,
send_and_render, pestana Chat con historial + chat_input, y warning en el
sidebar si la URL trae localhost o webhook-test).
Prohibido: tocar solucion-referencia/, commitear secretos, salirte de starter/,
implementar T3-T6. Hecho = check.py con cliente chat + chat UI en PASS.
Evidencia: comando + output pegados en tu resumen.
```

Reglas de lanzamiento que aprendimos a golpes:
- **Un T por lanzamiento**: si le pides T2–T6 de una, mezcla todo y el juez no te dice qué falló.
- **Pega el prompt completo**: sin los archivos de contexto el agente inventa el contrato (otro puerto, otro payload).
- **Trabaja en foreground**: mira lo que hace en vivo, no lo dejes solo hasta el T4.

✅ Esperado: el orquestador responde con su plan (explore → frontend) y empieza a trabajar. Si en cambio te pregunta qué hacer, no pegaste el contexto: repite el prompt.

## 7. Supervisa a los subagentes (tú eres el QA, no el teclista) [terminal-Codespace]

- `explore` debe mostrarte `Status: 200` de `Peticion.py` (corre en el mismo
  Codespace, así que usa `http://n8n:5678`). Si no lo logra, el problema es
  n8n (vuelve al punto 4 del paso 1), no el código: detén al orquestador y
  arregla n8n tú.
- `frontend` solo puede tocar `starter/app.py`. Vigila con (en cualquier pestaña):
```bash
git status --short; git diff --stat
```
- ❌ Si ves cambios fuera de `starter/` (referencia, workflows, Pagina): detén y redirige con la regla 1 de `AGENTS.md`: *"SPEC manda: solo T2 en starter/app.py, revierte el resto"*.
- ❌ Si propone credenciales quemadas o URLs distintas a las del SPEC: detén y redirige con la regla 2: *"nada de secretos en el repo, URLs solo de variables + sidebar"*.

## 8. Verifica TÚ (el juez no se delega) [terminal-Codespace + Streamlit]

El código ya está en tu clon (lo hizo el agente aquí mismo). Verifica y commitea:
```bash
python "Clase 11/starter/check.py"
git add "Clase 11/starter/app.py"; git commit -m "T2: chat + memoria via orquestador"; git push
streamlit run "Clase 11/starter/app.py"   # UI en :8501 de PORTS
```

✅ Esperado en el juez: `cliente chat` + `chat UI` en `PASS` → 5/9 en verde.

En la UI, con `session_id demo-01`:
1. Pregunta "¿Hay osciloscopios?" → responde el agente.
2. Pregunta "¿y dónde están?" (mismo session) → usa contexto (memoria OK).
3. Cambia a `demo-02`, repite → empieza de cero (memoria aislada OK).

- ❌ Si el spinner nunca termina: n8n caído o workflow sin `Publish`. Vuelve al punto 4 del paso 1.
- ❌ Si el juez sigue en FAIL tras el agente: pégale al orquestador el output tal cual de `check.py` y pídele que corrija solo eso.

El commit ya quedó hecho arriba, antes de la prueba viva: se commitea y se demuestra después.

## Checkpoint del paso 2 (avísame esto para seguir al paso 3)
1. `check.py` en 5/9 (pega el conteo).
2. `git log --oneline -1` de tu commit T2.
3. Qué respondió a "¿y dónde están?" con `demo-01`.

## Paso 3 — T3: panel grounding (botones + JSON crudo)

> Meta: `check.py` enciende `grounding` (6/9). Reutiliza el T2, no lo reescribas.

## 9. Lánzale el T3 (copia y pega este prompt) [terminal-Codespace]

En la pestaña del agente (`opencode`), pega:
```text
Rol: orquestador de la Clase 11. Ejecuta SOLO la tarea T3 de TASKS.md.
Lee antes: SPEC (historia grounding), TASKS T3, AGENTS reglas,
skills streamlit-chat-ui + n8n-webhook-client.
Contexto: T2 hecho y commiteado (send_and_render existe y funciona, no lo toques).
Delega: frontend agrega a la pestana Inventario y clima 3 botones
("¿Hay osciloscopios?", "¿Hay Raspberry Pi?", "Clima Manizales") que reutilicen
send_and_render y muestren respuesta + expander "JSON crudo"
(usa post_chat directo si necesitas el JSON sin renderizar).
Prohibido: tocar T4-T6, solucion-referencia/, secretos, archivos fuera de starter/app.py.
Hecho = check.py con grounding en PASS. Evidencia: comando + output.
```

✅ Esperado: plan corto (solo frontend) y cambios solo en `starter/app.py`.

## 10. Supervisa [terminal-Codespace]

```bash
git status --short; git diff --stat   # siempre git: gh no ve tu working tree
```

- ❌ Si reescribe `send_and_render` o toca el sidebar/chat: detén y redirige con AGENTS regla 1: *"T3 solo agrega botones que reutilizan T2, revierte el resto"*.

## 11. Verifica tú y commitea [terminal-Codespace + Streamlit]

```bash
python "Clase 11/starter/check.py"   # grounding en PASS -> 6/9
git add "Clase 11/starter/app.py"; git commit -m "T3: panel grounding"; git push
```

En la UI (`:8501`) pulsa los 3 botones y abre el JSON crudo del clima.
- ❌ Botón sin respuesta: mira si es 404/401 (paso 1, punto 4).

## Checkpoint del paso 3
1. `check.py` en 6/9 (pega el conteo).
2. Qué trae el JSON crudo del clima (una línea basta).

## Paso 4 — T4: escritura con confirmación (mitad tú en n8n, mitad el agente)

> Meta: `check.py` enciende `escritura` (7/9). Ojo: el tool se crea A MANO en
> n8n (los agentes no clican UI); el formulario lo hace el orquestador.

## 12. Primero TÚ en n8n (5 min), luego el prompt [n8n + terminal-Codespace]

En n8n, sobre `Clase11 - Agente Logistica UNAL`: duplica el `Google Sheets Tool`
→ `Operation: Append` → renómbralo `Inventario_Write` → `Document: Inventario
Laboratorio UNAL` → `Sheet: Hoja 1` → pega el `toolDescription` restrictivo del
`PLAN.md`. Pulsa **`Publish`** de nuevo y verifica en una ejecución de prueba
que el tool existe. Recién entonces pega esto en el agente:
```text
Rol: orquestador de la Clase 11. Ejecuta SOLO la tarea T4 de TASKS.md.
Lee antes: SPEC (historia escritura), TASKS T4, AGENTS reglas, skill streamlit-chat-ui.
Contexto: el tool Inventario_Write YA existe en n8n (lo cree yo). T2/T3 hechos.
Delega: frontend agrega formulario ID/Componente/Cantidad/Ubicacion/Estado +
checkbox "Confirmo" + preview del chatInput generado. SIN check marcado NO hay
POST bajo ninguna circunstancia (warning en UI). Con check: send_and_render.
Prohibido: tocar T5-T6, solucion-referencia/, secretos, probar escrituras reales
(las pruebas contra Sheets las hago YO). Hecho = check escritura en PASS.
```

## 13. Supervisa [terminal-Codespace]

- Solo `starter/app.py`. Si el agente propone "probar" escribiendo de verdad en el Sheet: detén — punto 14 lo haces tú.

## 14. Verifica tú (la parte delicada) y commitea [terminal-Codespace + n8n + Streamlit]

```bash
python "Clase 11/starter/check.py"   # escritura en PASS -> 7/9
git add "Clase 11/starter/app.py"; git commit -m "T4: escritura con confirmacion"; git push
```

1. Rellena el form con un ID REAL, **SIN** marcar el check, envía → warning, y verifica en n8n `Executions` que **NO** hay ejecución nueva.
2. Marca el check, envía → respuesta del agente + ejecución nueva con `Inventario_Write` + fila visible en el Sheet.

## Checkpoint del paso 4
1. `check.py` en 7/9 (pega el conteo).
2. ID que registraste + confirmación de que sin check no hubo ejecución.

## Paso 5 — T5: subir PDF e ingesta

> Meta: ingesta funcionando con los 2 PDFs. El check seguirá en 7/9 (normal:
> el check de PDF pide también el `FPDF` del T6). No te asustes.

## 15. Lánzale el T5 (copia y pega este prompt) [terminal-Codespace]

```text
Rol: orquestador de la Clase 11. Ejecuta SOLO la tarea T5 de TASKS.md.
Lee antes: SPEC (historia subir PDF + contrato 3.2), TASKS T5, AGENTS reglas,
skills pdf-report + n8n-webhook-client.
Contexto: T2-T4 hechos. La rama de ingesta YA esta publicada en n8n.
Delega: frontend agrega file_uploader PDF (max 10 MB, rechaza con error legible),
extraccion con pypdf (max 20000 chars, preview 1000 en expander, aviso si es
escaneado sin texto), POST {"sessionId","filename","text"} a N8N_INGEST_URL y
render del summary + expander JSON crudo.
Prohibido: tocar T6, binarios hacia n8n (parseo en Streamlit, SPEC 3.2),
solucion-referencia/, secretos. Hecho = ingesta OK con poema_test.pdf.
```

## 16. Supervisa [terminal-Codespace]

- Solo `starter/app.py`. Si mete `multipart`/binarios o cambia el contrato JSON: detén y redirige con SPEC 3.2: *"parseo en Streamlit, a n8n solo texto"*.

## 17. Verifica tú y commitea [terminal-Codespace + Streamlit]

```bash
python "Clase 11/starter/check.py"
git add "Clase 11/starter/app.py"; git commit -m "T5: subida e ingesta PDF"; git push
```

Sube `poema_test.pdf` y `reporte_planta.pdf`: en ambos debe salir `summary` + JSON crudo. `check.py` seguirá en 7/9 (el `FPDF` llega en el paso 6).

## Checkpoint del paso 5
1. `summary` devuelto para `reporte_planta.pdf` (pégalo).
2. Conteo del check (debe seguir 7/9).

## Paso 6 — T6: generar reporte PDF

> Meta: `check.py` enciende lo que falta del check de PDF (8/9) y el reporte se descarga y abre.

## 18. Lánzale el T6 (copia y pega este prompt) [terminal-Codespace]

```text
Rol: orquestador de la Clase 11. Ejecuta SOLO la tarea T6 de TASKS.md.
Lee antes: SPEC (historia generar PDF), TASKS T6, AGENTS reglas, skill pdf-report.
Contexto: T2-T5 hechos (messages y last_summary viven en st.session_state).
Delega: frontend agrega boton que arma el reporte con fpdf2 (portada: sesion,
fecha; una seccion por intercambio user/agente; cierre con ultimo summary) y lo
entrega con download_button "Descargar reporte.pdf".
Prohibido: tocar T1-T5 ya commiteados salvo ajustes minimos, solucion-referencia/,
secretos. Hecho = check.py 8/9.
```

## 19. Supervisa [terminal-Codespace]

- Solo `starter/app.py`. Si rompe botones o formularios previos: detén y redirige con AGENTS regla 1.

## 20. Verifica tú y commitea [terminal-Codespace + Streamlit]

```bash
python "Clase 11/starter/check.py"   # 8/9
git add "Clase 11/starter/app.py"; git commit -m "T6: reporte PDF"; git push
```

Pulsa generar, descarga `reporte.pdf`, ábrelo: debe traer sesión, fecha y al menos 1 intercambio.

## Checkpoint del paso 6
1. `check.py` en 8/9 (pega el conteo).
2. El PDF descargado abre y tiene tus intercambios (sí/no + cuántas páginas).

## Paso 7 — T7+T8: ingesta por curl + QA final + demo

> Meta: `check.py` 9/9, repo sin secretos y demo en vivo completa. Cierre de la clase.

## 21. Lánzale el T7+T8 (último prompt, copia y pega) [terminal-Codespace]

```text
Rol: orquestador de la Clase 11. Ejecuta T7 y T8 de TASKS.md, en orden.
Lee antes: TASKS T7+T8, AGENTS reglas, skill n8n-webhook-client.
T7: prueba la rama de ingesta con curl POST JSON {"sessionId","filename","text"}
a N8N_INGEST_URL y confirma {"ok":true,"summary":...}. Si da 404/401 diagnostica
(publicado? /webhook/ vs /webhook-test/? URL http://n8n:5678?).
T8: QA final — check.py 9/9, grep de secretos vacio, repaso del checklist SPEC S4.
Prohibido: cambios funcionales salvo fixes que pida el QA, solucion-referencia/.
Hecho = 9/9 + grep vacio. Evidencia: comando + output pegados en tu resumen.
```

## 22. Supervisa [terminal-Codespace]

- Solo fixes menores. Si propone refactors grandes a estas alturas: detén, ya no es momento.

## 23. Verifica tú, demo y cierre [terminal-Codespace + n8n + Streamlit]

```bash
curl -X POST http://n8n:5678/webhook/ingesta-reporte-pdf \
  -H "Content-Type: application/json" \
  -d '{"sessionId":"demo-01","filename":"prueba.json","text":"Contenido de prueba para verificar la rama de ingesta del workflow."}'
python "Clase 11/starter/check.py"   # 9/9
grep -ri "sk-\|client_secret\|authtoken" "Clase 11/starter"  # vacio
git add -A; git commit -m "Clase 11 completa: check 9/9 + demo"; git push
```

Demo en vivo (la nota): chat con memoria (`demo-01` recuerda, `demo-02` no),
grounding, escritura SIN check (sin ejecución nueva) y CON check (fila en Sheets),
ingesta de `reporte_planta.pdf`, reporte descargado.

## Checkpoint final (clase construida)
1. `check.py` en 9/9 + `grep` vacío (pega ambos).
2. Demo hecha (sí/no + qué falló, si algo).
