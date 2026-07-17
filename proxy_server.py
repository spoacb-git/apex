"""
Proxy Python (Flask) entre ESP32 e Oracle ORDS/APEX
=====================================================
Usa curl_cffi para imitar o fingerprint TLS do Chrome, contornando
o bloqueio do Akamai Bot Manager que barra clientes "não-navegador"
(curl comum, mbedTLS do ESP32, Google Apps Script, Cloudflare Workers).

Instalação:
    pip install flask curl_cffi

Rodar localmente (teste):
    python proxy_server.py

Depois, hospede em um serviço como Render.com, Railway.app, etc.
"""

from flask import Flask, jsonify
from curl_cffi import requests as curl_requests

app = Flask(__name__)

ORDS_URL = "https://oracleapex.com/ords/tecmx2026/iot/consult"


@app.route("/consult", methods=["GET"])
def consult():
    try:
        response = curl_requests.get(ORDS_URL, impersonate="chrome120", timeout=15)

        # Repassa o corpo e o status exatamente como veio do ORDS
        return (response.text, response.status_code, {"Content-Type": "application/json"})

    except Exception as err:
        return jsonify({"error": "proxy_error", "message": str(err)}), 502


@app.route("/", methods=["GET"])
def health_check():
    # Rota simples para confirmar que o servidor está no ar
    return jsonify({"status": "online"})


if __name__ == "__main__":
    # host="0.0.0.0" é necessário para funcionar quando hospedado na nuvem
    app.run(host="0.0.0.0", port=5000)
