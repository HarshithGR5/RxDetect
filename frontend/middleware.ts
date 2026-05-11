import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

const PUBLIC_PATHS = ['/', '/login', '/signup']

// Routes that viewers (read-only role) cannot access
const VIEWER_BLOCKED = ['/upload']

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  // Let public pages, Next internals, and API proxy pass through
  const isPublic =
    PUBLIC_PATHS.includes(pathname) ||
    pathname.startsWith('/_next') ||
    pathname.startsWith('/api') ||
    pathname.includes('.')

  if (isPublic) return NextResponse.next()

  // Check session cookie
  const session = request.cookies.get('rx_session')
  if (!session) {
    return NextResponse.redirect(new URL('/login', request.url))
  }

  // Role-based access: viewers cannot upload
  const role = request.cookies.get('rx_role')?.value
  if (role === 'viewer' && VIEWER_BLOCKED.some(p => pathname.startsWith(p))) {
    return NextResponse.redirect(new URL('/dashboard', request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
}
