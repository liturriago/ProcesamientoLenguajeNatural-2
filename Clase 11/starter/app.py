"""Clase 11 - Starter del estudiante (NO la solucion).

Implementa aqui los TODOs T2-T6 siguiendo SPEC.md, PLAN.md y los skills en
../skills/. La referencia del profesor esta en ../solucion-referencia/app/
y NO se puede copiar: la nota esta en tu demo en vivo + check.py en verde.
"""
import json
import os

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
    # TODO(T5): file_uploader PDF <=10 MB, extraer con pypdf (skills/pdf-report),
    #   preview 1000 chars, POST {"sessionId","filename","text"} al Workflow B.
    st.info("TODO T5: subida e ingesta de PDF aqui.")

with tab_report:
    # TODO(T6): armar PDF con fpdf2 (sesion, fecha, intercambios, ultimo summary)
    #   y download_button.
    st.info("TODO T6: generacion y descarga del reporte aqui.")
