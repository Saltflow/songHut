/** @type {import('tailwindcss').Config} */
export default {
  content: [
    '../shared/src/**/*.{ts,tsx}',
    './src/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: '#4f46e5',
        dark: '#1a1a2e',
      },
    },
  },
  plugins: [],
}
