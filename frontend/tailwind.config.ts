import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: {
          base: '#0D1117',
          surface: '#161B22',
          elevated: '#21262D',
        },
        border: '#30363D',
        text: {
          primary: '#E6EDF3',
          secondary: '#8B949E',
          muted: '#484F58',
        },
        primary: {
          DEFAULT: '#2F81F7',
          hover: '#388BFD',
        },
        success: '#3FB950',
        warning: '#D29922',
        error: '#F85149',
        info: '#79C0FF',
        node: {
          concept: '#2F81F7',
          individual: '#3FB950',
        },
        edge: {
          object: '#A78BFA',
          data: '#FB923C',
        },
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
} satisfies Config
