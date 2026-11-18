"""Clase 11 - Thin client Streamlit para el agente logistico (Clase 10).

Secciones: Chat+memoria / Inventario y clima / Subir PDF / Generar reporte.
Contratos en ../SPEC.md y skills en ../skills/.
"""
import os
from datetime import datetime

import requests
import streamlit as st
from pypdf import PdfReader
from fpdf import FPDF

DEFAULT_CHAT = "http://n8n:5678/webhook/agente-logistica-unal"
DEFAULT_INGEST = "http://n8n:5678/webhook/ingesta-reporte-pdf"

st.set_page_config(page_title="UNAL Logistica - Agente", layout="wide")
st.title("Agente de logistica UNAL — Interfaz Clase 11")

with st.sidebar:
    st.header("Conexion")
    chat_url = st.text_input("N8N_CHAT_URL", os.getenv("N8N_CHAT_URL", DEFAULT_CHAT))
    ingest_url = st.text_input("N8N_INGEST_URL", os.getenv("N8N_INGEST_URL", DEFAULT_INGEST))
    session_id = st.text_input("session_id (memoria)", "demo-01")
    st.caption("Mismo session_id = misma conversacion (Window Buffer Memory).")
    for _u in (chat_url, ingest_url):
        if "localhost" in _u or "webhook-test" in _u:
            st.warning("Esa URL no va a funcionar: usa el host interno http://n8n:5678 y paths /webhook/ (no localhost ni /webhook-test/).")
            break

if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_summary" not in st.session_state:
    st.session_state.last_summary = ""


def parse_output(data):
    if isinstance(data, list) and data and isinstance(data[0], dict) and "output" in data[0]:
        return str(data[0]["output"])
    if isinstance(data, dict) and "output" in data:
        return str(data["output"])
    return None


def post_chat(url, sid, msg):
    r = requests.post(url, json={"sessionId": sid, "chatInput": msg}, timeout=120)
    if r.status_code == 404:
        raise RuntimeError("404: workflow no publicado o path mal (usa /webhook/, no /webhook-test/).")
    if r.status_code == 401:
        raise RuntimeError("401: puerto 5678 en Private con URL https. Usa http://n8n:5678/... o pon el puerto en Public.")
    r.raise_for_status()
    try:
        data = r.json()
    except ValueError:
        return r.text
    out = parse_output(data)
    return out if out is not None else r.text


def send_and_render(prompt):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"), st.spinner("Consultando al agente..."):
        try:
            answer = post_chat(chat_url, session_id, prompt)
            raw = None
        except Exception as e:  # noqa: BLE001 - mensaje legible para clase
            answer = f"Error: {e}"
            raw = None
    st.session_state.messages.append({"role": "assistant", "content": answer})
    with st.chat_message("assistant"):
        st.markdown(answer)
    return answer


tab_chat, tab_ground, tab_pdf, tab_report = st.tabs(
    ["Chat", "Inventario y clima", "Subir PDF", "Reporte"]
)

with tab_chat:
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
    if prompt := st.chat_input("Pregunta al agente (ej. ¿Hay osciloscopios?)"):
        send_and_render(prompt)

with tab_ground:
    st.subheader("Evidencia de grounding")
    col1, col2, col3 = st.columns(3)
    if col1.button("¿Hay osciloscopios?"):
        ans = send_and_render("¿Hay osciloscopios? Indica Componente, ID, Cantidad, Ubicacion y Estado.")
        with st.expander("Respuesta"):
            st.write(ans)
    if col2.button("¿Hay Raspberry Pi?"):
        ans = send_and_render("¿Hay Raspberry Pi disponible? Indica Componente, ID, Cantidad, Ubicacion y Estado.")
        with st.expander("Respuesta"):
            st.write(ans)
    if col3.button("Clima Manizales"):
        ans = send_and_render("¿Cómo está el clima en Manizales?")
        with st.expander("Respuesta"):
            st.write(ans)
    st.divider()
    st.subheader("Registrar / actualizar (requiere confirmación)")
    with st.form("write_form"):
        c1, c2 = st.columns(2)
        wid = c1.text_input("ID* (exacto, ej. UNAL-001)")
        comp = c2.text_input("Componente* (ej. Osciloscopio)")
        cant = c1.text_input("Cantidad* (ej. 3)")
        ubi = c2.text_input("Ubicacion* (ej. Lab 204)")
        est = st.text_input("Estado* (ej. Disponible / Mantenimiento Requerido)")
        confirm = st.checkbox("Confirmo que quiero escribir en el inventario")
        sent = st.form_submit_button("Enviar al agente")
    if sent:
        if not all([wid, comp, cant, ubi, est]):
            st.warning("Completa todos los campos marcados con *.")
        elif not confirm:
            st.warning("Marca la confirmación antes de enviar. Sin check no hay POST.")
        else:
            msg = (f"Registra/actualiza inventario con confirmacion del usuario: "
                   f"ID={wid} Componente={comp} Cantidad={cant} Ubicacion={ubi} Estado={est}.")
            st.info(f"Payload a enviar: {msg}")
            send_and_render(msg)

with tab_pdf:
    st.subheader("Subir PDF para ingesta (Workflow B)")
    up = st.file_uploader("PDF con texto (máx 10 MB)", type=["pdf"])
    if up is not None:
        if up.size > 10 * 1024 * 1024:
            st.error("PDF mayor a 10 MB.")
        else:
            reader = PdfReader(up)
            text = "\n".join([(p.extract_text() or "") for p in reader.pages])[:20000]
            if not text.strip():
                st.error("PDF sin texto extraíble (escaneado). Usa un PDF con texto.")
            else:
                with st.expander("Preview (1000 chars)"):
                    st.write(text[:1000])
                if st.button("Enviar a ingesta"):
                    with st.spinner("Enviando al workflow B..."):
                        try:
                            r = requests.post(
                                ingest_url,
                                json={"sessionId": session_id, "filename": up.name, "text": text},
                                timeout=120,
                            )
                            r.raise_for_status()
                            data = r.json()
                            st.session_state.last_summary = str(data.get("summary", data))
                            st.success("Ingesta OK")
                            st.write(st.session_state.last_summary)
                            with st.expander("JSON crudo"):
                                st.json(data)
                        except Exception as e:  # noqa: BLE001
                            st.error(f"Error de ingesta: {e}")

with tab_report:
    st.subheader("Generar reporte PDF")
    if st.button("Generar reporte de la sesión"):
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, "Reporte agente logistica UNAL", ln=True)
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 8, f"Sesion: {session_id}  Fecha: {datetime.now():%Y-%m-%d %H:%M}", ln=True)
        pdf.ln(4)
        for m in st.session_state.messages:
            tag = "Usuario" if m["role"] == "user" else "Agente"
            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(0, 7, f"{tag}:", ln=True)
            pdf.set_font("Helvetica", "", 10)
            safe = m["content"].encode("latin-1", "replace").decode("latin-1")
            pdf.multi_cell(0, 6, safe)
            pdf.ln(2)
        if st.session_state.last_summary:
            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(0, 7, "Ultimo resumen de ingesta:", ln=True)
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(0, 6, st.session_state.last_summary.encode("latin-1", "replace").decode("latin-1"))
        out = bytes(pdf.output())
        st.download_button("Descargar reporte.pdf", out, "reporte.pdf", "application/pdf")
    if not st.session_state.messages:
        st.info("Aún no hay intercambios para reportar.")
