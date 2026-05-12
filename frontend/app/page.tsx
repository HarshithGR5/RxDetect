'use client'
import Link from 'next/link'
import { motion } from 'framer-motion'
import {
  ShieldCheck, ScanLine, Brain, ClipboardCheck,
  ArrowRight, CheckCircle2, AlertTriangle, Users, Lock, FileText,
  ChevronRight, Zap, Database, BarChart3, Activity,
} from 'lucide-react'

/* ── Animation helpers ────────────────────────────────────────────────────── */
// Direct props — avoids variant propagation hydration mismatch in Next.js 14
function fadeInUp(delay = 0) {
  return {
    initial:    { opacity: 0, y: 24 },
    animate:    { opacity: 1, y: 0 },
    transition: { duration: 0.55, delay, ease: [0.22, 1, 0.36, 1] as [number,number,number,number] },
  }
}

function fadeInView(delay = 0) {
  return {
    initial:    { opacity: 0, y: 20 },
    whileInView:{ opacity: 1, y: 0 },
    viewport:   { once: true, margin: '-60px' as const },
    transition: { duration: 0.5, delay, ease: 'easeOut' },
  }
}

/* ── Static data ──────────────────────────────────────────────────────────── */
const FEATURES = [
  {
    icon: ScanLine,
    title: 'Vision OCR Extraction',
    desc: 'GPT-4o Vision reads handwritten and printed prescriptions, extracting all structured fields with clinical-grade accuracy.',
    iconBg: 'bg-blue-500/10 text-blue-400',
  },
  {
    icon: ClipboardCheck,
    title: 'Rule-Based Safety Engine',
    desc: '20+ deterministic clinical rules catch omissions, commission errors, illegibility, and internal inconsistencies instantly.',
    iconBg: 'bg-teal-500/10 text-teal-400',
  },
  {
    icon: Brain,
    title: 'Clinical AI Reasoning',
    desc: 'RxNorm + OpenFDA drug data feeds a GPT-4o reasoning chain that validates dosage, interactions, and contraindications.',
    iconBg: 'bg-indigo-500/10 text-indigo-400',
  },
  {
    icon: FileText,
    title: 'Audit-Ready PDF Reports',
    desc: 'Structured PDF reports with full clinical evidence, rule findings, 27-param checklist, and pharmacist feedback.',
    iconBg: 'bg-emerald-500/10 text-emerald-400',
  },
]

const PIPELINE = [
  { step: '01', label: 'Upload',   desc: 'Image or PDF',      icon: ScanLine },
  { step: '02', label: 'Extract',  desc: 'AI-OCR fields',     icon: Zap },
  { step: '03', label: 'Validate', desc: 'RxNorm + FDA',      icon: Database },
  { step: '04', label: 'Analyse',  desc: 'Rule engine + LLM', icon: Brain },
  { step: '05', label: 'Report',   desc: 'Audit PDF',         icon: BarChart3 },
]

const DISCREPANCY_TYPES = [
  { label: 'No Discrepancy', dot: 'bg-emerald-400', ring: 'ring-emerald-500/30 bg-emerald-500/10 text-emerald-300', desc: 'Prescription is clinically sound' },
  { label: 'Omission',       dot: 'bg-amber-400',   ring: 'ring-amber-500/30 bg-amber-500/10 text-amber-300',       desc: 'Required field or drug is missing' },
  { label: 'Commission',     dot: 'bg-red-400',      ring: 'ring-red-500/30 bg-red-500/10 text-red-300',             desc: 'Incorrect drug, dose, or route' },
  { label: 'Inconsistency',  dot: 'bg-orange-400',   ring: 'ring-orange-500/30 bg-orange-500/10 text-orange-300',   desc: 'Conflicting information detected' },
  { label: 'Illegibility',   dot: 'bg-slate-400',    ring: 'ring-slate-500/30 bg-slate-500/10 text-slate-300',       desc: 'Unreadable — manual review needed' },
]

const TRUST_BADGES = [
  { icon: ShieldCheck,  label: 'Clinical-grade validation', sub: 'WHO & FDA aligned checks' },
  { icon: Lock,         label: 'Secure by design',          sub: 'JWT auth, role-based access' },
  { icon: Users,        label: 'Built for clinical teams',  sub: 'Pharmacist & admin workflows' },
  { icon: CheckCircle2, label: 'Evidence-backed decisions', sub: 'Every finding has a source' },
]

/* ── Dashboard mockup (pure CSS animations — no framer-motion Infinity) ───── */
function DashboardMockup() {
  return (
    <motion.div {...fadeInUp(0.3)} className="relative w-full max-w-sm mx-auto lg:max-w-none">
      <div className="relative rounded-2xl border border-white/10 bg-slate-900/80 backdrop-blur-xl shadow-2xl overflow-hidden">
        {/* Window chrome */}
        <div className="bg-slate-800/60 border-b border-white/5 px-4 py-3 flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full bg-red-400/70" />
          <div className="w-2.5 h-2.5 rounded-full bg-amber-400/70" />
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-400/70" />
          <span className="ml-2 text-xs text-slate-500 font-mono">analysis · 3c77ff91</span>
        </div>

        <div className="p-4 space-y-3">
          {/* Classification */}
          <div className="flex items-start justify-between gap-2">
            <div>
              <p className="text-xs text-slate-500 uppercase tracking-widest mb-1">Classification</p>
              <span className="inline-flex items-center gap-1.5 bg-amber-500/15 border border-amber-500/30 text-amber-300 text-sm font-bold px-2.5 py-1 rounded-lg">
                <AlertTriangle size={12} />
                Omission
              </span>
            </div>
            <div className="text-right">
              <p className="text-xs text-slate-500 mb-1">AI Confidence</p>
              <p className="text-xl font-bold text-white">87%</p>
              <div className="w-20 h-1.5 bg-slate-700 rounded-full mt-1 ml-auto">
                <div className="h-full bg-teal-400 rounded-full" style={{ width: '87%' }} />
              </div>
            </div>
          </div>

          {/* Drugs */}
          <div className="border-t border-white/5 pt-3">
            <p className="text-xs text-slate-500 uppercase tracking-widest mb-2">Prescribed Drugs</p>
            <div className="space-y-1.5">
              {[
                { name: 'Syp Relent Plus',      dose: '2.5 ml', route: 'Oral',       ok: true },
                { name: 'Nasivion Saline Drop',  dose: '1 drop', route: 'Intranasal', ok: true },
                { name: 'Syp Moxclav DS',        dose: '3 ml',   route: 'Oral',       ok: false },
              ].map(d => (
                <div key={d.name} className="flex items-center gap-2 bg-slate-800/40 rounded-lg px-2.5 py-1.5">
                  <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${d.ok ? 'bg-emerald-400' : 'bg-amber-400'}`} />
                  <span className="text-xs text-slate-200 flex-1 min-w-0 truncate">{d.name}</span>
                  <span className="text-xs text-slate-500">{d.dose}</span>
                  <span className="text-[10px] bg-slate-700 text-slate-400 px-1.5 py-0.5 rounded">{d.route}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Rule findings */}
          <div className="border-t border-white/5 pt-3">
            <p className="text-xs text-slate-500 uppercase tracking-widest mb-2">Rule Findings</p>
            <div className="space-y-1.5">
              {[
                { id: 'OM003', severity: 'HIGH',   desc: 'Prescribing doctor name is missing' },
                { id: 'OM006', severity: 'MEDIUM', desc: 'Diagnosis / indication is missing' },
              ].map(r => (
                <div key={r.id} className="flex items-start gap-2 bg-slate-800/40 rounded-lg px-2.5 py-1.5">
                  <span className="text-[10px] font-mono bg-slate-700 text-slate-400 px-1.5 py-0.5 rounded flex-shrink-0">{r.id}</span>
                  <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded flex-shrink-0 ${r.severity === 'HIGH' ? 'bg-amber-500/20 text-amber-300' : 'bg-blue-500/20 text-blue-300'}`}>{r.severity}</span>
                  <span className="text-xs text-slate-300 leading-tight">{r.desc}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Checklist summary */}
          <div className="border-t border-white/5 pt-3 flex items-center justify-between">
            <span className="text-xs text-slate-500">27-param checklist</span>
            <div className="flex items-center gap-1">
              <span className="text-xs text-emerald-400 font-semibold">19 ✓</span>
              <span className="text-xs text-slate-500 mx-1">/</span>
              <span className="text-xs text-red-400 font-semibold">5 ✗</span>
              <span className="text-xs text-slate-500 mx-1">/</span>
              <span className="text-xs text-slate-400">3 N/A</span>
            </div>
          </div>
        </div>
      </div>

      {/* Floating badges — CSS animation avoids framer-motion hydration mismatch */}
      <div className="absolute -top-4 -right-4 bg-emerald-500/15 border border-emerald-500/30
                      backdrop-blur-xl rounded-xl px-3 py-2 hidden sm:flex items-center gap-2
                      shadow-lg animate-bounce"
        style={{ animationDuration: '3s' }}>
        <Activity size={13} className="text-emerald-400" />
        <span className="text-xs font-semibold text-emerald-300">Pipeline active</span>
      </div>

      <div className="absolute -bottom-4 -left-4 bg-teal-500/15 border border-teal-500/30
                      backdrop-blur-xl rounded-xl px-3 py-2 hidden sm:flex items-center gap-2
                      shadow-lg animate-bounce"
        style={{ animationDuration: '4s', animationDelay: '0.5s' }}>
        <ShieldCheck size={13} className="text-teal-400" />
        <span className="text-xs font-semibold text-teal-300">RxNorm validated</span>
      </div>
    </motion.div>
  )
}

/* ── Page ─────────────────────────────────────────────────────────────────── */
export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#050d1a] text-slate-100 overflow-x-hidden">

      {/* ── NAVBAR ──────────────────────────────────────────────────────── */}
      <nav className="fixed top-0 left-0 right-0 z-50 border-b border-white/5 bg-[#050d1a]/80 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 bg-gradient-to-br from-teal-400 to-teal-600 rounded-lg flex items-center justify-center shadow-lg shadow-teal-500/30">
              <ShieldCheck size={14} className="text-white" />
            </div>
            <span className="font-bold text-white text-base tracking-tight">RxDetect</span>
          </div>
          <div className="flex items-center gap-2">
            <Link href="/login"
              className="text-sm text-slate-400 hover:text-white px-4 py-2 rounded-xl hover:bg-white/5 transition min-h-[40px] flex items-center">
              Sign in
            </Link>
            <Link href="/signup"
              className="text-sm font-semibold bg-gradient-to-r from-teal-500 to-teal-400 hover:from-teal-400 hover:to-teal-300 text-slate-950 px-4 py-2 rounded-xl shadow shadow-teal-500/25 hover:shadow-teal-500/40 transition flex items-center gap-1.5 min-h-[40px]">
              Get Started <ArrowRight size={13} />
            </Link>
          </div>
        </div>
      </nav>

      {/* ── HERO ────────────────────────────────────────────────────────── */}
      <section className="relative min-h-screen flex items-center pt-14 overflow-hidden">
        {/* Background — plain div, no motion scroll hook to avoid hydration mismatch */}
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute inset-0"
            style={{ background: 'radial-gradient(ellipse 80% 60% at 50% -10%, rgba(46,196,182,0.15) 0%, transparent 60%)' }} />
          <div className="absolute top-1/4 -left-32 w-96 h-96 bg-[#1B3A6B]/40 rounded-full blur-[100px]" />
          <div className="absolute top-1/3 -right-32 w-80 h-80 bg-teal-500/15 rounded-full blur-[120px]" />
          <div className="absolute inset-0 opacity-[0.015]"
            style={{ backgroundImage: 'linear-gradient(rgba(255,255,255,0.8) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.8) 1px, transparent 1px)', backgroundSize: '48px 48px' }} />
        </div>

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 py-20 lg:py-28 w-full">
          <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">

            {/* Left — direct animate props, no variant propagation */}
            <div>
              <motion.div {...fadeInUp(0)}>
                <span className="inline-flex items-center gap-2 border border-teal-500/30 bg-teal-500/10 text-teal-300 text-xs font-semibold px-3 py-1.5 rounded-full mb-6 backdrop-blur-sm">
                  <span className="w-1.5 h-1.5 bg-teal-400 rounded-full animate-pulse" />
                  Clinical Decision Support System
                </span>
              </motion.div>

              <motion.h1 {...fadeInUp(0.1)}
                className="text-4xl sm:text-5xl lg:text-6xl font-bold leading-[1.08] tracking-tight mb-5 text-white">
                RxDetect —{' '}
                <span className="bg-gradient-to-r from-teal-400 to-teal-300 bg-clip-text text-transparent">
                  AI-Powered
                </span>
                <br />
                Prescription
                <br />
                Discrepancy
                <br />
                Detection System
              </motion.h1>

              <motion.p {...fadeInUp(0.2)}
                className="text-base sm:text-lg text-slate-400 leading-relaxed mb-8 max-w-lg">
                RxDetect combines deterministic rule-based checks, clinical AI reasoning, and real-time
                drug validation to detect discrepancies in handwritten and printed prescriptions.
              </motion.p>

              <motion.div {...fadeInUp(0.3)} className="flex flex-col sm:flex-row gap-3 mb-10">
                <Link href="/signup"
                  className="inline-flex items-center justify-center gap-2 bg-gradient-to-r from-teal-500 to-teal-400 hover:from-teal-400 hover:to-teal-300 text-slate-950 font-semibold px-6 py-3.5 rounded-xl shadow-lg shadow-teal-500/25 hover:shadow-teal-500/40 transition-all min-h-[48px]">
                  Start Validating <ArrowRight size={16} />
                </Link>
                <Link href="/login"
                  className="inline-flex items-center justify-center gap-2 border border-white/10 hover:border-white/20 bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white font-medium px-6 py-3.5 rounded-xl transition-all min-h-[48px]">
                  Sign In
                </Link>
              </motion.div>

              <motion.div {...fadeInUp(0.4)} className="flex flex-wrap gap-3">
                {[
                  { icon: Database,     label: 'FDA + RxNorm Data' },
                  { icon: ShieldCheck,  label: 'HIPAA-aware Design' },
                  { icon: Activity,     label: 'Real-time Analysis' },
                  { icon: CheckCircle2, label: 'Audit-ready Reports' },
                ].map(b => (
                  <span key={b.label} className="inline-flex items-center gap-1.5 text-xs text-slate-400 border border-white/10 bg-white/5 px-3 py-1.5 rounded-full">
                    <b.icon size={11} className="text-teal-400" />
                    {b.label}
                  </span>
                ))}
              </motion.div>
            </div>

            {/* Right */}
            <DashboardMockup />
          </div>

          {/* Stats bar */}
          <motion.div {...fadeInUp(0.5)}
            className="mt-20 border border-white/5 bg-white/3 backdrop-blur-sm rounded-2xl grid grid-cols-3 divide-x divide-white/5 overflow-hidden">
            {[
              { val: '5',    label: 'Discrepancy Types',   sub: 'Fully covered' },
              { val: '27',   label: 'Clinical Parameters', sub: 'Per prescription' },
              { val: '100%', label: 'Audit Trail',         sub: 'Every analysis logged' },
            ].map(s => (
              <div key={s.label} className="text-center py-5 px-3">
                <p className="text-2xl sm:text-3xl font-bold bg-gradient-to-r from-teal-400 to-teal-300 bg-clip-text text-transparent">{s.val}</p>
                <p className="text-xs sm:text-sm text-white mt-0.5 font-medium">{s.label}</p>
                <p className="text-[10px] sm:text-xs text-slate-500 mt-0.5">{s.sub}</p>
              </div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* ── FEATURES ────────────────────────────────────────────────────── */}
      <section className="relative py-20 sm:py-28">
        <div className="absolute inset-0 pointer-events-none"
          style={{ background: 'radial-gradient(ellipse 60% 40% at 50% 100%, rgba(27,58,107,0.35) 0%, transparent 60%)' }} />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-14">
            <motion.p {...fadeInView(0)} className="text-xs font-semibold uppercase tracking-[0.2em] text-teal-400 mb-3">Core Capabilities</motion.p>
            <motion.h2 {...fadeInView(0.05)} className="text-3xl sm:text-4xl font-bold text-white">Built for clinical accuracy</motion.h2>
            <motion.p {...fadeInView(0.1)} className="text-slate-400 mt-4 max-w-xl mx-auto text-sm sm:text-base">
              Every prescription is processed through a multi-layer AI pipeline designed with pharmacists and clinical safety in mind.
            </motion.p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {FEATURES.map((f, i) => (
              <motion.div key={f.title} {...fadeInView(i * 0.08)}
                className="group border border-white/8 bg-white/3 hover:bg-white/6 rounded-2xl p-6 transition-all duration-300 cursor-default">
                <div className={`w-11 h-11 rounded-xl flex items-center justify-center mb-4 ${f.iconBg}`}>
                  <f.icon size={20} />
                </div>
                <h3 className="font-semibold text-white mb-2 text-sm sm:text-base">{f.title}</h3>
                <p className="text-sm text-slate-400 leading-relaxed">{f.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── HOW IT WORKS ────────────────────────────────────────────────── */}
      <section className="py-20 sm:py-28 relative">
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-[#1B3A6B]/20 to-transparent pointer-events-none" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-14">
            <motion.p {...fadeInView(0)} className="text-xs font-semibold uppercase tracking-[0.2em] text-teal-400 mb-3">How It Works</motion.p>
            <motion.h2 {...fadeInView(0.05)} className="text-3xl sm:text-4xl font-bold text-white">From upload to report in seconds</motion.h2>
          </div>

          <div className="hidden sm:block">
            <div className="relative flex items-start justify-between max-w-4xl mx-auto">
              <div className="absolute top-6 left-12 right-12 h-px bg-gradient-to-r from-teal-500/30 via-[#1B3A6B]/60 to-teal-500/30" />
              {PIPELINE.map((p, i) => (
                <motion.div key={p.step} {...fadeInView(i * 0.1)}
                  className="relative flex flex-col items-center text-center flex-1 group">
                  <div className="relative z-10 w-12 h-12 bg-gradient-to-br from-[#1B3A6B] to-[#0f2548] border border-teal-500/30 group-hover:border-teal-400/60 text-white rounded-xl flex items-center justify-center mb-4 shadow-lg transition-all duration-300">
                    <p.icon size={18} className="text-teal-300" />
                  </div>
                  <p className="text-[10px] font-bold text-teal-400 tracking-widest mb-1">{p.step}</p>
                  <p className="font-semibold text-white text-sm">{p.label}</p>
                  <p className="text-xs text-slate-500 mt-0.5">{p.desc}</p>
                </motion.div>
              ))}
            </div>
          </div>

          <div className="sm:hidden flex flex-col gap-3 max-w-sm mx-auto">
            {PIPELINE.map((p, i) => (
              <motion.div key={p.step} {...fadeInView(i * 0.08)}
                className="flex items-center gap-4 border border-white/8 bg-white/3 rounded-xl px-4 py-3">
                <div className="w-10 h-10 bg-gradient-to-br from-[#1B3A6B] to-[#0f2548] border border-teal-500/30 text-teal-300 rounded-xl flex items-center justify-center flex-shrink-0">
                  <p.icon size={16} />
                </div>
                <div>
                  <p className="font-semibold text-white text-sm">{p.label}</p>
                  <p className="text-xs text-slate-500">{p.desc}</p>
                </div>
                {i < PIPELINE.length - 1 && <ChevronRight size={14} className="text-slate-600 ml-auto flex-shrink-0" />}
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── DISCREPANCY TYPES ───────────────────────────────────────────── */}
      <section className="py-20 sm:py-28">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-12">
            <motion.p {...fadeInView(0)} className="text-xs font-semibold uppercase tracking-[0.2em] text-teal-400 mb-3">Detection Coverage</motion.p>
            <motion.h2 {...fadeInView(0.05)} className="text-3xl sm:text-4xl font-bold text-white">Every discrepancy type, covered</motion.h2>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            {DISCREPANCY_TYPES.map((t, i) => (
              <motion.div key={t.label} {...fadeInView(i * 0.07)}
                className={`border rounded-2xl p-4 sm:p-5 text-center ring-1 ${t.ring}`}>
                <div className={`w-2 h-2 rounded-full ${t.dot} mx-auto mb-3`} />
                <p className="font-bold text-sm text-white">{t.label}</p>
                <p className="text-xs mt-1.5 text-slate-400 leading-tight">{t.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── TRUST ───────────────────────────────────────────────────────── */}
      <section className="py-20 sm:py-28 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-[#1B3A6B] via-[#1a3560] to-[#0f2548]" />
        <div className="absolute inset-0"
          style={{ background: 'radial-gradient(ellipse 70% 80% at 20% 50%, rgba(46,196,182,0.15) 0%, transparent 50%)' }} />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-12">
            <motion.h2 {...fadeInView(0)} className="text-3xl sm:text-4xl font-bold text-white">Designed for clinical trust</motion.h2>
            <motion.p {...fadeInView(0.05)} className="text-blue-200 mt-3 text-sm sm:text-base">Built to the standards healthcare professionals expect</motion.p>
          </div>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {TRUST_BADGES.map((t, i) => (
              <motion.div key={t.label} {...fadeInView(i * 0.08)}
                className="bg-white/8 hover:bg-white/12 border border-white/10 hover:border-white/20 rounded-2xl p-5 transition-all duration-300 group">
                <div className="w-10 h-10 bg-white/10 rounded-xl flex items-center justify-center mb-4 group-hover:bg-teal-500/20 transition-colors">
                  <t.icon size={18} className="text-teal-300" />
                </div>
                <p className="font-semibold text-white text-sm sm:text-base">{t.label}</p>
                <p className="text-xs sm:text-sm text-blue-200 mt-1">{t.sub}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ─────────────────────────────────────────────────────────── */}
      <section className="relative py-24 sm:py-32 overflow-hidden">
        <div className="absolute inset-0 pointer-events-none"
          style={{ background: 'radial-gradient(ellipse 60% 70% at 50% 50%, rgba(46,196,182,0.1) 0%, transparent 60%)' }} />
        <div className="relative max-w-3xl mx-auto px-4 sm:px-6 text-center">
          <motion.div {...fadeInView(0)}>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-teal-400 mb-4">Get Started Today</p>
            <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold text-white mb-5 leading-tight">
              Ready to validate your
              <br />
              <span className="bg-gradient-to-r from-teal-400 to-teal-300 bg-clip-text text-transparent">first prescription?</span>
            </h2>
            <p className="text-slate-400 mb-10 text-sm sm:text-base max-w-xl mx-auto">
              Join clinical teams using RxDetect to catch errors before they reach patients. No setup required — start analysing immediately.
            </p>
            <Link href="/signup"
              className="inline-flex items-center gap-2 bg-gradient-to-r from-teal-500 to-teal-400 hover:from-teal-400 hover:to-teal-300 text-slate-950 font-semibold text-base px-8 py-4 rounded-xl shadow-lg shadow-teal-500/30 hover:shadow-teal-500/50 transition-all">
              Get Started Free <ArrowRight size={18} />
            </Link>
            <p className="text-xs text-slate-500 mt-4">No credit card required. Clinical use only.</p>
          </motion.div>
        </div>
      </section>

      {/* ── FOOTER ──────────────────────────────────────────────────────── */}
      <footer className="border-t border-white/5 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-500">
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 bg-gradient-to-br from-teal-400 to-teal-600 rounded flex items-center justify-center">
              <ShieldCheck size={10} className="text-white" />
            </div>
            <span className="font-semibold text-slate-300">RxDetect</span>
            <span>— AI-Powered Prescription Discrepancy Detection System</span>
          </div>
          <p>For clinical use only. Always verify with a licensed pharmacist.</p>
        </div>
      </footer>
    </div>
  )
}
