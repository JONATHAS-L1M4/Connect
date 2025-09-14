# modulo/config.py
"""
Carrega variáveis de ambiente e configurações globais.
Também desabilita os warnings de SSL (apenas para ambientes controlados).
"""

import os
import requests
from dotenv import load_dotenv

# Desabilita warnings de SSL quando verify=False (use HTTPS em produção!)
requests.packages.urllib3.disable_warnings()

# Carrega .env
load_dotenv()

# Variáveis de ambiente
API_KEY = os.getenv("EVOLUTION_GLOBAL_KEY")
DOMAIN_ENV = os.getenv("EVOLUTION_DOMAIN", "").strip()
EVOLUTION_INSTANCE_NAME_ADMIN = os.getenv("EVOLUTION_INSTANCE_NAME_ADMIN")
EVOLUTION_INSTANCE_KEY_ADMIN = os.getenv("EVOLUTION_INSTANCE_KEY_ADMIN")