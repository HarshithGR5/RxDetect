'use client'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  LayoutDashboard, Upload, FileText, LogOut, Menu, X,
  ShieldCheck, User, ChevronDown, Eye, BarChart2
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { authApi, clearTokens, saveRole } from '@/lib/api'
import type { User as UserType } from '@/lib/types'
import BottomNav from '@/components/BottomNav'

const ROLE_CONFIG = {
  admin:      { label: 'Admin',      color: 'text-purple-400', bg: 'bg-purple-500/15' },
  pharmacist: { label: 'Pharmacist', color: 'text-teal-400',   bg: 'bg-teal-500/15' },
  viewer:     { label: 'Viewer',     color: 'text-slate-400',  bg: 'bg-slate-500/15' },
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

  const isViewer = user?.role === 'viewer'
  const NAV = [
    { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard, hidden: false },
    { href: '/upload',    label: 'Upload',    icon: Upload,          hidden: isViewer },
    { href: '/reports',   label: 'Reports',   icon: FileText,        hidden: false },
    { href: '/results',   label: 'Results',   icon: BarChart2,       hidden: false },
  ].filter(n => !n.hidden)

  const logout = async () => {
    try { await authApi.logout() } catch {}
    clearTokens()
    router.push('/login')
  }

  const roleCfg = user?.role ? ROLE_CONFIG[user.role as keyof typeof ROLE_CONFIG] : null

  return (
    <>
      <nav className="sticky top-0 z-50 bg-[#050d1a]/90 backdrop-blur-xl border-b border-white/5">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex items-center h-14 sm:h-16 gap-4 sm:gap-6">

          {/* Logo */}
          <Link href="/dashboard" className="flex items-center gap-2 mr-2 sm:mr-4 flex-shrink-0">
            <div className="w-7 h-7 sm:w-8 sm:h-8 bg-gradient-to-br from-teal-400 to-teal-600 rounded-lg flex items-center justify-center shadow shadow-teal-500/30">
              <ShieldCheck className="text-white" size={16} />
            </div>
            <span className="font-bold text-white text-base sm:text-lg tracking-tight">RxDetect</span>
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
                    ? 'bg-teal-500/15 text-teal-400'
                    : 'text-slate-400 hover:bg-white/5 hover:text-white'
                )}
              >
                <Icon size={15} />
                {label}
              </Link>
            ))}
            {isViewer && (
              <span className="flex items-center gap-1 text-xs text-slate-500 ml-2 px-2">
                <Eye size={12} /> Read-only access
              </span>
            )}
          </div>

          {/* User menu — desktop */}
          <div className="ml-auto relative hidden md:block">
            <button
              onClick={() => setOpen(!open)}
              className="flex items-center gap-2 px-2.5 py-1.5 rounded-xl hover:bg-white/5 transition min-h-[44px]"
            >
              <div className="w-7 h-7 bg-teal-500/20 rounded-full flex items-center justify-center flex-shrink-0">
                <User size={13} className="text-teal-400" />
              </div>
              <span className="text-sm font-medium text-slate-300 max-w-[120px] truncate">
                {user?.full_name || user?.email || 'Account'}
              </span>
              <ChevronDown size={13} className="text-slate-500" />
            </button>

            <AnimatePresence>
              {open && (
                <motion.div
                  initial={{ opacity: 0, y: -8, scale: 0.96 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -8, scale: 0.96 }}
                  transition={{ duration: 0.15 }}
                  className="absolute right-0 mt-2 w-56 bg-slate-900 border border-white/10 rounded-2xl shadow-2xl overflow-hidden z-50"
                >
                  <div className="px-4 py-3 border-b border-white/5">
                    <p className="text-sm font-semibold text-white truncate">{user?.full_name || 'User'}</p>
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
                    className="w-full flex items-center gap-2 px-4 py-3 text-sm text-red-400 hover:bg-red-500/10 transition min-h-[44px]"
                  >
                    <LogOut size={14} />
                    Sign out
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Mobile: user avatar + hamburger */}
          <div className="ml-auto flex items-center gap-1 md:hidden">
            <button
              onClick={() => setOpen(!open)}
              className="p-2 rounded-xl hover:bg-white/5 transition touch-manipulation min-h-[44px] min-w-[44px]"
              aria-label="Account menu"
            >
              <div className="w-7 h-7 bg-teal-500/20 rounded-full flex items-center justify-center">
                <User size={13} className="text-teal-400" />
              </div>
            </button>
            <button
              onClick={() => setMenuOpen(!menuOpen)}
              className="p-2 rounded-xl hover:bg-white/5 touch-manipulation min-h-[44px] min-w-[44px] text-slate-400"
              aria-label="Toggle menu"
            >
              {menuOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
          </div>
        </div>

        {/* Mobile account dropdown — md:hidden prevents duplicate on desktop */}
        <AnimatePresence>
          {open && (
            <motion.div
              initial={{ opacity: 0, y: -8, scale: 0.96 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -8, scale: 0.96 }}
              transition={{ duration: 0.15 }}
              className="md:hidden absolute right-4 mt-1 w-64 bg-slate-900 border border-white/10 rounded-2xl shadow-2xl overflow-hidden z-50"
            >
              <div className="px-4 py-3 border-b border-white/5">
                <p className="text-sm font-semibold text-white truncate">{user?.full_name || 'User'}</p>
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
                onClick={() => { setOpen(false); logout() }}
                className="w-full flex items-center gap-2 px-4 py-3 text-sm text-red-400 hover:bg-red-500/10 transition min-h-[44px]"
              >
                <LogOut size={14} />
                Sign out
              </button>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Mobile nav drawer */}
        <AnimatePresence>
          {menuOpen && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="md:hidden border-t border-white/5 bg-[#050d1a] overflow-hidden"
            >
              <div className="px-4 py-3 flex flex-col gap-1">
                {NAV.map(({ href, label, icon: Icon }) => (
                  <Link
                    key={href}
                    href={href}
                    onClick={() => setMenuOpen(false)}
                    className={cn(
                      'flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium touch-manipulation min-h-[44px]',
                      pathname.startsWith(href)
                        ? 'bg-teal-500/15 text-teal-400'
                        : 'text-slate-400 hover:bg-white/5 hover:text-white'
                    )}
                  >
                    <Icon size={16} />
                    {label}
                  </Link>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </nav>

      <BottomNav isViewer={isViewer} />

      {(open || menuOpen) && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => { setOpen(false); setMenuOpen(false) }}
        />
      )}
    </>
  )
}
