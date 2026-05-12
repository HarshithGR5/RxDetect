'use client'
import { motion } from 'framer-motion'
import { cn, SEVERITY_CONFIG } from '@/lib/utils'
import type { RuleTriggered } from '@/lib/types'
import { ShieldAlert, AlertTriangle, Info, ChevronRight } from 'lucide-react'

const TYPE_ICON: Record<string, React.ElementType> = {
  Commission:    ShieldAlert,
  Omission:      AlertTriangle,
  Inconsistency: Info,
  Illegibility:  AlertTriangle,
}

interface Props { rules: RuleTriggered[] }

export default function RuleFindings({ rules }: Props) {
  if (!rules?.length) return (
    <div className="text-sm text-slate-500 py-4 text-center">No rule violations detected</div>
  )

  return (
    <div className="space-y-2">
      {rules.map((r, i) => {
        const Icon = TYPE_ICON[r.type] || ChevronRight
        const sev  = SEVERITY_CONFIG[r.severity] || SEVERITY_CONFIG.LOW
        return (
          <motion.div
            key={i}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.05 }}
            className="flex items-start gap-3 p-3 rounded-xl border border-white/8 bg-white/3"
          >
            <div className={cn('mt-0.5 p-1 rounded-lg flex-shrink-0', sev.bg)}>
              <Icon size={12} className={sev.color} />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 flex-wrap">
                <span className={cn('text-xs font-semibold px-2 py-0.5 rounded-full', sev.bg, sev.color)}>
                  {r.severity}
                </span>
                <span className="text-xs text-slate-500 font-mono">{r.rule_id}</span>
                <span className="text-xs text-slate-500 bg-white/5 px-1.5 py-0.5 rounded">{r.type}</span>
              </div>
              <p className="text-sm text-slate-300 mt-1 leading-snug">{r.description}</p>
            </div>
          </motion.div>
        )
      })}
    </div>
  )
}
