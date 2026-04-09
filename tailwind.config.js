export default ({
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        primary: "var(--primary)",
      },
      animation: {
        blink: "blink 1s step-start infinite",
        typing: "typing 0.8s steps(40, end)",
      },
      keyframes: {
        blink: {
          "50%": { opacity: "0" },
        },
        typing: {
          from: { width: "0" },
          to: { width: "100%" },
        },
        wave: {
          "0%": { transform: "rotate(0.0deg)" },
          "10%": { transform: "rotate(15deg)" },
          "20%": { transform: "rotate(-9deg)" },
          "30%": { transform: "rotate(15deg)" },
          "40%": { transform: "rotate(-3deg)" },
          "50%": { transform: "rotate(10deg)" },
          "60%": { transform: "rotate(0.0deg)" },
          "100%": { transform: "rotate(0.0deg)" },
        },
        pan: {
          "0%": { transform: "translate(0, 0)",  scale: 1.0},
          "100%": { transform: "translate(-12px, -12px) ",scale: -1.0},
        },
      },
      animation: {
        slowPan: "pan 5s alternate infinite",
      },
    },
  },
  plugins: [],
})
