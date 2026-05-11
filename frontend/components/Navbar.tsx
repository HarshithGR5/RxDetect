'use client'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  LayoutDashboard, Upload, FileText, LogOut, Menu, X,
  ShieldCheck, User, ChevronDown, Eye
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { authApi, clearTokens, saveRole } from '@/lib/api'
import type { User as UserType } from '@/lib/types'

const ROLE_CONFIG = {
  admin:       { label: 'Admin',       color: 'text-purple-600', bg: 'bg-purple-50' },
  pharmacist:  { label: 'Pharmacist',  color: 'text-primary-600', bg: 'bg-primary-50' },
  viewer:      { label: 'Viewer',      color: 'text-slate-600',  bg: 'bg-slate-100' },
}

export default function Navbar() {
  const pathname = usePathname()
  const router   = useRouter()
  const [user, setUser]         = useState<UserType | null>(null)
  const [open, setOpen]         = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)

  useEffect(() => {
    authApi.me().then(r => {
      setUser(r.data)
      if (r.data?.role) saveRole(r.data.role)
    }).catch(() => {})
  }, [])

  // Role-aware nav — viewers cannot upload
  const isViewer = user?.role === 'viewer'
  const NAV = [
    { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard, hidden: false },
    { href: '/upload',    label: 'Upload',    icon: Upload,          hidden: isViewer },
    { href: '/reports',   label: 'Reports',   icon: FileText,        hidden: false },
  ].filter(n => !n.hidden)

  const logout = async () => {
    try { await authApi.logout() } catch {}
    clearTokens()
    router.push('/login')
  }

  const roleCfg = user?.role ? ROLE_CONFIG[user.role] : null

  return (
    <nav className="sticky top-0 z-50 bg-white/95 backdrop-blur border-b border-slate-100 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 flex items-center h-14 sm:h-16 gap-4 sm:gap-6">

        {/* Logo */}
        <Link href="/dashboard" className="flex items-center gap-2 mr-2 sm:mr-4 flex-shrink-0">
          <div className="w-7 h-7 sm:w-8 sm:h-8 bg-primary-500 rounded-lg flex items-center justify-center shadow">
            <ShieldCheck className="text-white" size={16} />
          </div>
          <span className="font-bold text-primary-500 text-base sm:text-lg tracking-tight">RxDetect</span>
        </Link>

        {/* Desktop nav */}
        <div className="hidden md:flex items-center gap-1 flex-1">
          {NAV.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className={cn(
                'flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all',
                pathname.startsWith(href)
                  ? 'bg-primary-50 text-primary-600'
                  : 'text-slate-600 hover:bg-slate-50 hover:text-slate-800'
              )}
            >
              <Icon size={15} />
              {label}
            </Link>
          ))}
          {isViewer && (
            <span className="flex items-center gap-1 text-xs text-slate-400 ml-2 px-2">
              <Eye size={12} /> Read-only access
            </span>
          )}
        </div>

        {/* User menu */}
        <div className="ml-auto relative">
          <button
            onClick={() => setOpen(!open)}
            className="flex items-center gap-2 px-2.5 py-1.5 rounded-xl hover:bg-slate-50 transition"
          >
            <div className="w-7 h-7 bg-primary-100 rounded-full flex items-center justify-center flex-shrink-0">
              <User size={13} className="text-primary-600" />
            </div>
            <span className="hidden sm:block text-sm font-medium text-slate-700 max-w-[120px] truncate">
              {user?.full_name || user?.email || 'Account'}
            </span>
            <ChevronDown size={13} className="text-slate-400 hidden sm:block" />
          </button>

          <AnimatePresence>
            {open && (
              <motion.div
                initial={{ opacity: 0, y: -8, scale: 0.96 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -8, scale: 0.96 }}
                transition={{ duration: 0.15 }}
                className="absolute right-0 mt-2 w-56 bg-white border border-slate-100 rounded-2xl shadow-xl overflow-hidden z-50"
              >
                <div className="px-4 py-3 border-b border-slate-50">
                  <p className="text-sm font-semibold text-slate-800 truncate">{user?.full_name || 'User'}</p>
                  <p className="text-xs text-slate-400 truncate">{user?.email}</p>
                  {roleCfg && (
                    <span className={cn(
                      'inline-block mt-1.5 text-xs font-medium px-2 py-0.5 rounded-full capitalize',
                      roleCfg.color, roleCfg.bg
                    )}>
                      {roleCfg.label}
                    </span>
                  )}
                </div>
                <button
                  onClick={logout}
                  className="w-full flex items-center gap-2 px-4 py-3 text-sm text-red-600 hover:bg-red-50 transition"
                >
                  <LogOut size={14} />
                  Sign out
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Mobile hamburger */}
        <button
          onClick={() => setMenuOpen(!menuOpen)}
          className="md:hidden p-2 rounded-xl hover:bg-slate-50 touch-manipulation"
          aria-label="Toggle menu"
        >
          {menuOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>

      {/* Mobile nav drawer */}
      <AnimatePresence>
        {menuOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="md:hidden border-t border-slate-100 bg-white overflow-hidden"
          >
            <div className="px-4 py-3 flex flex-col gap-1">
              {NAV.map(({ href, label, icon: Icon }) => (
                <Link
                  key={href}
                  href={href}
                  onClick={() => setMenuOpen(false)}
                  className={cn(
                    'flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium touch-manipulation',
                    pathname.startsWith(href)
                      ? 'bg-primary-50 text-primary-600'
                      : 'text-slate-600 hover:bg-slate-50'
                  )}
                >
                  <Icon size={16} />
                  {label}
                </Link>
              ))}
              {/* Mobile user info */}
              <div className="mt-2 pt-2 border-t border-slate-100">
                <div className="px-4 py-2 flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-slate-700">{user?.full_name || user?.email}</p>
                    {roleCfg && (
                      <span className={cn('text-xs font-medium capitalize', roleCfg.color)}>
                        {roleCfg.label}
                      </span>
                    )}
                  </div>
                  <button
                    onClick={() => { setMenuOpen(false); logout() }}
                    className="flex items-center gap-1.5 text-xs text-red-500 px-3 py-1.5 rounded-lg border border-red-100 hover:bg-red-50 touch-manipulation"
                  >
                    <LogOut size={12} /> Sign out
                  </button>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Click-outside overlay */}
      {open && (
        <div className="fixed inset-0 z-[-1]" onClick={() => setOpen(false)} />
      )}
    </nav>
  )
}
