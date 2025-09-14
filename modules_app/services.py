import requests
from typing import Dict, Any

from .config import DOMAIN
from .utils import _extract_qrcode

def fetch_qr_code_status(instance_name: str, apikey: str) -> Dict[str, Any]:
    # Chama o endpoint do servidor WPP para pegar status e/ou QR. Aceita vários formatos.
    try:
        url = f"{DOMAIN}/instance/connect/{instance_name}"
        headers = {"apikey": apikey}
        r = requests.get(url, headers=headers, verify=False, timeout=10)
        r.raise_for_status()
        data = r.json()
    except Exception:
        return {
            "qrcode": None,
            "qr_format": None,
            "status": "error",
            "message": "Não foi possível obter o status do servidor. Verifique a conexão e tente novamente.",
        }

    state = str(data.get("instance", {}).get("state", "")).lower()
    root_state = str(data.get("status", "")).lower()

    qr_info = _extract_qrcode(data)
    if qr_info["value"]:
        return {"qrcode": qr_info["value"], "qr_format": qr_info["format"], "status": "qr_code"}

    if state == "open" or root_state in ("open", "connected"):
        return {"qrcode": None, "qr_format": None, "status": "connected"}

    return {"qrcode": None, "qr_format": None, "status": "unknown", "raw": data}

def get_bot_profile(apikey: str) -> Dict[str, Any]:
    try:
        url = f"{DOMAIN}/instance/fetchInstances"
        headers = {"apikey": apikey}
        r = requests.get(url, headers=headers, verify=False, timeout=10)
        r.raise_for_status()
        js = r.json()
        if isinstance(js, list) and js:
            p = js[0] or {}
            return {
                "ok": True,
                "profile": {
                    "profileName": p.get("profileName") or p.get("name"),
                    "name": p.get("profileName") or p.get("name"),
                    "number": p.get("number"),
                    "profilePicUrl": p.get("profilePicUrl"),
                },
            }
        return {"ok": False, "message": "Lista de perfis vazia."}
    except Exception:
        return {"ok": False, "message": "Não foi possível carregar o perfil do WhatsApp."}
