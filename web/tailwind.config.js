/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        gray: {
          750: '#2d3748',  // extra shade for hover states
          950: '#0d1117',
        },
      },
    },
  },
  plugins: [],
}
