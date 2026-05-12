'use client'
import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'

interface Props {
  score: number
  label?: string
}

export default function ClarityIndicator({ score, label = 'Data Clarity' }: Props) {
  const pct = Math.round(score * 100)
  const color =
    pct >= 80 ? 'bg-emerald-500' :
    pct >= 60 ? 'bg-amber-400'   :
                'bg-red-400'
  const textColor =
    pct >= 80 ? 'text-emerald-400' :
    pct >= 60 ? 'text-amber-400'   :
                'text-red-400'

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs">
        <span className="text-slate-500 font-medium">{label}</span>
        <span className={cn('font-semibold', textColor)}>{pct}%</span>
      </div>
      <div className="h-1.5 w-full bg-white/8 rounded-full overflow-hidden">
        <motion.div
          className={cn('h-full rounded-full', color)}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.7, ease: 'easeOut' }}
        />
      </div>
    </div>
  )
}
