'use client'
import { useState } from 'react'
import Link from 'next/link'
import { useQuery, useMutation } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  FileText, Download, ExternalLink, RefreshCw,
  CheckCircle2, AlertTriangle, ChevronRight
} from 'lucide-react'
import Navbar from '@/components/Navbar'
import DiscrepancyBadge from '@/components/DiscrepancyBadge'
import { TableRowSkeleton } from '@/components/Skeleton'
import { reportApi } from '@/lib/api'
import { formatDate, formatConfidence } from '@/lib/utils'
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
    <div className="min-h-screen bg-slate-50">
      <Navbar />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8">

        {/* Header */}
        <div className="flex items-center justify-between mb-8 flex-wrap gap-3">
          <div>
            <h1 className="text-2xl font-bold text-primary-500">Reports</h1>
            <p className="text-slate-400 text-sm mt-0.5">All prescription analysis reports</p>
          </div>
          <button onClick={() => refetch()} className="btn-ghost text-sm">
            <RefreshCw size={14} /> Refresh
          </button>
        </div>

        {/* Summary bar */}
        {items.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-8"
          >
            {(
              ['No Discrepancy', 'Omission', 'Commission', 'Inconsistency', 'Illegibility'] as DiscrepancyLabel[]
            ).map((label, i) => (
              <div
                key={label}
                className="card py-3 px-4 flex items-center gap-2.5"
              >
                <DiscrepancyBadge label={label} size="sm" showText={false} />
                <div>
                  <p className="text-lg font-bold text-slate-800">{labelCounts[label] || 0}</p>
                  <p className="text-xs text-slate-400 leading-tight">{label}</p>
                </div>
              </div>
            ))}
          </motion.div>
        )}

        {/* Table */}
        <div className="bg-white rounded-2xl border border-slate-100 shadow-card overflow-hidden">
          <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between">
            <p className="text-sm font-semibold text-slate-700">
              {total} report{total !== 1 ? 's' : ''} found
            </p>
            <Link href="/upload" className="btn-primary text-xs py-1.5 px-3">
              New Analysis
            </Link>
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
                        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                          r.consensus === 'HIGH'
                            ? 'bg-green-50 text-green-700'
                            : 'bg-amber-50 text-amber-700'
                        }`}>
                          {r.consensus || '—'}
                        </span>
                      </td>
                      <td className="px-4 py-3.5">
                        <div className="flex items-center gap-2">
                          <div className="w-16 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-primary-400 rounded-full"
                              style={{ width: `${(r.confidence || 0) * 100}%` }}
                            />
                          </div>
                          <span className="text-xs text-slate-500">
                            {formatConfidence(r.confidence || 0)}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-3.5 text-sm text-slate-500 text-xs">
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
                        <div className="flex items-center gap-2">
                          <Link
                            href={`/analysis/${r.prescription_id}`}
                            className="text-xs text-primary-500 hover:text-primary-700 flex items-center gap-1"
                          >
                            View <ExternalLink size={10} />
                          </Link>
                          <button
                            onClick={() => handleDownload(r.prescription_id, r.pdf_ready)}
                            disabled={generating === r.prescription_id}
                            className="text-xs text-slate-500 hover:text-slate-700 flex items-center gap-1"
                          >
                            {generating === r.prescription_id ? (
                              <div className="w-3 h-3 border border-slate-400 border-t-transparent rounded-full animate-spin" />
                            ) : (
                              <Download size={12} />
                            )}
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

          {/* Pagination */}
          {total > 20 && (
            <div className="flex items-center justify-between px-5 py-3 border-t border-slate-100">
              <p className="text-sm text-slate-400">
                Page {page} of {Math.ceil(total / 20)}
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
