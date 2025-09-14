# modulo/evolution_api.py
"""
Chamadas à Evolution Global API (instâncias, QR/status, logout).
Não altera a estrutura do algoritmo original.
"""

import json
import requests
from typing import List, Dict, Any, Tuple

from . import config
from .utils import build_url


def fetch_instances_from_api() -> List[Dict[str, Any]]:
    """
    Lê todas as instâncias via Evolution Global API e normaliza para:
      {
        "name": "<instance_name>",
        "key": "<token_da_instancia>",
        "customer_number": "<numero_cadastrado>",
        "instance_number": "<numero_cadastrado>",
        "owner_jid": "<ownerJid>",
        "connection_status": "<open|close|...>"
      }
    """
    if not config.API_KEY:
        print("[ERRO] EVOLUTION_GLOBAL_KEY não configurada.")
        return []

    try:
        url = build_url("/instance/fetchInstances")
        headers = {"apikey": config.API_KEY}
        resp = requests.get(url, headers=headers, verify=False, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        if isinstance(data, dict):
            raw_list = data.get("instances")
            if isinstance(raw_list, list):
                instances = raw_list
            else:
                instances = list(data.values())[0] if data.values() else []
        elif isinstance(data, list):
            instances = data
        else:
            instances = []

        out: List[Dict[str, Any]] = []
        for it in instances or []:
            name = (it or {}).get("name") or ""
            token = (it or {}).get("token") or ""
            number = (it or {}).get("number") or ""       # número do cadastro
            cstatus = (it or {}).get("connectionStatus") or ""
            owner_jid = (it or {}).get("ownerJid") or ""  # jid do aparelho logado

            if not name or not token:
                continue

            out.append({
                "name": name,
                "key": token,
                "customer_number": number,
                "instance_number": number,
                "owner_jid": owner_jid,
                "connection_status": str(cstatus).lower()
            })

        return out

    except Exception as e:
        print(f"[ERRO] Falha ao buscar instâncias na API: {e}")
        return []


def fetch_qr_code_status(instanceName: str, apikey: str) -> Dict[str, Any]:
    """
    Retorna:
      - {"qrcode": <code>, "status": "qr_code"} se houver QR
      - {"qrcode": None, "status": "connected"} se já conectado
      - {"qrcode": None, "status": "unknown"|"error", ...} para outros casos
    """
    try:
        url = build_url(f"/instance/connect/{instanceName}")
        headers = {"apikey": apikey}
        rqs = requests.get(url, headers=headers, verify=False, timeout=10)
        data = rqs.json()

        code = data.get("code")
        if code:
            return {"qrcode": code, "status": "qr_code"}

        state = str(data.get("instance", {}).get("state", "")).lower()
        if state == "open":
            return {"qrcode": None, "status": "connected"}

        return {"qrcode": None, "status": "unknown", "raw": data}
    except Exception:
        return {
            "qrcode": None,
            "status": "error",
            "message": "Não foi possível obter o status do servidor."
        }

def logout_instance(instance: str, apikey: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Desloga a instância usando o mesmo domínio configurado via EVOLUTION_DOMAIN.
    """
    try:
        url = build_url(f"/instance/logout/{instance}")
        headers = {"apikey": apikey}
        r = requests.delete(url, headers=headers, verify=False, timeout=15)
        r.raise_for_status()
        try:
            return True, r.json()
        except Exception:
            return True, {"text": r.text}
    except Exception as e:
        return False, {"error": str(e)}