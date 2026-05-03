'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import { CheckCircle2, ArrowRight, ShieldCheck, Loader2 } from 'lucide-react'
import Navbar from '@/components/Navbar'
import UploadZone from '@/components/UploadZone'
import { prescriptionApi } from '@/lib/api'
import toast from 'react-hot-toast'

const STEPS = [
  { id: 'upload',   label: 'Upload',         desc: 'Prescription file received' },
  { id: 'ocr',      label: 'OCR Extraction', desc: 'Reading prescription fields' },
  { id: 'validate', label: 'Drug Validation',desc: 'Checking RxNorm & OpenFDA' },
  { id: 'analyse',  label: 'Clinical Analysis', desc: 'Rule engine + AI reasoning' },
]

type UploadState = 'idle' | 'uploading' | 'polling' | 'done' | 'failed'

const STATUS_STEP: Record<string, number> = {
  uploaded: 0, processing: 1, ocr_done: 1, validated: 2, analyzed: 3, failed: -1,
}

export default function UploadPage() {
  const router = useRouter()
  const [state,          setState]          = useState<UploadState>('idle')
  const [prescriptionId, setPrescriptionId] = useState<string | null>(null)
  const [currentStep,    setCurrentStep]    = useState(-1)

  const handleFile = async (file: File) => {
    setState('uploading')
    try {
      const { data } = await prescriptionApi.upload(file)
      const id = data.prescription_id
      setPrescriptionId(id)
      setState('polling')
      toast.success('File uploaded — analysis started')
      poll(id)
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Upload failed')
      setState('failed')
    }
  }

  const poll = async (id: string) => {
    const interval = setInterval(async () => {
      try {
        const { data } = await prescriptionApi.getStatus(id)
        const step = STATUS_STEP[data.status] ?? -1
        setCurrentStep(step)
        if (data.status === 'analyzed') {
          clearInterval(interval)
          setState('done')
          setTimeout(() => router.push(`/analysis/${id}`), 1200)
        } else if (data.status === 'failed') {
          clearInterval(interval)
          setState('failed')
          toast.error('Analysis failed. Please try again.')
        }
      } catch {
        clearInterval(interval)
        setState('failed')
      }
    }, 3000)
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <Navbar />
      <main className="max-w-2xl mx-auto px-4 py-12">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-primary-500">Upload Prescription</h1>
          <p className="text-slate-400 text-sm mt-1">
            Upload a prescription image or PDF to begin clinical validation
          </p>
        </div>

        <div className="card mb-6">
          <UploadZone onFile={handleFile} loading={state === 'uploading'} />
        </div>

        {/* Pipeline progress */}
        <AnimatePresence>
          {(state === 'polling' || state === 'done') && (
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              className="card"
            >
              <div className="flex items-center gap-2 mb-5">
                <ShieldCheck size={16} className="text-primary-400" />
                <p className="font-semibold text-slate-800">
                  {state === 'done' ? 'Analysis complete' : 'Analysis in progress…'}
                </p>
              </div>

              <div className="space-y-3">
                {STEPS.map((step, i) => {
                  const done    = i <= currentStep
                  const active  = i === currentStep + 1 && state === 'polling'
                  const pending = i > currentStep + 1

                  return (
                    <motion.div
                      key={step.id}
                      initial={{ opacity: 0, x: -8 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.08 }}
                      className={`flex items-center gap-3 p-3 rounded-xl border transition-colors ${
                        done   ? 'bg-green-50 border-green-100' :
                        active ? 'bg-primary-50 border-primary-100' :
                                 'bg-slate-50 border-slate-100'
                      }`}
                    >
                      <div className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 ${
                        done   ? 'bg-green-500' :
                        active ? 'bg-primary-500' : 'bg-slate-200'
                      }`}>
                        {done ? (
                          <CheckCircle2 size={13} className="text-white" />
                        ) : active ? (
                          <Loader2 size={12} className="text-white animate-spin" />
                        ) : (
                          <span className="text-xs text-slate-400 font-bold">{i + 1}</span>
                        )}
                      </div>
                      <div>
                        <p className={`text-sm font-medium ${
                          done ? 'text-green-700' : active ? 'text-primary-700' : 'text-slate-400'
                        }`}>{step.label}</p>
                        <p className="text-xs text-slate-400">{step.desc}</p>
                      </div>
                    </motion.div>
                  )
                })}
              </div>

              {state === 'done' && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="mt-4 p-3 bg-green-50 border border-green-100 rounded-xl flex items-center gap-2"
                >
                  <CheckCircle2 size={16} className="text-green-500" />
                  <p className="text-sm text-green-700 font-medium">
                    Redirecting to analysis report…
                  </p>
                  <ArrowRight size={14} className="text-green-500 ml-auto" />
                </motion.div>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {state === 'failed' && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="card border-red-100 bg-red-50 text-sm text-red-700"
          >
            Analysis failed. Please check the prescription image and try again.
            <button
              onClick={() => setState('idle')}
              className="block mt-3 text-xs underline"
            >
              Try again
            </button>
          </motion.div>
        )}

        {/* Guidelines */}
        <div className="mt-6 p-4 bg-primary-50 border border-primary-100 rounded-xl">
          <p className="text-xs font-semibold text-primary-600 mb-2">Accepted prescription formats</p>
          <ul className="space-y-1 text-xs text-primary-500">
            <li>• JPEG / PNG / WEBP prescription images</li>
            <li>• PDF prescriptions (scanned or digital)</li>
            <li>• Maximum file size: 20 MB</li>
            <li>• Best results with clear, well-lit images</li>
          </ul>
        </div>
      </main>
    </div>
  )
}
