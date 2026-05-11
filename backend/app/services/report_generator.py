"""
report_generator.py
Clinical-grade PDF report generator using reportlab (pure Python, no GTK/WeasyPrint).
"""

import uuid
import structlog
from datetime import datetime
from pathlib import Path
from io import BytesIO

log = structlog.get_logger(__name__)


# =========================================================
# COLOURS & STYLES
# =========================================================

COLORS = {
    "navy":        (0.04, 0.24, 0.36),   # #0B3C5D
    "teal":        (0.18, 0.77, 0.71),   # #2EC4B6
    "white":       (1.0,  1.0,  1.0),
    "light_grey":  (0.95, 0.96, 0.98),
    "mid_grey":    (0.70, 0.73, 0.78),
    "dark_grey":   (0.20, 0.22, 0.26),
    "green":       (0.08, 0.56, 0.23),
    "amber":       (0.80, 0.50, 0.04),
    "red":         (0.64, 0.11, 0.15),
    "amber_light": (1.0,  0.97, 0.88),
    "red_light":   (0.99, 0.90, 0.91),
    "green_light": (0.90, 0.97, 0.92),
}

LABEL_COLOR = {
    "No Discrepancy": "green",
    "Omission":       "amber",
    "Commission":     "red",
    "Inconsistency":  "red",
    "Illegibility":   "mid_grey",
}

SEVERITY_COLOR = {
    "CRITICAL": (0.64, 0.11, 0.15),
    "HIGH":     (0.80, 0.50, 0.04),
    "MEDIUM":   (0.04, 0.45, 0.63),
    "LOW":      (0.18, 0.77, 0.71),
}


def _rgb(key: str):
    return COLORS.get(key, (0.5, 0.5, 0.5))


def _clean_label(raw) -> str:
    """
    Safely extract a human-readable label string from an enum or plain string.
    Handles:
      - DiscrepancyLabel.omission  →  "Omission"
      - "Omission"                 →  "Omission"
      - DiscrepancyLabel enum obj  →  uses .value
    """
    if hasattr(raw, "value"):
        return str(raw.value)
    s = str(raw)
    # Strip "ClassName.member" prefix
    if "." in s:
        s = s.split(".")[-1]
    return s.replace("_", " ").title()


# =========================================================
# HELPERS
# =========================================================

def _format_clinical_summary(per_drug: list) -> list:
    formatted = []
    for d in (per_drug or []):
        fda = d.get("fda_clinical") or {}
        drug_classes = []
        for comp in (d.get("components") or []):
            rx = comp.get("rxnorm") or {}
            drug_classes.extend(rx.get("drug_classes") or [])
        formatted.append({
            "raw_name":              d.get("raw_name", ""),
            "clean_names":           d.get("clean_names", []),
            "is_combination":        d.get("is_combination", False),
            "drug_classes":          list(set(drug_classes))[:4],
            "fda_indications":       (fda.get("indications_and_usage", "") or "")[:400],
            "fda_warnings":          (fda.get("warnings", "") or "")[:400],
            "fda_contraindications": (fda.get("contraindications", "") or "")[:400],
            "fda_drug_interactions": (fda.get("drug_interactions", "") or "")[:600],
            "fda_dosage_guidance":   (fda.get("dosage_and_administration", "") or "")[:400],
            "validation_issues":     d.get("issues", []),
        })
    return formatted


# =========================================================
# FIELD LABEL MAP — human-readable display names
# =========================================================

FIELD_LABELS = {
    "patient_name":           "Patient Name",
    "patient_age":            "Patient Age",
    "patient_gender":         "Gender",
    "patient_weight":         "Weight",
    "date":                   "Prescription Date",
    "doctor_name":            "Doctor Name",
    "doctor_qualification":   "Qualification",
    "doctor_registration_no": "Registration No.",
    "hospital_clinic":        "Hospital / Clinic",
    "clinic_address":         "Address",
    "contact_details":        "Contact",
    "signature_present":      "Signature Present",
    "diagnosis":              "Diagnosis",
    "allergy_history":        "Allergy History",
    "previous_medical_history": "Medical History",
    "overall_legibility_score": "Legibility Score",
    "_completeness":          "Completeness",
}


def _field_label(key: str) -> str:
    return FIELD_LABELS.get(key, key.replace("_", " ").title())


# =========================================================
# PDF GENERATOR
# =========================================================

def generate_pdf_bytes(prescription_id: str, extracted_fields: dict, result) -> bytes:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib import colors as rl_colors
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            HRFlowable, KeepTogether
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

    except ImportError as e:
        log.error("report_generator.reportlab_missing", error=str(e))
        raise RuntimeError("reportlab is not installed. Run: pip install reportlab")

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm,
        topMargin=18*mm,  bottomMargin=18*mm,
    )

    W, H = A4
    styles = getSampleStyleSheet()

    # ── Custom paragraph styles ──────────────────────────────────────────────
    def _style(name, **kw):
        defaults = dict(fontName="Helvetica", fontSize=9, leading=13, textColor=rl_colors.HexColor("#333344"))
        defaults.update(kw)
        return ParagraphStyle(name, parent=styles["Normal"], **defaults)

    S = {
        "h1":      _style("h1",  fontName="Helvetica-Bold", fontSize=16, leading=20, textColor=rl_colors.HexColor("#0B3C5D"), spaceAfter=4),
        "h2":      _style("h2",  fontName="Helvetica-Bold", fontSize=12, leading=16, textColor=rl_colors.HexColor("#0B3C5D"), spaceBefore=12, spaceAfter=4),
        "h3":      _style("h3",  fontName="Helvetica-Bold", fontSize=10, leading=14, textColor=rl_colors.HexColor("#1a3350"), spaceBefore=6, spaceAfter=2),
        "body":    _style("body", fontSize=9, leading=13),
        "small":   _style("small", fontSize=8, leading=11, textColor=rl_colors.HexColor("#666677")),
        "label":   _style("label", fontName="Helvetica-Bold", fontSize=8, textColor=rl_colors.HexColor("#0B3C5D")),
        "hdr":     _style("hdr",  fontName="Helvetica-Bold", fontSize=8, textColor=rl_colors.white),
        "meta":    _style("meta",  fontSize=8, leading=11, textColor=rl_colors.HexColor("#888899"), alignment=TA_RIGHT),
        "center":  _style("center", alignment=TA_CENTER),
        "italic":  _style("italic", fontName="Helvetica-Oblique", fontSize=9),
        "footer":  _style("footer", fontSize=7, leading=10, textColor=rl_colors.HexColor("#aaaaaa"), alignment=TA_CENTER),
        "cl_yes":  _style("cl_yes", fontName="Helvetica-Bold", fontSize=9, textColor=rl_colors.HexColor("#1E8F3A"), alignment=TA_CENTER),
        "cl_no":   _style("cl_no",  fontName="Helvetica-Bold", fontSize=9, textColor=rl_colors.HexColor("#A01C24"), alignment=TA_CENTER),
        "cl_na":   _style("cl_na",  fontName="Helvetica-Bold", fontSize=8, textColor=rl_colors.HexColor("#888899"), alignment=TA_CENTER),
    }

    def navy():  return rl_colors.HexColor("#0B3C5D")
    def teal():  return rl_colors.HexColor("#2EC4B6")
    def lgrey(): return rl_colors.HexColor("#F3F5F8")
    def mgrey(): return rl_colors.HexColor("#C0C4CC")

    def _hr(): return HRFlowable(width="100%", thickness=0.5, color=mgrey(), spaceAfter=6)
    def _sp(h=4): return Spacer(1, h*mm)

    story = []

    # ── Header ───────────────────────────────────────────────────────────────
    report_id  = str(uuid.uuid4())[:8].upper()
    generated  = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    # Clean the label — strip enum class prefix if present
    label_str   = _clean_label(getattr(result, "label", "Unknown"))
    confidence  = getattr(result, "confidence", 0.0)
    llm_reason  = getattr(result, "llm_reason", "")
    recs        = getattr(result, "recommendations", []) or []
    rules       = getattr(result, "rules_triggered", []) or []
    evidence    = getattr(result, "evidence_sources", []) or []
    clinical_s  = _format_clinical_summary((getattr(result, "clinical_summary", None) or []))
    checklist   = getattr(result, "checklist_items", None) or []

    fields      = dict(extracted_fields or {})
    drugs       = fields.get("drugs", [])
    therapy     = fields.get("therapy_suggestions", [])

    lc          = LABEL_COLOR.get(label_str, "mid_grey")
    label_color = rl_colors.HexColor(
        {"green": "#1E8F3A", "amber": "#CC8008", "red": "#A01C24", "mid_grey": "#555566"}.get(lc, "#555566")
    )

    header_data = [[
        Paragraph("<b>RxDetect</b>", _style("brand", fontName="Helvetica-Bold", fontSize=18, textColor=navy())),
        Paragraph(
            f"Report ID: <b>{report_id}</b><br/>"
            f"Generated: {generated}<br/>"
            f"Prescription: {prescription_id}",
            S["meta"]
        ),
    ]]
    header_tbl = Table(header_data, colWidths=["55%", "45%"])
    header_tbl.setStyle(TableStyle([
        ("ALIGN", (0, 0), (0, 0), "LEFT"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, -1), lgrey()),
        ("ROUNDEDCORNERS", [6, 6, 6, 6]),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (0, -1), 14),
        ("RIGHTPADDING", (-1, 0), (-1, -1), 14),
    ]))
    story.append(header_tbl)
    story.append(_sp(5))
    story.append(_hr())

    # ── Section 1: Classification ────────────────────────────────────────────
    story.append(Paragraph("1. Classification", S["h2"]))

    conf_pct   = f"{int(confidence * 100)}%"
    class_data = [[
        Paragraph(f"<b>{label_str}</b>", _style("badge", fontName="Helvetica-Bold", fontSize=14, textColor=label_color)),
        Paragraph(f"AI Confidence: <b>{conf_pct}</b>", S["body"]),
    ]]
    class_tbl = Table(class_data, colWidths=["55%", "45%"])
    class_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), lgrey()),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (0, -1), 14),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(class_tbl)
    story.append(_sp(3))

    if llm_reason:
        story.append(Paragraph("<b>Clinical Reasoning:</b>", S["label"]))
        story.append(Paragraph(llm_reason, S["italic"]))
        story.append(_sp(2))

    if recs:
        story.append(Paragraph("<b>Recommendations:</b>", S["label"]))
        for r in recs:
            story.append(Paragraph(f"• {r}", S["body"]))
    story.append(_hr())

    # ── Section 2: Patient & Prescription Details ────────────────────────────
    story.append(Paragraph("2. Patient & Prescription Details", S["h2"]))

    skip_keys = {"drugs", "illegible_fields", "therapy_suggestions", "_completeness"}
    detail_rows = []
    for k, v in fields.items():
        if k in skip_keys or v is None or v == "" or v == []:
            continue
        detail_rows.append([
            Paragraph(_field_label(k), S["label"]),
            Paragraph(str(v), S["body"]),
        ])

    if detail_rows:
        detail_tbl = Table(detail_rows, colWidths=["35%", "65%"])
        detail_tbl.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.25, mgrey()),
            ("BACKGROUND", (0, 0), (0, -1), lgrey()),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [rl_colors.white, lgrey()]),
        ]))
        story.append(detail_tbl)
    story.append(_hr())

    # ── Section 3: Prescribed Drugs ──────────────────────────────────────────
    story.append(Paragraph("3. Prescribed Drugs", S["h2"]))

    drug_header = [
        Paragraph("<b>Drug Name</b>", S["hdr"]),
        Paragraph("<b>Generic</b>",   S["hdr"]),
        Paragraph("<b>Dose</b>",      S["hdr"]),
        Paragraph("<b>Freq</b>",      S["hdr"]),
        Paragraph("<b>Route</b>",     S["hdr"]),
        Paragraph("<b>Duration</b>",  S["hdr"]),
    ]
    drug_rows = [drug_header]
    for d in drugs:
        drug_rows.append([
            Paragraph(d.get("drug_name", ""), S["body"]),
            Paragraph(d.get("generic_name") or "—", S["small"]),
            Paragraph(d.get("dose") or "—", S["body"]),
            Paragraph(d.get("frequency") or "—", S["body"]),
            Paragraph(d.get("route") or "—", S["body"]),
            Paragraph(d.get("duration") or "—", S["body"]),
        ])

    if len(drug_rows) > 1:
        drug_tbl = Table(drug_rows, colWidths=["22%", "16%", "14%", "16%", "14%", "18%"])
        drug_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), navy()),
            ("TEXTCOLOR",  (0, 0), (-1, 0), rl_colors.white),
            ("GRID",  (0, 0), (-1, -1), 0.25, mgrey()),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [rl_colors.white, lgrey()]),
        ]))
        story.append(drug_tbl)
    story.append(_hr())

    # ── Section 4: Therapy Suggestions ───────────────────────────────────────
    if therapy:
        story.append(Paragraph("4. Non-Drug Therapy Suggestions", S["h2"]))
        for t in therapy:
            tp   = str(t.get("type", "other")).replace("_", " ").title()
            desc = t.get("description", "")
            story.append(Paragraph(f"<b>{tp}:</b> {desc}", S["body"]))
        story.append(_hr())
        section_offset = 1
    else:
        section_offset = 0

    # ── Section 5: Drug Clinical Summary ─────────────────────────────────────
    if clinical_s:
        n = 4 + section_offset
        story.append(Paragraph(f"{n}. Drug Clinical Summary (RxNorm + OpenFDA)", S["h2"]))
        for d in clinical_s:
            combo = f" (combination: {' + '.join(d['clean_names'])})" if d["is_combination"] else ""
            story.append(Paragraph(f"<b>{d['raw_name']}</b>{combo}", S["h3"]))
            if d["drug_classes"]:
                story.append(Paragraph(f"<b>Class:</b> {', '.join(d['drug_classes'])}", S["body"]))
            for lbl, key in [
                ("Indications", "fda_indications"),
                ("Warnings",    "fda_warnings"),
                ("Contraindications", "fda_contraindications"),
                ("Drug Interactions", "fda_drug_interactions"),
                ("Dosage Guidance",   "fda_dosage_guidance"),
            ]:
                val = d.get(key, "")
                if val:
                    story.append(Paragraph(f"<b>{lbl}:</b> {val}", S["body"]))
            if d["validation_issues"]:
                for issue in d["validation_issues"]:
                    story.append(Paragraph(f"⚠ {issue}", _style("warn", textColor=rl_colors.HexColor("#A01C24"), fontSize=8)))
        story.append(_hr())
        section_offset += 1

    # ── Section 6: Rule Engine Findings ──────────────────────────────────────
    if rules:
        n = 5 + section_offset
        story.append(Paragraph(f"{n}. Rule Engine Findings", S["h2"]))
        rule_header = [
            Paragraph("<b>Rule</b>",     S["hdr"]),
            Paragraph("<b>Type</b>",     S["hdr"]),
            Paragraph("<b>Severity</b>", S["hdr"]),
            Paragraph("<b>Description</b>", S["hdr"]),
        ]
        rule_rows = [rule_header]
        for r in rules:
            sev = r.get("severity", "")
            sev_color = rl_colors.Color(*SEVERITY_COLOR.get(sev, (0.5, 0.5, 0.5)))
            rule_rows.append([
                Paragraph(r.get("rule_id", ""), S["small"]),
                Paragraph(r.get("type", ""), S["body"]),
                Paragraph(sev, _style(f"sev_{sev}", textColor=sev_color, fontName="Helvetica-Bold", fontSize=8)),
                Paragraph(r.get("description", ""), S["body"]),
            ])
        rule_tbl = Table(rule_rows, colWidths=["12%", "18%", "14%", "56%"])
        rule_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), navy()),
            ("TEXTCOLOR",  (0, 0), (-1, 0), rl_colors.white),
            ("GRID", (0, 0), (-1, -1), 0.25, mgrey()),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [rl_colors.white, lgrey()]),
        ]))
        story.append(rule_tbl)
        story.append(_hr())
        section_offset += 1

    # ── Section 7: Clinical Evidence ─────────────────────────────────────────
    if evidence:
        n = 6 + section_offset
        story.append(Paragraph(f"{n}. Clinical Evidence Used", S["h2"]))
        for ev in evidence:
            score_val = ev.get("score") or 0
            score_str = f"  (relevance: {score_val:.0%})" if score_val else ""
            story.append(Paragraph(f"<b>{ev.get('source', 'Unknown')}</b>{score_str}", S["label"]))
            story.append(Paragraph(ev.get("excerpt", ""), S["body"]))
            story.append(_sp(2))
        story.append(_hr())
        section_offset += 1

    # ── Section 8: 27-Parameter Clinical Checklist (Sl.No / Parameter / YES / NO) ──
    if checklist:
        n = 7 + section_offset
        story.append(Paragraph(f"{n}. 27-Parameter Clinical Checklist", S["h2"]))

        # Header row — navy background with white text
        cl_header = [
            Paragraph("<b>Sl.No</b>",      S["hdr"]),
            Paragraph("<b>Parameter</b>",  S["hdr"]),
            Paragraph("<b>YES</b>",        S["hdr"]),
            Paragraph("<b>NO</b>",         S["hdr"]),
            Paragraph("<b>N/A</b>",        S["hdr"]),
        ]
        cl_rows = [cl_header]

        for idx, item in enumerate(checklist, 1):
            res = (item.get("result") or "na").lower()
            yes_cell = Paragraph("✓", S["cl_yes"]) if res == "yes"     else Paragraph("",  S["body"])
            no_cell  = Paragraph("✗", S["cl_no"])  if res == "no"      else Paragraph("",  S["body"])
            na_cell  = Paragraph("–", S["cl_na"])  if res in ("na", "partial") else Paragraph("", S["body"])
            cl_rows.append([
                Paragraph(str(idx), S["small"]),
                Paragraph(item.get("parameter", ""), S["body"]),
                yes_cell,
                no_cell,
                na_cell,
            ])

        cl_tbl = Table(cl_rows, colWidths=["7%", "63%", "10%", "10%", "10%"])
        cl_tbl.setStyle(TableStyle([
            # Header row: navy background, white text
            ("BACKGROUND", (0, 0), (-1, 0), navy()),
            ("TEXTCOLOR",  (0, 0), (-1, 0), rl_colors.white),
            ("ALIGN",      (0, 0), (-1, 0), "CENTER"),
            # Data rows
            ("GRID", (0, 0), (-1, -1), 0.25, mgrey()),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [rl_colors.white, lgrey()]),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            # Center the YES/NO/N/A columns
            ("ALIGN", (2, 1), (4, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(cl_tbl)
        story.append(_hr())

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(_sp(3))
    story.append(Paragraph(
        "This report is AI-generated using RxNorm, OpenFDA, and clinical guidelines. "
        "Always verify findings with a licensed clinical pharmacist or physician before taking action.",
        S["footer"]
    ))

    doc.build(story)
    return buf.getvalue()


# =========================================================
# LOCAL STORAGE
# =========================================================

def save_pdf_locally(pdf_bytes: bytes, prescription_id: str) -> str:
    try:
        base_dir = Path("generated_reports")
        base_dir.mkdir(parents=True, exist_ok=True)

        filename  = f"{prescription_id}_{int(datetime.utcnow().timestamp())}.pdf"
        file_path = base_dir / filename

        with open(file_path, "wb") as f:
            f.write(pdf_bytes)

        log.info("report.saved_locally", path=str(file_path))
        return str(file_path)

    except Exception as e:
        log.error("report.local_save_failed", error=str(e))
        raise
