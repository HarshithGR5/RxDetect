import type { Metadata, Viewport } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import Providers from './providers'

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' })

export const metadata: Metadata = {
  title: 'RxDetect — AI-Powered Prescription Discrepancy Detection System',
  description: 'AI-powered prescription discrepancy detection that catches clinical errors before they reach patients.',
  openGraph: {
    title: 'RxDetect — AI-Powered Prescription Discrepancy Detection System',
    description: 'AI-powered prescription discrepancy detection that catches clinical errors before they reach patients.',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'RxDetect — AI-Powered Prescription Discrepancy Detection System',
    description: 'AI-powered prescription discrepancy detection that catches clinical errors before they reach patients.',
  },
}

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable}>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
