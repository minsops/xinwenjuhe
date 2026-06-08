import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        ink: "#1f2933",
        paper: "#f7f7f4",
        signal: "#c2410c",
        civic: "#155e75",
        moss: "#3f6212"
      }
    }
  },
  plugins: []
} satisfies Config;

