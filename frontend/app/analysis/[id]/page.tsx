'use client'
import { useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useQuery, useMutation } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ArrowLeft, Download, RefreshCw, FileText, Brain,
  BookOpen, ShieldCheck, ChevronDown, ChevronUp,
  CheckCircle2, AlertCircle, Send, Loader2,
  ClipboardList, Leaf, XCircle, Minus, Lock, Activity
} from 'lucide-react'
import Navbar from '@/components/Navbar'
import DiscrepancyBadge from '@/components/DiscrepancyBadge'
import ClarityIndicator from '@/components/ClarityIndicator'
import FieldExtractPanel from '@/components/FieldExtractPanel'
import EvidencePanel from '@/components/EvidencePanel'
import RuleFindings from '@/components/RuleFindings'
import StatusPill from '@/components/StatusPill'
import ClinicalChecklistModal from '@/components/ClinicalChecklistModal'
import PrescriptionErrorRate from '@/components/PrescriptionErrorRate'
import { Skeleton } from '@/components/Skeleton'
import { prescriptionApi, reportApi, getRole } from '@/lib/api'
import { formatDate, formatConfidence, LABEL_CONFIG, cn } from '@/lib/utils'
import type { DiscrepancyLabel, PrescriptionStatus, AnalysisResult, ChecklistItem } from '@/lib/types'
import toast from 'react-hot-toast'

function ChecklistResultIcon({ result }: { result: ChecklistItem['result'] | undefined }) {
  if (!result || result === 'unknown') return <Minus size={12} className="text-slate-600" />
  if (result === 'yes')     return <CheckCircle2 size={12} className="text-emerald-400" />
  if (result === 'no')      return <XCircle size={12} className="text-red-400" />
  if (result === 'na')      return <span className="text-[9px] font-medium text-slate-500">N/A</span>
  if (result === 'partial') return (
    <span className="inline-flex items-center justify-center w-3 h-3 rounded-full bg-amber-500/20">
      <span className="text-[7px] font-bold text-amber-400">P</span>
    </span>
  )
  return <Minus size={12} className="text-slate-600" />
}

export default function AnalysisPage() {
  const { id } = useParams<{ id: string }>()
  const router  = useRouter()
  const role    = getRole()
  const isViewer = role === 'viewer'

  const [feedbackLabel,   setFeedbackLabel]   = useState('')
  const [feedbackNote,    setFeedbackNote]     = useState('')
  const [feedbackCorrect, setFeedbackCorrect] = useState<boolean | null>(null)
  const [showFeedback,    setShowFeedback]     = useState(false)
  const [feedbackSent,    setFeedbackSent]     = useState(false)
  const [activeTab,       setActiveTab]        = useState<'fields' | 'rules' | 'evidence'>('fields')
  const [showChecklist,   setShowChecklist]    = useState(false)
  const [showTherapy,     setShowTherapy]      = useState(false)
  const [rulesCollapsed,  setRulesCollapsed]   = useState(false)

  const { data: statusData } = useQuery({
    queryKey: ['rx-status', id],
    queryFn: () => prescriptionApi.getStatus(id).then(r => r.data),
    refetchInterval: (query) => {
      const d = query.state.data as { status?: string } | undefined
      return d?.status && !['analyzed', 'failed'].includes(d.status) ? 4000 : false
    },
  })

  const { data: result, isLoading, error: resultError, refetch } = useQuery<AnalysisResult>({
    queryKey: ['rx-result', id],
    queryFn: () => prescriptionApi.getResult(id).then(r => r.data),
    enabled: statusData?.status === 'analyzed' || !statusData,
    retry: false,
  })

  const feedbackMut = useMutation({
    mutationFn: () =>
      prescriptionApi.submitFeedback(id, feedbackLabel, feedbackNote, feedbackCorrect ?? true),
    onSuccess: () => {
      toast.success('Feedback recorded. Thank you.')
      setFeedbackSent(true)
    },
    onError: () => toast.error('Failed to submit feedback'),
  })

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
  const checklistItems     = result?.checklist_items ?? []
  const therapySuggestions = fields?.therapy_suggestions ?? []

  const checklistNo      = checklistItems.filter(i => i.result === 'no').length
  const checklistYes     = checklistItems.filter(i => i.result === 'yes').length
  const checklistPartial = checklistItems.filter(i => i.result === 'partial').length

  const CATEGORY_ORDER = ['patient', 'prescriber', 'drug', 'safety', 'completeness']
  const categorised = CATEGORY_ORDER.map(cat => ({
    cat,
    items: checklistItems.filter(i => i.category === cat),
  })).filter(g => g.items.length > 0)

  return (
    <div className="min-h-screen bg-[#050d1a] has-bottom-nav">
      <Navbar />

      {showChecklist && checklistItems.length > 0 && (
        <ClinicalChecklistModal items={checklistItems} onClose={() => setShowChecklist(false)} />
      )}

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8">

        {/* Header */}
        <div className="flex items-start sm:items-center justify-between mb-5 sm:mb-6 gap-3 flex-wrap">
          <div className="flex items-center gap-3">
            <button onClick={() => router.back()} className="btn-ghost text-sm p-2">
              <ArrowLeft size={16} />
            </button>
            <div>
              <h1 className="text-lg sm:text-xl font-bold text-white">Prescription Analysis</h1>
              <p className="text-xs text-slate-500 font-mono mt-0.5 truncate max-w-[180px] sm:max-w-none">{id}</p>
            </div>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            {statusData && <StatusPill status={statusData.status as PrescriptionStatus} />}
            <button onClick={() => refetch()} className="btn-ghost text-sm">
              <RefreshCw size={13} />
              <span className="hidden sm:inline">Refresh</span>
            </button>
          </div>
        </div>

        {/* Quick-stats bar */}
        {result && checklistItems.length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
            {(() => {
              const _na  = checklistItems.filter(i => i.result === 'na').length
              const _no  = checklistItems.filter(i => i.result === 'no').length
              const _par = checklistItems.filter(i => i.result === 'partial').length
              const _ev  = checklistItems.length - _na
              const _er  = _ev > 0 ? Math.round((_no + _par * 0.5) / _ev * 100) : 0
              const _col  = _er === 0 ? 'text-emerald-400' : _er <= 15 ? 'text-emerald-400' : _er <= 40 ? 'text-amber-400' : _er <= 65 ? 'text-orange-400' : 'text-red-400'
              const _lbl  = _er === 0 ? 'No errors' : _er <= 15 ? 'Low risk' : _er <= 40 ? 'Moderate' : _er <= 65 ? 'High risk' : 'Critical'
              return (
                <button
                  onClick={() => setShowChecklist(true)}
                  className="card p-3 sm:p-4 text-left hover:border-teal-500/30 hover:shadow-md transition group"
                >
                  <div className="flex items-center gap-2 mb-1">
                    <Activity size={14} className={_col} />
                    <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Error Rate</span>
                  </div>
                  <p className={`text-xl font-bold font-mono ${_col}`}>{_er}%</p>
                  <p className="text-xs mt-0.5">
                    <span className={`font-medium ${_col}`}>{_lbl}</span>
                    {_no > 0 && <span className="text-slate-500"> · {_no} fail</span>}
                  </p>
                </button>
              )
            })()}
            <div className="card p-3 sm:p-4">
              <div className="flex items-center gap-2 mb-1">
                <ShieldCheck size={14} className="text-teal-400" />
                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Confidence</span>
              </div>
              <p className="text-xl font-bold text-white">{formatConfidence(discrepancy?.confidence ?? 0)}</p>
              <p className="text-xs text-slate-500 mt-0.5">System score</p>
            </div>
            <div className="card p-3 sm:p-4">
              <div className="flex items-center gap-2 mb-1">
                <AlertCircle size={14} className="text-amber-400" />
                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Rules Hit</span>
              </div>
              <p className="text-xl font-bold text-white">{discrepancy?.rules?.length ?? 0}</p>
              <p className="text-xs text-slate-500 mt-0.5">Validation rules</p>
            </div>
            {therapySuggestions.length > 0 ? (
              <button onClick={() => setShowTherapy(v => !v)}
                className="card p-3 sm:p-4 text-left hover:border-teal-500/30 hover:shadow-md transition group">
                <div className="flex items-center gap-2 mb-1">
                  <Leaf size={14} className="text-teal-400" />
                  <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Therapy</span>
                </div>
                <p className="text-xl font-bold text-white">{therapySuggestions.length}</p>
                <p className="text-xs text-teal-400 mt-0.5 font-medium">View suggestions</p>
              </button>
            ) : (
              <div className="card p-3 sm:p-4">
                <div className="flex items-center gap-2 mb-1">
                  <BookOpen size={14} className="text-blue-400" />
                  <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Evidence</span>
                </div>
                <p className="text-xl font-bold text-white">{discrepancy?.evidence_sources?.length ?? 0}</p>
                <p className="text-xs text-slate-500 mt-0.5">Sources cited</p>
              </div>
            )}
          </div>
        )}

        {/* Therapy suggestions panel */}
        <AnimatePresence>
          {showTherapy && therapySuggestions.length > 0 && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="overflow-hidden mb-5"
            >
              <div className="card border-teal-500/20 bg-teal-500/5">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <Leaf size={15} className="text-teal-400" />
                    <h3 className="font-semibold text-teal-300 text-sm">Non-Drug / Therapy Suggestions</h3>
                  </div>
                  <button onClick={() => setShowTherapy(false)} className="text-teal-500 hover:text-teal-300 text-xs">
                    Dismiss
                  </button>
                </div>
                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
                  {therapySuggestions.map((s, i) => (
                    <div key={i} className="bg-white/5 rounded-xl p-3 border border-teal-500/15">
                      <p className="text-xs font-semibold text-teal-400 uppercase tracking-wide mb-1">
                        {String(s.type || '').replace(/_/g, ' ').toUpperCase() || 'Therapy'}
                      </p>
                      <p className="text-sm text-slate-300 leading-relaxed">{s.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Mobile checklist shortcut */}
        {result && checklistItems.length > 0 && (
          <div className="flex gap-2 mb-5 sm:hidden">
            <button onClick={() => setShowChecklist(true)} className="flex-1 btn-secondary text-sm py-2">
              <ClipboardList size={14} />
              View 27-param Checklist
              {checklistNo > 0 && (
                <span className="ml-1 bg-red-500/20 text-red-400 text-xs px-1.5 py-0.5 rounded-full">{checklistNo}</span>
              )}
            </button>
          </div>
        )}

        {/* Processing state */}
        {isProcessing && (
          <div className="card flex items-center justify-center py-16 mb-6">
            <div className="text-center">
              <div className="w-12 h-12 rounded-full border-2 border-teal-900 border-t-teal-400 animate-spin mx-auto mb-4" />
              <p className="font-semibold text-white">Analysis in progress</p>
              <p className="text-sm text-slate-400 mt-1 capitalize">{statusData?.status?.replace('_', ' ')}…</p>
            </div>
          </div>
        )}

        {/* Error / not ready */}
        {!isProcessing && (resultError || !result) && !isLoading && (
          <div className="card border-amber-500/20 bg-amber-500/10 flex items-center gap-3 py-5">
            <AlertCircle size={18} className="text-amber-400 flex-shrink-0" />
            <div>
              <p className="font-semibold text-amber-400">Results not available yet</p>
              <p className="text-sm text-amber-400/70 mt-0.5">
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

        {/* ── Main 3-column layout ── */}
        {result && discrepancy && fields && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
            className="grid lg:grid-cols-3 gap-5 sm:gap-6">

            {/* ── LEFT: Extracted Fields ── */}
            <div className="lg:col-span-1 space-y-4">
              <div className="card">
                <div className="flex items-center gap-2 mb-4">
                  <FileText size={15} className="text-teal-400" />
                  <h2 className="font-semibold text-white">Extracted Fields</h2>
                  {checklistItems.length > 0 && (
                    <button
                      onClick={() => setShowChecklist(true)}
                      className="ml-auto hidden sm:flex items-center gap-1 text-xs font-medium
                                 text-teal-400 bg-teal-500/15 px-2.5 py-1 rounded-lg
                                 hover:bg-teal-500/25 transition"
                    >
                      <ClipboardList size={12} />
                      Checklist
                      {checklistNo > 0 && (
                        <span className="bg-red-500/20 text-red-400 px-1 rounded-full text-[10px]">{checklistNo}</span>
                      )}
                    </button>
                  )}
                </div>

                <div className="space-y-2 mb-4 pb-4 border-b border-white/5">
                  <ClarityIndicator score={fields.overall_legibility_score ?? 0} label="OCR Readability" />
                  <ClarityIndicator score={discrepancy.confidence ?? 0} label="System Confidence" />
                </div>

                {/* Mobile tab switcher */}
                <div className="flex lg:hidden gap-1 mb-4">
                  {(['fields', 'rules', 'evidence'] as const).map(t => (
                    <button
                      key={t}
                      onClick={() => setActiveTab(t)}
                      className={`flex-1 text-xs font-medium py-2 rounded-lg capitalize transition touch-manipulation ${
                        activeTab === t ? 'bg-teal-500 text-slate-950' : 'bg-white/5 text-slate-400'
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

            {/* ── CENTER: Discrepancy Result + Collapsible Rule Findings ── */}
            <div className="lg:col-span-1 space-y-4">
              <div className={`card border-2 ${cfg?.border}`}>
                <div className="flex items-center gap-2 mb-4">
                  <ShieldCheck size={15} className="text-teal-400" />
                  <h2 className="font-semibold text-white">Validation Result</h2>
                </div>

                <div className={`rounded-xl p-5 sm:p-6 text-center mb-4 ${cfg?.bg}`}>
                  <DiscrepancyBadge label={label!} size="lg" animated />
                  <p className={`text-sm mt-3 font-medium ${cfg?.color}`}>{cfg?.text}</p>
                  <div className="flex items-center justify-center gap-2 mt-2">
                    <span className="text-xs text-slate-500">Confidence:</span>
                    <span className="text-xs font-semibold text-slate-300">
                      {formatConfidence(discrepancy.confidence)}
                    </span>
                  </div>
                </div>

                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <Brain size={13} className="text-teal-400" />
                    <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                      Clinical Reasoning
                    </p>
                  </div>
                  <div className="bg-white/3 rounded-xl p-4 text-sm text-slate-300 leading-relaxed">
                    {discrepancy.llm_reason || 'No clinical reasoning provided.'}
                  </div>
                </div>
              </div>

              {/* Prescription Error Rate */}
              {checklistItems.length > 0 && (
                <PrescriptionErrorRate
                  items={checklistItems}
                  onViewChecklist={() => setShowChecklist(true)}
                />
              )}

              {/* Collapsible Rule Findings */}
              <div className={`card ${activeTab !== 'rules' ? 'hidden lg:block' : ''}`}>
                <button
                  onClick={() => setRulesCollapsed(v => !v)}
                  className="w-full flex items-center justify-between"
                >
                  <div className="flex items-center gap-2">
                    <ShieldCheck size={14} className="text-teal-400" />
                    <h2 className="font-semibold text-white text-sm">Rule Findings</h2>
                    {discrepancy.rules?.length > 0 && (
                      <span className="text-xs font-semibold bg-teal-500/15 text-teal-400 px-2 py-0.5 rounded-full">
                        {discrepancy.rules.length}
                      </span>
                    )}
                  </div>
                  {rulesCollapsed
                    ? <ChevronDown size={14} className="text-slate-500" />
                    : <ChevronUp size={14} className="text-slate-500" />
                  }
                </button>

                <AnimatePresence initial={false}>
                  {!rulesCollapsed && (
                    <motion.div
                      key="rules-body"
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="overflow-hidden"
                    >
                      <div className="mt-3">
                        <RuleFindings rules={discrepancy.rules || []} />
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>

            {/* ── RIGHT: Evidence + Drug Validation + Audit + Pharmacist Correction ── */}
            <div className="lg:col-span-1 space-y-4">

              {/* Guideline Evidence */}
              <div className={`card ${activeTab !== 'evidence' ? 'hidden lg:block' : ''}`}>
                <div className="flex items-center gap-2 mb-4">
                  <BookOpen size={15} className="text-teal-400" />
                  <h2 className="font-semibold text-white">Guideline Evidence</h2>
                  {discrepancy.evidence_sources?.length > 0 && (
                    <span className="ml-auto text-xs font-semibold bg-teal-500/15 text-teal-400 px-2 py-0.5 rounded-full">
                      {discrepancy.evidence_sources.length}
                    </span>
                  )}
                </div>
                <EvidencePanel sources={discrepancy.evidence_sources || []} />
              </div>

              {/* Drug Validation */}
              {fields.drugs?.length > 0 && (
                <div className="card">
                  <div className="flex items-center gap-2 mb-3">
                    <ShieldCheck size={14} className="text-teal-400" />
                    <h2 className="font-semibold text-white text-sm">Drug Validation</h2>
                  </div>
                  <div className="space-y-2">
                    {fields.drugs.map((drug, i) => (
                      <div key={i} className="flex items-center gap-2 px-3 py-2 bg-teal-500/8 rounded-lg">
                        <div className="w-2 h-2 rounded-full bg-teal-400 flex-shrink-0" />
                        <span className="text-sm font-medium text-teal-300 flex-1 min-w-0 truncate">
                          {drug.drug_name}
                        </span>
                        <div className="flex items-center gap-1 flex-shrink-0">
                          {drug.is_high_alert && (
                            <span className="text-[10px] bg-red-500/15 text-red-400 px-1.5 py-0.5 rounded font-semibold">HIGH-ALERT</span>
                          )}
                          {drug.narrow_therapeutic_index && (
                            <span className="text-[10px] bg-amber-500/15 text-amber-400 px-1.5 py-0.5 rounded font-semibold">NTI</span>
                          )}
                          <span className="text-xs text-teal-500">{drug.dose || '—'}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                  <p className="text-xs text-slate-500 mt-2">Validated against RxNorm &amp; OpenFDA</p>
                </div>
              )}

              {/* Audit Report */}
              <div className="card bg-teal-500/8 border-teal-500/20">
                <div className="flex items-center gap-2 mb-3">
                  <FileText size={14} className="text-teal-400" />
                  <h2 className="font-semibold text-teal-300 text-sm">Audit Report</h2>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed mb-4">
                  Generate a structured PDF with all findings, clinical reasoning, checklist results,
                  and guideline evidence.
                </p>
                {isViewer ? (
                  <div className="flex items-center gap-2 text-xs text-slate-500 bg-white/3 rounded-xl px-4 py-3 border border-white/8">
                    <Lock size={13} className="text-slate-500 flex-shrink-0" />
                    Report download is not available for viewer accounts
                  </div>
                ) : (
                  <button
                    onClick={() => reportMut.mutate()}
                    disabled={reportMut.isPending}
                    className="btn-primary w-full text-sm"
                  >
                    {reportMut.isPending
                      ? <><Loader2 size={13} className="animate-spin" /> Generating…</>
                      : <><Download size={13} /> Generate &amp; Download</>
                    }
                  </button>
                )}
              </div>

              {/* Pharmacist Correction */}
              <div className="card">
                {isViewer ? (
                  <div className="flex items-center gap-2 text-xs text-slate-500">
                    <Lock size={13} className="flex-shrink-0" />
                    Pharmacist feedback is not available for viewer accounts
                  </div>
                ) : (
                  <>
                    <button
                      onClick={() => setShowFeedback(!showFeedback)}
                      className="w-full flex items-center justify-between text-sm font-semibold
                                 text-slate-300 hover:text-teal-400 transition touch-manipulation"
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
                            <div className="mt-4 flex items-center gap-2 text-emerald-400 text-sm">
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
                              <div className="flex items-center gap-3 flex-wrap">
                                <span className="text-sm text-slate-500">System was correct?</span>
                                {[true, false].map(v => (
                                  <button
                                    key={String(v)}
                                    onClick={() => setFeedbackCorrect(v)}
                                    className={cn(
                                      'text-xs font-medium px-3 py-2 rounded-lg border transition touch-manipulation',
                                      feedbackCorrect === v
                                        ? v ? 'bg-emerald-500 text-white border-emerald-500'
                                            : 'bg-red-500 text-white border-red-500'
                                        : 'bg-white/5 text-slate-400 border-white/10'
                                    )}
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

                    {result.pharmacist_feedback?.label && (
                      <div className="mt-4 pt-4 border-t border-white/5">
                        <p className="text-xs text-slate-500 mb-1">Last submitted</p>
                        <div className="flex items-center gap-2 flex-wrap">
                          <DiscrepancyBadge
                            label={result.pharmacist_feedback.label as DiscrepancyLabel}
                            size="sm"
                          />
                          {result.pharmacist_feedback.is_correct != null && (
                            <span className={`text-xs ${result.pharmacist_feedback.is_correct ? 'text-emerald-400' : 'text-red-400'}`}>
                              {result.pharmacist_feedback.is_correct ? '✓ Marked correct' : '✗ Marked incorrect'}
                            </span>
                          )}
                        </div>
                        {result.pharmacist_feedback.note && (
                          <p className="text-xs text-slate-500 mt-1 italic">{result.pharmacist_feedback.note}</p>
                        )}
                      </div>
                    )}
                  </>
                )}
              </div>

            </div>
          </motion.div>
        )}
      </main>
    </div>
  )
}
