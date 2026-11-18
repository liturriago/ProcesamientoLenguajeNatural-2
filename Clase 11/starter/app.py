"""Clase 11 - Starter del estudiante (NO la solucion).

Implementa aqui los TODOs T2-T6 siguiendo SPEC.md, PLAN.md y los skills en
../skills/. La referencia del profesor esta en ../solucion-referencia/app/
y NO se puede copiar: la nota esta en tu demo en vivo + check.py en verde.
"""
import json
import os
from datetime import datetime

import requests
import streamlit as st

DEFAULT_CHAT = "http://n8n:5678/webhook/agente-logistica-unal"
DEFAULT_INGEST = "http://n8n:5678/webhook/ingesta-reporte-pdf"

# PLAN.md decision 1 / SPEC.md S3.1: el codigo dentro del Codespace usa siempre el
# DNS interno de Compose (derivado de DEFAULT_CHAT, sin URL nueva hardcodeada).
WEBHOOK_HINT = DEFAULT_CHAT.split("/webhook/")[0] + "/webhook/..."

st.set_page_config(page_title="UNAL Logistica - Agente", layout="wide")
st.title("Agente de logistica UNAL — Interfaz Clase 11")

with st.sidebar:
    st.header("Conexion")
    chat_url = st.text_input("N8N_CHAT_URL", os.getenv("N8N_CHAT_URL", DEFAULT_CHAT))
    ingest_url = st.text_input("N8N_INGEST_URL", os.getenv("N8N_INGEST_URL", DEFAULT_INGEST))
    session_id = st.text_input("session_id (memoria)", "demo-01")
    st.caption("Mismo session_id = misma conversacion (Window Buffer Memory).")

    # T2: aviso visible en el sidebar si alguna URL no sirve desde el Codespace.
    if any("localhost" in u or "webhook-test" in u for u in (chat_url, ingest_url)):
        st.warning(
            "URL invalida dentro del Codespace: usa siempre "
            f"`{WEBHOOK_HINT}` (DNS interno de Compose). "
            "`localhost` no llega al contenedor n8n y la ruta `/webhook-test/` "
            "no esta publicada: el workflow debe estar en `Publish` y el path "
            "debe ser `/webhook/`. La URL `https` de PORTS es solo para el navegador."
        )

if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_summary" not in st.session_state:
    st.session_state.last_summary = ""


class ChatError(Exception):
    """Fallo al hablar con n8n; el mensaje ya viene redactado para la UI."""


# T2: parsear [{"output": ...}] o {"output": ...} a str. Nunca lanza excepcion.
def parse_output(data):
    try:
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and "output" in item:
                    return str(item["output"])
        elif isinstance(data, dict) and "output" in data:
            return str(data["output"])
        # Formato inesperado: mostrar el JSON crudo como texto, sin romper la app.
        try:
            return json.dumps(data, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(data)
    except Exception:  # noqa: BLE001 - el parseo jamas debe tumbar la UI
        return str(data)


# T2/T3: POST {"sessionId","chatInput"} con timeout 120; 404/401 con mensaje
# en espanol segun skills/n8n-webhook-client/SKILL.md. Devuelve el JSON crudo
# para que el panel grounding lo muestre sin repetir la peticion (un solo POST
# por turno: dos POST con el mismo sessionId contaminan la memoria).
def _request_chat(url, sid, msg):
    payload = {"sessionId": sid, "chatInput": msg}
    try:
        r = requests.post(url, json=payload, timeout=120)
    except requests.exceptions.Timeout:
        raise ChatError(
            "Timeout de 120 s esperando a n8n. Revisa `docker compose ps` "
            "(n8n debe estar Up en el puerto 5678) y que el workflow siga publicado."
        )
    except requests.exceptions.ConnectionError:
        raise ChatError(
            "No se pudo conectar con n8n. Dentro del Codespace la URL debe ser "
            f"{WEBHOOK_HINT} (no `localhost`: no llega al contenedor n8n). "
            "Revisa `docker compose ps` (n8n debe estar Up en el puerto 5678) "
            "y que el workflow siga publicado."
        )
    except requests.exceptions.RequestException as e:
        raise ChatError(
            f"Error de red al llamar a n8n ({e}). Revisa `docker compose ps` "
            f"y usa {WEBHOOK_HINT} dentro del Codespace."
        )

    if r.status_code == 404:
        raise ChatError(
            "404: el workflow no esta publicado o el path esta mal. Publica el "
            "workflow en n8n y usa `/webhook/` (no `/webhook-test/`). "
            "Revisa: docker compose ps"
        )
    if r.status_code == 401:
        raise ChatError(
            "401: se uso la URL `https://...app.github.dev` en codigo interno, "
            f"o el puerto 5678 esta en Private. Usa {WEBHOOK_HINT} dentro del "
            "Codespace; la URL `https` de PORTS es solo para el navegador."
        )
    if r.status_code >= 400:
        extracto = (r.text or "").strip()[:300] or "(body vacio)"
        raise ChatError(
            f"{r.status_code}: n8n respondio con error. Extracto del body: {extracto}"
        )

    try:
        data = r.json()
    except ValueError:
        raise ChatError(
            "200 pero la respuesta no es JSON. Extracto del body: "
            f"{(r.text or '').strip()[:300] or '(vacio)'}"
        )
    return data


# T2: contrato de chat sobre el helper; parse_output nunca lanza excepcion.
def post_chat(url, sid, msg):
    return parse_output(_request_chat(url, sid, msg))


# T5: limites del contrato de ingesta (SPEC.md S2.4 y S3.2).
MAX_PDF_BYTES = 10 * 1024 * 1024
MAX_INGEST_CHARS = 20000
PREVIEW_CHARS = 1000


class IngestError(Exception):
    """Fallo al subir el PDF al Workflow B; el mensaje ya viene para la UI."""


# T5: parseo en Streamlit (SPEC.md S3.2: el workflow B NO recibe binarios).
# Devuelve (texto, truncado); sube solo texto y nunca el archivo.
def extract_pdf_text(uploaded):
    from pypdf import PdfReader

    try:
        uploaded.seek(0)
        reader = PdfReader(uploaded)
        paginas = [page.extract_text() or "" for page in reader.pages]
    except Exception as e:  # noqa: BLE001 - PDF corrupto: avisar, no tumbar la UI
        raise IngestError(
            f"No se pudo leer el PDF ({e}). Verifica que no este corrupto ni "
            "protegido con contrasena."
        )
    texto = "\n".join(paginas).strip()
    truncado = len(texto) > MAX_INGEST_CHARS
    return texto[:MAX_INGEST_CHARS], truncado


# T5: POST {"sessionId","filename","text"} al Workflow B, timeout 120.
# Devuelve el JSON crudo (dict esperado) para renderizar summary + JSON crudo.
def post_ingest(url, sid, filename, text):
    payload = {"sessionId": sid, "filename": filename, "text": text}
    try:
        r = requests.post(url, json=payload, timeout=120)
    except requests.exceptions.Timeout:
        raise IngestError(
            "Timeout de 120 s esperando a n8n. Revisa `docker compose ps` "
            "(n8n debe estar Up en el puerto 5678) y que el workflow de ingesta "
            "siga publicado."
        )
    except requests.exceptions.ConnectionError:
        raise IngestError(
            "No se pudo conectar con n8n. Dentro del Codespace la URL debe ser "
            f"{WEBHOOK_HINT} (no `localhost`: no llega al contenedor n8n). "
            "Revisa `docker compose ps` (n8n debe estar Up en el puerto 5678)."
        )
    except requests.exceptions.RequestException as e:
        raise IngestError(
            f"Error de red al llamar a n8n ({e}). Revisa `docker compose ps` "
            f"y usa {WEBHOOK_HINT} dentro del Codespace."
        )

    if r.status_code == 404:
        raise IngestError(
            "404: el workflow no esta publicado o el path esta mal. Publica el "
            "workflow en n8n y usa `/webhook/` (no `/webhook-test/`). "
            "Revisa: docker compose ps"
        )
    if r.status_code == 401:
        raise IngestError(
            "401: se uso la URL `https://...app.github.dev` en codigo interno, "
            f"o el puerto 5678 esta en Private. Usa {WEBHOOK_HINT} dentro del "
            "Codespace; la URL `https` de PORTS es solo para el navegador."
        )
    if r.status_code >= 400:
        extracto = (r.text or "").strip()[:300] or "(body vacio)"
        raise IngestError(
            f"{r.status_code}: n8n respondio con error. Extracto del body: {extracto}"
        )

    try:
        return r.json()
    except ValueError:
        raise IngestError(
            "200 pero la respuesta no es JSON. Extracto del body: "
            f"{(r.text or '').strip()[:300] or '(vacio)'}"
        )


# T2: append user, chat_message, spinner, append assistant, render.
def send_and_render(prompt):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    try:
        with st.spinner("Consultando al agente en n8n..."):
            salida = post_chat(chat_url, session_id, prompt)
    except ChatError as e:
        # El turno queda sin respuesta: se retira para no dejar el historial a medias.
        st.session_state.messages.pop()
        st.error(str(e))
        return
    except Exception as e:  # noqa: BLE001 - la UI nunca debe caerse por un turno
        st.session_state.messages.pop()
        st.error(f"Error inesperado al consultar al agente: {e}")
        return

    st.session_state.messages.append({"role": "assistant", "content": salida})
    with st.chat_message("assistant"):
        st.markdown(salida)


# T6: el PDF se arma en la app, n8n solo razona y persiste (AGENTS.md regla 4;
# SPEC.md S2.5 y S4; skills/pdf-report seccion "Generar").
REPORT_TITLE = "Reporte de sesion - Agente de logistica UNAL"


def _report_text(valor):
    """Helvetica solo cubre latin-1: emojis/—/ñ se reemplazan, nunca lanzan."""
    return (
        str(valor if valor is not None else "")
        .encode("latin-1", "replace")
        .decode("latin-1")
    )


def build_report_pdf(session_id, messages, last_summary):
    """Devuelve el PDF del reporte como bytes (portada + historial + summary)."""
    from fpdf import FPDF

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Portada: titulo, sesion y fecha/hora local.
    pdf.set_font("Helvetica", "B", 18)
    pdf.multi_cell(0, 10, _report_text(REPORT_TITLE), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    pdf.set_font("Helvetica", "", 12)
    pdf.multi_cell(
        0,
        8,
        _report_text(f"Session ID: {session_id}"),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.multi_cell(
        0,
        8,
        _report_text(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}"),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.multi_cell(
        0,
        8,
        _report_text(f"Mensajes en el historial: {len(messages)}"),
        new_x="LMARGIN",
        new_y="NEXT",
    )

    if not messages:
        # La UI ya bloquea este caso; el helper tampoco debe fallar.
        pdf.ln(4)
        pdf.multi_cell(
            0,
            8,
            _report_text("Sin intercambios registrados en esta sesion."),
            new_x="LMARGIN",
            new_y="NEXT",
        )
    else:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 14)
        pdf.multi_cell(0, 9, "Conversacion", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        # Una seccion por mensaje: etiqueta en negrita + contenido con multi_cell
        # (fpdf2 salta de pagina solo cuando el texto no cabe).
        for numero, mensaje in enumerate(messages, start=1):
            if isinstance(mensaje, dict):
                rol = mensaje.get("role")
                contenido = mensaje.get("content")
            else:
                rol, contenido = None, mensaje
            etiqueta = "usuario:" if rol == "user" else "agente:"
            texto = _report_text(contenido).strip() or "(vacio)"

            pdf.set_font("Helvetica", "B", 11)
            pdf.multi_cell(
                0,
                8,
                _report_text(f"{numero}. {etiqueta}"),
                new_x="LMARGIN",
                new_y="NEXT",
            )
            pdf.set_font("Helvetica", "", 11)
            pdf.multi_cell(0, 8, texto, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(3)

    resumen = _report_text(last_summary).strip()
    if resumen:
        # Cierre: ultimo summary devuelto por el Workflow B (si existe).
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 14)
        pdf.multi_cell(
            0, 9, "Ultimo resumen de ingesta", new_x="LMARGIN", new_y="NEXT"
        )
        pdf.ln(2)
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 8, resumen, new_x="LMARGIN", new_y="NEXT")

    # fpdf2 2.9: output() devuelve bytearray; el download_button pide bytes.
    return bytes(pdf.output())


tab_chat, tab_ground, tab_pdf, tab_report = st.tabs(
    ["Chat", "Inventario y clima", "Subir PDF", "Reporte"]
)

with tab_chat:
    # T2: historial con st.chat_message + st.chat_input -> send_and_render.
    if not st.session_state.messages:
        st.caption("Sin mensajes todavia. Escribe abajo para consultar al agente.")
    for mensaje in st.session_state.messages:
        with st.chat_message(mensaje["role"]):
            st.markdown(mensaje["content"])

    prompt = st.chat_input("Escribe tu consulta (ej: ¿Hay osciloscopios?)")
    if prompt:
        send_and_render(prompt)

with tab_ground:
    # T3: botones de grounding (chatInput fijo) -> un solo POST -> respuesta +
    # JSON crudo colapsable. Ver skills/streamlit-chat-ui y n8n-webhook-client.
    st.subheader("Evidencia de grounding")
    st.markdown(
        "Atajos de consulta: **Osciloscopios**, **Raspberry Pi** y "
        "**clima en Manizales**. La respuesta incluye el JSON crudo del webhook."
    )
    st.caption(
        "Cada boton envia un chatInput fijo al agente con el mismo session_id. "
        "Un solo POST por clic: la respuesta y el JSON crudo vienen del mismo turno."
    )
    col_osciloscopios, col_raspberry, col_clima = st.columns(3)
    grounding_prompt = None
    with col_osciloscopios:
        if st.button(
            "¿Hay osciloscopios?", key="ground_osciloscopios", use_container_width=True
        ):
            grounding_prompt = "¿Hay osciloscopios?"
    with col_raspberry:
        if st.button(
            "¿Hay Raspberry Pi?", key="ground_raspberry_pi", use_container_width=True
        ):
            grounding_prompt = "¿Hay Raspberry Pi?"
    with col_clima:
        if st.button(
            "Clima Manizales", key="ground_clima_manizales", use_container_width=True
        ):
            grounding_prompt = "¿Clima en Manizales?"

    if grounding_prompt:
        with st.chat_message("user"):
            st.markdown(grounding_prompt)

        try:
            with st.spinner("Consultando al agente en n8n..."):
                data = _request_chat(chat_url, session_id, grounding_prompt)
            salida = parse_output(data)
        except ChatError as e:
            # Sin turnos a medias: no se toca el historial si la peticion falla.
            st.error(str(e))
        except Exception as e:  # noqa: BLE001 - la UI nunca debe caerse por un turno
            st.error(f"Error inesperado al consultar al agente: {e}")
        else:
            st.session_state.messages.append(
                {"role": "user", "content": grounding_prompt}
            )
            st.session_state.messages.append(
                {"role": "assistant", "content": salida}
            )
            with st.chat_message("assistant"):
                st.markdown(salida)
            with st.expander("JSON crudo"):
                st.code(
                    json.dumps(data, ensure_ascii=False, indent=2), language="json"
                )

    # T4: escritura con confirmacion (SPEC.md S2.3 y S4: preview del payload ANTES
    # de enviar y sin checkbox no hay POST). Widgets normales, no st.form: el
    # preview debe actualizarse en vivo con cada cambio.
    st.divider()
    st.subheader("Registrar / actualizar inventario")
    st.caption(
        "El agente exige el `ID` exacto para actualizar; sin `ID` exacto no borra "
        "ni sobrescribe nada."
    )

    col_id, col_cantidad = st.columns([2, 1])
    with col_id:
        inv_id = st.text_input("ID", key="inv_id", placeholder="ej: INV-001")
    with col_cantidad:
        inv_cantidad = st.number_input(
            "Cantidad", min_value=0, step=1, value=0, key="inv_cantidad"
        )

    col_componente, col_ubicacion = st.columns(2)
    with col_componente:
        inv_componente = st.text_input(
            "Componente", key="inv_componente", placeholder="ej: Osciloscopio"
        )
    with col_ubicacion:
        inv_ubicacion = st.text_input(
            "Ubicacion", key="inv_ubicacion", placeholder="ej: Laboratorio 301"
        )

    inv_estado = st.selectbox(
        "Estado",
        ["Disponible", "En uso", "En mantenimiento", "Dado de baja"],
        key="inv_estado",
    )

    # Preview en vivo del chatInput: mismo formato que espera el agente.
    inv_cantidad_int = int(inv_cantidad)
    preview = (
        f"Registra: ID={inv_id.strip()} Componente={inv_componente.strip()} "
        f"Cantidad={inv_cantidad_int} Ubicacion={inv_ubicacion.strip()} "
        f"Estado={inv_estado}"
    )
    st.markdown("**Vista previa del mensaje que se enviara al agente:**")
    st.code(preview, language="text")

    confirmo = st.checkbox("Confirmo escritura", key="confirmo_escritura")
    st.caption(
        "Sin marcar `Confirmo escritura` no se envia nada al agente y no se "
        "escribe en Google Sheets. El agente exige el `ID` exacto: un ID "
        "inexistente no actualiza ni borra filas."
    )

    if st.button("Enviar al agente", key="inv_enviar"):
        datos_invalidos = (
            not inv_id.strip()
            or not inv_componente.strip()
            or inv_cantidad_int <= 0
        )
        if datos_invalidos:
            # Validacion previa: nunca se llama al webhook con datos incompletos.
            st.error(
                "Datos incompletos: `ID` y `Componente` son obligatorios y "
                "`Cantidad` debe ser mayor que 0. No se envio nada al agente."
            )
        elif not confirmo:
            # Regla dura (SPEC.md S4): sin confirmacion explicita no hay POST.
            st.warning(
                "Marca 'Confirmo escritura' para enviar el registro. "
                "No se envio nada al agente."
            )
        else:
            send_and_render(preview)

with tab_pdf:
    # T5: subida + ingesta de PDF (SPEC.md S2.4, S3.2; skills/pdf-report y
    # n8n-webhook-client). El parseo ocurre aqui y a n8n solo viaja texto.
    st.subheader("Subir PDF")
    st.markdown(
        "Sube un PDF con texto: la app extrae el contenido con `pypdf` y envia "
        "**solo el texto** al Workflow B de n8n, que devuelve un `summary`."
    )
    st.caption(
        "Limite 10 MB. Maximo 20000 caracteres por envio (contrato de ingesta). "
        "No se envian binarios: el workflow B no recibe el archivo."
    )

    uploaded = st.file_uploader(
        "Sube un PDF (max 10 MB)", type=["pdf"], key="ingest_pdf"
    )

    if uploaded is None:
        st.caption("Sin archivo todavia. Sube un PDF para ver la vista previa.")
    elif uploaded.size > MAX_PDF_BYTES:
        st.error(
            f"El PDF supera 10 MB ({uploaded.size / (1024 * 1024):.1f} MB). "
            "Sube un archivo mas liviano: no se extrajo ni se envio nada."
        )
    else:
        st.caption(
            f"Archivo: `{uploaded.name}` ({uploaded.size / 1024:.1f} KB)."
        )
        texto = None
        truncado = False
        try:
            with st.spinner("Extrayendo texto del PDF..."):
                texto, truncado = extract_pdf_text(uploaded)
        except IngestError as e:
            st.error(str(e))
        except Exception as e:  # noqa: BLE001 - un PDF raro no debe tumbar la UI
            st.error(f"Error inesperado al extraer el texto del PDF: {e}")

        if texto is not None and not texto:
            # PDF escaneado (solo imagenes): no hay texto que enviar.
            st.warning(
                "El PDF no contiene texto extraible: parece escaneado (solo "
                "imagenes). Sube un PDF con texto o pasalo antes por OCR. "
                "No se envio nada a n8n."
            )
        elif texto:
            st.caption(
                f"{len(texto)} caracteres listos para enviar. "
                "Revisa la vista previa antes de confirmar."
            )
            if truncado:
                st.caption(
                    "El PDF tiene mas de 20000 caracteres: se enviaran solo los "
                    "primeros 20000 (limite del contrato de ingesta)."
                )

            with st.expander("Vista previa del texto (1000 caracteres)"):
                st.text(texto[:PREVIEW_CHARS])

            st.caption(
                "Un solo POST por clic. Nada se envia hasta que pulses el boton."
            )
            if st.button("Enviar texto a n8n", key="ingest_enviar"):
                try:
                    with st.spinner("Enviando texto a n8n..."):
                        data = post_ingest(
                            ingest_url, session_id, uploaded.name, texto
                        )
                except IngestError as e:
                    st.error(str(e))
                except Exception as e:  # noqa: BLE001 - el POST no debe tumbar la UI
                    st.error(f"Error inesperado al enviar la ingesta a n8n: {e}")
                else:
                    if isinstance(data, dict):
                        if data.get("ok") is False:
                            st.warning(
                                "El workflow respondio con `ok: false`: no se "
                                "confirmo la ingesta del PDF."
                            )
                        resumen = str(data.get("summary") or "").strip()
                        nombre = str(data.get("filename") or uploaded.name)
                        chars = data.get("chars", len(texto))
                        st.success(
                            f"Ingesta completada: `{nombre}` ({chars} caracteres)."
                        )
                        if resumen:
                            st.markdown("**Resumen del agente:**")
                            st.markdown(resumen)
                            st.session_state.last_summary = resumen
                        else:
                            st.caption(
                                "El workflow no devolvio `summary` en la respuesta."
                            )
                    else:
                        st.warning(
                            "La respuesta de n8n no tiene el formato esperado "
                            "`{ok, filename, summary, chars}`. Revisa el JSON crudo."
                        )
                    with st.expander("JSON crudo"):
                        st.code(
                            json.dumps(data, ensure_ascii=False, indent=2),
                            language="json",
                        )

with tab_report:
    # T6: reporte PDF con fpdf2 generado en la app (SPEC.md S2.5 y S4;
    # skills/pdf-report seccion "Generar"). El PDF se guarda en session_state
    # para que el download_button siga visible despues de un rerun.
    st.subheader("Generar reporte")
    total_mensajes = len(st.session_state.messages)
    st.caption(
        f"Sesion actual: `{session_id}` — {total_mensajes} mensajes en el "
        "historial (usuario + agente)."
    )
    st.markdown(
        "El PDF incluye portada (sesion y fecha/hora), una seccion por "
        "intercambio y el ultimo resumen de ingesta, si existe."
    )

    if st.button("Generar reporte", key="report_generar"):
        if not st.session_state.messages:
            # Estado vacio: sin intercambios no hay nada que reportar.
            st.warning(
                "Aun no hay intercambios: chatea primero (o usa los atajos de "
                "grounding) y despues genera el reporte."
            )
        else:
            try:
                with st.spinner("Construyendo el PDF del reporte..."):
                    pdf_generado = build_report_pdf(
                        session_id,
                        list(st.session_state.messages),
                        st.session_state.last_summary,
                    )
            except Exception as e:  # noqa: BLE001 - un PDF no debe tumbar la UI
                # Sin PDF a medias: se descarta el anterior para no ofrecer un
                # archivo que no corresponde a este clic.
                st.session_state.pop("report_pdf", None)
                st.session_state.pop("report_pdf_name", None)
                st.session_state.pop("report_pdf_meta", None)
                st.error(
                    "No se pudo generar el reporte: "
                    f"{e}. Revisa que `fpdf2` este instalado "
                    "(`pip install -r requirements.txt`) e intenta de nuevo."
                )
            else:
                st.session_state.report_pdf = pdf_generado
                st.session_state.report_pdf_name = "reporte.pdf"
                st.session_state.report_pdf_meta = {
                    "session_id": session_id,
                    "mensajes": total_mensajes,
                    "hora": datetime.now().strftime("%Y-%m-%d %H:%M"),
                }

    if "report_pdf" in st.session_state:
        pdf_bytes = st.session_state.report_pdf
        nombre_reporte = st.session_state.get("report_pdf_name", "reporte.pdf")
        meta = st.session_state.get("report_pdf_meta") or {}

        st.success(
            f"Reporte listo: {len(pdf_bytes) / 1024:.1f} KB "
            f"({meta.get('mensajes', total_mensajes)} mensajes, generado "
            f"{meta.get('hora', 'ahora')})."
        )
        if meta and (
            meta.get("session_id") != session_id
            or meta.get("mensajes") != total_mensajes
        ):
            st.caption(
                "Ojo: el historial o la sesion cambiaron despues de generar el "
                "PDF. Pulsa 'Generar reporte' otra vez para actualizarlo."
            )

        st.download_button(
            "Descargar reporte.pdf",
            data=pdf_bytes,
            file_name=nombre_reporte,
            mime="application/pdf",
            key="report_descargar",
        )
    else:
        st.caption(
            "Sin reporte generado todavia. El boton se habilita cuando exista "
            "al menos un intercambio en el chat."
        )

