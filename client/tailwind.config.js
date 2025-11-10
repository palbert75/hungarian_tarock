/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'table-green': '#1a5f3f',
        'table-felt': '#2a7f5f',
        'card-back': '#8b0000',
        'suit-red': '#dc143c',
        'suit-black': '#000000',
        'tarokk': '#4169e1',
      },
      fontFamily: {
        'display': ['Cinzel', 'serif'],
        'sans': ['Inter', 'system-ui', 'sans-serif'],
        'mono': ['Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
}
