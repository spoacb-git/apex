"""
Proxy Python (Flask) entre ESP32 e Oracle ORDS/APEX
=====================================================
Usa curl_cffi para imitar o fingerprint TLS do Chrome, contornando
o bloqueio do Akamai Bot Manager que barra clientes "não-navegador"
(curl comum, mbedTLS do ESP32, Google Apps Script, Cloudflare Workers).

Agora o workspace é informado dinamicamente na URL, permitindo
consultar diferentes bases/workspaces do APEX com o mesmo proxy:

    https://SEU-PROXY.onrender.com/consult?workspace=tecmx2026
    https://SEU-PROXY.onrender.com/consult?workspace=outro_workspace

Instalação:
    pip install flask curl_cffi

Rodar localmente (teste):
    python proxy_server.py

Depois, hospede em um serviço como Render.com, Railway.app, etc.
"""

import re
from flask import Flask, jsonify, request
from curl_cffi import requests as curl_requests

app = Flask(__name__)

# Monte aqui o restante do caminho, que é fixo (só o workspace muda)
ORDS_MODULE_PATH = "iot/consult"
ORDS_INSERT_PATH = "iot/insert"

# Só permite letras, números, underline e hífen no nome do workspace,
# para evitar que alguém injete outra URL/host através do parâmetro
# (proteção básica contra uso indevido do proxy como "open relay").
WORKSPACE_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


@app.route("/consult", methods=["GET"])
def consult():
    workspace = request.args.get("workspace", "").strip()

    if not workspace:
        return jsonify({"error": "missing_workspace", "message": "Informe ?workspace=NOME_DO_WORKSPACE na URL"}), 400

    if not WORKSPACE_PATTERN.match(workspace):
        return jsonify({"error": "invalid_workspace", "message": "Workspace contém caracteres não permitidos"}), 400

    ords_url = f"https://oracleapex.com/ords/{workspace}/{ORDS_MODULE_PATH}"

    try:
        response = curl_requests.get(ords_url, impersonate="chrome120", timeout=15)

        # Repassa o corpo e o status exatamente como veio do ORDS
        return (response.text, response.status_code, {"Content-Type": "application/json"})

    except Exception as err:
        return jsonify({"error": "proxy_error", "message": str(err)}), 502



@app.route("/insert", methods=["GET"])
def insert():
    """
    Recebe os campos via query string (mais simples para o ESP32 montar)
    e faz o POST em JSON de verdade para o ORDS.

    Exemplo de chamada:
        /insert?workspace=tecmx2026&tipo=TEMP&valor=66

    Isso vira, internamente, um POST para:
        https://oracleapex.com/ords/tecmx2026/iot/insert
    com corpo:
        {"tipo": "TEMP", "valor": 66}
    """
    args = request.args.to_dict()

    workspace = args.pop("workspace", "").strip()

    if not workspace:
        return jsonify({"error": "missing_workspace", "message": "Informe ?workspace=NOME_DO_WORKSPACE na URL"}), 400

    if not WORKSPACE_PATTERN.match(workspace):
        return jsonify({"error": "invalid_workspace", "message": "Workspace contém caracteres não permitidos"}), 400

    if not args:
        return jsonify({"error": "missing_fields", "message": "Informe ao menos um campo (ex: ?tipo=TEMP&valor=66)"}), 400

    # Monta o corpo JSON, convertendo valores numéricos automaticamente
    # (ex: "66" -> 66, "25.4" -> 25.4), e deixando o resto como texto.
    body = {}
    for key, value in args.items():
        body[key] = _converter_tipo(value)

    ords_url = f"https://oracleapex.com/ords/{workspace}/{ORDS_INSERT_PATH}"

    try:
        response = curl_requests.post(ords_url, json=body, impersonate="chrome120", timeout=15)
        return (response.text, response.status_code, {"Content-Type": "application/json"})

    except Exception as err:
        return jsonify({"error": "proxy_error", "message": str(err)}), 502


def _converter_tipo(valor):
    """Tenta converter string para int ou float; se não der, mantém como texto."""
    try:
        return int(valor)
    except ValueError:
        pass
    try:
        return float(valor)
    except ValueError:
        pass
    return valor





@app.route("/", methods=["GET"])
def health_check():
    # Rota simples para confirmar que o servidor está no ar
    return jsonify({"status": "online"})


if __name__ == "__main__":
    # host="0.0.0.0" é necessário para funcionar quando hospedado na nuvem
    app.run(host="0.0.0.0", port=5000)

