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
    color: 'text-green-700',
    bg: 'bg-green-50',
    border: 'border-green-200',
    dot: 'bg-green-500',
    text: 'No issues detected',
  },
  'Omission': {
    color: 'text-amber-700',
    bg: 'bg-amber-50',
    border: 'border-amber-200',
    dot: 'bg-amber-500',
    text: 'Missing information',
  },
  'Commission': {
    color: 'text-red-700',
    bg: 'bg-red-50',
    border: 'border-red-200',
    dot: 'bg-red-500',
    text: 'Incorrect entry detected',
  },
  'Inconsistency': {
    color: 'text-orange-700',
    bg: 'bg-orange-50',
    border: 'border-orange-200',
    dot: 'bg-orange-500',
    text: 'Internal inconsistency',
  },
  'Illegibility': {
    color: 'text-gray-700',
    bg: 'bg-gray-100',
    border: 'border-gray-300',
    dot: 'bg-gray-500',
    text: 'Prescription unreadable',
  },
}

export const STATUS_CONFIG: Record<PrescriptionStatus, { label: string; color: string; bg: string }> = {
  uploaded:   { label: 'Uploaded',    color: 'text-blue-700',  bg: 'bg-blue-50' },
  processing: { label: 'Processing',  color: 'text-indigo-700',bg: 'bg-indigo-50' },
  ocr_done:   { label: 'OCR Done',    color: 'text-cyan-700',  bg: 'bg-cyan-50' },
  validated:  { label: 'Validated',   color: 'text-teal-700',  bg: 'bg-teal-50' },
  analyzed:   { label: 'Complete',    color: 'text-green-700', bg: 'bg-green-50' },
  failed:     { label: 'Failed',      color: 'text-red-700',   bg: 'bg-red-50' },
}

export const SEVERITY_CONFIG: Record<string, { color: string; bg: string }> = {
  CRITICAL: { color: 'text-red-700',    bg: 'bg-red-100' },
  HIGH:     { color: 'text-orange-700', bg: 'bg-orange-100' },
  MEDIUM:   { color: 'text-amber-700',  bg: 'bg-amber-100' },
  LOW:      { color: 'text-gray-600',   bg: 'bg-gray-100' },
}

export function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

export function formatConfidence(val: number) {
  return `${Math.round(val * 100)}%`
}
