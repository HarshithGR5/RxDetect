'use client'
import { motion } from 'framer-motion'
import { BookOpen, ExternalLink } from 'lucide-react'
import type { EvidenceSource } from '@/lib/types'

interface Props { sources: EvidenceSource[] }

export default function EvidencePanel({ sources }: Props) {
  if (!sources?.length) return (
    <div className="text-sm text-slate-400 py-6 text-center flex flex-col items-center gap-2">
      <BookOpen size={20} className="opacity-40" />
      No clinical guideline evidence retrieved
    </div>
  )

  return (
    <div className="space-y-3">
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
  )
}
