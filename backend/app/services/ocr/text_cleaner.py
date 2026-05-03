"""
text_cleaner.py

Normalises and cleans extracted prescription fields.
- Fixes common OCR character substitutions
- Normalises drug name variants and abbreviations
- Standardises frequency / route abbreviations
"""

import re
from ftfy import fix_text
from unidecode import unidecode
from rapidfuzz import process, fuzz


# ---------------------------------------------------
# DRUG ALIASES
# ---------------------------------------------------

DRUG_ALIASES: dict[str, str] = {
    "pcm": "Paracetamol",
    "paracetmol": "Paracetamol",
    "paracatamol": "Paracetamol",
    "acetaminophen": "Paracetamol",
    "amox": "Amoxicillin",
    "amoxycillin": "Amoxicillin",
    "augmentin": "Amoxicillin-Clavulanate",
    "mtx": "Methotrexate",
    "pred": "Prednisolone",
    "metformin hcl": "Metformin",
    "atorva": "Atorvastatin",
    "pan": "Pantoprazole",
    "pan 40": "Pantoprazole 40mg",
    "omez": "Omeprazole",
    "crocin": "Paracetamol",
    "dolo": "Paracetamol",
    "azee": "Azithromycin",
    "azithro": "Azithromycin",
    "cipro": "Ciprofloxacin",
    "levo": "Levofloxacin",
}


# ---------------------------------------------------
# FREQUENCY NORMALISATION
# ---------------------------------------------------

FREQUENCY_MAP: dict[str, str] = {
    "od": "OD",
    "once daily": "OD",
    "1-0-0": "OD",

    "bd": "BD",
    "twice daily": "BD",
    "bid": "BD",
    "b.i.d": "BD",
    "1-0-1": "BD",

    "tds": "TDS",
    "tid": "TDS",
    "t.i.d": "TDS",
    "thrice daily": "TDS",
    "three times daily": "TDS",
    "1-1-1": "TDS",

    "qid": "QID",
    "four times daily": "QID",
    "1-1-1-1": "QID",

    "sos": "SOS",
    "prn": "SOS",
    "as needed": "SOS",

    "hs": "HS",
    "at bedtime": "HS",
    "night": "HS",

    "stat": "STAT",
    "immediately": "STAT",
}


# ---------------------------------------------------
# ROUTE NORMALISATION
# ---------------------------------------------------

ROUTE_MAP: dict[str, str] = {
    "oral": "PO",
    "by mouth": "PO",
    "po": "PO",

    "iv": "IV",
    "intravenous": "IV",

    "im": "IM",
    "intramuscular": "IM",

    "sc": "SC",
    "subcutaneous": "SC",

    "sl": "SL",
    "sublingual": "SL",

    "topical": "Topical",

    "inhaler": "Inhalation",
    "inh": "Inhalation",

    "nasal": "Intranasal",

    "rectal": "PR",
    "pr": "PR",

    "ear": "Otic",
    "eye": "Ophthalmic",
}


# ---------------------------------------------------
# KNOWN DRUGS (FOR FUZZY MATCH)
# ---------------------------------------------------

KNOWN_DRUGS: list[str] = list({v for v in DRUG_ALIASES.values()}) + [
    "Amoxicillin", "Azithromycin", "Ciprofloxacin", "Metformin", "Atorvastatin",
    "Amlodipine", "Losartan", "Aspirin", "Warfarin", "Metoprolol",
    "Omeprazole", "Pantoprazole", "Ranitidine", "Prednisolone", "Dexamethasone",
    "Insulin", "Glibenclamide", "Lisinopril", "Hydrochlorothiazide",
]


# ---------------------------------------------------
# OCR FIXES
# ---------------------------------------------------

def _fix_ocr_chars(text: str) -> str:
    if not text:
        return text

    replacements = [
        (r"\b0(?=[a-zA-Z])", "O"),
        (r"(?<=[a-zA-Z])0\b", "o"),
        (r"\bl\b", "1"),
        (r"rn(?=[a-z])", "m"),
    ]

    for pattern, repl in replacements:
        text = re.sub(pattern, repl, text)

    return text


# ---------------------------------------------------
# DRUG NAME CLEANING
# ---------------------------------------------------

def clean_drug_name(name: str) -> str:
    if not name:
        return name

    text = fix_text(name)
    text = unidecode(text).strip()
    text = _fix_ocr_chars(text)

    lower = text.lower().strip()

    # Exact alias
    if lower in DRUG_ALIASES:
        return DRUG_ALIASES[lower]

    # Fuzzy match
    match = process.extractOne(
        lower,
        [k.lower() for k in KNOWN_DRUGS],
        scorer=fuzz.WRatio
    )

    if match and match[1] >= 88:
        idx = [k.lower() for k in KNOWN_DRUGS].index(match[0])
        return KNOWN_DRUGS[idx]

    return text.title()


# ---------------------------------------------------
# NORMALISERS
# ---------------------------------------------------

def normalise_frequency(freq: str | None) -> str | None:
    if not freq:
        return None

    lower = freq.lower().strip()
    return FREQUENCY_MAP.get(lower, freq.upper())


def normalise_route(route: str | None) -> str | None:
    if not route:
        return None

    lower = route.lower().strip()
    return ROUTE_MAP.get(lower, route.title())


# ---------------------------------------------------
# MAIN CLEAN FUNCTION
# ---------------------------------------------------

def clean_extracted_fields(fields: dict) -> dict:

    if not fields:
        return fields

    cleaned = dict(fields)

    # ---------------------------
    # Clean drugs
    # ---------------------------
    cleaned_drugs = []

    for drug in cleaned.get("drugs", []) or []:
        d = dict(drug)

        d["drug_name"] = clean_drug_name(d.get("drug_name", ""))
        d["frequency"] = normalise_frequency(d.get("frequency"))
        d["route"] = normalise_route(d.get("route"))

        if d.get("dose"):
            d["dose"] = re.sub(r"\s+", " ", d["dose"]).strip()

        cleaned_drugs.append(d)

    cleaned["drugs"] = cleaned_drugs

    # ---------------------------
    # Clean names
    # ---------------------------
    if cleaned.get("patient_name"):
        cleaned["patient_name"] = cleaned["patient_name"].title().strip()

    if cleaned.get("doctor_name"):
        cleaned["doctor_name"] = cleaned["doctor_name"].title().strip()

    # ---------------------------
    # 🔥 IMPORTANT FIX (YOU WERE MISSING THIS)
    # ---------------------------
    cleaned["illegible_fields"] = list(set(cleaned.get("illegible_fields", [])))

    return cleaned