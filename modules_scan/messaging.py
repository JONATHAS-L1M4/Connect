# modulo/messaging.py
"""
Envio de mensagens via instância ADMIN (texto com link).
"""

import requests
from typing import Tuple, Dict, Any

from . import config
from .utils import build_url


def send_text_admin_to_client(client_number: str, link: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Envia o link de conexão para o número do cliente via instância ADMIN.
    """
    url = build_url(f"/message/sendText/{config.EVOLUTION_INSTANCE_NAME_ADMIN}")
    payload = {
        "linkPreview": True,
        "number": client_number,
        "text": f"Olá, tudo bem? 👋 Conecte seu dispositivo ao agente do WhatsApp 🔗.\n{link}"
    }
    headers = {
        "apikey": config.EVOLUTION_INSTANCE_KEY_ADMIN,
        "Content-Type": "application/json"
    }
    try:
        rqs = requests.post(url, json=payload, headers=headers, verify=False, timeout=15)
        rqs.raise_for_status()
        return True, rqs.json()
    except Exception as e:
        return False, {"error": str(e)}
