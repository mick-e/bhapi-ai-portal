/** @type {import('tailwindcss').Config} */
const config = {
  content: [
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: "#FFF7F2",
          100: "#FFEAD9",
          200: "#FFD0B0",
          300: "#FFB080",
          400: "#FF8F55",
          500: "#FF6B35",
          600: "#E85A24",
          700: "#CC4A18",
          800: "#A63B12",
          900: "#7F2E0E",
          950: "#4D1A08",
          DEFAULT: "#FF6B35",
        },
        accent: {
          50: "#F0FDFA",
          100: "#CCFBF1",
          200: "#99F6E4",
          300: "#5EEAD4",
          400: "#2DD4BF",
          500: "#14B8A6",
          600: "#0D9488",
          700: "#0F766E",
          800: "#115E59",
          900: "#134E4A",
          950: "#042F2E",
          DEFAULT: "#0D9488",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
