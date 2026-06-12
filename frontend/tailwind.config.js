/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Design-system colors (direct)
        app:    "#020408",
        panel:  "#050D14",
        card2:  "#080F18",
        cyan:   "#00D4FF",
        neon: {
          cyan:   "#00D4FF",
          green:  "#00FF88",
          red:    "#FF2D55",
          orange: "#FF8C00",
          yellow: "#FFD60A",
          blue:   "#0A84FF",
        },
        ink: {
          DEFAULT: "#E8F4F8",
          muted:   "#4A6880",
        },
        grid: "#0A2035",

        // shadcn token bridge (existing ui/* components)
        border: "hsl(var(--border-hsl))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
      },
      fontFamily: {
        display: ["var(--font-display)", "Space Grotesk", "sans-serif"],
        body: ["var(--font-body)", "Inter", "sans-serif"],
        mono: ["var(--font-mono)", "JetBrains Mono", "monospace"],
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      boxShadow: {
        "glow-cyan": "0 0 20px rgba(0, 212, 255, 0.3)",
        "glow-red": "0 0 20px rgba(255, 45, 85, 0.3)",
        "glow-green": "0 0 20px rgba(0, 255, 136, 0.25)",
      },
    },
  },
  plugins: [],
};
