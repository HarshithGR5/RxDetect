"""
eka_client.py
Eka Care API integration for drug normalization + validation.
Robust + debuggable version.
"""

import hashlib
import json
import structlog
import requests
from typing import Optional

from app.config import settings

log = structlog.get_logger(__name__)

BASE = "https://api.dev.eka.care/medical-db/v1/drugs-and-labs"
TTL = 60 * 60 * 24 * 7


# ---------------------------------------------------------
# Redis cache
# ---------------------------------------------------------

def _get_redis():
    try:
        import redis as redis_lib
        return redis_lib.from_url(settings.redis_url, decode_responses=True)
    except Exception:
        return None


def _cache_key(drug: str) -> str:
    return f"eka:{hashlib.md5(drug.lower().encode()).hexdigest()}"


# ---------------------------------------------------------
# Search Eka
# ---------------------------------------------------------

def search_eka(drug_name: str) -> Optional[dict]:
    r = _get_redis()
    ck = _cache_key(drug_name)

    # ---- Cache ----
    if r:
        cached = r.get(ck)
        if cached:
            return json.loads(cached) if cached != "NULL" else None

    try:
        if not settings.eka_api_key:
            log.warning("eka.no_api_key")
            return None

        headers = {
            "Authorization": f"Bearer {settings.eka_api_key}"
        }

        # ✅ FIXED PARAM (was q, now name)
        resp = requests.get(
            BASE,
            params={"name": drug_name},
            headers=headers,
            timeout=6,
        )

        log.info("eka.request", drug=drug_name, status=resp.status_code)

        # 🔥 VERY IMPORTANT DEBUG LOG
        try:
            log.info("eka.raw_response", response=resp.text[:500])
        except Exception:
            pass

        if resp.status_code == 404:
            if r:
                r.setex(ck, TTL, "NULL")
            return None

        resp.raise_for_status()

        data = resp.json()
        drugs = data.get("drugs", [])

        if not drugs:
            log.warning("eka.no_results", drug=drug_name)

        drug = drugs[0] if drugs else None

    except Exception as e:
        log.warning("eka.error", drug=drug_name, error=str(e))
        drug = None

    # ---- Cache result ----
    if r:
        r.setex(ck, TTL, json.dumps(drug) if drug else "NULL")

    return drug


# ---------------------------------------------------------
# Validation wrapper
# ---------------------------------------------------------

def validate_eka(drug_name: str) -> dict:
    """
    Returns normalized drug info from Eka.
    Safe fallback if API unavailable.
    """

    if not settings.eka_api_key:
        return {"found": False}

    drug = search_eka(drug_name)

    if not drug:
        return {
            "found": False,
            "source": "eka",
        }

    return {
        "found": True,
        "source": "eka",
        "name": drug.get("name"),
        "generic": drug.get("generic_name"),
        "common_name": drug.get("common_name"),
        "dosage": drug.get("dosage", {}),
        "manufacturer": drug.get("manufacturer_name"),
        "is_otc": drug.get("is_otc"),
    }