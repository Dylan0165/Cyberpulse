/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        bg: "#020408",
        "bg-secondary": "#050D14",
        card: "#080F18",
        cyan: "#00B4D8",
        green: "#00FF88",
        red: "#FF2D55",
        orange: "#FF8C00",
        ink: "#E8F4F8",
        "ink-muted": "#4A6880",
        grid: "#0D1F35",
      },
      fontFamily: {
        display: ["var(--font-display)", "system-ui", "sans-serif"],
        body: ["var(--font-body)", "system-ui", "sans-serif"],
      },
      boxShadow: {
        "glow-cyan": "0 0 28px rgba(0,180,216,0.18)",
      },
      maxWidth: {
        content: "1200px",
      },
    },
  },
  plugins: [],
};
