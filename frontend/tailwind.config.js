/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#f59e0b',
          dark: '#d97706',
        },
        accent: {
          blue: '#3b82f6',
          green: '#10b981',
          red: '#ef4444',
          purple: '#8b5cf6',
        },
        dark: {
          bg: '#0a0a0b',
          secondary: '#0f0f11',
          tertiary: '#141416',
          elevated: '#1a1a1d',
        },
        light: {
          bg: '#fafafa',
          secondary: '#f4f4f5',
          tertiary: '#ffffff',
        }
      }
    },
  },
  plugins: [],
}
