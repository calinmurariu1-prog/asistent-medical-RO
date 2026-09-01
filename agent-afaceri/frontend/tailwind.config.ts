import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "#1e3a5f",
          light: "#2f5a8f",
          accent: "#c9a227",
        },
      },
    },
  },
  plugins: [],
};

export default config;
