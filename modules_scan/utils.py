# modulo/utils.py
"""
Funções utilitárias (normalização de números, construção de URL, etc.).
"""
import re
from . import config

def build_url(path: str) -> str:
    """
    Constrói a URL baseando-se em config.DOMAIN_ENV.
    Garante https:// quando necessário.
    """
    base = config.DOMAIN_ENV.rstrip("/")
    if not base:
        raise RuntimeError("EVOLUTION_DOMAIN não configurado.")
    if not base.startswith("http://") and not base.startswith("https://"):
        base = "https://" + base
    return f"{base}{path}"


def normalize_number(n: str) -> str:
    """
    Mantém apenas dígitos em um número de telefone.
    """
    return re.sub(r'\D+', '', n or '')


def number_from_owner_jid(owner_jid: str) -> str:
    """
    Extrai apenas os dígitos de algo como:
    '5511960012470@s.whatsapp.net' -> '5511960012470'
    """
    if not owner_jid:
        return ""
    m = re.match(r'(\d+)', owner_jid)
    return m.group(1) if m else ""