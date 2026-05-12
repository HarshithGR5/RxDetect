'use client'
import { motion } from 'framer-motion'
import { cn, LABEL_CONFIG } from '@/lib/utils'
import type { DiscrepancyLabel } from '@/lib/types'
import { CheckCircle2, AlertTriangle, XCircle, AlertOctagon, EyeOff } from 'lucide-react'

const ICONS: Record<DiscrepancyLabel, React.ElementType> = {
  'No Discrepancy': CheckCircle2,
  'Omission':       AlertTriangle,
  'Commission':     XCircle,
  'Inconsistency':  AlertOctagon,
  'Illegibility':   EyeOff,
}

interface Props {
  label: DiscrepancyLabel
  size?: 'sm' | 'md' | 'lg'
  showText?: boolean
  animated?: boolean
}

export default function DiscrepancyBadge({ label, size = 'md', showText = true, animated = false }: Props) {
  const cfg  = LABEL_CONFIG[label]
  const Icon = ICONS[label]

  const sizeClass = {
    sm: 'text-xs px-2.5 py-1 gap-1.5',
    md: 'text-sm px-3.5 py-1.5 gap-2',
    lg: 'text-base px-5 py-2.5 gap-2.5',
  }[size]

  const iconSize = { sm: 12, md: 14, lg: 18 }[size]

  const badge = (
    <span className={cn(
      'inline-flex items-center font-semibold rounded-full border',
      cfg.color, cfg.bg, cfg.border, sizeClass
    )}>
      <Icon size={iconSize} />
      {showText && label}
    </span>
  )

  if (!animated) return badge

  return (
    <motion.div
      initial={{ scale: 0.85, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ type: 'spring', stiffness: 300, damping: 22 }}
    >
      {badge}
    </motion.div>
  )
}
