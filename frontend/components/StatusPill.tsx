import { cn, STATUS_CONFIG } from '@/lib/utils'
import type { PrescriptionStatus } from '@/lib/types'

interface Props { status: PrescriptionStatus; pulse?: boolean }

export default function StatusPill({ status }: Props) {
  const cfg = STATUS_CONFIG[status] ?? { label: status, color: 'text-slate-400', bg: 'bg-slate-500/15' }
  return (
    <span className={cn('inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full', cfg.color, cfg.bg)}>
      <span className={cn('w-1.5 h-1.5 rounded-full flex-shrink-0',
        status === 'processing' ? 'bg-indigo-400 animate-pulse' :
        status === 'analyzed'   ? 'bg-emerald-400' :
        status === 'failed'     ? 'bg-red-400' : 'bg-current opacity-60'
      )} />
      {cfg.label}
    </span>
  )
}
