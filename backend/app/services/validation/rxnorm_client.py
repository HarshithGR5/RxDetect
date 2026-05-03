"""
rxnorm_client.py

RxNorm client:
- Drug name → RxCUI lookup
- Drug properties (name, TTY, synonyms)
- Drug class lookup

NOTE: The RxNorm drug-drug interaction API has been discontinued by NLM.
Drug interaction data is now sourced from OpenFDA drug labels.
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


# ---------------------------------------------------
# Redis
# ---------------------------------------------------

def _get_redis():
    try:
        import redis as redis_lib
        return redis_lib.from_url(settings.redis_url, decode_responses=True)
    except Exception:
        return None


def _cache_key(drug: str) -> str:
    return f"rxnorm:{hashlib.md5(drug.lower().encode()).hexdigest()}"


# ---------------------------------------------------
# RxCUI Lookup
# ---------------------------------------------------

def get_rxcui(drug_name: str) -> Optional[str]:
    """Look up the RxCUI identifier for a drug name."""
    r = _get_redis()
    cache_key = f"rxcui:{_cache_key(drug_name)}"

    if r:
        cached = r.get(cache_key)
        if cached:
            return cached if cached != "NONE" else None

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
        r.setex(cache_key, TTL, rxcui if rxcui else "NONE")

    return rxcui


# ---------------------------------------------------
# Drug Properties
# ---------------------------------------------------

def get_drug_properties(rxcui: str) -> dict:
    """Fetch drug properties (name, TTY, language) from RxNorm."""
    r = _get_redis()
    cache_key = f"rxprop:{rxcui}"

    if r:
        cached = r.get(cache_key)
        if cached:
            return json.loads(cached)

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
        r.setex(cache_key, TTL, json.dumps(props))

    return props


# ---------------------------------------------------
# Drug Classes (from RxNorm)
# Useful for LLM pharmacological class reasoning
# ---------------------------------------------------

def get_drug_classes(rxcui: str) -> list[str]:
    """Fetch pharmacological drug classes for a given RxCUI."""
    r = _get_redis()
    cache_key = f"rxclass:{rxcui}"

    if r:
        cached = r.get(cache_key)
        if cached:
            return json.loads(cached)

    classes = []
    try:
        resp = requests.get(
            f"https://rxnav.nlm.nih.gov/REST/rxclass/class/byRxcui.json",
            params={"rxcui": rxcui, "relaSource": "PHARMACIST"},
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
        r.setex(cache_key, TTL, json.dumps(classes))

    return classes


# ---------------------------------------------------
# Full Validation (NO INTERACTION LOOKUP - discontinued)
# ---------------------------------------------------

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
