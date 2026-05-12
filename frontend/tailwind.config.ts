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
