'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import { CheckCircle2, ArrowRight, ShieldCheck, Loader2, XCircle } from 'lucide-react'
import Navbar from '@/components/Navbar'
import UploadZone from '@/components/UploadZone'
import { prescriptionApi } from '@/lib/api'
import toast from 'react-hot-toast'

const STEPS = [
  { id: 'upload',   label: 'File Upload',       desc: 'Prescription received & stored' },
  { id: 'ocr',      label: 'OCR Extraction',    desc: 'Reading fields via GPT-4o Vision' },
  { id: 'validate', label: 'Drug Validation',   desc: 'Checking RxNorm & OpenFDA' },
  { id: 'analyse',  label: 'Clinical Analysis', desc: '27-param checklist + AI reasoning' },
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
    <div className="min-h-screen bg-[#050d1a] has-bottom-nav">
      <Navbar />
      <main className="max-w-2xl mx-auto px-4 py-6 sm:py-12">

        <div className="mb-5 sm:mb-8">
          <h1 className="text-xl sm:text-2xl font-bold text-white">Upload Prescription</h1>
          <p className="text-slate-400 text-sm mt-1">
            Upload an image or PDF — or use your camera — to begin AI-powered clinical validation
          </p>
        </div>

        <div className="card mb-5">
          <UploadZone onFile={handleFile} loading={state === 'uploading'} />
        </div>

        {/* Pipeline progress */}
        <AnimatePresence>
          {(state === 'polling' || state === 'done') && (
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="card mb-5"
            >
              <div className="flex items-center gap-2 mb-5">
                <ShieldCheck size={16} className="text-teal-400" />
                <p className="font-semibold text-white">
                  {state === 'done' ? 'Analysis complete' : 'Analysis in progress…'}
                </p>
                {state === 'polling' && (
                  <Loader2 size={14} className="text-teal-400 animate-spin ml-auto" />
                )}
              </div>

              <div className="space-y-2.5">
                {STEPS.map((step, i) => {
                  const done   = i <= currentStep
                  const active = i === currentStep + 1 && state === 'polling'

                  return (
                    <motion.div
                      key={step.id}
                      initial={{ opacity: 0, x: -8 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.08 }}
                      className={`flex items-center gap-3 p-3 rounded-xl border transition-colors ${
                        done   ? 'bg-emerald-500/10 border-emerald-500/20' :
                        active ? 'bg-teal-500/10 border-teal-500/20' :
                                 'bg-white/3 border-white/8'
                      }`}
                    >
                      <div className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 ${
                        done   ? 'bg-emerald-500' :
                        active ? 'bg-teal-500' : 'bg-white/10'
                      }`}>
                        {done ? (
                          <CheckCircle2 size={14} className="text-white" />
                        ) : active ? (
                          <Loader2 size={13} className="text-white animate-spin" />
                        ) : (
                          <span className="text-xs text-slate-500 font-bold">{i + 1}</span>
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className={`text-sm font-medium ${
                          done ? 'text-emerald-400' : active ? 'text-teal-400' : 'text-slate-500'
                        }`}>{step.label}</p>
                        <p className="text-xs text-slate-500 truncate">{step.desc}</p>
                      </div>
                      {done && (
                        <CheckCircle2 size={14} className="text-emerald-400 flex-shrink-0" />
                      )}
                    </motion.div>
                  )
                })}
              </div>

              {state === 'done' && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="mt-4 p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl flex items-center gap-2"
                >
                  <CheckCircle2 size={16} className="text-emerald-400" />
                  <p className="text-sm text-emerald-400 font-medium flex-1">
                    Redirecting to analysis report…
                  </p>
                  <ArrowRight size={14} className="text-emerald-400" />
                </motion.div>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Failed state */}
        {state === 'failed' && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="card border-red-500/20 bg-red-500/10 mb-5"
          >
            <div className="flex items-center gap-3 mb-3">
              <XCircle size={18} className="text-red-400" />
              <p className="text-sm font-semibold text-red-400">Analysis failed</p>
            </div>
            <p className="text-sm text-red-400/80 mb-4">
              Please check the prescription image quality and try again.
            </p>
            <button
              onClick={() => { setState('idle'); setCurrentStep(-1) }}
              className="btn-primary text-sm"
            >
              Try again
            </button>
          </motion.div>
        )}

        {/* Format guidelines */}
        <div className="p-4 bg-teal-500/8 border border-teal-500/15 rounded-2xl">
          <p className="text-xs font-semibold text-teal-400 mb-2 uppercase tracking-wide">Accepted formats</p>
          <ul className="space-y-1.5 text-xs text-slate-400">
            {[
              'JPEG / PNG / WEBP prescription images',
              'PDF prescriptions (scanned or digital)',
              'Camera capture directly from your phone',
              'Maximum file size: 20 MB',
              'Best results with clear, well-lit images',
            ].map(txt => (
              <li key={txt} className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-teal-500/60 flex-shrink-0" />
                {txt}
              </li>
            ))}
          </ul>
        </div>

      </main>
    </div>
  )
}
