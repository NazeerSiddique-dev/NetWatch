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
          blue: '#0284C7', // Darker Sky Blue for contrast
          cyan: '#0891B2', // Darker Cyan for contrast
          lime: '#DEFFC6',
          mint: '#C5F5C6',
          dark: '#0F172A', // Navy/Slate for text
          light: '#F8FAFC', // Off-white for background
        },
        dark: {
          900: '#F8FAFC', // Overwrite dark-900 to light background to minimize refactoring effort
          800: '#FFFFFF', // Overwrite dark-800 to pure white for cards
          700: '#E2E8F0', // Overwrite dark-700 to light borders
        }
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      }
    },
  },
  plugins: [],
}
