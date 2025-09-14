import base64
from io import BytesIO
from typing import Dict, Any

import qrcode
import requests
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse

from modules_scan.core_links import shorten_after_connected  # mantém dependência externa

from .config import templates, STATIC_DIR
from .utils import json_no_store
from .security import guard_and_get_payload
from .services import fetch_qr_code_status, get_bot_profile

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
def ui_connect(request: Request):
    token = request.query_params.get("t")
    try:
        _ = guard_and_get_payload(token)
    except HTTPException as e:
        resp = templates.TemplateResponse("invalid.html", {"request": request}, status_code=e.status_code)
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp

    resp = templates.TemplateResponse("connect.html", {"request": request, "token": token})
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp

@router.get("/api/qr-status")
def api_qr_status(request: Request):
    token = request.query_params.get("t")
    try:
        payload = guard_and_get_payload(token)
    except HTTPException:
        return json_no_store({"status": "invalid", "message": "Link inválido ou expirado"}, status_code=200)

    instance = payload["instance"]
    apikey = payload["apikey"]

    data = fetch_qr_code_status(instance, apikey)
    if data.get("status") == "connected":
        try:
            shorten_after_connected(token)
        except Exception:
            pass
    return json_no_store(data)

@router.get("/api/qr-png")
def api_qr_png(request: Request):
    """
    Fallback: gera um PNG do QR no servidor a partir do código textual
    ou traduz uma dataURL/base64 em PNG binário.
    """
    token = request.query_params.get("t")
    try:
        payload = guard_and_get_payload(token)
    except HTTPException as e:
        raise HTTPException(status_code=404, detail=str(e.detail))

    instance = payload["instance"]
    apikey = payload["apikey"]

    data = fetch_qr_code_status(instance, apikey)
    if data.get("status") != "qr_code":
        raise HTTPException(status_code=404, detail="QR indisponível")

    qrv = data.get("qrcode") or ""
    # Se já veio imagem base64/dataURL -> retornar como PNG binário
    if isinstance(qrv, str) and (qrv.startswith("data:image/") or (len(qrv) > 100 and qrv[:5] == "iVBOR")):
        if qrv.startswith("data:image/"):
            try:
                _, b64 = qrv.split(",", 1)
            except ValueError:
                raise HTTPException(status_code=502, detail="DataURL inválida")
        else:
            b64 = qrv
        try:
            raw = base64.b64decode(b64, validate=True)
            return StreamingResponse(BytesIO(raw), media_type="image/png", headers={"Cache-Control": "no-store"})
        except Exception:
            pass  # se base64 inválida, tenta como texto

    txt = str(qrv).strip()
    if not txt:
        raise HTTPException(status_code=404, detail="Código de QR vazio")

    qr_img = qrcode.make(txt)
    buf = BytesIO()
    qr_img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png", headers={"Cache-Control": "no-store"})

@router.get("/api/profile")
def api_profile(request: Request):
    token = request.query_params.get("t")
    try:
        payload = guard_and_get_payload(token)
    except HTTPException as e:
        return json_no_store({"ok": False, "message": str(e.detail)}, status_code=200)

    apikey = payload["apikey"]
    info = get_bot_profile(apikey)
    if not info.get("ok"):
        return json_no_store({"ok": False, "message": info.get("message", "Falha ao obter perfil")}, status_code=200)

    p = info["profile"]
    has_photo = True if p.get("profilePicUrl") else False
    return json_no_store(
        {
            "ok": True,
            "profile": {
                "profileName": p.get("profileName"),
                "name": p.get("name"),
                "number": p.get("number"),
                "hasPhoto": has_photo,
            },
        }
    )

@router.get("/api/profile-photo")
def api_profile_photo(request: Request):
    token = request.query_params.get("t")
    try:
        payload = guard_and_get_payload(token)
    except HTTPException as e:
        raise HTTPException(status_code=404, detail=str(e.detail))

    apikey = payload["apikey"]
    info = get_bot_profile(apikey)
    if not info.get("ok"):
        raise HTTPException(status_code=404, detail="Perfil indisponível")

    p = info["profile"]
    img_url = p.get("profilePicUrl")
    if not img_url:
        raise HTTPException(status_code=404, detail="Sem imagem de perfil")

    try:
        r = requests.get(img_url, stream=True, timeout=10, verify=False)
        r.raise_for_status()
        content_type = r.headers.get("Content-Type", "image/jpeg")
        return StreamingResponse(r.raw, media_type=content_type, headers={"Cache-Control": "no-store"})
    except Exception:
        raise HTTPException(status_code=502, detail="Falha ao carregar a imagem")

@router.get("/favicon.ico", include_in_schema=False)
def favicon():
    return FileResponse(str(STATIC_DIR / "img" / "favicon.png"), media_type="image/png")
