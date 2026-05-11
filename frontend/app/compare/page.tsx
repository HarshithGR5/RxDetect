'use client'
import { useMemo } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { useQueries } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  ArrowLeft, CheckCircle2, XCircle, Minus,
  AlertCircle, Columns2, Loader2
} from 'lucide-react'
import Navbar from '@/components/Navbar'
import DiscrepancyBadge from '@/components/DiscrepancyBadge'
import { prescriptionApi } from '@/lib/api'
import { cn } from '@/lib/utils'
import type { AnalysisResult, ChecklistItem, DiscrepancyLabel } from '@/lib/types'

// ── Result icon ──────────────────────────────────────────────────────────────
function ResultIcon({ result }: { result: ChecklistItem['result'] | undefined }) {
  if (!result || result === 'unknown') {
    return <Minus size={14} className="text-slate-300 mx-auto" />
  }
  if (result === 'yes') {
    return <CheckCircle2 size={14} className="text-green-500 mx-auto" />
  }
  if (result === 'no') {
    return <XCircle size={14} className="text-red-500 mx-auto" />
  }
  if (result === 'na') {
    return <span className="text-[10px] font-medium text-slate-400 block text-center">N/A</span>
  }
  if (result === 'partial') {
    return (
      <span className="inline-flex items-center justify-center w-3.5 h-3.5 rounded-full bg-amber-100 mx-auto">
        <span className="text-[8px] font-bold text-amber-600">P</span>
      </span>
    )
  }
  return <Minus size={14} className="text-slate-300 mx-auto" />
}

// ── Cell background by result ─────────────────────────────────────────────────
function cellBg(result: ChecklistItem['result'] | undefined): string {
  if (result === 'yes')     return 'bg-green-50'
  if (result === 'no')      return 'bg-red-50'
  if (result === 'partial') return 'bg-amber-50'
  return ''
}

export default function ComparePage() {
  const router       = useRouter()
  const searchParams = useSearchParams()
  const rawIds       = searchParams.get('ids') ?? ''
  const ids          = rawIds.split(',').filter(Boolean).slice(0, 4) // max 4

  const results = useQueries({
    queries: ids.map(id => ({
      queryKey: ['rx-result', id],
      queryFn:  () => prescriptionApi.getResult(id).then(r => r.data as AnalysisResult),
      retry: false,
    })),
  })

  const isLoading = results.some(r => r.isLoading)
  const hasError  = results.some(r => r.isError)
  const ready     = results.filter(r => r.data)

  // Build a master list of all unique checklist parameters in category order
  const { categories, paramsByCategory } = useMemo(() => {
    const categoryMap = new Map<string, string[]>()

    ready.forEach(({ data }) => {
      (data?.checklist_items ?? []).forEach(item => {
        if (!categoryMap.has(item.category)) categoryMap.set(item.category, [])
        const existing = categoryMap.get(item.category)!
        if (!existing.includes(item.parameter)) existing.push(item.parameter)
      })
    })

    return {
      categories:       [...categoryMap.keys()],
      paramsByCategory: categoryMap,
    }
  }, [ready])

  // Fast lookup: resultMap[id][parameter] → ChecklistItem
  const resultMaps = useMemo(() => {
    return ready.map(({ data }) => {
      const m = new Map<string, ChecklistItem>()
      ;(data?.checklist_items ?? []).forEach(item => m.set(item.parameter, item))
      return m
    })
  }, [ready])

  const colCount = ready.length

  return (
    <div className="min-h-screen bg-slate-50">
      <Navbar />
      <main className="max-w-screen-xl mx-auto px-4 sm:px-6 py-6 sm:py-8">

        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <button onClick={() => router.back()} className="btn-ghost p-2">
            <ArrowLeft size={16} />
          </button>
          <div>
            <h1 className="text-xl font-bold text-primary-500 flex items-center gap-2">
              <Columns2 size={18} />
              Prescription Comparison
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Side-by-side 27-parameter checklist for {ids.length} prescription{ids.length !== 1 ? 's' : ''}
            </p>
          </div>
        </div>

        {/* Loading */}
        {isLoading && (
          <div className="flex items-center justify-center py-24 text-slate-400 gap-3">
            <Loader2 size={20} className="animate-spin" />
            <span className="text-sm">Loading analysis results…</span>
          </div>
        )}

        {/* Error */}
        {!isLoading && hasError && (
          <div className="card border-amber-100 bg-amber-50 flex items-center gap-3 py-5">
            <AlertCircle size={18} className="text-amber-500 flex-shrink-0" />
            <div>
              <p className="font-semibold text-amber-700">Some results could not be loaded</p>
              <p className="text-sm text-amber-600 mt-0.5">
                Only prescriptions with completed analysis can be compared.
              </p>
            </div>
          </div>
        )}

        {/* No checklists */}
        {!isLoading && ready.length > 0 && categories.length === 0 && (
          <div className="card border-slate-100 text-center py-12">
            <AlertCircle size={28} className="mx-auto mb-3 text-slate-300" />
            <p className="font-semibold text-slate-500">No checklist data available</p>
            <p className="text-sm text-slate-400 mt-1">
              These prescriptions were analysed before the 27-parameter checklist was added.
              Re-run the analysis to generate checklists.
            </p>
          </div>
        )}

        {/* ── Comparison table ── */}
        {!isLoading && ready.length >= 1 && categories.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
          >
            {/* Prescription header cards — static grid classes (Tailwind JIT safe) */}
            <div className={cn('grid gap-3 mb-4', {
              'grid-cols-2': colCount === 1,
              'grid-cols-3': colCount === 2,
              'grid-cols-4': colCount === 3,
              'grid-cols-5': colCount === 4,
            })}>
              <div />
              {ready.map(({ data }, ci) => {
                const discrepancy = data?.discrepancy
                const label       = discrepancy?.label as DiscrepancyLabel | undefined
                const rxId        = data?.prescription_id ?? ids[ci]
                return (
                  <div key={rxId} className="bg-white rounded-xl border border-slate-100 shadow-sm p-3">
                    <p className="text-xs font-mono text-slate-400 truncate mb-1">{rxId?.slice(0, 12)}…</p>
                    {label && <DiscrepancyBadge label={label} size="sm" />}
                    {discrepancy?.confidence != null && (
                      <p className="text-xs text-slate-400 mt-1">
                        {Math.round(discrepancy.confidence * 100)}% confidence
                      </p>
                    )}
                  </div>
                )
              })}
            </div>

            {/* Parameter table */}
            <div className="bg-white rounded-2xl border border-slate-100 shadow-card overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm border-collapse">
                  {/* Sticky column headers */}
                  <thead>
                    <tr className="bg-slate-50 border-b border-slate-100">
                      <th className="text-left text-xs font-semibold text-slate-500 uppercase tracking-wider px-4 py-3 min-w-[220px] sticky left-0 bg-slate-50 z-10">
                        Parameter
                      </th>
                      {ready.map(({ data }, ci) => {
                        const rxId = data?.prescription_id ?? ids[ci]
                        return (
                          <th key={rxId} className="text-center text-xs font-semibold text-slate-500 uppercase tracking-wider px-4 py-3 min-w-[120px]">
                            Rx {ci + 1}
                          </th>
                        )
                      })}
                    </tr>
                  </thead>

                  <tbody>
                    {categories.map((category, ci) => (
                      <>
                        {/* Category divider row */}
                        <tr key={`cat-${ci}`} className="bg-primary-50/60">
                          <td
                            colSpan={colCount + 1}
                            className="px-4 py-2 text-xs font-semibold text-primary-700 uppercase tracking-widest sticky left-0"
                          >
                            {category}
                          </td>
                        </tr>

                        {/* Parameter rows */}
                        {(paramsByCategory.get(category) ?? []).map((param, pi) => {
                          const items = resultMaps.map(m => m.get(param))
                          const anyFail = items.some(it => it?.result === 'no')
                          return (
                            <tr
                              key={`${ci}-${pi}`}
                              className={cn(
                                'border-b border-slate-50 hover:bg-slate-50/50 transition-colors',
                                anyFail && 'bg-red-50/20'
                              )}
                            >
                              <td className="px-4 py-2.5 text-sm text-slate-700 sticky left-0 bg-white z-10 border-r border-slate-50">
                                <span className="text-xs text-slate-400 mr-1.5">{pi + 1}.</span>
                                {param}
                              </td>
                              {items.map((item, ii) => (
                                <td
                                  key={ii}
                                  className={cn(
                                    'px-4 py-2.5 text-center',
                                    cellBg(item?.result)
                                  )}
                                  title={item?.reasoning ?? undefined}
                                >
                                  <ResultIcon result={item?.result} />
                                </td>
                              ))}
                            </tr>
                          )
                        })}
                      </>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Legend */}
              <div className="flex items-center gap-5 px-4 py-3 border-t border-slate-100 bg-slate-50/40 flex-wrap">
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide">Legend</p>
                {[
                  { icon: <CheckCircle2 size={13} className="text-green-500" />, label: 'Pass' },
                  { icon: <XCircle size={13} className="text-red-500" />,       label: 'Fail' },
                  { icon: <span className="inline-flex items-center justify-center w-3.5 h-3.5 rounded-full bg-amber-100"><span className="text-[8px] font-bold text-amber-600">P</span></span>, label: 'Partial' },
                  { icon: <span className="text-[10px] font-medium text-slate-400">N/A</span>, label: 'Not applicable' },
                  { icon: <Minus size={13} className="text-slate-300" />,       label: 'Not checked' },
                ].map(({ icon, label }) => (
                  <div key={label} className="flex items-center gap-1.5 text-xs text-slate-500">
                    {icon} {label}
                  </div>
                ))}
                <p className="ml-auto text-xs text-slate-400 italic">
                  Hover a cell to read the system's reasoning for that parameter.
                </p>
              </div>
            </div>
          </motion.div>
        )}

      </main>
    </div>
  )
}
