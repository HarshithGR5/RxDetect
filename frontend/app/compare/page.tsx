'use client'
import { useMemo, useState, Suspense } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { useQueries } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ArrowLeft, CheckCircle2, XCircle, Minus,
  AlertCircle, Columns2, Loader2, Download,
  ChevronDown, ChevronRight
} from 'lucide-react'
import Navbar from '@/components/Navbar'
import DiscrepancyBadge from '@/components/DiscrepancyBadge'
import { prescriptionApi } from '@/lib/api'
import { cn } from '@/lib/utils'
import type { AnalysisResult, ChecklistItem, DiscrepancyLabel } from '@/lib/types'

function ResultIcon({ result }: { result: ChecklistItem['result'] | undefined }) {
  if (!result || result === 'unknown') return <Minus size={14} className="text-slate-600 mx-auto" />
  if (result === 'yes') return <CheckCircle2 size={14} className="text-emerald-400 mx-auto" />
  if (result === 'no') return <XCircle size={14} className="text-red-400 mx-auto" />
  if (result === 'na') return <span className="text-[10px] font-medium text-slate-500 block text-center">N/A</span>
  if (result === 'partial') return (
    <span className="inline-flex items-center justify-center w-3.5 h-3.5 rounded-full bg-amber-500/20 mx-auto">
      <span className="text-[8px] font-bold text-amber-400">P</span>
    </span>
  )
  return <Minus size={14} className="text-slate-600 mx-auto" />
}

function ResultPill({ result }: { result: ChecklistItem['result'] | undefined }) {
  if (result === 'yes')     return <span className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-400 bg-emerald-500/15 px-2 py-0.5 rounded-full"><CheckCircle2 size={10} />Pass</span>
  if (result === 'no')      return <span className="inline-flex items-center gap-1 text-xs font-semibold text-red-400 bg-red-500/15 px-2 py-0.5 rounded-full"><XCircle size={10} />Fail</span>
  if (result === 'partial') return <span className="inline-flex items-center gap-1 text-xs font-semibold text-amber-400 bg-amber-500/15 px-2 py-0.5 rounded-full">Partial</span>
  if (result === 'na')      return <span className="text-xs font-medium text-slate-500">N/A</span>
  return <span className="text-xs text-slate-600">—</span>
}

function cellBg(result: ChecklistItem['result'] | undefined): string {
  if (result === 'yes')     return 'bg-emerald-500/8'
  if (result === 'no')      return 'bg-red-500/8'
  if (result === 'partial') return 'bg-amber-500/8'
  return ''
}

function resultLabel(result: ChecklistItem['result'] | undefined): string {
  if (result === 'yes')     return 'PASS'
  if (result === 'no')      return 'FAIL'
  if (result === 'partial') return 'PARTIAL'
  if (result === 'na')      return 'N/A'
  return '—'
}

function CompareInner() {
  const router       = useRouter()
  const searchParams = useSearchParams()
  const rawIds       = searchParams.get('ids') ?? ''
  const ids          = rawIds.split(',').filter(Boolean)

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

  const { categories, paramsByCategory } = useMemo(() => {
    const categoryMap = new Map<string, string[]>()
    ready.forEach(({ data }) => {
      (data?.checklist_items ?? []).forEach(item => {
        if (!categoryMap.has(item.category)) categoryMap.set(item.category, [])
        const existing = categoryMap.get(item.category)!
        if (!existing.includes(item.parameter)) existing.push(item.parameter)
      })
    })
    return { categories: Array.from(categoryMap.keys()), paramsByCategory: categoryMap }
  }, [ready])

  const resultMaps = useMemo(() => {
    return ready.map(({ data }) => {
      const m = new Map<string, ChecklistItem>()
      ;(data?.checklist_items ?? []).forEach(item => m.set(item.parameter, item))
      return m
    })
  }, [ready])

  const colCount = ready.length

  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set())

  function toggleCategory(cat: string) {
    setExpandedCategories(prev => {
      const next = new Set(prev)
      if (next.has(cat)) next.delete(cat)
      else next.add(cat)
      return next
    })
  }

  function exportCSV() {
    const header = [
      'Parameter',
      'Category',
      ...ready.map((_, ci) => `Rx ${ci + 1}`),
      ...ready.map((_, ci) => `Rx ${ci + 1} Reasoning`),
    ]
    const rows: string[][] = [header]

    categories.forEach(category => {
      ;(paramsByCategory.get(category) ?? []).forEach(param => {
        const items = resultMaps.map(m => m.get(param))
        rows.push([
          param,
          category,
          ...items.map(it => resultLabel(it?.result)),
          ...items.map(it => it?.reasoning ?? ''),
        ])
      })
    })

    const csv = rows
      .map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(','))
      .join('\n')

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a')
    a.href     = url
    a.download = `rxdetect_comparison_${ids.map(id => id.slice(0, 6)).join('_')}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="min-h-screen bg-[#050d1a] has-bottom-nav">
      <Navbar />
      <main className="max-w-screen-xl mx-auto px-4 sm:px-6 py-6 sm:py-8">

        {/* Header */}
        <div className="flex items-center justify-between gap-3 mb-6 flex-wrap">
          <div className="flex items-center gap-3">
            <button onClick={() => router.back()} className="btn-ghost p-2">
              <ArrowLeft size={16} />
            </button>
            <div>
              <h1 className="text-xl font-bold text-white flex items-center gap-2">
                <Columns2 size={18} />
                Prescription Comparison
              </h1>
              <p className="text-xs text-slate-400 mt-0.5">
                Side-by-side 27-parameter checklist for {ids.length} prescription{ids.length !== 1 ? 's' : ''}
              </p>
            </div>
          </div>

          {!isLoading && ready.length > 0 && categories.length > 0 && (
            <button onClick={exportCSV} className="btn-secondary text-sm">
              <Download size={14} />
              Export CSV
            </button>
          )}
        </div>

        {/* Loading */}
        {isLoading && (
          <div className="flex items-center justify-center py-24 text-slate-500 gap-3">
            <Loader2 size={20} className="animate-spin" />
            <span className="text-sm">Loading analysis results…</span>
          </div>
        )}

        {/* Error */}
        {!isLoading && hasError && (
          <div className="card border-amber-500/20 bg-amber-500/10 flex items-center gap-3 py-5">
            <AlertCircle size={18} className="text-amber-400 flex-shrink-0" />
            <div>
              <p className="font-semibold text-amber-400">Some results could not be loaded</p>
              <p className="text-sm text-amber-400/70 mt-0.5">
                Only prescriptions with completed analysis can be compared.
              </p>
            </div>
          </div>
        )}

        {/* No checklists */}
        {!isLoading && ready.length > 0 && categories.length === 0 && (
          <div className="card text-center py-12">
            <AlertCircle size={28} className="mx-auto mb-3 text-slate-600" />
            <p className="font-semibold text-slate-400">No checklist data available</p>
            <p className="text-sm text-slate-500 mt-1">Re-run the analysis to generate checklists.</p>
          </div>
        )}

        {/* ── Content ── */}
        {!isLoading && ready.length >= 1 && categories.length > 0 && (
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>

            {/* Prescription header cards — shared by both views */}
            <div className="flex gap-3 mb-4 overflow-x-auto pb-1">
              <div className="w-[220px] flex-shrink-0 hidden sm:block" />
              {ready.map(({ data }, ci) => {
                const discrepancy = data?.discrepancy
                const label       = discrepancy?.label as DiscrepancyLabel | undefined
                const rxId        = data?.prescription_id ?? ids[ci]
                return (
                  <div key={rxId} className="card p-3 min-w-[130px] flex-shrink-0">
                    <p className="text-[10px] font-semibold text-teal-400 uppercase tracking-wide mb-1">Rx {ci + 1}</p>
                    <p className="text-xs font-mono text-slate-500 truncate mb-1.5">{rxId?.slice(0, 10)}…</p>
                    {label && <DiscrepancyBadge label={label} size="sm" />}
                    {discrepancy?.confidence != null && (
                      <p className="text-xs text-slate-500 mt-1.5">
                        {Math.round(discrepancy.confidence * 100)}% confidence
                      </p>
                    )}
                  </div>
                )
              })}
            </div>

            {/* ── Desktop table ── */}
            <div className="hidden sm:block bg-slate-900/60 border border-white/8 rounded-2xl overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm border-collapse">
                  <thead>
                    <tr className="bg-white/3 border-b border-white/5">
                      <th className="text-left text-xs font-semibold text-slate-500 uppercase tracking-wider px-4 py-3 min-w-[220px] sticky left-0 bg-slate-900/90 z-10">
                        Parameter
                      </th>
                      {ready.map(({ data }, ci) => (
                        <th key={data?.prescription_id ?? ids[ci]}
                          className="text-center text-xs font-semibold text-slate-500 uppercase tracking-wider px-4 py-3 min-w-[120px]">
                          Rx {ci + 1}
                        </th>
                      ))}
                    </tr>
                  </thead>

                  <tbody>
                    {categories.map((category, ci) => (
                      <>
                        <tr key={`cat-${ci}`} className="bg-teal-500/8">
                          <td colSpan={colCount + 1}
                            className="px-4 py-2 text-xs font-semibold text-teal-400 uppercase tracking-widest sticky left-0">
                            {category}
                          </td>
                        </tr>

                        {(paramsByCategory.get(category) ?? []).map((param, pi) => {
                          const items   = resultMaps.map(m => m.get(param))
                          const anyFail = items.some(it => it?.result === 'no')
                          return (
                            <tr
                              key={`${ci}-${pi}`}
                              className={cn(
                                'border-b border-white/5 hover:bg-white/3 transition-colors',
                                anyFail && 'bg-red-500/5'
                              )}
                            >
                              <td className="px-4 py-2.5 text-sm text-slate-300 sticky left-0 bg-slate-900/90 z-10 border-r border-white/5">
                                <span className="text-xs text-slate-600 mr-1.5">{pi + 1}.</span>
                                {param}
                              </td>
                              {items.map((item, ii) => (
                                <td
                                  key={ii}
                                  className={cn('px-4 py-2.5 text-center', cellBg(item?.result))}
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
              <div className="flex items-center gap-5 px-4 py-3 border-t border-white/5 bg-white/2 flex-wrap">
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Legend</p>
                {[
                  { icon: <CheckCircle2 size={13} className="text-emerald-400" />, label: 'Pass' },
                  { icon: <XCircle size={13} className="text-red-400" />,          label: 'Fail' },
                  { icon: <span className="inline-flex items-center justify-center w-3.5 h-3.5 rounded-full bg-amber-500/20"><span className="text-[8px] font-bold text-amber-400">P</span></span>, label: 'Partial' },
                  { icon: <span className="text-[10px] font-medium text-slate-500">N/A</span>, label: 'Not applicable' },
                  { icon: <Minus size={13} className="text-slate-600" />,           label: 'Not checked' },
                ].map(({ icon, label }) => (
                  <div key={label} className="flex items-center gap-1.5 text-xs text-slate-500">
                    {icon} {label}
                  </div>
                ))}
                <p className="ml-auto text-xs text-slate-600 italic hidden lg:block">
                  Hover a cell to read the system&apos;s reasoning for that parameter.
                </p>
              </div>
            </div>

            {/* ── Mobile accordion ── */}
            <div className="sm:hidden space-y-2">
              {categories.map(category => {
                const params    = paramsByCategory.get(category) ?? []
                const isOpen    = expandedCategories.has(category)
                const failCount = params.filter(p =>
                  resultMaps.some(m => m.get(p)?.result === 'no')
                ).length

                return (
                  <div key={category} className="bg-slate-900/60 border border-white/8 rounded-2xl overflow-hidden">
                    <button
                      onClick={() => toggleCategory(category)}
                      className="w-full flex items-center justify-between px-4 py-3.5 touch-manipulation"
                    >
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-teal-400 uppercase tracking-widest">
                          {category}
                        </span>
                        {failCount > 0 && (
                          <span className="text-[10px] font-bold text-red-400 bg-red-500/15 px-1.5 py-0.5 rounded-full">
                            {failCount} fail
                          </span>
                        )}
                        <span className="text-xs text-slate-600">{params.length} params</span>
                      </div>
                      {isOpen
                        ? <ChevronDown size={15} className="text-slate-500 flex-shrink-0" />
                        : <ChevronRight size={15} className="text-slate-500 flex-shrink-0" />
                      }
                    </button>

                    <AnimatePresence initial={false}>
                      {isOpen && (
                        <motion.div
                          key="body"
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          transition={{ duration: 0.2 }}
                          className="overflow-hidden"
                        >
                          <div className="border-t border-white/5 divide-y divide-white/5">
                            {params.map((param, pi) => {
                              const items   = resultMaps.map(m => m.get(param))
                              const anyFail = items.some(it => it?.result === 'no')
                              return (
                                <div
                                  key={pi}
                                  className={cn('px-4 py-3', anyFail && 'bg-red-500/5')}
                                >
                                  <p className="text-xs text-slate-400 mb-2">
                                    <span className="text-slate-600 mr-1">{pi + 1}.</span>
                                    {param}
                                  </p>
                                  <div className="flex flex-wrap gap-2">
                                    {items.map((item, ii) => (
                                      <div key={ii} className="flex items-center gap-1.5">
                                        <span className="text-[10px] text-slate-600 font-mono">Rx{ii + 1}:</span>
                                        <ResultPill result={item?.result} />
                                      </div>
                                    ))}
                                  </div>
                                  {items.some(it => it?.reasoning) && (
                                    <p className="text-[11px] text-slate-600 mt-2 leading-relaxed line-clamp-2">
                                      {items.find(it => it?.reasoning)?.reasoning}
                                    </p>
                                  )}
                                </div>
                              )
                            })}
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                )
              })}

              {/* Mobile legend */}
              <div className="flex items-center gap-3 px-1 pt-1 flex-wrap">
                {[
                  { icon: <CheckCircle2 size={11} className="text-emerald-400" />, label: 'Pass' },
                  { icon: <XCircle size={11} className="text-red-400" />,          label: 'Fail' },
                  { icon: <span className="text-[9px] font-medium text-amber-400">P</span>, label: 'Partial' },
                  { icon: <Minus size={11} className="text-slate-600" />,          label: '—' },
                ].map(({ icon, label }) => (
                  <div key={label} className="flex items-center gap-1 text-xs text-slate-500">
                    {icon} {label}
                  </div>
                ))}
              </div>
            </div>

          </motion.div>
        )}

      </main>
    </div>
  )
}

export default function ComparePage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-[#050d1a] flex items-center justify-center">
        <div className="flex items-center gap-3 text-slate-500">
          <Loader2 size={20} className="animate-spin" />
          <span className="text-sm">Loading comparison…</span>
        </div>
      </div>
    }>
      <CompareInner />
    </Suspense>
  )
}
