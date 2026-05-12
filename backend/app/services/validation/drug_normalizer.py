"""
drug_normalizer.py
Robust drug normalization with:
- Strong cleaning (preserves D3, B12 etc.)
- Brand-column AND generic-column fuzzy matching
- Combination drug handling (multi-word drug names)
- GPT-4 fallback for unknown brand names (brand → generic conversion)
- Safe fallbacks
"""

import re
import json
import pandas as pd
import structlog
from functools import lru_cache
from rapidfuzz import process, fuzz

log = structlog.get_logger(__name__)

CSV_PATH = "data/brand_names.csv"
MATCH_THRESHOLD = 75


# ---------------------------------------------------
# Known multi-word drug component names
# ---------------------------------------------------

MULTI_WORD_DRUGS = sorted([
    # Acids
    "clavulanic acid",
    "valproic acid",
    "folic acid",
    "tranexamic acid",
    "mefenamic acid",
    "fusidic acid",
    "hyaluronic acid",
    "azelaic acid",
    "nalidixic acid",
    "zoledronic acid",
    "ascorbic acid",
    "ursodeoxycholic acid",
    "obeticholic acid",
    "chenodeoxycholic acid",

    # Named combinations / salts
    "co amoxiclav",
    "co trimoxazole",
    "co codamol",
    "potassium clavulanate",
    "sodium valproate",
    "magnesium hydroxide",
    "calcium carbonate",
    "ferrous sulfate",
    "ferrous sulphate",
    "ferrous fumarate",
    "zinc sulfate",
    "zinc sulphate",
    "potassium chloride",
    "sodium bicarbonate",

    # Vitamins — full names
    "vitamin b12",
    "vitamin b1",
    "vitamin b6",
    "vitamin b complex",
    "vitamin d3",
    "vitamin d2",
    "vitamin d",
    "vitamin k",
    "vitamin c",
    "vitamin e",
    "vitamin a",

    # Fatty acids
    "docosahexaenoic acid",
    "eicosapentaenoic acid",
    "alpha lipoic acid",

    # Beta-blockers/combinations
    "metoprolol succinate",
    "metoprolol tartrate",
    "bisoprolol fumarate",
    "atenolol chlorthalidone",

    # Other multi-word generics found in Indian formularies
    "dicycloverine hydrochloride",
    "ondansetron hydrochloride",
    "domperidone maleate",
    "cetirizine hydrochloride",
    "levocetirizine dihydrochloride",
], key=len, reverse=True)


# ---------------------------------------------------
# Load CSV
# ---------------------------------------------------

@lru_cache()
def load_drug_db():
    df = pd.read_csv(CSV_PATH)
    df["brand"]    = df["brand"].fillna("").str.lower().str.strip()
    df["generic"]  = df["generic"].fillna("").str.lower().str.strip()
    df["category"] = df.get("category", "").fillna("").astype(str)
    return df


# ---------------------------------------------------
# Combination drug splitter
# ---------------------------------------------------

def split_combination_generics(generic_str: str) -> list[str]:
    """
    Split a generic drug field into individual drug component names.
    Uses greedy longest-match against known multi-word drug names.
    Falls back to single-word splitting for unknown tokens.
    """
    text = generic_str.lower().strip()
    text = text.replace(",", " ").replace("+", " ").replace("/", " ")
    text = " ".join(text.split())

    result = []
    remaining = text

    while remaining:
        matched = False
        for mw in MULTI_WORD_DRUGS:
            if remaining.startswith(mw):
                result.append(mw.strip())
                remaining = remaining[len(mw):].strip()
                matched = True
                break

        if not matched:
            parts = remaining.split(None, 1)
            result.append(parts[0].strip())
            remaining = parts[1].strip() if len(parts) > 1 else ""

    return [r for r in result if r]


# ---------------------------------------------------
# Clean OCR drug name
# Strips dosage form prefixes and dose amounts
# while PRESERVING drug suffixes like D3, B12, etc.
# ---------------------------------------------------

# Dosage form prefixes to strip
_FORM_PREFIX_RE = re.compile(
    r"^\s*\b(tab|tablet|tabs|cap|capsule|caps|inj|injection|syrup|suspension"
    r"|drops|cream|ointment|gel|patch|soln|solution|inhaler|spray|sachet)\b\s*",
    re.IGNORECASE,
)

# Dose amounts — matches "40 mg", "50 mcg", "500 ml", "10 iu" etc.
# Does NOT match "D3" or "B12" (no space + unit pattern)
_DOSE_AMOUNT_RE = re.compile(
    r"\b\d+\.?\d*\s*(?:mg|mcg|ug|g|ml|iu|units?|mmol|meq|mEq)\b.*",
    re.IGNORECASE,
)

# Trailing standalone numbers (e.g. "aspirin 75" after mcg removal)
_TRAILING_NUM_RE = re.compile(r"\s+\d+\s*$")


def clean_drug_name(name: str) -> str:
    """
    Clean a raw OCR drug name for lookup purposes.
    - Strips leading dosage form (Tab, Cap, Inj …)
    - Strips trailing dose amounts (40 mg, 50 mcg …) but preserves D3, B12
    - Normalises "Vit" → "vitamin"
    - Handles "+" combination separators
    """
    if not name:
        return ""

    text = name.lower()

    # Strip leading dosage form prefix
    text = _FORM_PREFIX_RE.sub("", text)

    # Normalise common abbreviations before splitting on "+"
    text = re.sub(r"\bvit\b", "vitamin", text)

    # Normalise "+" / "&" as space so combination names work
    text = text.replace("+", " ").replace("&", " ")

    # Remove dose amounts (40 mg, 500 mg, 50 mcg …) but keep D3, B12
    text = _DOSE_AMOUNT_RE.sub("", text)

    # Remove any leftover trailing standalone numbers
    text = _TRAILING_NUM_RE.sub("", text)

    # Remove remaining punctuation except hyphens inside words
    text = re.sub(r"[^a-z0-9\s\-]", " ", text)

    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


# ---------------------------------------------------
# GPT brand → generic fallback
# Called when CSV + RxNorm both fail to identify the drug
# ---------------------------------------------------

def _gpt_brand_to_generic(brand_name: str) -> str | None:
    """
    Use GPT-4o to convert an unrecognised brand/trade name to its generic INN.
    Returns the generic name string or None if GPT cannot identify it.
    """
    try:
        from openai import OpenAI
        from app.config import settings

        openai_client = OpenAI(api_key=settings.openai_api_key)

        prompt = (
            f"You are a clinical pharmacist. Convert the drug brand/trade name below to its "
            f"INN (international non-proprietary / generic) name.\n\n"
            f"Brand name: {brand_name}\n\n"
            f"Rules:\n"
            f"- Return ONLY the generic name (INN), nothing else\n"
            f"- If it is a combination product, list the components separated by ' + '\n"
            f"- If you cannot identify this drug with confidence, return exactly: UNKNOWN\n"
            f"- Do NOT include dosage, form, or units\n"
        )

        resp = openai_client.chat.completions.create(
            model=settings.openai_reasoning_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=80,
            temperature=0.0,
        )

        raw = resp.choices[0].message.content.strip()
        if raw.upper() == "UNKNOWN" or not raw:
            log.info("drug.gpt_brand_fallback_unknown", brand=brand_name)
            return None

        log.info("drug.gpt_brand_to_generic", brand=brand_name, generic=raw)
        return raw.lower()

    except Exception as e:
        log.warning("drug.gpt_brand_fallback_error", brand=brand_name, error=str(e))
        return None


# ---------------------------------------------------
# Normalize drug name
# 1. Try brand column (fuzzy)
# 2. Try generic column (fuzzy)
# 3. GPT brand → generic fallback
# 4. Fallback: use cleaned name as-is
# ---------------------------------------------------

def normalize_drug_name(raw_name: str) -> dict:
    """
    Normalize a raw drug name (brand or generic) to generic component(s).

    Returns:
        {
          "found": bool,
          "input": str,
          "cleaned": str,          <- always present
          "normalized_brand": str,
          "generic": list[str],    <- always a list
          "category": str,
          "confidence": int,
          "source": str,
        }
    """
    df = load_drug_db()
    clean_name = clean_drug_name(raw_name)

    # ---------------------------------------------------
    # Pass 1: fuzzy match against brand column
    # ---------------------------------------------------
    brand_list = df["brand"].tolist()
    brand_match, brand_score, brand_idx = process.extractOne(
        clean_name,
        brand_list,
        scorer=fuzz.token_sort_ratio,
    )

    if brand_score >= MATCH_THRESHOLD:
        row = df.iloc[brand_idx]
        generics = split_combination_generics(row["generic"])
        log.info(
            "drug.normalized_via_brand",
            input=raw_name,
            cleaned=clean_name,
            matched_brand=brand_match,
            generic=generics,
            score=brand_score,
            is_combination=len(generics) > 1,
        )
        return {
            "found":            True,
            "input":            raw_name,
            "cleaned":          clean_name,
            "normalized_brand": brand_match,
            "generic":          generics,
            "category":         str(row.get("category") or ""),
            "confidence":       brand_score,
            "source":           "csv_brand",
            "is_combination":   len(generics) > 1,
        }

    # ---------------------------------------------------
    # Pass 2: fuzzy match against generic column
    # This catches prescriptions written using INN/generic
    # names directly (e.g. "Tab Telmisartan 40 Mg")
    # ---------------------------------------------------
    generic_list = df["generic"].tolist()
    gen_match, gen_score, gen_idx = process.extractOne(
        clean_name,
        generic_list,
        scorer=fuzz.token_sort_ratio,
    )

    if gen_score >= MATCH_THRESHOLD:
        row = df.iloc[gen_idx]
        # Split the matched generic row (handles combinations)
        generics = split_combination_generics(gen_match)

        # When the match score is borderline, prefer splitting the cleaned
        # incoming name directly — it preserves "calcium carbonate", "vitamin d3"
        # etc. rather than an imprecisely matched CSV row.
        if gen_score < 90:
            generics = split_combination_generics(clean_name) or generics

        log.info(
            "drug.normalized_via_generic_col",
            input=raw_name,
            cleaned=clean_name,
            matched_generic=gen_match,
            generic=generics,
            score=gen_score,
            is_combination=len(generics) > 1,
        )
        return {
            "found":            True,
            "input":            raw_name,
            "cleaned":          clean_name,
            "normalized_brand": None,
            "generic":          generics,
            "category":         str(row.get("category") or ""),
            "confidence":       gen_score,
            "source":           "csv_generic",
            "is_combination":   len(generics) > 1,
        }

    # ---------------------------------------------------
    # Pass 3: GPT brand → generic fallback
    # Only attempted when CSV lookup fails for both columns.
    # This handles unfamiliar trade names, regional brands, etc.
    # ---------------------------------------------------
    gpt_generic = _gpt_brand_to_generic(raw_name)

    if gpt_generic and gpt_generic != "unknown":
        generics = split_combination_generics(gpt_generic)
        log.info(
            "drug.normalized_via_gpt_fallback",
            input=raw_name,
            cleaned=clean_name,
            gpt_generic=gpt_generic,
            components=generics,
        )
        return {
            "found":            True,
            "input":            raw_name,
            "cleaned":          clean_name,
            "normalized_brand": clean_name,
            "generic":          generics,
            "category":         "",
            "confidence":       70,   # moderate confidence — GPT-inferred
            "source":           "gpt_brand_fallback",
            "is_combination":   len(generics) > 1,
        }

    # ---------------------------------------------------
    # Pass 4: Nothing matched — fall back to cleaned name
    # split on "+" / combination splitter
    # ---------------------------------------------------
    log.warning(
        "drug.not_found_in_csv_or_gpt",
        input=raw_name,
        cleaned=clean_name,
        best_brand_match=brand_match,
        brand_score=brand_score,
        best_generic_match=gen_match,
        generic_score=gen_score,
    )

    # Still attempt combination splitting on the cleaned name
    fallback_generics = split_combination_generics(clean_name) if clean_name else [raw_name.lower().strip()]

    return {
        "found":          False,
        "input":          raw_name,
        "cleaned":        clean_name,
        "generic":        [],
        "fallback":       fallback_generics,
        "best_guess":     brand_match,
        "confidence":     brand_score,
        "is_combination": False,
    }
