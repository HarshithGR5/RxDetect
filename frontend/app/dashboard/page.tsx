'use client'
import { useState } from 'react'
import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  Upload, RefreshCw, FileText, CheckCircle2,
  AlertTriangle, XCircle, Clock, ChevronRight, Search, Filter
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
  { value: '',          label: 'All Status' },
  { value: 'uploaded',  label: 'Uploaded' },
  { value: 'processing',label: 'Processing' },
  { value: 'analyzed',  label: 'Analysed' },
  { value: 'failed',    label: 'Failed' },
]

export default function DashboardPage() {
  const [statusFilter, setStatusFilter] = useState('')
  const [search,       setSearch]       = useState('')
  const [page,         setPage]         = useState(1)

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

  // Stats
  const reports: ReportListItem[] = reportData?.items || []
  const analyzed   = items.filter(r => r.status === 'analyzed').length
  const processing = items.filter(r => r.status === 'processing').length
  const failed     = items.filter(r => r.status === 'failed').length

  const labelCounts = reports.reduce((acc: Record<string, number>, r) => {
    acc[r.label] = (acc[r.label] || 0) + 1
    return acc
  }, {})
  const flagged = reports.filter(r => r.label !== 'No Discrepancy').length
  const cleanPct = reports.length ? Math.round((reports.length - flagged) / reports.length * 100) : 0

  const filtered = search
    ? items.filter(rx =>
        rx.original_filename?.toLowerCase().includes(search.toLowerCase()) ||
        rx.id.toLowerCase().includes(search.toLowerCase())
      )
    : items

  return (
    <div className="min-h-screen bg-slate-50">
      <Navbar />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8">

        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-primary-500">Dashboard</h1>
            <p className="text-slate-400 text-sm mt-0.5">Prescription validation overview</p>
          </div>
          <div className="flex items-center gap-3">
            <button onClick={() => refetch()} className="btn-ghost text-sm">
              <RefreshCw size={14} /> Refresh
            </button>
            <Link href="/upload" className="btn-primary text-sm">
              <Upload size={14} /> Upload Prescription
            </Link>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <StatsCard
            label="Total Processed"
            value={rxData?.total ?? '—'}
            icon={FileText}
            delay={0}
          />
          <StatsCard
            label="Flagged"
            value={flagged}
            icon={AlertTriangle}
            iconColor="text-amber-500"
            iconBg="bg-amber-50"
            sub="Discrepancies found"
            delay={0.05}
          />
          <StatsCard
            label="Clean Prescriptions"
            value={`${cleanPct}%`}
            icon={CheckCircle2}
            iconColor="text-green-500"
            iconBg="bg-green-50"
            sub="No discrepancy"
            delay={0.1}
          />
          <StatsCard
            label="Processing"
            value={processing}
            icon={Clock}
            iconColor="text-indigo-500"
            iconBg="bg-indigo-50"
            sub={`${failed} failed`}
            delay={0.15}
          />
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3 mb-5">
          <div className="relative flex-1 min-w-[200px]">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              className="input pl-9 text-sm"
              placeholder="Search by filename or ID…"
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
          <div className="flex items-center gap-2">
            <Filter size={14} className="text-slate-400" />
            {STATUS_OPTS.map(opt => (
              <button
                key={opt.value}
                onClick={() => { setStatusFilter(opt.value); setPage(1) }}
                className={cn(
                  'text-xs font-medium px-3 py-1.5 rounded-lg border transition',
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

        {/* Table */}
        <div className="bg-white rounded-2xl border border-slate-100 shadow-card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/70">
                  <th className="text-left text-xs font-semibold text-slate-400 uppercase tracking-wider px-5 py-3">File</th>
                  <th className="text-left text-xs font-semibold text-slate-400 uppercase tracking-wider px-4 py-3">Status</th>
                  <th className="text-left text-xs font-semibold text-slate-400 uppercase tracking-wider px-4 py-3">Uploaded</th>
                  <th className="text-left text-xs font-semibold text-slate-400 uppercase tracking-wider px-4 py-3">Data Clarity</th>
                  <th className="text-left text-xs font-semibold text-slate-400 uppercase tracking-wider px-4 py-3">Result</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {rxLoading
                  ? Array.from({ length: 5 }).map((_, i) => <TableRowSkeleton key={i} />)
                  : filtered.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="text-center py-16 text-slate-400 text-sm">
                        <FileText size={28} className="mx-auto mb-3 opacity-30" />
                        No prescriptions found. <Link href="/upload" className="text-primary-500 hover:underline">Upload one</Link>
                      </td>
                    </tr>
                  ) : filtered.map((rx, i) => {
                    const report = reports.find(r => r.prescription_id === rx.id)
                    return (
                      <motion.tr
                        key={rx.id}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: i * 0.03 }}
                        className="hover:bg-slate-50/60 transition-colors"
                      >
                        <td className="px-5 py-3.5">
                          <p className="text-sm font-medium text-slate-800 truncate max-w-[180px]">
                            {rx.original_filename || 'Untitled'}
                          </p>
                          <p className="text-xs text-slate-400 font-mono mt-0.5">{rx.id.slice(0, 8)}…</p>
                        </td>
                        <td className="px-4 py-3.5">
                          <StatusPill status={rx.status as PrescriptionStatus} />
                        </td>
                        <td className="px-4 py-3.5 text-sm text-slate-500">
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
                Showing {Math.min((page - 1) * 20 + 1, total)}–{Math.min(page * 20, total)} of {total}
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="btn-secondary text-sm py-1.5 px-3"
                >Previous</button>
                <button
                  onClick={() => setPage(p => p + 1)}
                  disabled={page * 20 >= total}
                  className="btn-primary text-sm py-1.5 px-3"
                >Next</button>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
