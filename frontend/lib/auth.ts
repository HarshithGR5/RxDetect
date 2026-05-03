// Re-export from api.ts so all auth code imports from one place
export { saveTokens as setTokens, clearTokens } from './api'

export function isLoggedIn(): boolean {
  if (typeof window === 'undefined') return false
  return !!(
    localStorage.getItem('rx_access') ||
    localStorage.getItem('rx_refresh')
  )
}
