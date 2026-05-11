'use client'
import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  X, CheckCircle2, XCircle, MinusCircle, HelpCircle,
  ClipboardList, ChevronDown, ChevronUp
} from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ChecklistItem } from '@/lib/types'

interface Props {
  items: ChecklistItem[]
  onClose: () => void
}

const RESULT_CONFIG = {
  yes:     { icon: CheckCircle2, color: 'text-green-600',  bg: 'bg-green-50',  border: 'border-green-200', label: 'Yes' },
  no:      { icon: XCircle,      color: 'text-red-600',    bg: 'bg-red-50',    border: 'border-red-200',   label: 'No' },
  partial: { icon: MinusCircle,  color: 'text-amber-500',  bg: 'bg-amber-50',  border: 'border-amber-200', label: 'Partial' },
  na:      { icon: MinusCircle,  color: 'text-slate-400',  bg: 'bg-slate-50',  border: 'border-slate-200', label: 'N/A' },
  unknown: { icon: HelpCircle,   color: 'text-amber-500',  bg: 'bg-amber-50',  border: 'border-amber-200', label: '?' },
}

// Map backend category codes to human-readable group names
const CATEGORY_LABELS: Record<string, string> = {
  patient:      'Patient Information',
  prescriber:   'Prescriber Information',
  completeness: 'Prescription Completeness',
  drug:         'Drug Details',
  safety:       'Safety Checks',
}

const GROUP_ORDER = [
  'Patient Information',
  'Prescriber Information',
  'Prescription Completeness',
  'Drug Details',
  'Safety Checks',
]

export default function ClinicalChecklistModal({ items, onClose }: Props) {
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(
    new Set(GROUP_ORDER)
  )

  const toggleGroup = (group: string) => {
    setExpandedGroups(prev => {
      const next = new Set(prev)
      if (next.has(group)) next.delete(group)
      else next.add(group)
      return next
    })
  }

  // Resolve group name from category field (backend uses 'category', not 'group')
  const getGroup = (item: ChecklistItem) => {
    const raw = (item as any).category || (item as any).group || 'other'
    return CATEGORY_LABELS[raw] ?? raw.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase())
  }

  // Group items
  const grouped = items.reduce<Record<string, (ChecklistItem & { _slno: number })[]>>((acc, item, idx) => {
    const g = getGroup(item)
    if (!acc[g]) acc[g] = []
    acc[g].push({ ...item, _slno: idx + 1 })
    return acc
  }, {})

  // Summary stats
  const yes     = items.filter(i => i.result === 'yes').length
  const no      = items.filter(i => i.result === 'no').length
  const na      = items.filter(i => i.result === 'na' || i.result === 'partial').length
  const total   = items.length

  // Render groups in defined order, then any extras
  const orderedGroups = [
    ...GROUP_ORDER.filter(g => grouped[g]),
    ...Object.keys(grouped).filter(g => !GROUP_ORDER.includes(g)),
  ]

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="absolute inset-0 bg-black/40 backdrop-blur-sm"
          onClick={onClose}
        />

        {/* Panel */}
        <motion.div
          initial={{ opacity: 0, y: 40, scale: 0.97 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 40, scale: 0.97 }}
          transition={{ type: 'spring', damping: 28, stiffness: 380 }}
          className="relative bg-white w-full sm:max-w-2xl sm:rounded-2xl rounded-t-2xl shadow-2xl
                     max-h-[90vh] flex flex-col overflow-hidden"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100 flex-shrink-0">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 bg-primary-50 rounded-lg flex items-center justify-center">
                <ClipboardList size={16} className="text-primary-500" />
              </div>
              <div>
                <h2 className="font-bold text-slate-800 text-base">Clinical Checklist</h2>
                <p className="text-xs text-slate-400">{total} parameters evaluated</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 rounded-xl hover:bg-slate-100 transition touch-manipulation"
              aria-label="Close"
            >
              <X size={18} className="text-slate-500" />
            </button>
          </div>

          {/* Summary bar */}
          <div className="flex items-center gap-3 px-5 py-3 bg-slate-50 border-b border-slate-100 flex-shrink-0">
            {[
              { count: yes,  label: 'Pass', color: 'text-green-700', bg: 'bg-green-100' },
              { count: no,   label: 'Fail', color: 'text-red-700',   bg: 'bg-red-100' },
              { count: na,   label: 'N/A',  color: 'text-slate-500', bg: 'bg-slate-200' },
            ].map(s => (
              <div key={s.label} className={cn('flex items-center gap-1.5 px-2.5 py-1 rounded-lg', s.bg)}>
                <span className={cn('text-sm font-bold', s.color)}>{s.count}</span>
                <span className={cn('text-xs font-medium', s.color)}>{s.label}</span>
              </div>
            ))}
            <div className="ml-auto text-xs text-slate-400">
              Score: <span className="font-semibold text-slate-600">
                {total > 0 ? Math.round((yes / (yes + no || 1)) * 100) : 0}%
              </span>
            </div>
          </div>

          {/* Scrollable body */}
          <div className="overflow-y-auto flex-1 px-5 py-4 space-y-3">
            {orderedGroups.map(group => {
              const groupItems = grouped[group]
              const isOpen     = expandedGroups.has(group)
              const groupNo    = groupItems.filter(i => i.result === 'no').length

              return (
                <div key={group} className="border border-slate-100 rounded-xl overflow-hidden">
                  {/* Group header */}
                  <button
                    onClick={() => toggleGroup(group)}
                    className="w-full flex items-center justify-between px-4 py-3 bg-slate-50
                               hover:bg-slate-100 transition text-left touch-manipulation"
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-slate-700">{group}</span>
                      <span className="text-xs text-slate-400">({groupItems.length})</span>
                      {groupNo > 0 && (
                        <span className="text-xs font-semibold text-red-600 bg-red-50 px-2 py-0.5 rounded-full">
                          {groupNo} issue{groupNo !== 1 ? 's' : ''}
                        </span>
                      )}
                    </div>
                    {isOpen ? <ChevronUp size={14} className="text-slate-400" /> : <ChevronDown size={14} className="text-slate-400" />}
                  </button>

                  {/* Inline table: Sl.No | Parameter | YES | NO */}
                  <AnimatePresence>
                    {isOpen && (
                      <motion.div
                        initial={{ height: 0 }}
                        animate={{ height: 'auto' }}
                        exit={{ height: 0 }}
                        className="overflow-hidden"
                      >
                        {/* Column headers */}
                        <div className="grid grid-cols-[3rem_1fr_3.5rem_3.5rem] bg-primary-700 text-white
                                        text-xs font-semibold px-0 py-1.5">
                          <span className="text-center">Sl.No</span>
                          <span className="pl-2">Parameter</span>
                          <span className="text-center">YES</span>
                          <span className="text-center">NO</span>
                        </div>

                        <div className="divide-y divide-slate-50">
                          {groupItems.map((item, idx) => {
                            const cfg  = RESULT_CONFIG[item.result as keyof typeof RESULT_CONFIG] ?? RESULT_CONFIG.unknown
                            const Icon = cfg.icon
                            const isNo = item.result === 'no'
                            const isYes = item.result === 'yes'

                            return (
                              <div
                                key={idx}
                                className={cn(
                                  'grid grid-cols-[3rem_1fr_3.5rem_3.5rem] items-start',
                                  isNo ? 'bg-red-50/50' : 'bg-white'
                                )}
                              >
                                {/* Sl.No */}
                                <span className="text-xs text-slate-400 text-center pt-3 font-mono">{item._slno}</span>

                                {/* Parameter + reasoning */}
                                <div className="py-2.5 pr-2 pl-2">
                                  <p className="text-sm font-medium text-slate-800">{item.parameter}</p>
                                  {item.reasoning && (
                                    <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">{item.reasoning}</p>
                                  )}
                                </div>

                                {/* YES checkmark */}
                                <div className="flex items-center justify-center pt-3">
                                  {isYes
                                    ? <CheckCircle2 size={16} className="text-green-600" />
                                    : <span className="w-4 h-4 rounded border border-slate-200 inline-block" />
                                  }
                                </div>

                                {/* NO cross */}
                                <div className="flex items-center justify-center pt-3">
                                  {isNo
                                    ? <XCircle size={16} className="text-red-500" />
                                    : item.result === 'na' || item.result === 'partial'
                                      ? <MinusCircle size={14} className="text-slate-300" />
                                      : <span className="w-4 h-4 rounded border border-slate-200 inline-block" />
                                  }
                                </div>
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

            {items.length === 0 && (
              <div className="text-center py-12 text-slate-400 text-sm">
                <ClipboardList size={32} className="mx-auto mb-3 opacity-30" />
                No checklist data available for this prescription.
              </div>
            )}
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  )
}
