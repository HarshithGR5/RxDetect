"""
drug_normalizer.py
Robust drug normalization with:
- Strong cleaning
- Fuzzy matching
- Proper combination drug handling (multi-word drug names)
- Safe fallbacks
"""

import pandas as pd
import structlog
from functools import lru_cache
from rapidfuzz import process, fuzz

log = structlog.get_logger(__name__)

CSV_PATH = "data/brand_names.csv"
MATCH_THRESHOLD = 75


# ---------------------------------------------------
# Known multi-word drug component names
# These must be matched as a unit, not split by spaces
# ---------------------------------------------------

MULTI_WORD_DRUGS = sorted([
    # Acids (common drug suffixes that are one name)
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

    # Vitamins
    "vitamin b12",
    "vitamin b1",
    "vitamin b6",
    "vitamin b complex",
    "vitamin d3",
    "vitamin d2",
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
], key=len, reverse=True)  # longest first for greedy matching


# ---------------------------------------------------
# Load CSV
# ---------------------------------------------------

@lru_cache()
def load_drug_db():
    df = pd.read_csv(CSV_PATH)
    df["brand"] = df["brand"].fillna("").str.lower().str.strip()
    df["generic"] = df["generic"].fillna("").str.lower().str.strip()
    df["category"] = df.get("category", "").fillna("").astype(str)
    return df


# ---------------------------------------------------
# Combination drug splitter (FIXED)
# Handles "amoxicillin clavulanic acid" → ["amoxicillin", "clavulanic acid"]
# Handles "ibuprofen paracetamol" → ["ibuprofen", "paracetamol"]
# ---------------------------------------------------

def split_combination_generics(generic_str: str) -> list[str]:
    """
    Split a generic drug field into individual drug component names.
    Uses greedy longest-match against known multi-word drug names.
    Falls back to single-word splitting for unknown tokens.
    """
    text = generic_str.lower().strip()
    # Normalize separators
    text = text.replace(",", " ").replace("+", " ").replace("/", " ")
    text = " ".join(text.split())  # collapse whitespace

    result = []
    remaining = text

    while remaining:
        matched = False
        # Try greedy longest match on known multi-word drugs
        for mw in MULTI_WORD_DRUGS:
            if remaining.startswith(mw):
                result.append(mw.strip())
                remaining = remaining[len(mw):].strip()
                matched = True
                break

        if not matched:
            # Take next single word as one drug component
            parts = remaining.split(None, 1)
            result.append(parts[0].strip())
            remaining = parts[1].strip() if len(parts) > 1 else ""

    return [r for r in result if r]


# ---------------------------------------------------
# Clean OCR drug name
# ---------------------------------------------------

def clean_drug_name(name: str) -> str:
    if not name:
        return ""

    import re

    name = name.lower()
    # Remove dosage amounts (50mg, 500, 75/10)
    name = re.sub(r"\d+.*", "", name)
    # Remove form prefixes
    name = re.sub(r"\b(tab|tablet|cap|capsule|inj|injection|syrup|suspension|drops|cream|ointment|gel|patch)\b", "", name)
    # Remove punctuation
    name = re.sub(r"[^a-z\s]", " ", name)
    # Normalize spaces
    name = re.sub(r"\s+", " ", name)

    return name.strip()


# ---------------------------------------------------
# Normalize
# ---------------------------------------------------

def normalize_drug_name(raw_name: str) -> dict:
    """
    Normalize a raw drug name (possibly brand name) to generic component(s).

    Returns:
        {
          "found": bool,
          "input": str,
          "normalized_brand": str,
          "generic": list[str],   <- always a list, handles combinations
          "category": str,
          "confidence": int,
          "source": str,
        }
    """
    df = load_drug_db()
    clean_name = clean_drug_name(raw_name)
    brand_list = df["brand"].tolist()

    match, score, idx = process.extractOne(
        clean_name,
        brand_list,
        scorer=fuzz.token_sort_ratio
    )

    if score >= MATCH_THRESHOLD:
        row = df.iloc[idx]
        generic_raw = row["generic"]

        # Properly split combination drugs
        generics = split_combination_generics(generic_raw)

        log.info(
            "drug.normalized",
            input=raw_name,
            cleaned=clean_name,
            matched_brand=match,
            generic=generics,
            score=score,
            is_combination=len(generics) > 1,
        )

        return {
            "found": True,
            "input": raw_name,
            "normalized_brand": match,
            "generic": generics,
            "category": str(row.get("category") or ""),
            "confidence": score,
            "source": "local_csv",
            "is_combination": len(generics) > 1,
        }

    # Not found in brand CSV — try treating the raw name itself as a generic
    log.warning(
        "drug.not_found_in_csv",
        input=raw_name,
        cleaned=clean_name,
        best_match=match,
        score=score,
    )

    return {
        "found": False,
        "input": raw_name,
        "cleaned": clean_name,
        "generic": [],
        "best_guess": match,
        "confidence": score,
        "is_combination": False,
    }
