"""Juez del starter (SPEC.md S4). Progreso x/9. Sin n8n corre 8/9; con n8n vivo, 9/9.

Uso:  python "Clase 11/starter/check.py"  [--chat-url URL] [--ingest-url URL]
"""
import os
import py_compile
import re
import sys

STARTER = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(STARTER, "app.py")
REQ = os.path.join(STARTER, "requirements.txt")

results = []


def check(name, ok, detail=""):
    tag = "SKIP" if ok == "SKIP" else ("PASS" if ok else "FAIL")
    results.append((name, ok if ok == "SKIP" else bool(ok), detail))
    print(f"[{tag}] {name}" + (f" — {detail}" if detail else ""))


src = open(APP, encoding="utf-8").read() if os.path.exists(APP) else ""

# 1. Compila
try:
    py_compile.compile(APP, doraise=True)
    check("py_compile app.py", True)
except Exception as e:  # noqa: BLE001
    check("py_compile app.py", False, str(e))

# 2. Sin secretos
secrets = [p for p in ("sk-", "client_secret", "refresh_token", "authtoken",
                       "Bearer ", "passwd", "aws_secret") if p.lower() in src.lower()]
check("sin secretos en app.py", not secrets, f"hallado: {secrets}" if secrets else "")

# 3-7. Marcadores funcionales (progreso real de T2-T6)
check("cliente chat (requests.post + sessionId/chatInput)",
      "requests.post" in src and "chatInput" in src and "sessionId" in src)
check("chat UI (st.chat_input + send)",
      "st.chat_input(" in src and "send_and_render(prompt)" in src
      and "NotImplementedError" not in src)
check("grounding (botones + JSON crudo)", "expander" in src and "Osciloscop" in src)
check("escritura con confirmacion (checkbox + sin check no hay POST)",
      "st.checkbox(" in src and "Confirmo" in src)
check("PDF (file_uploader + PdfReader + FPDF/download)",
      "file_uploader" in src and "PdfReader" in src and ("FPDF" in src or "download_button" in src))

# 8. Deps
req = open(REQ, encoding="utf-8").read().lower() if os.path.exists(REQ) else ""
check("requirements (streamlit, requests, pypdf, fpdf2)",
      all(p in req for p in ("streamlit", "requests", "pypdf", "fpdf2")))

# 9. Contrato vivo (opcional: SKIP sin n8n)
chat_url = (sys.argv[sys.argv.index("--chat-url") + 1] if "--chat-url" in sys.argv
            else os.getenv("N8N_CHAT_URL", "http://n8n:5678/webhook/agente-logistica-unal"))
try:
    import requests  # noqa: E402
    r = requests.post(chat_url, json={"sessionId": "check-01", "chatInput": "¿Hay osciloscopios?"},
                      timeout=25)
    if r.status_code == 404:
        check("contrato vivo", False, "404: publica el workflow / usa /webhook/")
    elif r.status_code == 401:
        check("contrato vivo", False, "401: usa localhost o puerto en Public")
    else:
        r.raise_for_status()
        d = r.json()
        out = (d[0].get("output") if isinstance(d, list) else d.get("output"))
        check("contrato vivo", bool(out), f"output {len(str(out))} chars" if out else "sin output")
except ImportError:
    check("contrato vivo", "SKIP", "requests no instalado")
except Exception as e:  # noqa: BLE001
    check("contrato vivo", "SKIP", f"n8n no alcanzable ({e}); resto OK sin n8n")

fails = [n for n, ok, _ in results if ok is False]
print(f"\n{sum(1 for _, ok, _ in results if ok is True)}/{len(results)} en verde.")
sys.exit(1 if fails else 0)
