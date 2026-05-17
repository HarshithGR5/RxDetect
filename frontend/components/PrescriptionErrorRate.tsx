import { useMemo } from 'react'
import { motion } from 'framer-motion'
import { Activity, ClipboardList, AlertTriangle } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ChecklistItem } from '@/lib/types'

interface Props {
  items: ChecklistItem[]
  onViewChecklist?: () => void
}

const CATEGORIES: { key: string; label: string }[] = [
  { key: 'patient',      label: 'Patient' },
  { key: 'prescriber',   label: 'Prescriber' },
  { key: 'drug',         label: 'Drug' },
  { key: 'safety',       label: 'Safety' },
  { key: 'completeness', label: 'Completeness' },
]

type Severity = 'none' | 'low' | 'moderate' | 'high' | 'critical'

const SEVERITY_CFG: Record<Severity, {
  label: string; color: string; trackFill: string
  border: string; bg: string; barColor: string
}> = {
  none:     { label: 'No Errors',      color: 'text-emerald-400', trackFill: '#34d399', border: 'border-emerald-500/25', bg: 'bg-emerald-500/6',  barColor: 'bg-emerald-400' },
  low:      { label: 'Low Risk',       color: 'text-emerald-400', trackFill: '#34d399', border: 'border-emerald-500/25', bg: 'bg-emerald-500/6',  barColor: 'bg-emerald-400' },
  moderate: { label: 'Moderate Risk',  color: 'text-amber-400',   trackFill: '#fbbf24', border: 'border-amber-500/25',   bg: 'bg-amber-500/6',    barColor: 'bg-amber-400' },
  high:     { label: 'High Risk',      color: 'text-orange-400',  trackFill: '#f97316', border: 'border-orange-500/25',  bg: 'bg-orange-500/6',   barColor: 'bg-orange-400' },
  critical: { label: 'Critical Risk',  color: 'text-red-400',     trackFill: '#f87171', border: 'border-red-500/25',     bg: 'bg-red-500/6',      barColor: 'bg-red-400' },
}

function getSeverity(rate: number): Severity {
  if (rate === 0)   return 'none'
  if (rate <= 15)   return 'low'
  if (rate <= 40)   return 'moderate'
  if (rate <= 65)   return 'high'
  return 'critical'
}

function computeRate(items: ChecklistItem[]) {
  const na        = items.filter(i => i.result === 'na').length
  const no        = items.filter(i => i.result === 'no').length
  const partial   = items.filter(i => i.result === 'partial').length
  const yes       = items.filter(i => i.result === 'yes').length
  const evaluable = items.length - na
  const score     = no + partial * 0.5
  const rate      = evaluable > 0 ? Math.round((score / evaluable) * 100) : 0
  return { rate, no, partial, yes, na, evaluable, total: items.length }
}

function ArcGauge({ rate, color }: { rate: number; color: string }) {
  const R = 30
  const cx = 42, cy = 42
  const circumference = 2 * Math.PI * R
  const arcLength     = circumference * 0.75          // 270° arc
  const fillLength    = arcLength * Math.min(rate, 100) / 100

  return (
    <svg width="84" height="84" viewBox="0 0 84 84" className="flex-shrink-0">
      <circle
        cx={cx} cy={cy} r={R}
        fill="none"
        stroke="#1e293b"
        strokeWidth={6}
        strokeDasharray={`${arcLength} ${circumference}`}
        strokeLinecap="round"
        transform={`rotate(135 ${cx} ${cy})`}
      />
      <motion.circle
        cx={cx} cy={cy} r={R}
        fill="none"
        stroke={color}
        strokeWidth={6}
        strokeLinecap="round"
        strokeDasharray={`${arcLength} ${circumference}`}
        initial={{ strokeDashoffset: arcLength }}
        animate={{ strokeDashoffset: arcLength - fillLength }}
        transition={{ duration: 1, ease: 'easeOut', delay: 0.2 }}
        transform={`rotate(135 ${cx} ${cy})`}
        style={{ filter: `drop-shadow(0 0 4px ${color}66)` }}
      />
      <text
        x={cx} y={cy - 3}
        textAnchor="middle"
        dominantBaseline="middle"
        fill={color}
        fontSize="13"
        fontWeight="700"
        fontFamily="ui-monospace, monospace"
      >
        {rate}%
      </text>
      <text
        x={cx} y={cy + 11}
        textAnchor="middle"
        dominantBaseline="middle"
        fill="#64748b"
        fontSize="7"
        fontWeight="600"
        fontFamily="ui-sans-serif, sans-serif"
        letterSpacing="0.05em"
      >
        ERR RATE
      </text>
    </svg>
  )
}

export default function PrescriptionErrorRate({ items, onViewChecklist }: Props) {
  const { rate, no, partial, yes, na, evaluable, total } = useMemo(
    () => computeRate(items),
    [items],
  )
  const severity = getSeverity(rate)
  const cfg      = SEVERITY_CFG[severity]

  const catStats = useMemo(() =>
    CATEGORIES
      .map(({ key, label }) => {
        const catItems  = items.filter(i => (i as any).category === key)
        if (!catItems.length) return null
        const { rate: r, no: n } = computeRate(catItems)
        return { key, label, rate: r, failed: n, total: catItems.length }
      })
      .filter(Boolean) as { key: string; label: string; rate: number; failed: number; total: number }[],
    [items],
  )

  return (
    <div className={cn('card border', cfg.border, cfg.bg)}>
      <div className="flex items-center gap-2 mb-3">
        <Activity size={13} className={cfg.color} />
        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wide">
          Prescription Error Rate
        </h3>
        {no > 0 && (
          <span className="ml-auto text-[10px] font-bold bg-red-500/15 text-red-400 px-1.5 py-0.5 rounded-full">
            {no} failed
          </span>
        )}
      </div>

      <div className="flex items-center gap-4 mb-4">
        <ArcGauge rate={rate} color={cfg.trackFill} />

        <div className="flex-1 min-w-0">
          <div className="flex items-baseline gap-1.5 mb-0.5">
            <span className={cn('text-2xl font-extrabold font-mono', cfg.color)}>{rate}%</span>
            <span className={cn('text-xs font-semibold', cfg.color)}>{cfg.label}</span>
          </div>
          <div className="text-xs text-slate-500 space-y-0.5 mt-1">
            <p>
              <span className="text-emerald-400 font-medium">{yes} pass</span>
              {no > 0   && <span className="text-red-400 font-medium">  · {no} fail</span>}
              {partial > 0 && <span className="text-amber-400 font-medium"> · {partial} partial</span>}
              {na > 0   && <span className="text-slate-500">  · {na} N/A</span>}
            </p>
            <p>{evaluable} of {total} params evaluable</p>
          </div>

          {severity !== 'none' && (
            <div className="mt-2 flex items-start gap-1.5">
              <AlertTriangle size={10} className={cn('mt-0.5 flex-shrink-0', cfg.color)} />
              <p className={cn('text-[10px] leading-snug', cfg.color)}>
                {severity === 'low'      && 'Minor issues detected. Review flagged parameters.'}
                {severity === 'moderate' && 'Several parameters failed. Pharmacist review recommended.'}
                {severity === 'high'     && 'High error rate. Clinical review required before dispensing.'}
                {severity === 'critical' && 'Critical error rate. Do not dispense without full pharmacist review.'}
              </p>
            </div>
          )}
        </div>
      </div>

      {catStats.length > 0 && (
        <div className="space-y-1.5 pt-3 border-t border-white/5">
          {catStats.map(({ key, label, rate: r, failed }) => {
            const barColor =
              r === 0   ? 'bg-emerald-400'
              : r <= 20 ? 'bg-amber-400'
              : r <= 50 ? 'bg-orange-400'
              : 'bg-red-400'

            return (
              <div key={key} className="flex items-center gap-2">
                <span className="text-[10px] text-slate-500 w-20 flex-shrink-0 truncate">{label}</span>
                <div className="flex-1 h-1.5 bg-white/5 rounded-full overflow-hidden">
                  <motion.div
                    className={cn('h-full rounded-full', barColor)}
                    initial={{ width: 0 }}
                    animate={{ width: `${r}%` }}
                    transition={{ duration: 0.7, ease: 'easeOut', delay: 0.1 }}
                  />
                </div>
                <span className={cn('text-[10px] font-mono w-8 text-right flex-shrink-0',
                  r === 0 ? 'text-slate-500' : r <= 20 ? 'text-amber-400' : r <= 50 ? 'text-orange-400' : 'text-red-400'
                )}>
                  {r > 0 ? `${r}%` : '—'}
                </span>
                {failed > 0 && (
                  <span className="text-[9px] text-red-400 flex-shrink-0">{failed}✗</span>
                )}
              </div>
            )
          })}
        </div>
      )}

      {onViewChecklist && (
        <button
          onClick={onViewChecklist}
          className="w-full mt-3 flex items-center gap-1.5 text-xs text-slate-500 hover:text-teal-400 transition pt-3 border-t border-white/5"
        >
          <ClipboardList size={11} />
          View full 27-param checklist
        </button>
      )}
    </div>
  )
}
