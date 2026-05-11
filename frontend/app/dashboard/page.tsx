'use client'
import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  Upload, RefreshCw, FileText, CheckCircle2,
  AlertTriangle, XCircle, Clock, ChevronRight,
  Search, Filter, Columns2, X
} from 'lucide-react'
import Navbar from '@/components/Navbar'
import StatsCard from '@/components/StatsCard'
import StatusPill from '@/components/StatusPill'
import DiscrepancyBadge from '@/components/DiscrepancyBadge'
import { TableRowSkeleton } from '@/components/Skeleton'
import { prescriptionApi, reportApi } from '@/lib/api'
import { formatDate, cn } from '@/lib/utils'
import type { PrescriptionListItem, PrescriptionStatus, DiscrepancyLabel, ReportListItem } from '@/lib/types'

const STATUS_OPTS: { value: string; label: string }[] = [
  { value: '',          label: 'All' },
  { value: 'uploaded',  label: 'Uploaded' },
  { value: 'processing',label: 'Processing' },
  { value: 'analyzed',  label: 'Analysed' },
  { value: 'failed',    label: 'Failed' },
]

export default function DashboardPage() {
  const router = useRouter()
  const [statusFilter, setStatusFilter] = useState('')
  const [search,       setSearch]       = useState('')
  const [page,         setPage]         = useState(1)
  const [selected,     setSelected]     = useState<Set<string>>(new Set())

  const { data: rxData, isLoading: rxLoading, refetch } = useQuery({
    queryKey: ['prescriptions', page, statusFilter],
    queryFn: () => prescriptionApi.list(page, 20, statusFilter || undefined).then(r => r.data),
    refetchInterval: 15_000,
  })

  const { data: reportData } = useQuery({
    queryKey: ['reports-summary'],
    queryFn: () => reportApi.list(1, 100).then(r => r.data),
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

  // Only analyzed prescriptions can be compared
  const analyzedSelected = [...selected].filter(id => {
    const rx = items.find(r => r.id === id)
    return rx?.status === 'analyzed'
  })

  function toggleSelect(id: string) {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  function clearSelection() {
    setSelected(new Set())
  }

  function goCompare() {
    if (analyzedSelected.length >= 2) {
      router.push(`/compare?ids=${analyzedSelected.join(',')}`)
    }
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <Navbar />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8">

        {/* Header */}
        <div className="flex items-center justify-between mb-6 sm:mb-8">
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-primary-500">Dashboard</h1>
            <p className="text-slate-400 text-sm mt-0.5">Prescription validation overview</p>
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

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4 mb-6 sm:mb-8">
          <StatsCard label="Total Processed" value={rxData?.total ?? '—'} icon={FileText} delay={0} />
          <StatsCard label="Flagged" value={flagged} icon={AlertTriangle}
            iconColor="text-amber-500" iconBg="bg-amber-50" sub="Discrepancies found" delay={0.05} />
          <StatsCard label="Clean" value={`${cleanPct}%`} icon={CheckCircle2}
            iconColor="text-green-500" iconBg="bg-green-50" sub="No discrepancy" delay={0.1} />
          <StatsCard label="Processing" value={processing} icon={Clock}
            iconColor="text-indigo-500" iconBg="bg-indigo-50" sub={`${failed} failed`} delay={0.15} />
        </div>

        {/* Compare bar — appears when selections are made */}
        {selected.size > 0 && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="flex items-center gap-3 bg-primary-600 text-white px-4 py-3 rounded-xl mb-4 shadow"
          >
            <Columns2 size={15} />
            <span className="text-sm font-medium flex-1">
              {selected.size} selected
              {analyzedSelected.length < 2 && selected.size > 0 && (
                <span className="ml-2 text-primary-200 text-xs">
                  (select {Math.max(0, 2 - analyzedSelected.length)} more analysed prescription{analyzedSelected.length === 1 ? '' : 's'} to compare)
                </span>
              )}
            </span>
            <button
              onClick={goCompare}
              disabled={analyzedSelected.length < 2}
              className={cn(
                'text-sm font-semibold px-4 py-1.5 rounded-lg transition',
                analyzedSelected.length >= 2
                  ? 'bg-white text-primary-600 hover:bg-primary-50'
                  : 'bg-primary-500 text-primary-300 cursor-not-allowed'
              )}
            >
              Compare Checklists
            </button>
            <button onClick={clearSelection} className="p-1 hover:bg-primary-500 rounded-lg transition">
              <X size={14} />
            </button>
          </motion.div>
        )}

        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-3 mb-5">
          <div className="relative flex-1">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              className="input pl-9 text-sm"
              placeholder="Search by filename or ID…"
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
            <Filter size={14} className="text-slate-400 flex-shrink-0" />
            {STATUS_OPTS.map(opt => (
              <button
                key={opt.value}
                onClick={() => { setStatusFilter(opt.value); setPage(1) }}
                className={cn(
                  'text-xs font-medium px-3 py-2 rounded-lg border transition flex-shrink-0 touch-manipulation',
                  statusFilter === opt.value
                    ? 'bg-primary-500 text-white border-primary-500'
                    : 'bg-white text-slate-600 border-slate-200 hover:border-slate-300'
                )}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* ── Desktop table ── */}
        <div className="hidden sm:block bg-white rounded-2xl border border-slate-100 shadow-card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/70">
                  <th className="w-10 px-4 py-3">
                    <span className="sr-only">Select</span>
                  </th>
                  <th className="text-left text-xs font-semibold text-slate-400 uppercase tracking-wider px-4 py-3">File</th>
                  <th className="text-left text-xs font-semibold text-slate-400 uppercase tracking-wider px-4 py-3">Status</th>
                  <th className="text-left text-xs font-semibold text-slate-400 uppercase tracking-wider px-4 py-3">Uploaded</th>
                  <th className="text-left text-xs font-semibold text-slate-400 uppercase tracking-wider px-4 py-3">Clarity</th>
                  <th className="text-left text-xs font-semibold text-slate-400 uppercase tracking-wider px-4 py-3">Result</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {rxLoading
                  ? Array.from({ length: 5 }).map((_, i) => <TableRowSkeleton key={i} />)
                  : filtered.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="text-center py-16 text-slate-400 text-sm">
                        <FileText size={28} className="mx-auto mb-3 opacity-30" />
                        No prescriptions found.{' '}
                        <Link href="/upload" className="text-primary-500 hover:underline">Upload one</Link>
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
                        className={cn(
                          'hover:bg-slate-50/60 transition-colors',
                          isSelected && 'bg-primary-50/40'
                        )}
                      >
                        <td className="px-4 py-3.5">
                          {canSelect && (
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={() => toggleSelect(rx.id)}
                              className="rounded border-slate-300 text-primary-500 focus:ring-primary-400 cursor-pointer"
                              title="Select for comparison"
                            />
                          )}
                        </td>
                        <td className="px-4 py-3.5">
                          <p className="text-sm font-medium text-slate-800 truncate max-w-[180px]">
                            {rx.original_filename || 'Untitled'}
                          </p>
                          <p className="text-xs text-slate-400 font-mono mt-0.5">{rx.id.slice(0, 8)}…</p>
                        </td>
                        <td className="px-4 py-3.5">
                          <StatusPill status={rx.status as PrescriptionStatus} />
                        </td>
                        <td className="px-4 py-3.5 text-sm text-slate-500 whitespace-nowrap">
                          {formatDate(rx.created_at)}
                        </td>
                        <td className="px-4 py-3.5">
                          {rx.ocr_confidence != null ? (
                            <div className="flex items-center gap-2">
                              <div className="w-20 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                                <div
                                  className={cn('h-full rounded-full',
                                    rx.ocr_confidence >= 0.8 ? 'bg-green-400' :
                                    rx.ocr_confidence >= 0.6 ? 'bg-amber-400' : 'bg-red-400'
                                  )}
                                  style={{ width: `${rx.ocr_confidence * 100}%` }}
                                />
                              </div>
                              <span className="text-xs text-slate-500">{Math.round(rx.ocr_confidence * 100)}%</span>
                            </div>
                          ) : <span className="text-xs text-slate-300">—</span>}
                        </td>
                        <td className="px-4 py-3.5">
                          {report ? (
                            <DiscrepancyBadge label={report.label as DiscrepancyLabel} size="sm" />
                          ) : rx.status === 'processing' ? (
                            <span className="text-xs text-indigo-500 animate-softpulse">Analysing…</span>
                          ) : (
                            <span className="text-xs text-slate-300">—</span>
                          )}
                        </td>
                        <td className="px-4 py-3.5 text-right">
                          {rx.status === 'analyzed' && (
                            <Link
                              href={`/analysis/${rx.id}`}
                              className="inline-flex items-center gap-1 text-xs font-medium text-primary-500 hover:text-primary-600"
                            >
                              View <ChevronRight size={12} />
                            </Link>
                          )}
                        </td>
                      </motion.tr>
                    )
                  })
                }
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {total > 20 && (
            <div className="flex items-center justify-between px-5 py-3 border-t border-slate-100">
              <p className="text-sm text-slate-400">
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

        {/* ── Mobile card list ── */}
        <div className="sm:hidden space-y-3">
          {rxLoading ? (
            Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="card animate-pulse space-y-2 p-4">
                <div className="h-3 bg-slate-100 rounded w-2/3" />
                <div className="h-3 bg-slate-100 rounded w-1/2" />
                <div className="h-3 bg-slate-100 rounded w-1/3" />
              </div>
            ))
          ) : filtered.length === 0 ? (
            <div className="text-center py-16 text-slate-400 text-sm">
              <FileText size={28} className="mx-auto mb-3 opacity-30" />
              No prescriptions found.{' '}
              <Link href="/upload" className="text-primary-500 hover:underline">Upload one</Link>
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
                className={cn(
                  'bg-white rounded-2xl border border-slate-100 shadow-card p-4',
                  isSelected && 'border-primary-300 bg-primary-50/30'
                )}
              >
                <div className="flex items-start justify-between gap-3 mb-3">
                  <div className="flex items-center gap-2.5 flex-1 min-w-0">
                    {canSelect && (
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleSelect(rx.id)}
                        className="rounded border-slate-300 text-primary-500 flex-shrink-0"
                      />
                    )}
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-slate-800 truncate">
                        {rx.original_filename || 'Untitled'}
                      </p>
                      <p className="text-xs text-slate-400 font-mono mt-0.5">{rx.id.slice(0, 12)}…</p>
                    </div>
                  </div>
                  <StatusPill status={rx.status as PrescriptionStatus} />
                </div>

                <div className="flex items-center justify-between text-xs text-slate-500 mb-3">
                  <span>{formatDate(rx.created_at)}</span>
                  {rx.ocr_confidence != null && (
                    <span>
                      OCR: <span className={cn('font-semibold',
                        rx.ocr_confidence >= 0.8 ? 'text-green-600' :
                        rx.ocr_confidence >= 0.6 ? 'text-amber-600' : 'text-red-500'
                      )}>{Math.round(rx.ocr_confidence * 100)}%</span>
                    </span>
                  )}
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    {report ? (
                      <DiscrepancyBadge label={report.label as DiscrepancyLabel} size="sm" />
                    ) : rx.status === 'processing' ? (
                      <span className="text-xs text-indigo-500 animate-softpulse">Analysing…</span>
                    ) : (
                      <span className="text-xs text-slate-300">Pending</span>
                    )}
                  </div>
                  {rx.status === 'analyzed' && (
                    <Link
                      href={`/analysis/${rx.id}`}
                      className="inline-flex items-center gap-1 text-xs font-semibold text-white
                                 bg-primary-500 px-3 py-1.5 rounded-lg touch-manipulation"
                    >
                      View Report <ChevronRight size={12} />
                    </Link>
                  )}
                </div>
              </motion.div>
            )
          })}

          {/* Mobile: compare CTA */}
          {analyzedSelected.length >= 2 && (
            <button
              onClick={goCompare}
              className="w-full btn-primary py-3 text-sm"
            >
              <Columns2 size={14} />
              Compare {analyzedSelected.length} Prescriptions
            </button>
          )}

          {/* Mobile pagination */}
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
