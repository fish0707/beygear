import type { Config } from 'tailwindcss'

export default {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#0b0e14',
        panel: '#141924',
        line: '#232b3a',
        muted: '#8b97ad',
        brand: '#4ea1ff',
        good: '#3ddc97',
        warn: '#ffb454',
        bad: '#ff6b6b',
      },
    },
  },
  plugins: [],
} satisfies Config
