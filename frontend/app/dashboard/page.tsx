'use client'
import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Upload, RefreshCw, FileText, CheckCircle2,
  AlertTriangle, Clock, ChevronRight,
  Search, Filter, Columns2, X, Trash2, AlertCircle
} from 'lucide-react'
import Navbar from '@/components/Navbar'
import StatsCard from '@/components/StatsCard'
import StatusPill from '@/components/StatusPill'
import DiscrepancyBadge from '@/components/DiscrepancyBadge'
import { TableRowSkeleton } from '@/components/Skeleton'
import { prescriptionApi, reportApi, getRole } from '@/lib/api'
import { formatDate, cn } from '@/lib/utils'
import type { PrescriptionListItem, PrescriptionStatus, DiscrepancyLabel, ReportListItem } from '@/lib/types'
import toast from 'react-hot-toast'

const STATUS_OPTS: { value: string; label: string }[] = [
  { value: '',           label: 'All' },
  { value: 'uploaded',   label: 'Uploaded' },
  { value: 'processing', label: 'Processing' },
  { value: 'analyzed',   label: 'Analysed' },
  { value: 'failed',     label: 'Failed' },
]

interface DeleteModalProps {
  count: number
  onConfirm: () => void
  onCancel: () => void
  loading: boolean
}

function DeleteModal({ count, onConfirm, onCancel, loading }: DeleteModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onCancel}
      />
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 8 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 8 }}
        transition={{ type: 'spring', damping: 30, stiffness: 400 }}
        className="relative bg-slate-900 border border-white/10 rounded-2xl shadow-2xl p-6 w-full max-w-sm"
      >
        <div className="w-12 h-12 rounded-full bg-red-500/15 flex items-center justify-center mb-4 mx-auto">
          <AlertCircle size={22} className="text-red-400" />
        </div>
        <h2 className="text-base font-bold text-white text-center mb-2">
          Delete {count > 1 ? `${count} prescriptions` : 'prescription'}?
        </h2>
        <p className="text-sm text-slate-400 text-center mb-6 leading-relaxed">
          {count > 1 ? 'These prescriptions' : 'This prescription'} will be soft-deleted and removed
          from the dashboard. Associated analysis reports will also be wiped.
          This action cannot be undone.
        </p>
        <div className="flex gap-3">
          <button
            onClick={onCancel}
            disabled={loading}
            className="flex-1 inline-flex items-center justify-center gap-2 bg-white/5 hover:bg-white/10 text-slate-300 font-medium border border-white/10 px-4 py-2.5 rounded-xl transition text-sm"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className="flex-1 inline-flex items-center justify-center gap-2 bg-red-500 hover:bg-red-400 text-white font-semibold px-4 py-2.5 rounded-xl transition disabled:opacity-50 text-sm"
          >
            {loading ? (
              <><div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Deleting…</>
            ) : (
              <><Trash2 size={14} /> Delete</>
            )}
          </button>
        </div>
      </motion.div>
    </div>
  )
}

export default function DashboardPage() {
  const router = useRouter()
  const qc = useQueryClient()
  const role = getRole()
  const canDelete = role === 'pharmacist' || role === 'admin'

  const [statusFilter, setStatusFilter] = useState('')
  const [search,       setSearch]       = useState('')
  const [page,         setPage]         = useState(1)
  const [selected,     setSelected]     = useState<Set<string>>(new Set())
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)
  const [bulkDelete,   setBulkDelete]   = useState(false)

  const { data: rxData, isLoading: rxLoading, refetch } = useQuery({
    queryKey: ['prescriptions', page, statusFilter],
    queryFn: () => prescriptionApi.list(page, 20, statusFilter || undefined).then(r => r.data),
    refetchInterval: 15_000,
  })

  const { data: reportData } = useQuery({
    queryKey: ['reports-summary'],
    queryFn: () => reportApi.list(1, 100).then(r => r.data),
  })

  const deleteMut = useMutation({
    mutationFn: async (ids: string[]) => {
      await Promise.all(ids.map(id => prescriptionApi.delete(id)))
    },
    onSuccess: (_, ids) => {
      toast.success(ids.length > 1 ? `${ids.length} prescriptions deleted` : 'Prescription deleted')
      setDeleteTarget(null)
      setBulkDelete(false)
      setSelected(new Set())
      void qc.invalidateQueries({ queryKey: ['prescriptions'] })
      void qc.invalidateQueries({ queryKey: ['reports-summary'] })
    },
    onError: () => {
      toast.error('Delete failed — you may not have permission')
      setDeleteTarget(null)
      setBulkDelete(false)
    },
  })

  const items: PrescriptionListItem[] = rxData?.items || []
  const total = rxData?.total || 0
  const reports: ReportListItem[] = reportData?.items || []
  const processing = items.filter(r => r.status === 'processing').length
  const failed     = items.filter(r => r.status === 'failed').length
  const flagged    = reports.filter(r => r.label !== 'No Discrepancy').length
  const cleanPct   = reports.length ? Math.round((reports.length - flagged) / reports.length * 100) : 0

  const filtered = search
    ? items.filter(rx =>
        rx.original_filename?.toLowerCase().includes(search.toLowerCase()) ||
        rx.id.toLowerCase().includes(search.toLowerCase())
      )
    : items

  const analyzedItems    = filtered.filter(rx => rx.status === 'analyzed')
  const analyzedSelected = Array.from(selected).filter(id => {
    const rx = items.find(r => r.id === id)
    return rx?.status === 'analyzed'
  })

  const allAnalyzedSelected  = analyzedItems.length > 0 && analyzedItems.every(rx => selected.has(rx.id))
  const someAnalyzedSelected = analyzedItems.some(rx => selected.has(rx.id))

  function toggleSelectAll() {
    if (allAnalyzedSelected) {
      setSelected(prev => {
        const next = new Set(prev)
        analyzedItems.forEach(rx => next.delete(rx.id))
        return next
      })
    } else {
      setSelected(prev => {
        const next = new Set(prev)
        analyzedItems.forEach(rx => next.add(rx.id))
        return next
      })
    }
  }

  function toggleSelect(id: string) {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  function goCompare() {
    if (analyzedSelected.length >= 2) {
      router.push(`/compare?ids=${analyzedSelected.join(',')}`)
    }
  }

  const deleteIds = bulkDelete ? Array.from(selected) : deleteTarget ? [deleteTarget] : []
  const showDeleteModal = (bulkDelete || deleteTarget !== null) && deleteIds.length > 0

  return (
    <div className="min-h-screen bg-[#050d1a] has-bottom-nav">
      <Navbar />

      <AnimatePresence>
        {showDeleteModal && (
          <DeleteModal
            count={deleteIds.length}
            onConfirm={() => deleteMut.mutate(deleteIds)}
            onCancel={() => { setDeleteTarget(null); setBulkDelete(false) }}
            loading={deleteMut.isPending}
          />
        )}
      </AnimatePresence>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8">

        <div className="flex items-center justify-between mb-6 sm:mb-8">
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-white">Dashboard</h1>
            <p className="text-slate-500 text-sm mt-0.5">Prescription validation overview</p>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={() => refetch()} className="btn-ghost text-sm">
              <RefreshCw size={14} />
              <span className="hidden sm:inline">Refresh</span>
            </button>
            <Link href="/upload" className="btn-primary text-sm">
              <Upload size={14} />
              <span className="hidden sm:inline">Upload Prescription</span>
              <span className="sm:hidden">Upload</span>
            </Link>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4 mb-6 sm:mb-8">
          <StatsCard label="Total Processed" value={rxData?.total ?? '—'} icon={FileText} delay={0} />
          <StatsCard label="Flagged" value={flagged} icon={AlertTriangle}
            iconColor="text-amber-400" iconBg="bg-amber-500/15" sub="Discrepancies found" delay={0.05} />
          <StatsCard label="Clean" value={`${cleanPct}%`} icon={CheckCircle2}
            iconColor="text-emerald-400" iconBg="bg-emerald-500/15" sub="No discrepancy" delay={0.1} />
          <StatsCard label="Processing" value={processing} icon={Clock}
            iconColor="text-indigo-400" iconBg="bg-indigo-500/15" sub={`${failed} failed`} delay={0.15} />
        </div>

        {selected.size > 0 && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="rounded-2xl mb-4 overflow-hidden border border-teal-500/30"
          >
            <div className="bg-teal-900/60 backdrop-blur-xl px-4 py-2.5 flex items-center gap-3">
              <div className="flex items-center gap-2 flex-1 min-w-0">
                <Columns2 size={15} className="text-teal-400 flex-shrink-0" />
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-semibold text-white">
                    {selected.size} prescription{selected.size !== 1 ? 's' : ''} selected
                  </span>
                  {analyzedSelected.length === 0 && (
                    <span className="text-xs text-teal-500">Select at least 2 analysed prescriptions to compare</span>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                <button
                  onClick={goCompare}
                  disabled={analyzedSelected.length < 2}
                  className={cn(
                    'text-sm font-semibold px-4 py-1.5 rounded-xl transition',
                    analyzedSelected.length >= 2
                      ? 'bg-teal-500 text-slate-950 hover:bg-teal-400'
                      : 'bg-teal-500/20 text-teal-600 cursor-not-allowed'
                  )}
                >
                  Compare {analyzedSelected.length >= 2 ? analyzedSelected.length : ''}
                </button>
                {canDelete && (
                  <button
                    onClick={() => setBulkDelete(true)}
                    className="text-sm font-semibold px-3 py-1.5 rounded-xl bg-red-500/15 text-red-400 hover:bg-red-500/25 transition flex items-center gap-1.5"
                  >
                    <Trash2 size={13} />
                    <span className="hidden sm:inline">Delete</span>
                  </button>
                )}
                <button onClick={() => setSelected(new Set())} className="p-1.5 hover:bg-teal-500/20 rounded-lg transition">
                  <X size={14} className="text-teal-400" />
                </button>
              </div>
            </div>

            {analyzedSelected.length >= 2 && (
              <div className="bg-teal-500/8 border-t border-teal-500/20 px-4 py-2 flex items-center gap-2 flex-wrap">
                {analyzedSelected.map((id, i) => (
                  <span key={id} className="inline-flex items-center gap-1.5 bg-white/5 border border-teal-500/20 text-teal-400 text-xs font-medium px-2.5 py-1 rounded-full">
                    <span className="w-4 h-4 rounded-full bg-teal-500 text-slate-950 flex items-center justify-center text-[9px] font-bold flex-shrink-0">{i + 1}</span>
                    <span className="font-mono">{id.slice(0, 10)}…</span>
                    <button onClick={() => toggleSelect(id)} className="text-teal-500 hover:text-red-400 transition ml-0.5">
                      <X size={10} />
                    </button>
                  </span>
                ))}
              </div>
            )}
          </motion.div>
        )}

        <div className="flex flex-col sm:flex-row gap-3 mb-5">
          <div className="relative flex-1">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              className="input pl-9 text-sm"
              placeholder="Search by filename or ID…"
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
            <Filter size={14} className="text-slate-500 flex-shrink-0" />
            {STATUS_OPTS.map(opt => (
              <button
                key={opt.value}
                onClick={() => { setStatusFilter(opt.value); setPage(1) }}
                className={cn(
                  'text-xs font-medium px-3 py-2 rounded-lg border transition flex-shrink-0 touch-manipulation',
                  statusFilter === opt.value
                    ? 'bg-teal-500 text-slate-950 border-teal-500'
                    : 'bg-white/5 text-slate-400 border-white/10 hover:border-white/20'
                )}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* Desktop table */}
        <div className="hidden sm:block bg-slate-900/60 backdrop-blur-xl rounded-2xl border border-white/8 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/5 bg-white/2">
                  <th className="w-10 px-4 py-3">
                    {analyzedItems.length > 0 && (
                      <input
                        type="checkbox"
                        checked={allAnalyzedSelected}
                        ref={el => {
                          if (el) el.indeterminate = someAnalyzedSelected && !allAnalyzedSelected
                        }}
                        onChange={toggleSelectAll}
                        title="Select all analysed"
                        className="rounded border-white/20 bg-white/5 text-teal-500 focus:ring-teal-400 cursor-pointer"
                      />
                    )}
                  </th>
                  {['File', 'Status', 'Uploaded', 'Clarity', 'Result', ''].map(h => (
                    <th key={h} className="text-left text-xs font-semibold text-slate-500 uppercase tracking-wider px-4 py-3">{h}</th>
                  ))}
                  {canDelete && <th className="w-10 px-4 py-3" />}
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {rxLoading
                  ? Array.from({ length: 5 }).map((_, i) => <TableRowSkeleton key={i} />)
                  : filtered.length === 0 ? (
                    <tr>
                      <td colSpan={canDelete ? 8 : 7} className="text-center py-16 text-slate-500 text-sm">
                        <FileText size={28} className="mx-auto mb-3 opacity-30" />
                        No prescriptions found.{' '}
                        <Link href="/upload" className="text-teal-400 hover:underline">Upload one</Link>
                      </td>
                    </tr>
                  ) : filtered.map((rx, i) => {
                    const report     = reports.find(r => r.prescription_id === rx.id)
                    const isSelected = selected.has(rx.id)
                    const canSelect  = rx.status === 'analyzed'
                    return (
                      <motion.tr
                        key={rx.id}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: i * 0.03 }}
                        className={cn('hover:bg-white/3 transition-colors', isSelected && 'bg-teal-500/8')}
                      >
                        <td className="px-4 py-3.5">
                          {canSelect && (
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={() => toggleSelect(rx.id)}
                              className="rounded border-white/20 bg-white/5 text-teal-500 focus:ring-teal-400 cursor-pointer"
                            />
                          )}
                        </td>
                        <td className="px-4 py-3.5">
                          <p className="text-sm font-medium text-slate-200 truncate max-w-[180px]">
                            {rx.original_filename || 'Untitled'}
                          </p>
                          <p className="text-xs text-slate-500 font-mono mt-0.5">{rx.id.slice(0, 8)}…</p>
                        </td>
                        <td className="px-4 py-3.5"><StatusPill status={rx.status as PrescriptionStatus} /></td>
                        <td className="px-4 py-3.5 text-sm text-slate-500 whitespace-nowrap">{formatDate(rx.created_at)}</td>
                        <td className="px-4 py-3.5">
                          {rx.ocr_confidence != null ? (
                            <div className="flex items-center gap-2">
                              <div className="w-20 h-1.5 bg-white/8 rounded-full overflow-hidden">
                                <div
                                  className={cn('h-full rounded-full',
                                    rx.ocr_confidence >= 0.8 ? 'bg-emerald-500' :
                                    rx.ocr_confidence >= 0.6 ? 'bg-amber-400' : 'bg-red-400'
                                  )}
                                  style={{ width: `${rx.ocr_confidence * 100}%` }}
                                />
                              </div>
                              <span className="text-xs text-slate-500">{Math.round(rx.ocr_confidence * 100)}%</span>
                            </div>
                          ) : <span className="text-xs text-slate-600">—</span>}
                        </td>
                        <td className="px-4 py-3.5">
                          {report ? (
                            <DiscrepancyBadge label={report.label as DiscrepancyLabel} size="sm" />
                          ) : rx.status === 'processing' ? (
                            <span className="text-xs text-indigo-400 animate-pulse">Analysing…</span>
                          ) : (
                            <span className="text-xs text-slate-600">—</span>
                          )}
                        </td>
                        <td className="px-4 py-3.5 text-right">
                          {rx.status === 'analyzed' && (
                            <Link
                              href={`/analysis/${rx.id}`}
                              className="inline-flex items-center gap-1 text-xs font-medium text-teal-400 hover:text-teal-300"
                            >
                              View <ChevronRight size={12} />
                            </Link>
                          )}
                        </td>
                        {canDelete && (
                          <td className="px-4 py-3.5 text-right">
                            <button
                              onClick={() => setDeleteTarget(rx.id)}
                              className="p-1.5 rounded-lg text-slate-600 hover:text-red-400 hover:bg-red-500/10 transition"
                              title="Delete prescription"
                            >
                              <Trash2 size={13} />
                            </button>
                          </td>
                        )}
                      </motion.tr>
                    )
                  })
                }
              </tbody>
            </table>
          </div>

          {total > 20 && (
            <div className="flex items-center justify-between px-5 py-3 border-t border-white/8">
              <p className="text-sm text-slate-500">
                {Math.min((page-1)*20+1, total)}–{Math.min(page*20, total)} of {total}
              </p>
              <div className="flex gap-2">
                <button onClick={() => setPage(p => Math.max(1, p-1))} disabled={page===1}
                  className="btn-secondary text-sm py-1.5 px-3">Previous</button>
                <button onClick={() => setPage(p => p+1)} disabled={page*20>=total}
                  className="btn-primary text-sm py-1.5 px-3">Next</button>
              </div>
            </div>
          )}
        </div>

        {/* Mobile card list */}
        <div className="sm:hidden space-y-3">
          {rxLoading ? (
            Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="card animate-pulse space-y-2 p-4">
                <div className="h-3 bg-white/8 rounded w-2/3" />
                <div className="h-3 bg-white/8 rounded w-1/2" />
              </div>
            ))
          ) : filtered.length === 0 ? (
            <div className="text-center py-16 text-slate-500 text-sm">
              <FileText size={28} className="mx-auto mb-3 opacity-30" />
              No prescriptions found.{' '}
              <Link href="/upload" className="text-teal-400 hover:underline">Upload one</Link>
            </div>
          ) : filtered.map((rx, i) => {
            const report     = reports.find(r => r.prescription_id === rx.id)
            const isSelected = selected.has(rx.id)
            const canSelect  = rx.status === 'analyzed'
            return (
              <motion.div
                key={rx.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.04 }}
                className={cn('card', isSelected && 'border-teal-500/30 bg-teal-500/8')}
              >
                <div className="flex items-start justify-between gap-3 mb-3">
                  <div className="flex items-center gap-2.5 flex-1 min-w-0">
                    {canSelect && (
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleSelect(rx.id)}
                        className="rounded border-white/20 bg-white/5 text-teal-500 flex-shrink-0"
                      />
                    )}
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-slate-200 truncate">{rx.original_filename || 'Untitled'}</p>
                      <p className="text-xs text-slate-500 font-mono mt-0.5">{rx.id.slice(0, 12)}…</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <StatusPill status={rx.status as PrescriptionStatus} />
                    {canDelete && (
                      <button
                        onClick={() => setDeleteTarget(rx.id)}
                        className="p-1.5 rounded-lg text-slate-600 hover:text-red-400 hover:bg-red-500/10 transition"
                      >
                        <Trash2 size={13} />
                      </button>
                    )}
                  </div>
                </div>
                <div className="flex items-center justify-between text-xs text-slate-500 mb-3">
                  <span>{formatDate(rx.created_at)}</span>
                  {rx.ocr_confidence != null && (
                    <span>OCR: <span className={cn('font-semibold',
                      rx.ocr_confidence >= 0.8 ? 'text-emerald-400' :
                      rx.ocr_confidence >= 0.6 ? 'text-amber-400' : 'text-red-400'
                    )}>{Math.round(rx.ocr_confidence * 100)}%</span></span>
                  )}
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    {report ? (
                      <DiscrepancyBadge label={report.label as DiscrepancyLabel} size="sm" />
                    ) : rx.status === 'processing' ? (
                      <span className="text-xs text-indigo-400 animate-pulse">Analysing…</span>
                    ) : <span className="text-xs text-slate-600">Pending</span>}
                  </div>
                  {rx.status === 'analyzed' && (
                    <Link
                      href={`/analysis/${rx.id}`}
                      className="inline-flex items-center gap-1 text-xs font-semibold text-slate-950 bg-teal-500 hover:bg-teal-400 px-3 py-1.5 rounded-lg touch-manipulation"
                    >
                      View Report <ChevronRight size={12} />
                    </Link>
                  )}
                </div>
              </motion.div>
            )
          })}

          {analyzedSelected.length >= 2 && (
            <button onClick={goCompare} className="w-full btn-primary py-3 text-sm">
              <Columns2 size={14} />
              Compare {analyzedSelected.length} Prescriptions
            </button>
          )}

          {canDelete && selected.size > 0 && (
            <button
              onClick={() => setBulkDelete(true)}
              className="w-full inline-flex items-center justify-center gap-2 bg-red-500/15 hover:bg-red-500/25 text-red-400 font-semibold px-4 py-3 rounded-xl border border-red-500/20 transition text-sm"
            >
              <Trash2 size={14} />
              Delete {selected.size} selected
            </button>
          )}

          {total > 20 && (
            <div className="flex gap-3 pt-2">
              <button onClick={() => setPage(p => Math.max(1, p-1))} disabled={page===1}
                className="flex-1 btn-secondary text-sm py-2">Previous</button>
              <button onClick={() => setPage(p => p+1)} disabled={page*20>=total}
                className="flex-1 btn-primary text-sm py-2">Next</button>
            </div>
          )}
        </div>

      </main>
    </div>
  )
}
