export type UserRole = 'pharmacist' | 'admin' | 'viewer'

export interface User {
  id: string
  email: string
  full_name: string | null
  role: UserRole
  is_active: boolean
  created_at: string
}

export type PrescriptionStatus =
  | 'uploaded'
  | 'processing'
  | 'ocr_done'
  | 'validated'
  | 'analyzed'
  | 'failed'

export type DiscrepancyLabel =
  | 'No Discrepancy'
  | 'Omission'
  | 'Commission'
  | 'Inconsistency'
  | 'Illegibility'

export interface Drug {
  drug_name: string
  dose: string | null
  route: string | null
  frequency: string | null
  duration: string | null
  special_instructions: string | null
}

export interface ExtractedFields {
  patient_name: string | null
  patient_age: number | null
  patient_gender: string | null
  date: string | null
  doctor_name: string | null
  doctor_registration_no: string | null
  hospital_clinic: string | null
  signature_present: boolean | null
  diagnosis: string | null
  drugs: Drug[]
  illegible_fields: string[]
  overall_legibility_score: number
}

export interface RuleTriggered {
  rule_id: string
  description: string
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'
  type: 'Illegibility' | 'Omission' | 'Commission' | 'Inconsistency'
}

export interface EvidenceSource {
  source: string
  excerpt: string
  score: number
}

export interface DiscrepancyReport {
  id: string
  label: DiscrepancyLabel
  confidence: number
  rule_label: string
  llm_label: string
  llm_reason: string
  rules_triggered: RuleTriggered[]
  evidence_sources: EvidenceSource[]
  consensus: string
  pdf_ready?: boolean
  generated_at?: string | null
}

export interface PrescriptionListItem {
  id: string
  status: PrescriptionStatus
  input_type: string
  original_filename: string | null
  ocr_confidence: number | null
  created_at: string
}

export interface PrescriptionDetail extends PrescriptionListItem {
  extracted_fields: ExtractedFields | null
  drug_validation_result: Record<string, unknown> | null
  celery_job_id: string | null
  updated_at: string
}

export interface AnalysisResult {
  prescription_id: string
  status: string
  extracted_fields: ExtractedFields
  discrepancy: {
    label: DiscrepancyLabel
    confidence: number
    rule_triggered: string
    rules: RuleTriggered[]
    llm_reason: string
    evidence_sources: EvidenceSource[]
    consensus: string
  }
  pharmacist_feedback: {
    label: string | null
    note: string | null
    is_correct: boolean | null
    submitted_at: string | null
  }
}

export interface PaginatedResponse<T> {
  total: number
  page: number
  page_size: number
  items: T[]
}

export interface ReportListItem {
  report_id: string
  prescription_id: string
  label: DiscrepancyLabel
  confidence: number
  consensus: string
  pdf_ready: boolean
  created_at: string
}
