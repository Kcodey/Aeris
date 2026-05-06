/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: '#d97706',
          light: '#fffbeb',
          dark: '#b45309',
        },
        surface: {
          page: '#fafaf9',
          card: '#ffffff',
        },
        content: {
          primary: '#292524',
          secondary: '#78716c',
          tertiary: '#a8a29e',
        },
        border: {
          DEFAULT: '#e7e5e4',
        },
        chart: {
          amber: '#d97706',
          gold: '#fbbf24',
          sand: '#fde68a',
          neutral: '#e7e5e4',
        },
      },
      borderRadius: {
        'sm': '8px',
        'md': '12px',
        'lg': '16px',
        'xl': '20px',
        '2xl': '24px',
      },
      boxShadow: {
        'subtle': '0 1px 3px rgba(0,0,0,0.04)',
        'elevated': '0 4px 16px rgba(0,0,0,0.06)',
        'floating': '0 12px 40px rgba(0,0,0,0.08)',
        'glow': '0 2px 12px rgba(217,119,6,0.3)',
      },
      fontFamily: {
        sans: ['system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
      },
      fontSize: {
        'display': ['28px', { fontWeight: '700', lineHeight: '1.2' }],
        'title': ['24px', { fontWeight: '700', lineHeight: '1.3' }],
        'heading': ['16px', { fontWeight: '600', lineHeight: '1.4' }],
        'body': ['14px', { fontWeight: '400', lineHeight: '1.6' }],
        'caption': ['13px', { fontWeight: '400', lineHeight: '1.5' }],
        'label': ['12px', { fontWeight: '500', lineHeight: '1.4' }],
      },
      backdropBlur: {
        'glass': '20px',
      },
    },
  },
  plugins: [],
}
