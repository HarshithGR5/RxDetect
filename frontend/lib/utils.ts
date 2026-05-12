import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'
import type { DiscrepancyLabel, PrescriptionStatus } from './types'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export const LABEL_CONFIG: Record<DiscrepancyLabel, {
  color: string
  bg: string
  border: string
  dot: string
  text: string
}> = {
  'No Discrepancy': {
    color:  'text-emerald-400',
    bg:     'bg-emerald-500/15',
    border: 'border-emerald-500/30',
    dot:    'bg-emerald-400',
    text:   'No issues detected',
  },
  'Omission': {
    color:  'text-amber-400',
    bg:     'bg-amber-500/15',
    border: 'border-amber-500/30',
    dot:    'bg-amber-400',
    text:   'Missing information',
  },
  'Commission': {
    color:  'text-red-400',
    bg:     'bg-red-500/15',
    border: 'border-red-500/30',
    dot:    'bg-red-400',
    text:   'Incorrect entry detected',
  },
  'Inconsistency': {
    color:  'text-orange-400',
    bg:     'bg-orange-500/15',
    border: 'border-orange-500/30',
    dot:    'bg-orange-400',
    text:   'Internal inconsistency',
  },
  'Illegibility': {
    color:  'text-slate-400',
    bg:     'bg-slate-500/15',
    border: 'border-slate-500/30',
    dot:    'bg-slate-400',
    text:   'Prescription unreadable',
  },
}

export const STATUS_CONFIG: Record<PrescriptionStatus, { label: string; color: string; bg: string }> = {
  uploaded:   { label: 'Uploaded',   color: 'text-blue-400',   bg: 'bg-blue-500/15' },
  processing: { label: 'Processing', color: 'text-indigo-400', bg: 'bg-indigo-500/15' },
  ocr_done:   { label: 'OCR Done',   color: 'text-cyan-400',   bg: 'bg-cyan-500/15' },
  validated:  { label: 'Validated',  color: 'text-teal-400',   bg: 'bg-teal-500/15' },
  analyzed:   { label: 'Complete',   color: 'text-emerald-400',bg: 'bg-emerald-500/15' },
  failed:     { label: 'Failed',     color: 'text-red-400',    bg: 'bg-red-500/15' },
}

export const SEVERITY_CONFIG: Record<string, { color: string; bg: string }> = {
  CRITICAL: { color: 'text-red-400',    bg: 'bg-red-500/15' },
  HIGH:     { color: 'text-orange-400', bg: 'bg-orange-500/15' },
  MEDIUM:   { color: 'text-amber-400',  bg: 'bg-amber-500/15' },
  LOW:      { color: 'text-slate-400',  bg: 'bg-slate-500/15' },
}

export function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

export function formatConfidence(val: number) {
  return `${Math.round(val * 100)}%`
}
