import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#0B3C5D',
          50:  '#E8F0F6',
          100: '#C5D8E9',
          200: '#8FB5D1',
          300: '#5992B9',
          400: '#2D6F9F',
          500: '#0B3C5D',
          600: '#093350',
          700: '#072843',
          800: '#051E36',
          900: '#031429',
        },
        teal: {
          DEFAULT: '#2EC4B6',
          50:  '#E8F8F7',
          100: '#C5EDEA',
          200: '#8CDBD6',
          300: '#52C9C2',
          400: '#2EC4B6',
          500: '#25A89B',
          600: '#1C8C80',
          700: '#147065',
          800: '#0C544A',
          900: '#04382F',
        },
      },
      fontFamily: {
        sans: ['Inter', 'IBM Plex Sans', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        card: '0 2px 12px rgba(11,60,93,0.08)',
        'card-hover': '0 4px 20px rgba(11,60,93,0.14)',
      },
      borderRadius: {
        xl: '0.875rem',
        '2xl': '1.25rem',
      },
    },
  },
  plugins: [],
}
export default config
