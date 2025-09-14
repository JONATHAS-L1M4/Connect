from typing import Dict, Any, Optional
from fastapi import HTTPException
from modules_scan.core_links import validate_token  # mantém dependência externa

def guard_and_get_payload(token: Optional[str]) -> Dict[str, Any]:
    if not token:
        raise HTTPException(status_code=404, detail="Link inválido ou expirado")

    ok, msg, payload = validate_token(token)
    if not ok or not payload or payload.get("page") != "connect":
        raise HTTPException(status_code=404, detail=(msg if isinstance(msg, str) else "Link inválido ou expirado"))

    instance = payload.get("instance")
    apikey = payload.get("apikey")
    if not instance or not apikey:
        raise HTTPException(status_code=400, detail="Payload incompleto")
    return payload
