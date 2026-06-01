'use client'
import { useState } from 'react'
import Link from 'next/link'
import { ChevronLeft, ChevronRight } from 'lucide-react'

// ── SVG donut data (Slide 1) ──────────────────────────────────────────────────
const R = 108
const CIRC = 2 * Math.PI * R
const CRIT_LEN = (7 / 23) * CIRC
const HIGH_LEN = (12 / 23) * CIRC
const MED_LEN  = (4 / 23) * CIRC

// ── Shared styles ─────────────────────────────────────────────────────────────
const CARD = 'rounded-2xl p-5 bg-[#0d2340]'
const LABEL = 'text-xs font-semibold uppercase tracking-widest text-teal-400'
const STAT_NUM = 'text-4xl font-black leading-none'

// ─────────────────────────────────────────────────────────────────────────────
// Slide 1 — Rule Engine Coverage
// ─────────────────────────────────────────────────────────────────────────────
function Slide1() {
  const barData = [
    { type: 'Omission',      count: 11, pct: 85, color: '#f59e0b' },
    { type: 'Commission',    count: 5,  pct: 38, color: '#ef4444' },
    { type: 'Inconsistency', count: 4,  pct: 31, color: '#a78bfa' },
    { type: 'Illegibility',  count: 3,  pct: 23, color: '#64748b' },
  ]

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row gap-6">
        {/* Bar chart */}
        <div className={`${CARD} flex-1`}>
          <p className="text-sm font-semibold text-slate-300 mb-4">Rules by Discrepancy Type</p>
          <div className="space-y-4">
            {barData.map(d => (
              <div key={d.type}>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-300 font-medium">{d.type}</span>
                  <span className="text-slate-400">{d.count} rules</span>
                </div>
                <div className="h-3 rounded-full bg-white/5 overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-700"
                    style={{ width: `${d.pct}%`, background: d.color }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* SVG donut */}
        <div className={`${CARD} flex flex-col items-center`} style={{ minWidth: 220 }}>
          <p className="text-sm font-semibold text-slate-300 mb-4 self-start">Rules by Severity</p>
          <svg viewBox="0 0 280 240" style={{ width: '100%', maxWidth: 280 }}>
            <g transform={`rotate(-90 140 120)`}>
              <circle cx="140" cy="120" r={R} fill="none" stroke="#ef4444" strokeWidth="44"
                strokeDasharray={`${CRIT_LEN} ${CIRC}`} strokeDashoffset="0" />
              <circle cx="140" cy="120" r={R} fill="none" stroke="#f97316" strokeWidth="44"
                strokeDasharray={`${HIGH_LEN} ${CIRC}`} strokeDashoffset={`${-CRIT_LEN}`} />
              <circle cx="140" cy="120" r={R} fill="none" stroke="#eab308" strokeWidth="44"
                strokeDasharray={`${MED_LEN} ${CIRC}`} strokeDashoffset={`${-(CRIT_LEN + HIGH_LEN)}`} />
            </g>
            <text x="140" y="113" textAnchor="middle" fill="#f1f5f9" fontSize="28" fontWeight="700">23</text>
            <text x="140" y="134" textAnchor="middle" fill="#64748b" fontSize="12">total rules</text>
            <circle cx="30" cy="200" r="6" fill="#ef4444" />
            <text x="42" y="205" fill="#e2e8f0" fontSize="13">CRITICAL: 7</text>
            <circle cx="140" cy="200" r="6" fill="#f97316" />
            <text x="152" y="205" fill="#e2e8f0" fontSize="13">HIGH: 12</text>
            <circle cx="30" cy="222" r="6" fill="#eab308" />
            <text x="42" y="227" fill="#e2e8f0" fontSize="13">MEDIUM: 4</text>
          </svg>
        </div>
      </div>

      {/* Stat tiles */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className={`${CARD} text-center`}>
          <p className={`${STAT_NUM} text-teal-400`}>23</p>
          <p className="text-xs text-slate-500 mt-1">total rules</p>
        </div>
        <div className={`${CARD} text-center`}>
          <p className={`${STAT_NUM} text-red-400`}>7</p>
          <p className="text-xs text-slate-500 mt-1">CRITICAL severity</p>
        </div>
        <div className={`${CARD} text-center`}>
          <p className={`${STAT_NUM} text-amber-400`}>11</p>
          <p className="text-xs text-slate-500 mt-1">omission rules</p>
        </div>
        <div className={`${CARD} text-center`}>
          <p className={`${STAT_NUM} text-purple-400`}>4</p>
          <p className="text-xs text-slate-500 mt-1">discrepancy types</p>
        </div>
      </div>

      <p className="text-xs text-slate-600">
        Source: rules/engine.py · omission_rules.py · commission_rules.py · consistency_rules.py · illegibility_rules.py
      </p>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Slide 2 — 3-Layer Confidence Scoring
// ─────────────────────────────────────────────────────────────────────────────
function Slide2() {
  const scenarios = [
    { label: 'CRITICAL rule hit',       conf: 0.95, color: '#ef4444' },
    { label: 'HIGH + LLM agree',        conf: 0.87, color: '#f97316' },
    { label: 'HIGH + LLM disagree',     conf: 0.82, color: '#f97316' },
    { label: 'LLM + interaction boost', conf: 0.80, color: '#2dd4bf' },
    { label: 'LLM drives alone',        conf: 0.70, color: '#2dd4bf' },
    { label: 'LLM + ML agree',          conf: 0.74, color: '#a78bfa' },
  ]

  const features = [
    'has_patient_name', 'has_patient_age', 'has_doctor_name', 'has_signature',
    'has_date', 'has_diagnosis', 'drug_count', 'missing_dose_count',
    'missing_freq_count', 'missing_duration_count', 'has_invalid_freq', 'ocr_confidence',
    'illegible_field_count', 'drug_not_in_rxnorm', 'dose_error_count', 'interaction_count',
  ]

  return (
    <div className="space-y-6">
      {/* Pipeline cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className={`${CARD} border-l-4 border-red-500`}>
          <p className="text-xs font-bold uppercase tracking-widest text-red-400 mb-2">Layer 1 — Rule Engine</p>
          <p className="text-3xl font-black text-white leading-none mb-1">0.95</p>
          <p className="text-xs text-slate-500 mb-3">fixed on CRITICAL hit</p>
          <ul className="space-y-1 text-xs text-slate-400">
            <li>CRITICAL → overrides all layers</li>
            <li>HIGH → 0.82 + 0.05 if LLM agrees</li>
            <li>Illegibility → LLM can override if &gt;0.60</li>
          </ul>
        </div>
        <div className={`${CARD} border-l-4 border-teal-400`}>
          <p className="text-xs font-bold uppercase tracking-widest text-teal-400 mb-2">Layer 2 — LLM (GPT-4o)</p>
          <p className="text-3xl font-black text-white leading-none mb-1">0.50–0.98</p>
          <p className="text-xs text-slate-500 mb-3">variable, probabilistic</p>
          <ul className="space-y-1 text-xs text-slate-400">
            <li>Drives score when no CRITICAL/HIGH</li>
            <li>Interaction detected → +0.05 boost</li>
            <li>LLM &gt;0.85 can override a HIGH rule</li>
          </ul>
        </div>
        <div className={`${CARD} border-l-4 border-purple-400`}>
          <p className="text-xs font-bold uppercase tracking-widest text-purple-400 mb-2">Layer 3 — XGBoost ML</p>
          <p className="text-3xl font-black text-white leading-none mb-1">±0.04</p>
          <p className="text-xs text-slate-500 mb-3">optional fine-tuning</p>
          <ul className="space-y-1 text-xs text-slate-400">
            <li>ML agrees with LLM → +0.04</li>
            <li>ML disagrees with LLM → −0.03</li>
            <li>16 features · feature_extractor.py</li>
          </ul>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row gap-4">
        {/* Scenario bars */}
        <div className={`${CARD} flex-1`}>
          <p className="text-sm font-semibold text-slate-300 mb-4">Confidence by Decision Scenario</p>
          <div className="space-y-3">
            {scenarios.map(s => (
              <div key={s.label}>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-300">{s.label}</span>
                  <span className="font-mono font-semibold" style={{ color: s.color }}>
                    {Math.round(s.conf * 100)}%
                  </span>
                </div>
                <div className="h-2 rounded-full bg-white/5 overflow-hidden">
                  <div className="h-full rounded-full" style={{ width: `${s.conf * 100}%`, background: s.color }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Features grid */}
        <div className={`${CARD} flex-1`}>
          <p className="text-sm font-semibold text-slate-300 mb-4">XGBoost — 16 Input Features</p>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
            {features.map(f => (
              <p key={f} className="text-xs text-slate-400 font-mono">{f}</p>
            ))}
          </div>
        </div>
      </div>

      <p className="text-xs text-slate-600">
        Source: aggregator.py · ml/feature_extractor.py · ml/predictor.py
      </p>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Slide 3 — 27-Parameter Weighted Error Rate
// ─────────────────────────────────────────────────────────────────────────────
function Slide3() {
  const categories = [
    { name: 'Patient Information',       color: '#2dd4bf' },
    { name: 'Prescriber Information',    color: '#f59e0b' },
    { name: 'Drug Details',              color: '#a78bfa' },
    { name: 'Safety Checks',             color: '#f87171' },
    { name: 'Prescription Completeness', color: '#34d399' },
  ]

  const thresholds = [
    { range: '0%',    label: 'No Errors',  sub: 'All pass',        color: '#22c55e' },
    { range: '1–15%', label: 'Low Risk',   sub: 'Minor issues',    color: '#34d399' },
    { range: '16–40%',label: 'Moderate',   sub: 'Review advised',  color: '#f59e0b' },
    { range: '41–65%',label: 'High Risk',  sub: 'Review required', color: '#f97316' },
    { range: '>65%',  label: 'Critical',   sub: 'Do not dispense', color: '#ef4444' },
  ]

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row gap-4">
        {/* Formula card */}
        <div className={`${CARD} flex-1`}>
          <p className="text-sm font-semibold text-slate-300 mb-4">Error Rate Formula</p>
          <div className="space-y-3">
            <div>
              <p className="text-xs text-slate-500 mb-0.5">Numerator (Error Score)</p>
              <p className="text-lg font-bold text-white">Failed + (Partial × 0.5)</p>
            </div>
            <div className="h-px bg-white/8" />
            <div>
              <p className="text-xs text-slate-500 mb-0.5">Denominator (Evaluable)</p>
              <p className="text-lg font-bold text-white">Total Params − N/A Params</p>
            </div>
            <div className="h-px bg-white/8" />
            <div>
              <p className="text-xs font-semibold text-teal-400 mb-0.5">Result</p>
              <p className="text-xl font-black text-teal-400">Error Score ÷ Evaluable × 100</p>
            </div>
          </div>
          <div className="grid grid-cols-3 gap-2 mt-4">
            <div className="rounded-xl bg-white/4 text-center py-2">
              <p className="text-2xl font-black text-teal-400">27</p>
              <p className="text-xs text-slate-500">parameters</p>
            </div>
            <div className="rounded-xl bg-white/4 text-center py-2">
              <p className="text-2xl font-black text-amber-400">5</p>
              <p className="text-xs text-slate-500">categories</p>
            </div>
            <div className="rounded-xl bg-white/4 text-center py-2">
              <p className="text-2xl font-black text-purple-400">0.98</p>
              <p className="text-xs text-slate-500">conf. cap</p>
            </div>
          </div>
        </div>

        {/* Category cards */}
        <div className={`${CARD} flex-1`}>
          <p className="text-sm font-semibold text-slate-300 mb-4">Checklist Categories</p>
          <div className="space-y-2">
            {categories.map(c => (
              <div
                key={c.name}
                className="rounded-xl py-2.5 px-3"
                style={{ background: '#0b1929', borderLeft: `4px solid ${c.color}` }}
              >
                <p className="text-sm font-semibold" style={{ color: c.color }}>{c.name}</p>
              </div>
            ))}
          </div>
          <p className="text-xs text-slate-600 mt-3">
            27 parameters evaluated per prescription — N/A excluded from denominator.
          </p>
        </div>
      </div>

      {/* Severity thresholds */}
      <div className={CARD}>
        <p className="text-sm font-semibold text-slate-300 mb-4">Severity Thresholds — Rate-to-Risk Mapping</p>
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
          {thresholds.map(t => (
            <div
              key={t.range}
              className="rounded-xl text-center py-3 border-2"
              style={{ borderColor: t.color, background: '#0b1929' }}
            >
              <p className="text-base font-black" style={{ color: t.color }}>{t.range}</p>
              <p className="text-xs font-semibold mt-0.5" style={{ color: t.color }}>{t.label}</p>
              <p className="text-xs text-slate-500 mt-0.5">{t.sub}</p>
            </div>
          ))}
        </div>
      </div>

      <p className="text-xs text-slate-600">
        Source: PrescriptionErrorRate.tsx · ocr/confidence.py · ClinicalChecklistModal.tsx
      </p>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Page wrapper
// ─────────────────────────────────────────────────────────────────────────────
const SLIDES = [
  {
    id: 1,
    title: 'Rule Engine Coverage',
    sub:   '23 deterministic rules · 4 discrepancy types · 3 severity tiers',
    component: Slide1,
  },
  {
    id: 2,
    title: '3-Layer Confidence Scoring',
    sub:   'Rule Engine · LLM Reasoning · XGBoost ML — final score capped at 0.98',
    component: Slide2,
  },
  {
    id: 3,
    title: '27-Parameter Weighted Error Rate',
    sub:   'Custom formula · partial errors = 0.5 weight · N/A excluded from denominator',
    component: Slide3,
  },
]

export default function ResultsPage() {
  const [current, setCurrent] = useState(0)

  const slide = SLIDES[current]
  const SlideComp = slide.component

  return (
    <div className="min-h-screen bg-[#050d1a] text-white">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">

        {/* Back link */}
        <Link href="/dashboard" className="inline-flex items-center gap-1.5 text-sm text-slate-400 hover:text-teal-400 transition mb-6">
          <ChevronLeft size={16} />
          Back to Dashboard
        </Link>

        {/* Section label */}
        <p className="text-xs font-semibold uppercase tracking-widest text-teal-400 mb-1">
          Results Analysis
        </p>

        {/* Slide title */}
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight mb-1">
          {slide.title}
        </h1>
        <p className="text-sm text-slate-400 mb-6">{slide.sub}</p>

        {/* Tab navigation */}
        <div className="flex gap-2 mb-6 border-b border-white/8 pb-0">
          {SLIDES.map((s, i) => (
            <button
              key={s.id}
              onClick={() => setCurrent(i)}
              className={[
                'text-sm font-semibold px-4 py-2.5 rounded-t-lg border-b-2 transition-colors',
                i === current
                  ? 'text-teal-400 border-teal-400 bg-teal-400/5'
                  : 'text-slate-500 border-transparent hover:text-slate-300',
              ].join(' ')}
            >
              Slide {s.id}
            </button>
          ))}
        </div>

        {/* Slide content */}
        <SlideComp />

        {/* Prev / Next */}
        <div className="flex items-center justify-between mt-8 pt-6 border-t border-white/8">
          <button
            onClick={() => setCurrent(c => Math.max(0, c - 1))}
            disabled={current === 0}
            className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition"
          >
            <ChevronLeft size={16} /> Previous
          </button>
          <span className="text-xs text-slate-600">
            {current + 1} / {SLIDES.length}
          </span>
          <button
            onClick={() => setCurrent(c => Math.min(SLIDES.length - 1, c + 1))}
            disabled={current === SLIDES.length - 1}
            className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition"
          >
            Next <ChevronRight size={16} />
          </button>
        </div>

      </div>
    </div>
  )
}
