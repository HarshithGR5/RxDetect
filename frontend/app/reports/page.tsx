'use client'
import { useState } from 'react'
import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  FileText, Download, ExternalLink, RefreshCw,
  CheckCircle2, AlertTriangle, ChevronRight, Loader2
} from 'lucide-react'
import Navbar from '@/components/Navbar'
import DiscrepancyBadge from '@/components/DiscrepancyBadge'
import { TableRowSkeleton } from '@/components/Skeleton'
import { reportApi } from '@/lib/api'
import { formatDate, formatConfidence, cn } from '@/lib/utils'
import type { DiscrepancyLabel, ReportListItem } from '@/lib/types'
import toast from 'react-hot-toast'

export default function ReportsPage() {
  const [page, setPage] = useState(1)
  const [generating, setGenerating] = useState<string | null>(null)

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['reports', page],
    queryFn: () => reportApi.list(page, 20).then(r => r.data),
    refetchInterval: 30_000,
  })

  const items: ReportListItem[] = data?.items || []
  const total = data?.total || 0

  const handleDownload = async (prescriptionId: string, hasPdf: boolean) => {
    setGenerating(prescriptionId)
    try {
      if (!hasPdf) {
        await reportApi.generate(prescriptionId)
        toast.success('Report generated')
      }
      await reportApi.download(prescriptionId)
    } catch {
      toast.error('Failed to download report')
    } finally {
      setGenerating(null)
    }
  }

  const labelCounts = items.reduce((acc: Record<string, number>, r) => {
    acc[r.label] = (acc[r.label] || 0) + 1
    return acc
  }, {})

  return (
    <div className="min-h-screen bg-slate-50 has-bottom-nav">
      <Navbar />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8">

        {/* Header */}
        <div className="flex items-center justify-between mb-6 sm:mb-8 flex-wrap gap-3">
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-primary-500">Reports</h1>
            <p className="text-slate-400 text-sm mt-0.5">All prescription analysis reports</p>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={() => refetch()} className="btn-ghost text-sm">
              <RefreshCw size={14} />
              <span className="hidden sm:inline">Refresh</span>
            </button>
            <Link href="/upload" className="btn-primary text-sm">
              New Analysis
            </Link>
          </div>
        </div>

        {/* Summary bar */}
        {items.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="grid grid-cols-3 sm:grid-cols-5 gap-2 sm:gap-3 mb-6 sm:mb-8"
          >
            {(
              ['No Discrepancy', 'Omission', 'Commission', 'Inconsistency', 'Illegibility'] as DiscrepancyLabel[]
            ).map((label) => (
              <div key={label} className="card py-3 px-3 sm:px-4 flex items-center gap-2">
                <DiscrepancyBadge label={label} size="sm" showText={false} />
                <div className="min-w-0">
                  <p className="text-base sm:text-lg font-bold text-slate-800">{labelCounts[label] || 0}</p>
                  <p className="text-[10px] sm:text-xs text-slate-400 leading-tight truncate">{label}</p>
                </div>
              </div>
            ))}
          </motion.div>
        )}

        {/* ── Desktop table ── */}
        <div className="hidden sm:block bg-white rounded-2xl border border-slate-100 shadow-card overflow-hidden">
          <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between">
            <p className="text-sm font-semibold text-slate-700">
              {total} report{total !== 1 ? 's' : ''} found
            </p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-50 bg-slate-50/70">
                  {['Prescription ID', 'Result', 'Consensus', 'Confidence', 'Generated', 'PDF', 'Actions'].map(h => (
                    <th key={h} className="text-left text-xs font-semibold text-slate-400 uppercase tracking-wider px-4 py-3">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {isLoading
                  ? Array.from({ length: 5 }).map((_, i) => <TableRowSkeleton key={i} />)
                  : items.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="text-center py-16 text-slate-400 text-sm">
                        <FileText size={28} className="mx-auto mb-3 opacity-30" />
                        No reports yet.{' '}
                        <Link href="/upload" className="text-primary-500 hover:underline">
                          Upload a prescription
                        </Link>{' '}
                        to get started.
                      </td>
                    </tr>
                  ) : items.map((r, i) => (
                    <motion.tr
                      key={r.report_id}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: i * 0.03 }}
                      className="hover:bg-slate-50/60 transition-colors"
                    >
                      <td className="px-4 py-3.5">
                        <p className="text-xs font-mono text-slate-500">{r.prescription_id.slice(0, 12)}…</p>
                      </td>
                      <td className="px-4 py-3.5">
                        <DiscrepancyBadge label={r.label as DiscrepancyLabel} size="sm" />
                      </td>
                      <td className="px-4 py-3.5">
                        <span className={cn(
                          'text-xs font-medium px-2 py-0.5 rounded-full',
                          r.consensus === 'HIGH' ? 'bg-green-50 text-green-700' : 'bg-amber-50 text-amber-700'
                        )}>
                          {r.consensus || '—'}
                        </span>
                      </td>
                      <td className="px-4 py-3.5">
                        <div className="flex items-center gap-2">
                          <div className="w-16 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                            <div className="h-full bg-primary-400 rounded-full"
                              style={{ width: `${(r.confidence || 0) * 100}%` }} />
                          </div>
                          <span className="text-xs text-slate-500">{formatConfidence(r.confidence || 0)}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3.5 text-xs text-slate-500 whitespace-nowrap">
                        {formatDate(r.created_at)}
                      </td>
                      <td className="px-4 py-3.5">
                        {r.pdf_ready ? (
                          <span className="flex items-center gap-1 text-green-600 text-xs">
                            <CheckCircle2 size={12} /> Ready
                          </span>
                        ) : (
                          <span className="text-xs text-slate-400">Not generated</span>
                        )}
                      </td>
                      <td className="px-4 py-3.5">
                        <div className="flex items-center gap-3">
                          <Link href={`/analysis/${r.prescription_id}`}
                            className="text-xs text-primary-500 hover:text-primary-700 flex items-center gap-1">
                            View <ExternalLink size={10} />
                          </Link>
                          <button
                            onClick={() => handleDownload(r.prescription_id, r.pdf_ready)}
                            disabled={generating === r.prescription_id}
                            className="text-xs text-slate-500 hover:text-slate-700 flex items-center gap-1"
                          >
                            {generating === r.prescription_id
                              ? <Loader2 size={12} className="animate-spin" />
                              : <Download size={12} />}
                            {r.pdf_ready ? 'PDF' : 'Generate'}
                          </button>
                        </div>
                      </td>
                    </motion.tr>
                  ))
                }
              </tbody>
            </table>
          </div>

          {total > 20 && (
            <div className="flex items-center justify-between px-5 py-3 border-t border-slate-100">
              <p className="text-sm text-slate-400">Page {page} of {Math.ceil(total / 20)}</p>
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
          {isLoading ? (
            Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="card animate-pulse space-y-2 p-4">
                <div className="h-3 bg-slate-100 rounded w-1/2" />
                <div className="h-3 bg-slate-100 rounded w-2/3" />
                <div className="h-3 bg-slate-100 rounded w-1/3" />
              </div>
            ))
          ) : items.length === 0 ? (
            <div className="text-center py-16 text-slate-400 text-sm">
              <FileText size={28} className="mx-auto mb-3 opacity-30" />
              No reports yet.{' '}
              <Link href="/upload" className="text-primary-500 hover:underline">Upload a prescription</Link>
            </div>
          ) : items.map((r, i) => (
            <motion.div
              key={r.report_id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.04 }}
              className="bg-white rounded-2xl border border-slate-100 shadow-card p-4"
            >
              {/* Top row */}
              <div className="flex items-center justify-between mb-3">
                <DiscrepancyBadge label={r.label as DiscrepancyLabel} size="sm" />
                <span className={cn(
                  'text-xs font-medium px-2 py-0.5 rounded-full',
                  r.consensus === 'HIGH' ? 'bg-green-50 text-green-700' : 'bg-amber-50 text-amber-700'
                )}>
                  {r.consensus || '—'} consensus
                </span>
              </div>

              {/* ID + date */}
              <p className="text-xs font-mono text-slate-400 mb-1">{r.prescription_id.slice(0, 16)}…</p>
              <p className="text-xs text-slate-500 mb-3">{formatDate(r.created_at)}</p>

              {/* Confidence bar */}
              <div className="flex items-center gap-2 mb-4">
                <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                  <div className="h-full bg-primary-400 rounded-full"
                    style={{ width: `${(r.confidence || 0) * 100}%` }} />
                </div>
                <span className="text-xs text-slate-500 flex-shrink-0">
                  {formatConfidence(r.confidence || 0)}
                </span>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-2">
                <Link
                  href={`/analysis/${r.prescription_id}`}
                  className="flex-1 btn-secondary text-xs py-2 justify-center"
                >
                  View Analysis <ChevronRight size={12} />
                </Link>
                <button
                  onClick={() => handleDownload(r.prescription_id, r.pdf_ready)}
                  disabled={generating === r.prescription_id}
                  className="flex-1 btn-primary text-xs py-2 justify-center"
                >
                  {generating === r.prescription_id
                    ? <Loader2 size={12} className="animate-spin" />
                    : <Download size={12} />}
                  {r.pdf_ready ? 'Download PDF' : 'Generate PDF'}
                </button>
              </div>
            </motion.div>
          ))}

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
