'use client'
import Link from 'next/link'
import { motion } from 'framer-motion'
import {
  ShieldCheck, ScanLine, Brain, ClipboardCheck,
  ArrowRight, CheckCircle2, AlertTriangle, Users, Lock, FileText, ChevronRight
} from 'lucide-react'

const FEATURES = [
  {
    icon: ScanLine,
    title: 'Intelligent OCR Extraction',
    desc: 'Automatically reads handwritten and printed prescriptions using vision AI, extracting all structured fields with high accuracy.',
    color: 'bg-blue-50 text-blue-600',
  },
  {
    icon: ClipboardCheck,
    title: 'Rule-Based Safety Checks',
    desc: 'Deterministic clinical rules detect omissions, commission errors, illegibility, and internal inconsistencies before AI analysis.',
    color: 'bg-teal-50 text-teal-600',
  },
  {
    icon: Brain,
    title: 'Clinical AI Reasoning',
    desc: 'Drug data from RxNorm and OpenFDA feeds a clinical reasoning engine that validates dosage, interactions, and contraindications.',
    color: 'bg-indigo-50 text-indigo-600',
  },
  {
    icon: FileText,
    title: 'Audit-Ready Reports',
    desc: 'Generate structured PDF reports with full clinical evidence, rule findings, and pharmacist feedback for compliance records.',
    color: 'bg-emerald-50 text-emerald-600',
  },
]

const PIPELINE = [
  { step: '01', label: 'Upload',    desc: 'Prescription image or PDF' },
  { step: '02', label: 'Extract',   desc: 'AI-powered field extraction' },
  { step: '03', label: 'Validate',  desc: 'RxNorm + OpenFDA drug check' },
  { step: '04', label: 'Analyse',   desc: 'Rule engine + clinical AI' },
  { step: '05', label: 'Report',    desc: 'Structured audit report' },
]

const TRUST = [
  { icon: ShieldCheck, label: 'Clinical-grade validation',   sub: 'Following WHO & FDA standards' },
  { icon: Lock,        label: 'Secure by design',            sub: 'JWT auth, role-based access' },
  { icon: Users,       label: 'Built for clinical teams',    sub: 'Pharmacist & admin workflows' },
  { icon: CheckCircle2,label: 'Evidence-backed decisions',   sub: 'Every finding has a source' },
]

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-white text-slate-800">

      {/* Navbar */}
      <nav className="sticky top-0 z-50 bg-white/95 backdrop-blur border-b border-slate-100">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 bg-primary-500 rounded-lg flex items-center justify-center">
              <ShieldCheck size={16} className="text-white" />
            </div>
            <span className="font-bold text-primary-500 text-lg">RxDetect</span>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/login" className="text-sm font-medium text-slate-600 hover:text-primary-500 px-4 py-2 rounded-xl hover:bg-slate-50 transition">
              Sign in
            </Link>
            <Link href="/signup" className="btn-primary text-sm">
              Get Started <ArrowRight size={14} />
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative overflow-hidden bg-gradient-to-br from-primary-500 via-primary-600 to-primary-700 text-white">
        <div className="absolute inset-0 opacity-10"
          style={{ backgroundImage: 'radial-gradient(circle at 30% 50%, #2EC4B6 0%, transparent 50%), radial-gradient(circle at 70% 80%, #ffffff 0%, transparent 40%)' }} />
        <div className="relative max-w-7xl mx-auto px-6 py-24 md:py-32">
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="max-w-3xl"
          >
            <div className="inline-flex items-center gap-2 bg-white/10 backdrop-blur border border-white/20 text-sm font-medium px-4 py-1.5 rounded-full mb-8">
              <ShieldCheck size={14} />
              Clinical Decision Support System
            </div>
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold leading-tight tracking-tight mb-6">
              AI-Assisted<br />
              <span className="text-teal-300">Prescription Safety</span><br />
              System
            </h1>
            <p className="text-lg md:text-xl text-blue-100 leading-relaxed mb-10 max-w-2xl">
              Detect prescription discrepancies before they reach the patient. Combines deterministic rule-based checks with clinical AI reasoning, validated by RxNorm and FDA drug data.
            </p>
            <div className="flex flex-wrap gap-4">
              <Link href="/signup" className="inline-flex items-center gap-2 bg-teal-400 hover:bg-teal-300 text-primary-800 font-semibold px-7 py-3 rounded-xl transition shadow-lg">
                Start Validating <ArrowRight size={16} />
              </Link>
              <Link href="/login" className="inline-flex items-center gap-2 bg-white/10 hover:bg-white/20 border border-white/30 font-medium px-7 py-3 rounded-xl transition">
                Sign In
              </Link>
            </div>
          </motion.div>
        </div>

        {/* Stat bar */}
        <div className="relative border-t border-white/10 bg-white/5">
          <div className="max-w-7xl mx-auto px-6 py-5 grid grid-cols-3 md:grid-cols-3 divide-x divide-white/10">
            {[
              { val: '5', label: 'Discrepancy Types Detected' },
              { val: 'FDA', label: 'Drug Data Source' },
              { val: '100%', label: 'Audit Trail' },
            ].map(({ val, label }) => (
              <div key={label} className="text-center px-4">
                <p className="text-2xl font-bold text-teal-300">{val}</p>
                <p className="text-sm text-blue-200 mt-0.5">{label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="max-w-7xl mx-auto px-6 py-20">
        <div className="text-center mb-14">
          <p className="text-xs font-semibold uppercase tracking-widest text-teal-500 mb-3">Core Capabilities</p>
          <h2 className="text-3xl md:text-4xl font-bold text-primary-500">Built for clinical accuracy</h2>
          <p className="text-slate-500 mt-4 max-w-xl mx-auto">
            Every prescription goes through a multi-layer validation pipeline designed with pharmacists and clinical safety in mind.
          </p>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {FEATURES.map((f, i) => (
            <motion.div
              key={f.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className="card hover:shadow-card-hover transition-shadow group"
            >
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center mb-4 ${f.color}`}>
                <f.icon size={18} />
              </div>
              <h3 className="font-semibold text-slate-800 mb-2">{f.title}</h3>
              <p className="text-sm text-slate-500 leading-relaxed">{f.desc}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Pipeline */}
      <section className="bg-slate-50 py-20">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-14">
            <p className="text-xs font-semibold uppercase tracking-widest text-teal-500 mb-3">How It Works</p>
            <h2 className="text-3xl font-bold text-primary-500">From upload to report in seconds</h2>
          </div>
          <div className="flex flex-col md:flex-row items-center gap-0 md:gap-0 max-w-4xl mx-auto">
            {PIPELINE.map((p, i) => (
              <div key={p.step} className="flex flex-col md:flex-row items-center flex-1">
                <motion.div
                  initial={{ opacity: 0, scale: 0.85 }}
                  whileInView={{ opacity: 1, scale: 1 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.12 }}
                  className="flex flex-col items-center text-center px-4 py-2"
                >
                  <div className="w-12 h-12 bg-primary-500 text-white rounded-xl flex items-center justify-center font-bold text-sm mb-3 shadow">
                    {p.step}
                  </div>
                  <p className="font-semibold text-slate-800 text-sm">{p.label}</p>
                  <p className="text-xs text-slate-400 mt-1">{p.desc}</p>
                </motion.div>
                {i < PIPELINE.length - 1 && (
                  <ChevronRight size={16} className="text-slate-300 hidden md:block flex-shrink-0" />
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Discrepancy types */}
      <section className="max-w-7xl mx-auto px-6 py-20">
        <div className="text-center mb-12">
          <p className="text-xs font-semibold uppercase tracking-widest text-teal-500 mb-3">Detection Coverage</p>
          <h2 className="text-3xl font-bold text-primary-500">Every discrepancy type, covered</h2>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-4">
          {[
            { label: 'No Discrepancy', color: 'bg-green-50 border-green-200 text-green-700',  desc: 'Clean prescription' },
            { label: 'Omission',       color: 'bg-amber-50 border-amber-200 text-amber-700',   desc: 'Missing required info' },
            { label: 'Commission',     color: 'bg-red-50 border-red-200 text-red-700',         desc: 'Incorrect entry' },
            { label: 'Inconsistency',  color: 'bg-orange-50 border-orange-200 text-orange-700',desc: 'Internal conflict' },
            { label: 'Illegibility',   color: 'bg-gray-100 border-gray-300 text-gray-700',     desc: 'Unreadable content' },
          ].map((t, i) => (
            <motion.div
              key={t.label}
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.08 }}
              className={`border rounded-2xl p-5 text-center ${t.color}`}
            >
              <p className="font-bold text-sm">{t.label}</p>
              <p className="text-xs mt-1 opacity-70">{t.desc}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Trust */}
      <section className="bg-primary-500 text-white py-20">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-14">
            <h2 className="text-3xl font-bold">Designed for clinical trust</h2>
            <p className="text-blue-200 mt-3">Built to the standards healthcare professionals expect</p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {TRUST.map((t, i) => (
              <motion.div
                key={t.label}
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
                className="bg-white/10 backdrop-blur border border-white/10 rounded-2xl p-5"
              >
                <t.icon size={20} className="text-teal-300 mb-3" />
                <p className="font-semibold">{t.label}</p>
                <p className="text-sm text-blue-200 mt-1">{t.sub}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-3xl mx-auto px-6 py-24 text-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          <h2 className="text-3xl md:text-4xl font-bold text-primary-500 mb-4">
            Ready to validate your first prescription?
          </h2>
          <p className="text-slate-500 mb-8">
            Join clinical teams using RxDetect to catch errors before they reach patients.
          </p>
          <Link href="/signup" className="btn-primary text-base px-8 py-3">
            Get Started Free <ArrowRight size={16} />
          </Link>
        </motion.div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-100 bg-slate-50 py-8">
        <div className="max-w-7xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-slate-400">
          <div className="flex items-center gap-2">
            <ShieldCheck size={16} className="text-primary-400" />
            <span className="font-semibold text-primary-500">RxDetect</span>
            <span>— AI-Assisted Prescription Safety</span>
          </div>
          <p>For clinical use only. Always verify with a licensed pharmacist.</p>
        </div>
      </footer>
    </div>
  )
}
