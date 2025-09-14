# modulo/core_loop.py
"""
Loop principal de varredura (scanner) exatamente como no algoritmo original,
apenas reorganizado por módulos.
"""

from time import sleep
from typing import Dict, Any

from .utils import normalize_number, number_from_owner_jid
from .core_links import init_db, get_or_create_connect_link, cleanup_orphan_links
from .evolution_api import fetch_instances_from_api, fetch_qr_code_status, logout_instance
from .messaging import send_text_admin_to_client

def main_loop():
    init_db()

    while True:
        instances = fetch_instances_from_api()
        instance_names = [item.get("name") for item in instances if item.get("name")]

        if not instances:
            print("[INFO] Nenhuma instância retornada pela API. Aguardando...")

        # 🧹 limpeza de links órfãos
        cleanup_orphan_links(instance_names)

        next_sleep = 60  # padrão

        for item in instances:
            instance = item.get('name')
            apikey = item.get('key')

            # número cadastrado (na API)
            instance_number = normalize_number(item.get('instance_number') or item.get('customer_number'))
            # número real do aparelho logado (ownerJid)
            owner_jid_number = normalize_number(number_from_owner_jid(item.get('owner_jid') or ""))

            conn_status_hint = (item.get('connection_status') or '').lower()

            if not instance or not apikey:
                print(f"[WARN] Registro inválido vindo da API: instance='{instance}', key presente? {bool(apikey)}")
                continue

            # Buscamos SEMPRE o status real do servidor antes de qualquer ação
            status: Dict[str, Any] = fetch_qr_code_status(instance, apikey)
            s = status.get('status')

            # 1) Se tem QR, prioriza gerar/enviar link e NÃO tenta deslogar
            if s == 'qr_code':
                client_number = instance_number
                token, link, created = get_or_create_connect_link(instance, apikey, ttl_seconds=4*60*60)
                if created:
                    if not client_number:
                        print(f"[WARN] instance={instance}: 'number' ausente; não é possível enviar o link.")
                    else:
                        ok, resp = send_text_admin_to_client(client_number, link)
                        if ok:
                            print(f"[OK] Link enviado p/ {client_number} (instance={instance})")
                        else:
                            print(f"[ERRO] Envio p/ {client_number} (instance={instance}) -> {resp}")
                else:
                    print(f"[INFO] instance={instance}: link já existe/recente; nada a enviar agora.")
                # Próxima instância
                continue

            # 2) Se está conectado, aí sim verificamos divergência de número e eventualmente deslogamos
            if s == 'connected' or conn_status_hint in ('open', 'connected'):
                if owner_jid_number and instance_number and owner_jid_number != instance_number:
                    print(f"[WARN] instance={instance}: divergência (ownerJid={owner_jid_number} != cadastro={instance_number}). Efetuando logout...")
                    ok, resp = logout_instance(instance, apikey)
                    if ok:
                        print(f"[OK] instance={instance}: logout realizado. Detalhe: {resp}")
                        get_or_create_connect_link(instance, apikey, ttl_seconds=4*60*60)
                    else:
                        print(f"[ERRO] instance={instance}: falha no logout -> {resp}")
                else:
                    print(f"[OK] instance={instance}: conectada e sem divergência.")
                continue

            # 3) Demais casos (não conectado): só aguardamos/otimizamos o polling
            if s == 'unknown':
                print(f"[INFO] instance={instance}: status desconhecido -> {status.get('raw')}")
            elif s == 'error':
                print(f"[ERRO] instance={instance}: {status.get('message')}")
            else:
                # ex.: estado 'close' ou sem estado definido
                if conn_status_hint == 'connecting':
                    print(f"[INFO] instance={instance}: connecting, aguardando QR...")
                    next_sleep = min(next_sleep, 15)  # acelera a próxima varredura
                else:
                    print(f"[INFO] instance={instance}: não conectada (hint='{conn_status_hint}').")

        sleep(next_sleep)