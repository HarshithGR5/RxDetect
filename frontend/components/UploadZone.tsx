'use client'
import { useCallback, useRef, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { motion, AnimatePresence } from 'framer-motion'
import { Upload, File, Camera, X } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Props {
  onFile: (file: File) => void
  loading?: boolean
}

const ACCEPT = {
  'image/jpeg': ['.jpg', '.jpeg'],
  'image/png':  ['.png'],
  'image/webp': ['.webp'],
  'application/pdf': ['.pdf'],
}

export default function UploadZone({ onFile, loading }: Props) {
  const [selected, setSelected] = useState<File | null>(null)
  const [preview,  setPreview]  = useState<string | null>(null)
  const cameraRef = useRef<HTMLInputElement>(null)

  const handleFile = useCallback((f: File) => {
    setSelected(f)
    if (f.type.startsWith('image/')) {
      setPreview(URL.createObjectURL(f))
    } else {
      setPreview(null)
    }
    onFile(f)
  }, [onFile])

  const onDrop = useCallback((accepted: File[]) => {
    if (accepted[0]) handleFile(accepted[0])
  }, [handleFile])

  const onCameraChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (f) handleFile(f)
  }

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop, accept: ACCEPT, maxFiles: 1, maxSize: 20 * 1024 * 1024, disabled: loading,
  })

  const clear = (e: React.MouseEvent) => {
    e.stopPropagation()
    setSelected(null)
    setPreview(null)
    if (cameraRef.current) cameraRef.current.value = ''
  }

  return (
    <div className="space-y-3">
      <div
        {...getRootProps()}
        className={cn(
          'relative border-2 border-dashed rounded-2xl transition-all duration-200 cursor-pointer',
          isDragActive
            ? 'border-teal-400 bg-teal-50 scale-[1.01]'
            : selected
            ? 'border-primary-200 bg-primary-50/40'
            : 'border-slate-200 bg-slate-50 hover:border-primary-300 hover:bg-primary-50/20',
          loading && 'opacity-60 cursor-not-allowed'
        )}
      >
        <input {...getInputProps()} />

        <div className="flex flex-col items-center justify-center py-10 sm:py-12 px-6 text-center">
          <AnimatePresence mode="wait">
            {selected ? (
              <motion.div
                key="selected"
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.8, opacity: 0 }}
                className="flex flex-col items-center gap-3"
              >
                {preview ? (
                  <img src={preview} alt="Preview"
                    className="w-28 h-28 object-cover rounded-xl shadow border border-slate-100" />
                ) : (
                  <div className="w-16 h-16 bg-primary-100 rounded-xl flex items-center justify-center">
                    <File size={28} className="text-primary-500" />
                  </div>
                )}
                <div>
                  <p className="font-semibold text-primary-700 break-all max-w-[220px] mx-auto">
                    {selected.name}
                  </p>
                  <p className="text-sm text-slate-400 mt-0.5">
                    {(selected.size / 1024).toFixed(0)} KB · {selected.type}
                  </p>
                </div>
                {!loading && (
                  <button
                    onClick={clear}
                    className="text-xs text-red-400 hover:text-red-600 flex items-center gap-1 mt-1
                               min-h-[44px] px-3 touch-manipulation"
                  >
                    <X size={12} /> Remove file
                  </button>
                )}
              </motion.div>
            ) : (
              <motion.div
                key="empty"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex flex-col items-center gap-4"
              >
                <div className={cn(
                  'w-16 h-16 rounded-2xl flex items-center justify-center transition-colors',
                  isDragActive ? 'bg-teal-100' : 'bg-primary-50'
                )}>
                  <Upload size={26} className={isDragActive ? 'text-teal-500' : 'text-primary-400'} />
                </div>
                <div>
                  <p className="font-semibold text-slate-700">
                    {isDragActive ? 'Drop to upload' : 'Drag & drop prescription'}
                  </p>
                  <p className="text-sm text-slate-400 mt-1">or tap to browse files</p>
                </div>
                <div className="flex flex-wrap justify-center gap-2 text-xs text-slate-400">
                  {['JPG', 'PNG', 'PDF', 'WEBP'].map(f => (
                    <span key={f}
                      className="bg-white border border-slate-200 px-2 py-0.5 rounded">{f}</span>
                  ))}
                </div>
                <p className="text-xs text-slate-400">Max file size: 20 MB</p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/80 rounded-2xl">
            <div className="flex flex-col items-center gap-3">
              <div className="w-10 h-10 rounded-full border-2 border-primary-200 border-t-primary-500 animate-spin" />
              <p className="text-sm font-medium text-primary-600">Uploading & analysing…</p>
            </div>
          </div>
        )}
      </div>

      {/* Camera capture button — visible on mobile only, hidden on desktop */}
      {!selected && !loading && (
        <div className="sm:hidden">
          <input
            ref={cameraRef}
            type="file"
            accept="image/*"
            capture="environment"
            className="hidden"
            onChange={onCameraChange}
            disabled={loading}
          />
          <button
            type="button"
            onClick={() => cameraRef.current?.click()}
            className="w-full flex items-center justify-center gap-2.5 py-3 rounded-xl
                       border border-dashed border-teal-300 bg-teal-50/60 text-teal-700
                       text-sm font-medium hover:bg-teal-50 transition touch-manipulation
                       min-h-[44px]"
          >
            <Camera size={17} />
            Take photo with camera
          </button>
        </div>
      )}
    </div>
  )
}
