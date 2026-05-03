import { cn, STATUS_CONFIG } from '@/lib/utils'
import type { PrescriptionStatus } from '@/lib/types'

interface Props { status: PrescriptionStatus; pulse?: boolean }

export default function StatusPill({ status, pulse }: Props) {
  const cfg = STATUS_CONFIG[status] ?? { label: status, color: 'text-slate-600', bg: 'bg-slate-100' }
  return (
    <span className={cn('inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full', cfg.color, cfg.bg)}>
      <span className={cn('w-1.5 h-1.5 rounded-full',
        status === 'processing' ? 'bg-indigo-500 animate-pulse' :
        status === 'analyzed'   ? 'bg-green-500' :
        status === 'failed'     ? 'bg-red-500' : 'bg-current opacity-60'
      )} />
      {cfg.label}
    </span>
  )
}
