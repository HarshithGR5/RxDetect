'use client'
import { cn } from '@/lib/utils'
import type { ExtractedFields } from '@/lib/types'
import { AlertCircle, CheckCircle2, User, Calendar, Stethoscope, Pill } from 'lucide-react'

interface Props {
  fields: ExtractedFields
  flaggedFields?: string[]
}

const FIELD_LABELS: Record<string, string> = {
  patient_name:          'Patient Name',
  patient_age:           'Age',
  patient_gender:        'Gender',
  date:                  'Date',
  doctor_name:           'Prescribing Doctor',
  doctor_registration_no:'Reg. No.',
  hospital_clinic:       'Hospital / Clinic',
  signature_present:     'Signature',
  diagnosis:             'Diagnosis',
}

export default function FieldExtractPanel({ fields, flaggedFields = [] }: Props) {
  const illegible = new Set(fields.illegible_fields || [])
  const flagged   = new Set(flaggedFields)

  const renderValue = (key: string, value: unknown) => {
    if (value === null || value === undefined) return <span className="text-slate-300">—</span>
    if (key === 'signature_present') return value ? '✓ Present' : '✗ Absent'
    return String(value)
  }

  const isBad = (key: string) => illegible.has(key) || flagged.has(key)
  const isEmpty = (val: unknown) => val === null || val === undefined || val === ''

  return (
    <div className="space-y-4">
      {/* Header fields */}
      <div>
        <p className="section-title">Patient & Prescription</p>
        <div className="space-y-1.5">
          {Object.entries(FIELD_LABELS).map(([key, label]) => {
            const val  = (fields as unknown as Record<string, unknown>)[key]
            const bad  = isBad(key)
            const miss = isEmpty(val)
            return (
              <div
                key={key}
                className={cn(
                  'flex items-start gap-2 px-3 py-2 rounded-lg text-sm',
                  bad ? 'bg-red-50 border border-red-100' :
                  miss ? 'bg-amber-50 border border-amber-100' :
                  'bg-slate-50'
                )}
              >
                <span className={cn(
                  'w-32 flex-shrink-0 text-xs font-medium mt-0.5',
                  bad ? 'text-red-600' : miss ? 'text-amber-600' : 'text-slate-400'
                )}>
                  {label}
                </span>
                <span className={cn(
                  'flex-1 font-medium',
                  bad ? 'text-red-700' : miss ? 'text-amber-500 italic' : 'text-slate-800'
                )}>
                  {miss ? 'Missing' : renderValue(key, val)}
                </span>
                {(bad || miss) && (
                  <AlertCircle size={13} className={bad ? 'text-red-400' : 'text-amber-400'} />
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* Drugs table */}
      {fields.drugs?.length > 0 && (
        <div>
          <p className="section-title">Prescribed Drugs</p>
          <div className="space-y-2">
            {fields.drugs.map((drug, i) => (
              <div key={i} className="border border-slate-100 rounded-xl p-3 bg-white">
                <div className="flex items-center gap-2 mb-2">
                  <Pill size={13} className="text-primary-400" />
                  <span className="font-semibold text-sm text-primary-700">{drug.drug_name}</span>
                </div>
                <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs text-slate-600">
                  {[
                    ['Dose', drug.dose],
                    ['Frequency', drug.frequency],
                    ['Route', drug.route],
                    ['Duration', drug.duration],
                  ].map(([label, val]) => (
                    <div key={label as string} className="flex gap-1.5">
                      <span className="text-slate-400 w-16 flex-shrink-0">{label}:</span>
                      <span className={cn('font-medium', !val && 'text-amber-500 italic')}>
                        {val || 'Missing'}
                      </span>
                    </div>
                  ))}
                </div>
                {drug.special_instructions && (
                  <p className="mt-2 text-xs text-slate-500 italic border-t border-slate-50 pt-1.5">
                    {drug.special_instructions}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Illegible fields */}
      {fields.illegible_fields?.length > 0 && (
        <div className="p-3 bg-gray-50 border border-gray-200 rounded-xl">
          <p className="text-xs font-semibold text-gray-600 mb-1">Illegible Fields</p>
          <div className="flex flex-wrap gap-1.5">
            {fields.illegible_fields.map(f => (
              <span key={f} className="text-xs bg-gray-200 text-gray-600 px-2 py-0.5 rounded">{f}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
