"""
openfda_client.py
Wrapper around the OpenFDA drug label API.
Retrieves dosage, warnings, contraindications, and drug interaction text
from official FDA drug labels.

Redis note
----------
Uses the shared get_redis() from redis_cache instead of creating a new
connection pool on every call.  Creating a new pool per call was the
original behaviour; it caused extra AUTH + connection commands on Upstash
even when the app was idle (openfda is called during every analysis task).
"""
import json
import hashlib
import structlog
import requests
from typing import Optional

from app.config import settings

log = structlog.get_logger(__name__)

BASE = settings.openfda_base_url
TTL = 60 * 60 * 24 * 7  # 7 days


def _get_redis():
    try:
        from app.utils.redis_cache import get_redis
        return get_redis()
    except Exception:
        return None


def _cache_key(drug: str) -> str:
    return f"fda:{hashlib.md5(drug.lower().encode()).hexdigest()}"


def get_drug_label(drug_name: str) -> Optional[dict]:
    """
    Fetch the first matching drug label from OpenFDA.
    Tries generic name first, then brand name.
    Returns the raw label dict or None on failure.
    """
    r = _get_redis()
    ck = _cache_key(drug_name)

    if r:
        try:
            cached = r.get(ck)
            if cached:
                return json.loads(cached) if cached != "NULL" else None
        except Exception as exc:
            log.warning("openfda_client.cache_get_failed", drug=drug_name, error=str(exc))
            r = None

    label = _fetch_label(drug_name, field="openfda.generic_name")

    if not label:
        label = _fetch_label(drug_name, field="openfda.substance_name")

    if r:
        try:
            r.setex(ck, TTL, json.dumps(label) if label else "NULL")
        except Exception as exc:
            log.warning("openfda_client.cache_set_failed", drug=drug_name, error=str(exc))

    return label


def _fetch_label(drug_name: str, field: str) -> Optional[dict]:
    try:
        resp = requests.get(
            f"{BASE}/label.json",
            params={"search": f'{field}:"{drug_name}"', "limit": 1},
            timeout=6,
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        results = resp.json().get("results", [])
        return results[0] if results else None
    except Exception as e:
        log.warning("openfda_client.fetch_error", drug=drug_name, field=field, error=str(e))
        return None


def extract_label_data(label: dict) -> dict:
    """
    Extract all clinically relevant fields from an FDA drug label.
    Returns clean structured data for LLM consumption.
    """
    if not label:
        return {}

    def _first(lst) -> str:
        if not lst:
            return ""
        for item in lst:
            if item and item.strip():
                return item.strip()[:2000]
        return ""

    return {
        "dosage_and_administration": _first(label.get("dosage_and_administration", [])),
        "warnings":                  _first(label.get("warnings", []) or label.get("warnings_and_cautions", [])),
        "contraindications":         _first(label.get("contraindications", [])),
        "drug_interactions":         _first(label.get("drug_interactions", [])),
        "indications_and_usage":     _first(label.get("indications_and_usage", [])),
        "adverse_reactions":         _first(label.get("adverse_reactions", [])),
        "use_in_specific_populations": _first(label.get("use_in_specific_populations", [])),
        "overdosage":                _first(label.get("overdosage", [])),
    }


def validate_drug_fda(drug_name: str) -> dict:
    """
    Full OpenFDA lookup for a single drug.

    Returns:
        {
          "found": bool,
          "dosage_and_administration": str,
          "warnings": str,
          "contraindications": str,
          "drug_interactions": str,
          "indications_and_usage": str,
          "adverse_reactions": str,
          "use_in_specific_populations": str,
          "overdosage": str,
        }
    """
    label = get_drug_label(drug_name)
    if not label:
        return {
            "found": False,
            "dosage_and_administration": "",
            "warnings": "",
            "contraindications": "",
            "drug_interactions": "",
            "indications_and_usage": "",
            "adverse_reactions": "",
            "use_in_specific_populations": "",
            "overdosage": "",
        }

    data = extract_label_data(label)
    return {"found": True, **data}
