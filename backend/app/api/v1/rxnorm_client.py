"""
rxnorm_client.py

RxNorm client:
- Drug name → RxCUI lookup
- Drug properties (name, TTY, synonyms)
- Drug class lookup

NOTE: The RxNorm drug-drug interaction API has been discontinued by NLM.
Drug interaction data is now sourced from OpenFDA drug labels.

Redis note
----------
Uses the shared get_redis() from redis_cache instead of calling
_make_redis_client() on every function call.  The original code created a
new connection pool each time any of get_rxcui / get_drug_properties /
get_drug_classes was called, which caused unnecessary AUTH + connection
commands on Upstash even during idle periods.
"""

import json
import hashlib
import structlog
import requests
from typing import Optional

from app.config import settings

log = structlog.get_logger(__name__)

BASE = settings.rxnorm_base_url
TTL = 60 * 60 * 24 * 7  # 7 days


def _get_redis():
    try:
        from app.utils.redis_cache import get_redis
        return get_redis()
    except Exception:
        return None


def _cache_key(drug: str) -> str:
    return f"rxnorm:{hashlib.md5(drug.lower().encode()).hexdigest()}"


def get_rxcui(drug_name: str) -> Optional[str]:
    """Look up the RxCUI identifier for a drug name."""
    r = _get_redis()
    cache_key = f"rxcui:{_cache_key(drug_name)}"

    if r:
        try:
            cached = r.get(cache_key)
            if cached:
                return cached if cached != "NONE" else None
        except Exception as exc:
            log.warning("rxnorm.cache_get_failed", drug=drug_name, error=str(exc))
            r = None

    try:
        resp = requests.get(
            f"{BASE}/rxcui.json",
            params={"name": drug_name, "search": 1},
            timeout=5,
        )
        resp.raise_for_status()

        data = resp.json()
        rxcui_list = data.get("idGroup", {}).get("rxnormId", [])
        rxcui = rxcui_list[0] if rxcui_list else None

    except Exception as e:
        log.warning("rxnorm.get_rxcui_error", drug=drug_name, error=str(e))
        return None

    if r:
        try:
            r.setex(cache_key, TTL, rxcui if rxcui else "NONE")
        except Exception as exc:
            log.warning("rxnorm.cache_set_failed", drug=drug_name, error=str(exc))

    return rxcui


def get_drug_properties(rxcui: str) -> dict:
    """Fetch drug properties (name, TTY, language) from RxNorm."""
    r = _get_redis()
    cache_key = f"rxprop:{rxcui}"

    if r:
        try:
            cached = r.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as exc:
            log.warning("rxnorm.cache_get_failed", key=cache_key, error=str(exc))
            r = None

    try:
        resp = requests.get(
            f"{BASE}/rxcui/{rxcui}/properties.json",
            timeout=5,
        )
        resp.raise_for_status()
        props = resp.json().get("properties", {})
    except Exception as e:
        log.warning("rxnorm.props_error", rxcui=rxcui, error=str(e))
        props = {}

    if r and props:
        try:
            r.setex(cache_key, TTL, json.dumps(props))
        except Exception as exc:
            log.warning("rxnorm.cache_set_failed", key=cache_key, error=str(exc))

    return props


def get_drug_classes(rxcui: str) -> list[str]:
    """Fetch pharmacological drug classes for a given RxCUI."""
    r = _get_redis()
    cache_key = f"rxclass:{rxcui}"

    if r:
        try:
            cached = r.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as exc:
            log.warning("rxnorm.cache_get_failed", key=cache_key, error=str(exc))
            r = None

    classes = []
    try:
        resp = requests.get(
            f"https://rxnav.nlm.nih.gov/REST/rxclass/class/byRxcui.json",
            params={"rxcui": rxcui, "relaSource": "MESH"},
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
        for entry in data.get("rxclassDrugInfoList", {}).get("rxclassDrugInfo", []):
            cls = entry.get("rxclassMinConceptItem", {}).get("className")
            if cls:
                classes.append(cls)
        classes = list(set(classes))[:5]
    except Exception as e:
        log.warning("rxnorm.class_error", rxcui=rxcui, error=str(e))

    if r:
        try:
            r.setex(cache_key, TTL, json.dumps(classes))
        except Exception as exc:
            log.warning("rxnorm.cache_set_failed", key=cache_key, error=str(exc))

    return classes


def validate_drug(drug_name: str) -> dict:
    """
    Validate a drug via RxNorm.
    Returns RxCUI, canonical name, TTY, and drug classes.
    Drug-drug interactions are NOT fetched here — use OpenFDA labels instead.
    """
    rxcui = get_rxcui(drug_name)

    log.info(
        "rxnorm.validate",
        input=drug_name,
        rxcui=rxcui,
        found=bool(rxcui),
    )

    if not rxcui:
        return {
            "found": False,
            "rxcui": None,
            "name": None,
            "tty": None,
            "drug_classes": [],
        }

    props = get_drug_properties(rxcui)
    drug_classes = get_drug_classes(rxcui)

    return {
        "found": True,
        "rxcui": rxcui,
        "name": props.get("name"),
        "tty": props.get("tty"),
        "drug_classes": drug_classes,
    }
