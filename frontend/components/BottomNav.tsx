'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { LayoutDashboard, Upload, FileText } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Props {
  isViewer?: boolean
}

export default function BottomNav({ isViewer = false }: Props) {
  const pathname = usePathname()

  const NAV = [
    { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    ...(!isViewer ? [{ href: '/upload', label: 'Upload', icon: Upload }] : []),
    { href: '/reports',   label: 'Reports',   icon: FileText },
  ]

  return (
    <nav
      className="fixed bottom-0 inset-x-0 z-40 md:hidden
                 bg-white/95 backdrop-blur border-t border-slate-100 shadow-[0_-1px_12px_rgba(0,0,0,0.06)]"
      style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}
    >
      <div className="flex items-stretch h-14">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = pathname.startsWith(href)
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                'flex-1 flex flex-col items-center justify-center gap-0.5 text-[10px] font-medium transition-colors touch-manipulation',
                active ? 'text-primary-600' : 'text-slate-400 hover:text-slate-600'
              )}
            >
              <Icon size={20} strokeWidth={active ? 2.5 : 1.8} />
              <span>{label}</span>
              {active && (
                <span className="absolute bottom-0 left-1/2 -translate-x-1/2 w-1 h-1 rounded-full bg-primary-500" />
              )}
            </Link>
          )
        })}
      </div>
    </nav>
  )
}
