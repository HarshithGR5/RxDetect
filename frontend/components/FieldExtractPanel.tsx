'use client'
import { cn } from '@/lib/utils'
import type { ExtractedFields } from '@/lib/types'
import { AlertCircle, Pill } from 'lucide-react'

interface Props {
  fields: ExtractedFields
  flaggedFields?: string[]
}

const PATIENT_FIELDS: [string, string][] = [
  ['patient_name',             'Patient Name'],
  ['patient_age',              'Age'],
  ['patient_gender',           'Gender'],
  ['patient_weight',           'Weight'],
  ['date',                     'Date'],
  ['allergy_history',          'Allergy History'],
  ['previous_medical_history', 'Medical History'],
  ['diagnosis',                'Diagnosis'],
]

const PRESCRIBER_FIELDS: [string, string][] = [
  ['doctor_name',            'Doctor Name'],
  ['doctor_qualification',   'Qualification'],
  ['doctor_registration_no', 'Reg. No.'],
  ['hospital_clinic',        'Hospital / Clinic'],
  ['clinic_address',         'Clinic Address'],
  ['contact_details',        'Contact'],
  ['signature_present',      'Signature'],
]

const FIELD_LABEL_MAP: Record<string, string> = Object.fromEntries([
  ...PATIENT_FIELDS,
  ...PRESCRIBER_FIELDS,
])

export function humanFieldLabel(key: string): string {
  return (
    FIELD_LABEL_MAP[key] ??
    key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
  )
}

export default function FieldExtractPanel({ fields, flaggedFields = [] }: Props) {
  const illegible = new Set(fields.illegible_fields || [])
  const flagged   = new Set(flaggedFields)

  const renderValue = (key: string, value: unknown) => {
    if (value === null || value === undefined) return <span className="text-slate-600">—</span>
    if (key === 'signature_present') return value ? '✓ Present' : '✗ Absent'
    return String(value)
  }

  const isBad   = (key: string) => illegible.has(key) || flagged.has(key)
  const isEmpty = (val: unknown) => val === null || val === undefined || val === ''

  const renderRow = (key: string, label: string) => {
    const val  = (fields as unknown as Record<string, unknown>)[key]
    const bad  = isBad(key)
    const miss = isEmpty(val)
    return (
      <div
        key={key}
        className={cn(
          'flex items-start gap-2 px-3 py-2 rounded-lg text-sm',
          bad  ? 'bg-red-500/10 border border-red-500/20' :
          miss ? 'bg-amber-500/10 border border-amber-500/20' :
          'bg-white/3'
        )}
      >
        <span className={cn(
          'w-28 flex-shrink-0 text-xs font-medium mt-0.5',
          bad ? 'text-red-400' : miss ? 'text-amber-400' : 'text-slate-500'
        )}>
          {label}
        </span>
        <span className={cn(
          'flex-1 font-medium break-words',
          bad ? 'text-red-300' : miss ? 'text-amber-400 italic' : 'text-slate-200'
        )}>
          {miss ? 'Missing' : renderValue(key, val)}
        </span>
        {(bad || miss) && (
          <AlertCircle size={13} className={bad ? 'text-red-400' : 'text-amber-400'} />
        )}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div>
        <p className="section-title">Patient &amp; Clinical</p>
        <div className="space-y-1.5">
          {PATIENT_FIELDS.map(([key, label]) => renderRow(key, label))}
        </div>
      </div>

      <div>
        <p className="section-title">Prescriber</p>
        <div className="space-y-1.5">
          {PRESCRIBER_FIELDS.map(([key, label]) => renderRow(key, label))}
        </div>
      </div>

      {fields.drugs?.length > 0 && (
        <div>
          <p className="section-title">Prescribed Drugs</p>
          <div className="space-y-2">
            {fields.drugs.map((drug, i) => (
              <div key={i} className="border border-white/8 rounded-xl p-3 bg-white/3">
                <div className="flex items-center gap-2 mb-2">
                  <Pill size={13} className="text-teal-400" />
                  <span className="text-sm font-semibold text-white">{drug.drug_name}</span>
                  {drug.is_high_alert && (
                    <span className="text-[10px] bg-red-500/15 text-red-400 px-1.5 py-0.5 rounded font-semibold">HIGH-ALERT</span>
                  )}
                  {drug.narrow_therapeutic_index && (
                    <span className="text-[10px] bg-amber-500/15 text-amber-400 px-1.5 py-0.5 rounded font-semibold">NTI</span>
                  )}
                </div>
                <div className="grid grid-cols-2 gap-1 text-xs text-slate-500">
                  {drug.dose      && <span>Dose: <span className="text-slate-300 font-medium">{drug.dose}</span></span>}
                  {drug.route     && <span>Route: <span className="text-slate-300 font-medium">{drug.route}</span></span>}
                  {drug.frequency && <span>Freq: <span className="text-slate-300 font-medium">{drug.frequency}</span></span>}
                  {drug.duration  && <span>Duration: <span className="text-slate-300 font-medium">{drug.duration}</span></span>}
                </div>
                {drug.generic_name && (
                  <p className="text-xs text-slate-500 mt-1">
                    Generic: <span className="text-slate-400">{drug.generic_name}</span>
                  </p>
                )}
                {drug.special_instructions && (
                  <p className="text-xs text-slate-500 mt-1.5 italic">{drug.special_instructions}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {fields.illegible_fields?.length > 0 && (
        <div className="p-3 bg-red-500/10 rounded-xl border border-red-500/20">
          <p className="text-xs font-semibold text-red-400 mb-1">Illegible Fields</p>
          <div className="flex flex-wrap gap-1">
            {fields.illegible_fields.map((f, i) => (
              <span key={i} className="text-xs bg-red-500/15 text-red-300 px-2 py-0.5 rounded">
                {humanFieldLabel(f)}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
