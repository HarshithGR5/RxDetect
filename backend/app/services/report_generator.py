"""
report_generator.py
Clinical-grade PDF report generator (LOCAL STORAGE ONLY)
Updated to use new RxNorm + OpenFDA drug data structure.
"""

import uuid
import structlog
from datetime import datetime
from pathlib import Path
from jinja2 import Environment, BaseLoader

log = structlog.get_logger(__name__)


# =========================================================
# HTML TEMPLATE
# =========================================================

REPORT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8"/>
<style>
body { font-family: Arial; margin: 40px; color: #1a1a2e; }
h1 { color: #16213e; }
h2 { color: #0f3460; margin-top: 30px; }
table { width: 100%; border-collapse: collapse; }
th { background: #0f3460; color: white; padding: 8px; text-align: left; }
td { padding: 7px; border-bottom: 1px solid #ddd; vertical-align: top; }

.badge { padding: 6px 12px; border-radius: 10px; font-weight: bold; }
.no-discrepancy { background: #d4edda; color: #155724; }
.omission { background: #fff3cd; color: #856404; }
.commission { background: #f8d7da; color: #721c24; }
.inconsistency { background: #fde8d8; color: #7d3c0a; }
.illegibility { background: #e2e3e5; color: #383d41; }

.evidence { background: #f1f4ff; padding: 10px; margin: 5px 0; border-left: 4px solid #0f3460; font-size: 13px; }
.warning-box { background: #fff3cd; padding: 10px; margin: 5px 0; border-left: 4px solid #e0a800; font-size: 13px; }
.danger-box { background: #f8d7da; padding: 10px; margin: 5px 0; border-left: 4px solid #dc3545; font-size: 13px; }
.info-label { font-weight: bold; color: #0f3460; }
.footer { margin-top: 40px; font-size: 12px; color: #666; border-top: 1px solid #ccc; padding-top: 10px; }
</style>
</head>

<body>

<h1>Prescription Discrepancy Report</h1>

<p>
<strong>Report ID:</strong> {{ report_id }} &nbsp;|&nbsp;
<strong>Date:</strong> {{ generated_at }} &nbsp;|&nbsp;
<strong>Prescription ID:</strong> {{ prescription_id }}
</p>

<h2>1. Classification</h2>
<p>
<span class="badge {{ label_class }}">{{ label }}</span>
&nbsp;&nbsp; <strong>Confidence:</strong> {{ confidence_pct }}%
{% if consensus %}&nbsp;&nbsp; <strong>Consensus:</strong> {{ consensus }}{% endif %}
</p>

{% if llm_reason %}
<p><em>{{ llm_reason }}</em></p>
{% endif %}

{% if recommendations %}
<h3>Recommendations</h3>
<ul>
{% for r in recommendations %}
<li>{{ r }}</li>
{% endfor %}
</ul>
{% endif %}

<h2>2. Patient & Prescription Details</h2>
<table>
{% for k, v in fields.items() %}
{% if k not in ["drugs", "illegible_fields", "_completeness"] and v is not none %}
<tr><td style="width:30%; font-weight:bold">{{ k }}</td><td>{{ v }}</td></tr>
{% endif %}
{% endfor %}
</table>

<h2>3. Prescribed Drugs</h2>
<table>
<tr><th>Drug Name</th><th>Dose</th><th>Frequency</th><th>Route</th><th>Duration</th><th>Instructions</th></tr>
{% for d in drugs %}
<tr>
<td>{{ d.drug_name }}</td>
<td>{{ d.dose or "—" }}</td>
<td>{{ d.frequency or "—" }}</td>
<td>{{ d.route or "—" }}</td>
<td>{{ d.duration or "—" }}</td>
<td>{{ d.special_instructions or "—" }}</td>
</tr>
{% endfor %}
</table>

{% if clinical_summary %}
<h2>4. Drug Clinical Summary (RxNorm + OpenFDA)</h2>
{% for d in clinical_summary %}
<div class="evidence">
  <p><span class="info-label">Drug:</span> {{ d.raw_name }}
  {% if d.is_combination %}<em>(combination: {{ d.clean_names | join(' + ') }})</em>{% endif %}</p>

  {% if d.drug_classes %}<p><span class="info-label">Drug Class:</span> {{ d.drug_classes | join(', ') }}</p>{% endif %}

  {% if d.fda_indications %}<p><span class="info-label">FDA Indications:</span> {{ d.fda_indications }}</p>{% endif %}

  {% if d.fda_warnings %}<p><span class="info-label">FDA Warnings:</span> {{ d.fda_warnings }}</p>{% endif %}

  {% if d.fda_contraindications %}<p><span class="info-label">Contraindications:</span> {{ d.fda_contraindications }}</p>{% endif %}

  {% if d.fda_drug_interactions %}<p><span class="info-label">Drug Interactions (FDA label):</span> {{ d.fda_drug_interactions }}</p>{% endif %}

  {% if d.fda_dosage_guidance %}<p><span class="info-label">Dosage Guidance:</span> {{ d.fda_dosage_guidance }}</p>{% endif %}

  {% if d.validation_issues %}
  <p><span class="info-label">Validation Issues:</span></p>
  <ul>{% for i in d.validation_issues %}<li>{{ i }}</li>{% endfor %}</ul>
  {% endif %}
</div>
{% endfor %}
{% endif %}

{% if interactions %}
<h2>5. Drug Interaction Signals</h2>
{% for i in interactions %}
<div class="warning-box">{{ i }}</div>
{% endfor %}
{% endif %}

{% if rules_triggered %}
<h2>6. Rule Engine Findings</h2>
<table>
<tr><th>Rule ID</th><th>Type</th><th>Severity</th><th>Description</th></tr>
{% for r in rules_triggered %}
<tr>
<td>{{ r.rule_id }}</td>
<td>{{ r.type }}</td>
<td>{{ r.severity }}</td>
<td>{{ r.description }}</td>
</tr>
{% endfor %}
</table>
{% endif %}

{% if evidence_sources %}
<h2>7. Clinical Evidence Used</h2>
{% for ev in evidence_sources %}
<div class="evidence">
<strong>{{ ev.source }}</strong>{% if ev.score %} (relevance: {{ "%.2f"|format(ev.score) }}){% endif %}<br/>
{{ ev.excerpt }}
</div>
{% endfor %}
{% endif %}

<div class="footer">
This report is AI-generated using RxNorm, OpenFDA, and clinical guidelines.
Always verify findings with a licensed clinical pharmacist or physician before taking action.
</div>

</body>
</html>
"""


LABEL_CLASS_MAP = {
    "No Discrepancy": "no-discrepancy",
    "Omission":       "omission",
    "Commission":     "commission",
    "Inconsistency":  "inconsistency",
    "Illegibility":   "illegibility",
}


# =========================================================
# CLINICAL SUMMARY FORMATTER
# Converts per_drug validation result into template-friendly format
# =========================================================

def _format_clinical_summary(per_drug: list) -> list:
    """Convert per_drug entries into a clean format for the report template."""
    formatted = []
    for d in (per_drug or []):
        fda = d.get("fda_clinical") or {}

        # Collect drug classes from components
        drug_classes = []
        for comp in (d.get("components") or []):
            rx = comp.get("rxnorm") or {}
            drug_classes.extend(rx.get("drug_classes") or [])

        formatted.append({
            "raw_name":            d.get("raw_name", ""),
            "clean_names":         d.get("clean_names", []),
            "is_combination":      d.get("is_combination", False),
            "drug_classes":        list(set(drug_classes))[:4],
            "fda_indications":     fda.get("indications_and_usage", "")[:400],
            "fda_warnings":        fda.get("warnings", "")[:400],
            "fda_contraindications": fda.get("contraindications", "")[:400],
            "fda_drug_interactions": fda.get("drug_interactions", "")[:600],
            "fda_dosage_guidance": fda.get("dosage_and_administration", "")[:400],
            "validation_issues":   d.get("issues", []),
        })
    return formatted


# =========================================================
# PDF GENERATOR
# =========================================================

def generate_pdf_bytes(prescription_id, extracted_fields, result):

    fields = dict(extracted_fields or {})
    drugs  = fields.get("drugs", [])

    confidence_pct = int(result.confidence * 100)

    # Format clinical summary for template
    clinical_summary = _format_clinical_summary(result.clinical_summary or [])

    # Format interaction signals
    interactions = []
    if hasattr(result, "rules_triggered"):
        for r in (result.rules_triggered or []):
            if r.get("rule_id") == "IC003":
                interactions.append(r.get("description", ""))

    # Also pull from validation interactions
    # (these come from cross-drug FDA label analysis)
    val_interactions = getattr(result, "_raw_interactions", [])
    for ix in val_interactions:
        s = ix.get("summary", "")
        if s and s not in interactions:
            interactions.append(s)

    env = Environment(loader=BaseLoader())
    template = env.from_string(REPORT_TEMPLATE)

    html = template.render(
        report_id=str(uuid.uuid4())[:8],
        generated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        prescription_id=prescription_id,

        label=result.label,
        label_class=LABEL_CLASS_MAP.get(result.label, ""),
        confidence_pct=confidence_pct,
        consensus=result.consensus,

        fields=fields,
        drugs=drugs,

        llm_reason=result.llm_reason,
        recommendations=getattr(result, "recommendations", []),
        flagged_fields=getattr(result, "flagged_fields", []),

        rules_triggered=result.rules_triggered,
        evidence_sources=result.evidence_sources,

        clinical_summary=clinical_summary,
        interactions=interactions,
    )

    try:
        from weasyprint import HTML
        return HTML(string=html).write_pdf()
    except Exception:
        log.warning("report.weasyprint_failed_fallback_html")
        return html.encode("utf-8")


# =========================================================
# LOCAL STORAGE
# =========================================================

def save_pdf_locally(pdf_bytes: bytes, prescription_id: str) -> str:
    """Save PDF locally and return file path."""
    try:
        base_dir = Path("generated_reports")
        base_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{prescription_id}_{int(datetime.utcnow().timestamp())}.pdf"
        file_path = base_dir / filename

        with open(file_path, "wb") as f:
            f.write(pdf_bytes)

        log.info("report.saved_locally", path=str(file_path))
        return str(file_path)

    except Exception as e:
        log.error("report.local_save_failed", error=str(e))
        raise
