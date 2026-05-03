/**
 * api.ts
 * Centralised Axios client + token storage.
 *
 * Tokens are stored in localStorage (always accessible in browser JS).
 * A thin cookie "rx_session=1" is kept solely for the Next.js middleware
 * route-guard (middleware cannot read localStorage).
 *
 * The Axios base URL points directly at the FastAPI backend so that no
 * Next.js proxy is needed and headers are never silently dropped.
 */

import axios, { AxiosRequestConfig } from 'axios'
import Cookies from 'js-cookie'

// ── Backend base URL ──────────────────────────────────────────────────────────
// Set NEXT_PUBLIC_API_URL in .env.local (or Replit secrets) to override.
// Default: same machine, port 8000.
const BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '') ??
  'http://localhost:8000/api/v1'

export const api = axios.create({
  baseURL: BASE,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: false,   // we use Bearer, not session cookies
})

// ── Token storage (localStorage) ─────────────────────────────────────────────
const KEY_ACCESS  = 'rx_access'
const KEY_REFRESH = 'rx_refresh'
const COOKIE_SESSION = 'rx_session'

function isBrowser() { return typeof window !== 'undefined' }

function getAccess(): string | null {
  if (!isBrowser()) return null
  return localStorage.getItem(KEY_ACCESS)
}

function getRefresh(): string | null {
  if (!isBrowser()) return null
  return localStorage.getItem(KEY_REFRESH)
}

export function saveTokens(access: string, refresh: string) {
  if (!isBrowser()) return
  localStorage.setItem(KEY_ACCESS, access)
  localStorage.setItem(KEY_REFRESH, refresh)
  // Thin cookie so Next.js middleware can protect routes server-side
  Cookies.set(COOKIE_SESSION, '1', { expires: 30, sameSite: 'lax' })
}

export function clearTokens() {
  if (!isBrowser()) return
  localStorage.removeItem(KEY_ACCESS)
  localStorage.removeItem(KEY_REFRESH)
  Cookies.remove(COOKIE_SESSION)
}

// ── Refresh mutex ─────────────────────────────────────────────────────────────
// Prevents parallel 401s from each firing their own refresh request.
let refreshPromise: Promise<string> | null = null

async function doRefresh(): Promise<string> {
  if (refreshPromise) return refreshPromise

  refreshPromise = (async () => {
    const rt = getRefresh()
    if (!rt) throw new Error('no_refresh_token')

    // Use a fresh axios instance (no interceptors) to avoid infinite loop
    const { data } = await axios.post(
      `${BASE}/auth/refresh`,
      { refresh_token: rt },
      { headers: { 'Content-Type': 'application/json' } },
    )
    saveTokens(data.access_token, data.refresh_token)
    return data.access_token as string
  })()

  refreshPromise.finally(() => { refreshPromise = null })
  return refreshPromise
}

// ── Request interceptor — attach Bearer token ─────────────────────────────────
api.interceptors.request.use((config) => {
  const token = getAccess()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// ── Response interceptor — transparent 401 refresh ───────────────────────────
api.interceptors.response.use(
  (res) => res,
  async (err) => {
    const original: AxiosRequestConfig & { _retry?: boolean } = err.config ?? {}

    if (err.response?.status === 401 && !original._retry) {
      original._retry = true

      if (!getRefresh()) {
        clearTokens()
        if (isBrowser()) window.location.href = '/login'
        return Promise.reject(err)
      }

      try {
        const newToken = await doRefresh()
        original.headers = {
          ...original.headers,
          Authorization: `Bearer ${newToken}`,
        }
        return api(original)
      } catch {
        clearTokens()
        if (isBrowser()) window.location.href = '/login'
        return Promise.reject(err)
      }
    }

    return Promise.reject(err)
  },
)

// ── Auth ──────────────────────────────────────────────────────────────────────
export const authApi = {
  login: (email: string, password: string) => {
    const form = new URLSearchParams()
    form.append('username', email)
    form.append('password', password)
    return api.post('/auth/login', form, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
  },
  register: (
    email: string,
    password: string,
    full_name: string,
    role: string,
  ) => api.post('/auth/register', { email, password, full_name, role }),
  me:     () => api.get('/auth/me'),
  logout: () => api.delete('/auth/logout'),
}

// ── Prescriptions ─────────────────────────────────────────────────────────────
export const prescriptionApi = {
  list: (page = 1, pageSize = 20, status?: string) =>
    api.get('/prescriptions/', { params: { page, page_size: pageSize, status } }),
  get:       (id: string) => api.get(`/prescriptions/${id}`),
  getStatus: (id: string) => api.get(`/prescriptions/${id}/status`),
  getResult: (id: string) => api.get(`/prescriptions/result/${id}`),
  getResults:(id: string) => api.get(`/prescriptions/${id}/results`),
  upload: (file: File, patientId?: string) => {
    const form = new FormData()
    form.append('file', file)
    if (patientId) form.append('patient_id', patientId)
    return api.post('/prescriptions/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  delete: (id: string) => api.delete(`/prescriptions/${id}`),
  submitFeedback: (
    id: string,
    pharmacist_label: string,
    feedback_note: string,
    is_correct: boolean,
  ) =>
    api.patch(`/prescriptions/feedback/${id}`, {
      pharmacist_label,
      feedback_note,
      is_correct,
    }),
}

// ── Reports ───────────────────────────────────────────────────────────────────
export const reportApi = {
  list: (page = 1, pageSize = 20) =>
    api.get('/reports/', { params: { page, page_size: pageSize } }),
  generate: (prescriptionId: string) =>
    api.post(`/reports/generate/${prescriptionId}`),
  /**
   * Authenticated PDF download — fetches via Axios (Bearer token attached)
   * then triggers a browser file-save dialog via a temporary blob URL.
   */
  download: async (prescriptionId: string): Promise<void> => {
    const res = await api.get(`/reports/download/${prescriptionId}`, {
      responseType: 'blob',
    })
    const blob = new Blob([res.data], { type: 'application/pdf' })
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a')
    a.href     = url
    a.download = `report-${prescriptionId.slice(0, 8)}.pdf`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  },
}

// ── Patients ──────────────────────────────────────────────────────────────────
export const patientApi = {
  list: (search?: string, page = 1) =>
    api.get('/patients/', { params: { search, page } }),
  get: (id: string) => api.get(`/patients/${id}`),
}
