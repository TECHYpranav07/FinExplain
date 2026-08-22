/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ['class'],
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        background: '#000000',
        foreground: '#ffffff',
        surface: '#111111',
        'surface-2': '#171717',
        'surface-3': '#202020',
        'pill-dark': '#28282a',
        muted: {
          DEFAULT: '#191919',
          foreground: '#8e8e8e',
        },
        border: 'rgba(255, 255, 255, 0.12)',
        'border-strong': 'rgba(255, 255, 255, 0.22)',
        primary: {
          DEFAULT: '#ffffff',
          foreground: '#000000',
        },
        secondary: {
          DEFAULT: '#202020',
          foreground: '#ffffff',
        },
        success: '#7ee787',
        warning: '#f2cc60',
        danger: '#ff7b72',
        info: '#79c0ff',
        sidebar: {
          DEFAULT: '#0d0d0d',
          foreground: '#ffffff',
          accent: '#1f1f1f',
          'accent-foreground': '#ffffff',
          border: 'rgba(255, 255, 255, 0.10)',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        display: ['BubbledotICG-FinePos', 'Inter', 'sans-serif'],
      },
      animation: {
        'slide-down': 'slideDown 0.7s cubic-bezier(0.22, 1, 0.36, 1) both',
        'headline-fade': 'headlineFade 0.9s cubic-bezier(0.22, 1, 0.36, 1) both',
        'reveal': 'reveal 0.8s cubic-bezier(0.22, 1, 0.36, 1) both',
      },
      keyframes: {
        slideDown: {
          from: { opacity: '0', transform: 'translateY(-16px)' },
          to: { opacity: '1', transform: 'none' },
        },
        headlineFade: {
          from: { opacity: '0', transform: 'translateY(18px)' },
          to: { opacity: '1', transform: 'none' },
        },
        reveal: {
          from: { opacity: '0', transform: 'translateY(24px)' },
          to: { opacity: '1', transform: 'none' },
        },
      }
    },
  },
  plugins: [],
}
