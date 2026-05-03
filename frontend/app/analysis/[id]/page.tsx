'use client'
import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useQuery, useMutation } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ArrowLeft, Download, RefreshCw, FileText, Brain,
  BookOpen, ShieldCheck, ChevronDown, ChevronUp,
  CheckCircle2, AlertCircle, Send, Loader2
} from 'lucide-react'
import Link from 'next/link'
import Navbar from '@/components/Navbar'
import DiscrepancyBadge from '@/components/DiscrepancyBadge'
import ClarityIndicator from '@/components/ClarityIndicator'
import FieldExtractPanel from '@/components/FieldExtractPanel'
import EvidencePanel from '@/components/EvidencePanel'
import RuleFindings from '@/components/RuleFindings'
import StatusPill from '@/components/StatusPill'
import { Skeleton } from '@/components/Skeleton'
import { prescriptionApi, reportApi } from '@/lib/api'
import { formatDate, formatConfidence, LABEL_CONFIG } from '@/lib/utils'
import type { DiscrepancyLabel, PrescriptionStatus, AnalysisResult } from '@/lib/types'
import toast from 'react-hot-toast'

export default function AnalysisPage() {
  const { id } = useParams<{ id: string }>()
  const router  = useRouter()

  const [feedbackLabel,   setFeedbackLabel]   = useState('')
  const [feedbackNote,    setFeedbackNote]     = useState('')
  const [feedbackCorrect, setFeedbackCorrect] = useState<boolean | null>(null)
  const [showFeedback,    setShowFeedback]     = useState(false)
  const [feedbackSent,    setFeedbackSent]     = useState(false)
  const [activeTab,       setActiveTab]        = useState<'fields' | 'rules' | 'evidence'>('fields')

  // Poll status if not yet analyzed
  const { data: statusData } = useQuery({
    queryKey: ['rx-status', id],
    queryFn: () => prescriptionApi.getStatus(id).then(r => r.data),
    refetchInterval: (query) => {
      const d = query.state.data as { status?: string } | undefined
      return d?.status && !['analyzed', 'failed'].includes(d.status) ? 4000 : false
    },
  })

  // Fetch result
  const { data: result, isLoading, error: resultError, refetch } = useQuery<AnalysisResult>({
    queryKey: ['rx-result', id],
    queryFn: () => prescriptionApi.getResult(id).then(r => r.data),
    enabled: statusData?.status === 'analyzed' || !statusData,
    retry: false,
  })

  // Feedback mutation
  const feedbackMut = useMutation({
    mutationFn: () =>
      prescriptionApi.submitFeedback(id, feedbackLabel, feedbackNote, feedbackCorrect ?? true),
    onSuccess: () => {
      toast.success('Feedback recorded. Thank you.')
      setFeedbackSent(true)
    },
    onError: () => toast.error('Failed to submit feedback'),
  })

  // Report generation + authenticated download
  const reportMut = useMutation({
    mutationFn: async () => {
      await reportApi.generate(id)
      await reportApi.download(id)
    },
    onSuccess: () => toast.success('Report downloaded'),
    onError: () => toast.error('Failed to generate report'),
  })

  const isProcessing = statusData?.status && !['analyzed', 'failed'].includes(statusData.status)
  const discrepancy  = result?.discrepancy
  const fields       = result?.extracted_fields
  const label        = discrepancy?.label as DiscrepancyLabel | undefined
  const cfg          = label ? LABEL_CONFIG[label] : null

  return (
    <div className="min-h-screen bg-slate-50">
      <Navbar />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8">

        {/* Header */}
        <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <button onClick={() => router.back()} className="btn-ghost text-sm p-2">
              <ArrowLeft size={16} />
            </button>
            <div>
              <h1 className="text-xl font-bold text-primary-500">Prescription Analysis</h1>
              <p className="text-xs text-slate-400 font-mono mt-0.5">{id}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {statusData && <StatusPill status={statusData.status as PrescriptionStatus} />}
            <button onClick={() => refetch()} className="btn-ghost text-sm">
              <RefreshCw size={13} /> Refresh
            </button>
            {result && (
              <button
                onClick={() => reportMut.mutate()}
                disabled={reportMut.isPending}
                className="btn-secondary text-sm"
              >
                {reportMut.isPending ? <Loader2 size={13} className="animate-spin" /> : <Download size={13} />}
                Download Report
              </button>
            )}
          </div>
        </div>

        {/* Processing state */}
        {isProcessing && (
          <div className="card flex items-center justify-center py-16 mb-6">
            <div className="text-center">
              <div className="w-12 h-12 rounded-full border-2 border-primary-100 border-t-primary-500 animate-spin mx-auto mb-4" />
              <p className="font-semibold text-primary-700">Analysis in progress</p>
              <p className="text-sm text-slate-400 mt-1 capitalize">{statusData?.status?.replace('_', ' ')}…</p>
            </div>
          </div>
        )}

        {/* Error / not ready */}
        {!isProcessing && (resultError || !result) && !isLoading && (
          <div className="card border-amber-100 bg-amber-50 flex items-center gap-3 py-5">
            <AlertCircle size={18} className="text-amber-500" />
            <div>
              <p className="font-semibold text-amber-700">Results not available yet</p>
              <p className="text-sm text-amber-600 mt-0.5">
                {statusData?.status === 'failed'
                  ? 'The analysis pipeline failed. Please try re-uploading.'
                  : 'Analysis is still running. Check back in a moment.'}
              </p>
            </div>
          </div>
        )}

        {/* Loading skeletons */}
        {isLoading && (
          <div className="grid lg:grid-cols-3 gap-6">
            {[1,2,3].map(i => (
              <div key={i} className="card space-y-3">
                <Skeleton className="h-4 w-1/3" />
                <Skeleton className="h-10 w-2/3" />
                <Skeleton className="h-3 w-full" />
                <Skeleton className="h-3 w-4/5" />
              </div>
            ))}
          </div>
        )}

        {/* Main analysis layout */}
        {result && discrepancy && fields && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="grid lg:grid-cols-3 gap-6"
          >
            {/* ── LEFT: Extracted Fields ─────────────────────────────────── */}
            <div className="lg:col-span-1 space-y-4">
              <div className="card">
                <div className="flex items-center gap-2 mb-4">
                  <FileText size={15} className="text-primary-400" />
                  <h2 className="font-semibold text-slate-800">Extracted Fields</h2>
                </div>

                {/* Clarity indicators */}
                <div className="space-y-2 mb-4 pb-4 border-b border-slate-50">
                  <ClarityIndicator
                    score={fields.overall_legibility_score ?? 0}
                    label="OCR Readability"
                  />
                  {result.pharmacist_feedback?.label && (
                    <ClarityIndicator
                      score={(discrepancy.confidence ?? 0)}
                      label="System Confidence"
                    />
                  )}
                </div>

                {/* Tab switcher for mobile */}
                <div className="flex lg:hidden gap-1 mb-4">
                  {(['fields', 'rules', 'evidence'] as const).map(t => (
                    <button
                      key={t}
                      onClick={() => setActiveTab(t)}
                      className={`flex-1 text-xs font-medium py-1.5 rounded-lg capitalize transition ${
                        activeTab === t
                          ? 'bg-primary-500 text-white'
                          : 'bg-slate-100 text-slate-500'
                      }`}
                    >
                      {t}
                    </button>
                  ))}
                </div>

                <div className={activeTab !== 'fields' ? 'hidden lg:block' : ''}>
                  <FieldExtractPanel fields={fields} />
                </div>
              </div>
            </div>

            {/* ── CENTER: Discrepancy Result ─────────────────────────────── */}
            <div className="lg:col-span-1 space-y-4">
              {/* Main result card */}
              <div className={`card border-2 ${cfg?.border}`}>
                <div className="flex items-center gap-2 mb-4">
                  <ShieldCheck size={15} className="text-primary-400" />
                  <h2 className="font-semibold text-slate-800">System Validation Result</h2>
                </div>

                {/* Big badge */}
                <div className={`rounded-xl p-6 text-center mb-4 ${cfg?.bg}`}>
                  <DiscrepancyBadge label={label!} size="lg" animated />
                  <p className={`text-sm mt-3 font-medium ${cfg?.color}`}>{cfg?.text}</p>
                  <div className="flex items-center justify-center gap-2 mt-2">
                    <span className="text-xs text-slate-400">System confidence:</span>
                    <span className="text-xs font-semibold text-slate-600">
                      {formatConfidence(discrepancy.confidence)}
                    </span>
                  </div>
                </div>

                {/* Consensus badge */}
                {discrepancy.consensus && (
                  <div className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium mb-4 ${
                    discrepancy.consensus === 'HIGH'
                      ? 'bg-green-50 text-green-700'
                      : 'bg-amber-50 text-amber-700'
                  }`}>
                    <CheckCircle2 size={12} />
                    {discrepancy.consensus === 'HIGH' ? 'High' : 'Low'} inter-system consensus
                  </div>
                )}

                {/* Clinical reasoning */}
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <Brain size={13} className="text-primary-400" />
                    <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                      Clinical Reasoning
                    </p>
                  </div>
                  <div className="bg-slate-50 rounded-xl p-4 text-sm text-slate-700 leading-relaxed">
                    {discrepancy.llm_reason || 'No clinical reasoning provided.'}
                  </div>
                </div>
              </div>

              {/* Rules triggered — CENTER on desktop, tab on mobile */}
              <div className={`card ${activeTab !== 'rules' ? 'hidden lg:block' : ''}`}>
                <div className="flex items-center gap-2 mb-4">
                  <ShieldCheck size={14} className="text-primary-400" />
                  <h2 className="font-semibold text-slate-800 text-sm">Rule Findings</h2>
                  {discrepancy.rules?.length > 0 && (
                    <span className="ml-auto text-xs font-semibold bg-primary-50 text-primary-600 px-2 py-0.5 rounded-full">
                      {discrepancy.rules.length}
                    </span>
                  )}
                </div>
                <RuleFindings rules={discrepancy.rules || []} />
              </div>

              {/* Pharmacist feedback */}
              <div className="card">
                <button
                  onClick={() => setShowFeedback(!showFeedback)}
                  className="w-full flex items-center justify-between text-sm font-semibold text-slate-700 hover:text-primary-600 transition"
                >
                  <span className="flex items-center gap-2">
                    <Send size={13} />
                    Pharmacist Correction
                  </span>
                  {showFeedback ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                </button>

                <AnimatePresence>
                  {showFeedback && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="overflow-hidden"
                    >
                      {feedbackSent ? (
                        <div className="mt-4 flex items-center gap-2 text-green-600 text-sm">
                          <CheckCircle2 size={14} />
                          Feedback recorded. Thank you.
                        </div>
                      ) : (
                        <div className="mt-4 space-y-3">
                          <div>
                            <label className="label">Correct label</label>
                            <select
                              className="input text-sm"
                              value={feedbackLabel}
                              onChange={e => setFeedbackLabel(e.target.value)}
                            >
                              <option value="">Select…</option>
                              {['No Discrepancy', 'Omission', 'Commission', 'Inconsistency', 'Illegibility'].map(l => (
                                <option key={l} value={l}>{l}</option>
                              ))}
                            </select>
                          </div>
                          <div>
                            <label className="label">Note (optional)</label>
                            <textarea
                              className="input text-sm resize-none h-20"
                              placeholder="Clinical notes or reasoning…"
                              value={feedbackNote}
                              onChange={e => setFeedbackNote(e.target.value)}
                            />
                          </div>
                          <div className="flex items-center gap-3">
                            <span className="text-sm text-slate-500">System was correct?</span>
                            {[true, false].map(v => (
                              <button
                                key={String(v)}
                                onClick={() => setFeedbackCorrect(v)}
                                className={`text-xs font-medium px-3 py-1.5 rounded-lg border transition ${
                                  feedbackCorrect === v
                                    ? v ? 'bg-green-500 text-white border-green-500'
                                        : 'bg-red-500 text-white border-red-500'
                                    : 'bg-white text-slate-600 border-slate-200'
                                }`}
                              >
                                {v ? 'Yes' : 'No'}
                              </button>
                            ))}
                          </div>
                          <button
                            onClick={() => feedbackMut.mutate()}
                            disabled={!feedbackLabel || feedbackMut.isPending}
                            className="btn-primary w-full text-sm"
                          >
                            {feedbackMut.isPending
                              ? <><Loader2 size={13} className="animate-spin" /> Submitting…</>
                              : <><Send size={13} /> Submit Feedback</>
                            }
                          </button>
                        </div>
                      )}
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* Prior feedback */}
                {result.pharmacist_feedback?.label && (
                  <div className="mt-4 pt-4 border-t border-slate-50">
                    <p className="text-xs text-slate-400 mb-1">Last submitted</p>
                    <div className="flex items-center gap-2">
                      <DiscrepancyBadge
                        label={result.pharmacist_feedback.label as DiscrepancyLabel}
                        size="sm"
                      />
                      {result.pharmacist_feedback.is_correct != null && (
                        <span className={`text-xs ${result.pharmacist_feedback.is_correct ? 'text-green-600' : 'text-red-500'}`}>
                          {result.pharmacist_feedback.is_correct ? '✓ Marked correct' : '✗ Marked incorrect'}
                        </span>
                      )}
                    </div>
                    {result.pharmacist_feedback.note && (
                      <p className="text-xs text-slate-500 mt-1 italic">{result.pharmacist_feedback.note}</p>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* ── RIGHT: Evidence Panel ──────────────────────────────────── */}
            <div className="lg:col-span-1 space-y-4">
              <div className={`card ${activeTab !== 'evidence' ? 'hidden lg:block' : ''}`}>
                <div className="flex items-center gap-2 mb-4">
                  <BookOpen size={15} className="text-primary-400" />
                  <h2 className="font-semibold text-slate-800">Guideline Evidence</h2>
                  {discrepancy.evidence_sources?.length > 0 && (
                    <span className="ml-auto text-xs font-semibold bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full">
                      {discrepancy.evidence_sources.length}
                    </span>
                  )}
                </div>
                <EvidencePanel sources={discrepancy.evidence_sources || []} />
              </div>

              {/* Drug validation summary */}
              {result.extracted_fields?.drugs?.length > 0 && (
                <div className="card">
                  <div className="flex items-center gap-2 mb-3">
                    <ShieldCheck size={14} className="text-teal-500" />
                    <h2 className="font-semibold text-slate-800 text-sm">Drug Validation</h2>
                  </div>
                  <div className="space-y-2">
                    {result.extracted_fields.drugs.map((drug, i) => (
                      <div key={i} className="flex items-center gap-2 px-3 py-2 bg-teal-50 rounded-lg">
                        <div className="w-2 h-2 rounded-full bg-teal-400 flex-shrink-0" />
                        <span className="text-sm font-medium text-teal-700">{drug.drug_name}</span>
                        <span className="text-xs text-teal-500 ml-auto">{drug.dose || '—'}</span>
                      </div>
                    ))}
                  </div>
                  <p className="text-xs text-slate-400 mt-2">
                    Validated against RxNorm & OpenFDA drug databases
                  </p>
                </div>
              )}

              {/* Report card */}
              <div className="card bg-primary-50 border-primary-100">
                <div className="flex items-center gap-2 mb-3">
                  <FileText size={14} className="text-primary-500" />
                  <h2 className="font-semibold text-primary-700 text-sm">Audit Report</h2>
                </div>
                <p className="text-xs text-primary-600 leading-relaxed mb-4">
                  Generate a structured PDF report with all findings, clinical reasoning, and guideline evidence for your records.
                </p>
                <button
                  onClick={() => reportMut.mutate()}
                  disabled={reportMut.isPending}
                  className="btn-primary w-full text-sm"
                >
                  {reportMut.isPending
                    ? <><Loader2 size={13} className="animate-spin" /> Generating…</>
                    : <><Download size={13} /> Generate & Download</>
                  }
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </main>
    </div>
  )
}
