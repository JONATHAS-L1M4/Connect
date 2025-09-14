from typing import Dict, Any, Optional
from fastapi.responses import JSONResponse

def json_no_store(payload: Dict[str, Any], status_code: int = 200) -> JSONResponse:
    return JSONResponse(
        content=payload,
        status_code=status_code,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )

def _join_nonempty(parts, sep=","):
    return sep.join([p for p in parts if isinstance(p, str) and p.strip()])

def _extract_from_dict(d: dict) -> Optional[Dict[str, Any]]:
    # Monta a partir de dicts com segmentos (ref/publicKey/clientId), imagem base64, ou texto.
    ref = d.get("ref") or d.get("Ref")
    pub = d.get("publicKey") or d.get("PublicKey") or d.get("key")
    cid = d.get("clientId") or d.get("clientID") or d.get("ClientID")

    if (ref and pub and cid):
        return {"value": f"{ref},{pub},{cid}", "format": "text"}

    for k in ("image", "img", "base64", "qrImage", "dataURL"):
        val = d.get(k)
        if isinstance(val, str) and val.strip():
            if val.startswith("data:image/") or len(val) > 100:
                return {"value": val, "format": "image"}

    for k in ("qrcode", "qrCode", "qr_code", "qr", "code"):
        val = d.get(k)
        if isinstance(val, str) and val.strip():
            return {"value": val, "format": "text"}

    for k in ("segments", "qrSegments", "parts", "codes"):
        val = d.get(k)
        if isinstance(val, (list, tuple)) and len(val) >= 2:
            return {"value": _join_nonempty(val, ","), "format": "text"}

    return None

def _extract_qrcode(raw: Any) -> Dict[str, Any]:
    # Extrai o QR do JSON (texto ou imagem base64), inclusive formatos aninhados e segmentados.
    if not isinstance(raw, dict):
        return {"value": None, "format": None}

    direct_candidates = [
        raw.get("code"),
        raw.get("qrcode"),
        raw.get("qrCode"),
        raw.get("qr_code"),
        raw.get("qr"),
        raw.get("image"),
    ]

    if isinstance(raw.get("code"), (list, tuple)) and len(raw["code"]) >= 2:
        return {"value": _join_nonempty(raw["code"], ","), "format": "text"}

    if isinstance(raw.get("code"), dict):
        r = _extract_from_dict(raw["code"])
        if r:
            return r

    for c in direct_candidates:
        if isinstance(c, str) and c.strip():
            if c.startswith("data:image/") or (len(c) > 100 and c[:5] == "iVBOR"):
                return {"value": c, "format": "image"}
            return {"value": c, "format": "text"}

    for key in ("data", "result", "payload", "instance", "connect", "qr"):
        val = raw.get(key)
        if isinstance(val, dict):
            if isinstance(val.get("code"), (list, tuple)) and len(val["code"]) >= 2:
                return {"value": _join_nonempty(val["code"], ","), "format": "text"}
            if isinstance(val.get("code"), dict):
                r = _extract_from_dict(val["code"])
                if r:
                    return r
            r = _extract_from_dict(val)
            if r:
                return r

    return {"value": None, "format": None}
