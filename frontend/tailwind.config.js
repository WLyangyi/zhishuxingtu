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
          DEFAULT: '#00d4ff',
          dark: '#00a8cc',
        },
        accent: {
          purple: '#7b2cbf',
          green: '#00ff9d',
        },
        dark: {
          bg: '#0f0f1a',
          card: '#1a1a2e',
          border: '#2a2a4a',
        },
        light: {
          bg: '#f8f9fa',
          card: '#ffffff',
          border: '#e5e7eb',
        }
      }
    },
  },
  plugins: [],
}
