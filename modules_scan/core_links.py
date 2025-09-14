# core_links.py (Redis)
import os, time, json, secrets
from typing import Tuple, Optional, Dict, Any
from dotenv import load_dotenv
import redis

load_dotenv()
BASE_URL = os.getenv("BASE_URL")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

def _now() -> int:
    return int(time.time())

def _key_token(tok: str) -> str:
    return f"token:{tok}"

def _key_connect_active(instance: str) -> str:
    return f"connect_active:{instance}"

def init_db():
    """
    Em Redis não há schema; só verificamos a conexão.
    Mantemos a função por compatibilidade com o restante do projeto.
    """
    try:
        r.ping()
    except Exception as e:
        print(f"[WARN] Redis indisponível no init_db(): {e}")

def _row_to_payload_from_hash(h: Dict[str, str]) -> Dict[str, Any]:
    """
    Converte o hash do Redis no mesmo formato que o código original espera.
    """
    exp_str = h.get("expires_at")
    one_time_str = h.get("one_time", "0")
    used_at_str = h.get("used_at")  # pode ser vazio

    return {
        "expires_at": int(exp_str) if exp_str else 0,
        "payload": json.loads(h.get("payload") or "{}"),
        "one_time": bool(int(one_time_str) if one_time_str else 0),
        "used_at": int(used_at_str) if (used_at_str and used_at_str.isdigit()) else None
    }

def _get_active_token_for_instance(instance: str) -> Optional[str]:
    """
    Retorna um token ATIVO (ainda válido no Redis) para a mesma instância e page='connect', se existir.
    Implementado via chave auxiliar connect_active:{instance} -> token.
    """
    try:
        tok = r.get(_key_connect_active(instance))
        if not tok:
            return None
        # Verifica se o token ainda existe (não expirou)
        if not r.exists(_key_token(tok)):
            # Limpa mapeamento “zumbi”
            r.delete(_key_connect_active(instance))
            return None

        # Por garantia, checa se o token realmente é da page 'connect' e da mesma instância.
        h = r.hgetall(_key_token(tok))
        if not h:
            r.delete(_key_connect_active(instance))
            return None
        data = _row_to_payload_from_hash(h)
        pl = data["payload"] or {}
        if pl.get("page") != "connect" or pl.get("instance") != instance:
            r.delete(_key_connect_active(instance))
            return None

        return tok
    except Exception:
        return None

def create_token(ttl_seconds: int, payload: Dict[str, Any], one_time: bool = False) -> Optional[str]:
    """
    Cria um token no Redis como hash com TTL.
    """
    try:
        token = secrets.token_urlsafe(16)
        expires_at = _now() + int(ttl_seconds)
        key = _key_token(token)

        with r.pipeline(transaction=True) as p:
            p.hset(key, mapping={
                "expires_at": str(expires_at),
                "payload": json.dumps(payload or {}, ensure_ascii=False),
                "one_time": "1" if one_time else "0",
                "used_at": ""  # compatível com o código original
            })
            p.expire(key, int(ttl_seconds))
            p.execute()

        return token
    except Exception:
        return None

def build_link(token: str) -> str:
    if not BASE_URL:
        # Evita link quebrado; em produção, lance exceção/alarme
        return f"/t={token}"
    return f"{BASE_URL}?t={token}"

def get_or_create_connect_link(instance: str, apikey: str, ttl_seconds: int = 8*60*60) -> Tuple[str, str, bool]:
    """
    Garante NO MÁXIMO 1 link 'connect' ativo por instância.
    Retorna (token, full_link, created_new).
    """
    # 1) Reutiliza se já existir
    existing = _get_active_token_for_instance(instance)
    if existing:
        return existing, build_link(existing), False

    # 2) Cria um novo 'connect'
    payload = {"page": "connect", "instance": instance, "apikey": apikey}
    tok = create_token(ttl_seconds, payload, one_time=False)
    if not tok:
        return "", "", False

    # 3) Tenta registrar como ativo (NX = só se não existir ainda)
    key_active = _key_connect_active(instance)
    ok = r.set(key_active, tok, ex=int(ttl_seconds), nx=True)
    if ok:
        return tok, build_link(tok), True

    # 4) Corrida: alguém registrou antes; usa o existente e remove o novo
    existing = _get_active_token_for_instance(instance)
    if existing:
        r.delete(_key_token(tok))
        return existing, build_link(existing), False

    # 5) Cenário raro: nenhum ativo mesmo após NX falhar -> registra sem NX
    r.set(key_active, tok, ex=int(ttl_seconds))
    return tok, build_link(tok), True

def validate_token(token: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Valida o token: existe? então é válido (TTL cuida da expiração).
    """
    try:
        key = _key_token(token)
        if not r.exists(key):
            return False, "Token inválido ou não encontrado.", None

        h = r.hgetall(key)
        data = _row_to_payload_from_hash(h)
        return True, "OK", data["payload"]
    except Exception:
        return False, "Erro ao validar token.", None

def shorten_after_connected(token: str, seconds: int = 30):
    """
    Ao detectar 'connected', reduz a validade do token para alguns segundos
    e sincroniza o TTL do mapeamento connect_active:{instance}, se aplicável.
    """
    try:
        key = _key_token(token)
        if not r.exists(key):
            return

        new_ttl = max(5, int(seconds))
        r.expire(key, new_ttl)
        # Atualiza expires_at (informativo)
        r.hset(key, "expires_at", str(_now() + new_ttl))

        # Se for um token 'connect', encurta o mapeamento por instância
        h = r.hgetall(key)
        if h:
            data = _row_to_payload_from_hash(h)
            pl = data["payload"] or {}
            if pl.get("page") == "connect" and pl.get("instance"):
                r.expire(_key_connect_active(pl["instance"]), new_ttl)
    except Exception:
        pass

import json

def cleanup_orphan_links(valid_instances: list[str]):
    """
    Remove do Redis todos os links de instâncias que não estão mais ativas.
    """
    # Limpa connect_active:*
    keys = r.keys("connect_active:*")  # ajuste o prefixo real
    for key in keys:
        instance_name = key.split(":")[-1]
        if instance_name not in valid_instances:
            r.delete(key)
            print(f"[CLEANUP] Link órfão removido do Redis: {instance_name}")
    
    # Limpa token:*
    keys = r.keys("token:*")
    for key in keys:
        # Lê o hash da chave
        data = r.hgetall(key)
        if not data:
            r.delete(key)
            print(f"[CLEANUP] Token vazio removido: {key}")
            continue

        payload = data.get("payload")
        if payload:
            try:
                payload_json = json.loads(payload)
                instance_name = payload_json.get("instance")
                if instance_name not in valid_instances:
                    r.delete(key)
                    print(f"[CLEANUP] Token de instância inválida removido: {key}")
            except json.JSONDecodeError:
                r.delete(key)
                print(f"[CLEANUP] Token inválido (payload corrompido) removido: {key}")
        else:
            r.delete(key)
            print(f"[CLEANUP] Token sem payload removido: {key}")