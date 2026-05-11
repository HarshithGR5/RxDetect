'use client'
import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { BookOpen, ExternalLink, ChevronDown, ChevronUp } from 'lucide-react'
import type { EvidenceSource } from '@/lib/types'

interface Props { sources: EvidenceSource[] }

export default function EvidencePanel({ sources }: Props) {
  const [open, setOpen] = useState(false)

  if (!sources?.length) return (
    <div className="text-sm text-slate-400 py-6 text-center flex flex-col items-center gap-2">
      <BookOpen size={20} className="opacity-40" />
      No clinical guideline evidence retrieved
    </div>
  )

  return (
    <div>
      {/* Collapsible toggle */}
      <button
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center justify-between text-sm font-medium text-primary-600
                   bg-blue-50 px-4 py-2.5 rounded-xl border border-blue-100
                   hover:bg-blue-100 transition touch-manipulation mb-2"
      >
        <span className="flex items-center gap-2">
          <BookOpen size={13} />
          {sources.length} guideline source{sources.length !== 1 ? 's' : ''} cited
        </span>
        {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </button>

      {/* Expanded evidence list */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="space-y-3 pt-1">
              {sources.map((src, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.06 }}
                  className="p-4 rounded-xl border border-blue-100 bg-blue-50/60"
                >
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div className="flex items-center gap-2">
                      <BookOpen size={13} className="text-primary-400 flex-shrink-0" />
                      <span className="text-xs font-semibold text-primary-600 leading-tight">{src.source}</span>
                    </div>
                    {src.score != null && (
                      <span className="text-xs text-slate-400 bg-white px-2 py-0.5 rounded-full border border-slate-100 flex-shrink-0">
                        {Math.round(src.score * 100)}% match
                      </span>
                    )}
                  </div>
                  {src.excerpt && (
                    <p className="text-xs text-slate-600 leading-relaxed line-clamp-4">{src.excerpt}</p>
                  )}
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
