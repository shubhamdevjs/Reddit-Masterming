/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f5f7ff',
          100: '#ebefff',
          200: '#d6dfff',
          300: '#b3c5ff',
          400: '#8da6ff',
          500: '#667eea',
          600: '#5568d3',
          700: '#4451b8',
          800: '#333d9c',
          900: '#232a7c',
        },
        secondary: {
          500: '#764ba2',
          600: '#6a4392',
        }
      }
    },
  },
  plugins: [],
}

