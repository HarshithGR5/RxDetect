'use client'
import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { ShieldCheck, Eye, EyeOff, AlertCircle, CheckCircle2 } from 'lucide-react'
import { authApi } from '@/lib/api'
import toast from 'react-hot-toast'

const ROLES = [
  { value: 'pharmacist', label: 'Pharmacist',    desc: 'Upload & analyse prescriptions' },
  { value: 'admin',      label: 'Administrator', desc: 'Full system access' },
  { value: 'viewer',     label: 'Viewer',        desc: 'Read-only access' },
]

export default function SignupPage() {
  const router = useRouter()
  const [fullName, setFullName] = useState('')
  const [email,    setEmail]    = useState('')
  const [password, setPassword] = useState('')
  const [role,     setRole]     = useState('pharmacist')
  const [showPw,   setShowPw]   = useState(false)
  const [loading,  setLoading]  = useState(false)
  const [error,    setError]    = useState('')

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (password.length < 8) { setError('Password must be at least 8 characters'); return }
    setLoading(true)
    try {
      await authApi.register(email, password, fullName, role)
      toast.success('Account created! Please sign in.')
      router.push('/login')
    } catch (err: any) {
      const detail = err.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#050d1a] flex items-start sm:items-center justify-center px-4 py-8 sm:py-10"
         style={{ paddingTop: 'max(2rem, env(safe-area-inset-top, 2rem))' }}>
      <div className="w-full max-w-md">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-8"
        >
          <Link href="/" className="inline-flex items-center gap-2.5 justify-center">
            <div className="w-10 h-10 bg-gradient-to-br from-teal-400 to-teal-600 rounded-xl flex items-center justify-center shadow shadow-teal-500/30">
              <ShieldCheck size={20} className="text-white" />
            </div>
            <span className="font-bold text-white text-xl">RxDetect</span>
          </Link>
          <p className="text-slate-500 text-sm mt-3">Create your clinical account</p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="card"
        >
          <h1 className="text-xl font-bold text-white mb-1">Create account</h1>
          <p className="text-sm text-slate-400 mb-6">Join your clinical team on RxDetect</p>

          {error && (
            <div className="flex items-center gap-2 bg-red-500/15 border border-red-500/30 text-red-400
                            text-sm px-4 py-3 rounded-xl mb-4">
              <AlertCircle size={14} className="flex-shrink-0" />
              {error}
            </div>
          )}

          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="label">Full name</label>
              <input
                type="text"
                className="input"
                placeholder="Dr. Sarah Mensah"
                value={fullName}
                onChange={e => setFullName(e.target.value)}
                autoFocus
              />
            </div>

            <div>
              <label className="label">Email address</label>
              <input
                type="email"
                className="input"
                placeholder="sarah@hospital.com"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
              />
            </div>

            <div>
              <label className="label">Password</label>
              <div className="relative">
                <input
                  type={showPw ? 'text' : 'password'}
                  className="input pr-10"
                  placeholder="Minimum 8 characters"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPw(!showPw)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500
                             hover:text-slate-300 touch-manipulation"
                  aria-label={showPw ? 'Hide password' : 'Show password'}
                >
                  {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {/* Role selector */}
            <div>
              <label className="label">Role</label>
              <div className="grid grid-cols-3 gap-2">
                {ROLES.map(r => (
                  <button
                    key={r.value}
                    type="button"
                    onClick={() => setRole(r.value)}
                    className={`flex flex-col items-center p-3 rounded-xl border-2 text-center
                                transition-all text-xs touch-manipulation ${
                      role === r.value
                        ? 'border-teal-500/60 bg-teal-500/15 text-teal-300'
                        : 'border-white/10 bg-white/3 text-slate-400 hover:border-white/20'
                    }`}
                  >
                    {role === r.value && (
                      <CheckCircle2 size={12} className="text-teal-400 mb-1" />
                    )}
                    <span className="font-semibold">{r.label}</span>
                    <span className="text-slate-500 mt-0.5 leading-tight hidden sm:block text-[10px]">
                      {r.desc}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            <button type="submit" disabled={loading} className="btn-primary w-full">
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-slate-950/30 border-t-slate-950 rounded-full animate-spin" />
                  Creating account…
                </>
              ) : 'Create account'}
            </button>
          </form>

          <p className="text-center text-sm text-slate-500 mt-5">
            Already have an account?{' '}
            <Link href="/login" className="text-teal-400 font-medium hover:underline">
              Sign in
            </Link>
          </p>
        </motion.div>
      </div>
    </div>
  )
}
