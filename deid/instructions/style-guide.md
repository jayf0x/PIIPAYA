# Style Guide

A design + implementation guide for applying this visual language across projects.
Not a component library — a philosophy with concrete patterns.

---

## Philosophy

**Minimal. Signal over noise. Refined.**

- Every element earns its place. No decorative filler, no lorem ipsum sections, no feature grids for padding.
- Content is high signal: short, direct, honest. No marketing fluff.
- Interactions are smooth but never theatrical. Animations communicate state, not personality.
- Dark and light modes are both first-class — neither is an afterthought.
- The background is alive but quiet. It supports content, never competes.

---

## Color System

All tokens defined in `tailwind.config.js` as a plugin — **single source of truth**.
Never scatter colors across CSS files, component styles, or hardcoded hex values.

```js
// tailwind.config.js
import plugin from "tailwindcss/plugin"

const tokens = {
  light: {
    "--background": "#f7f7f8",
    "--foreground": "#0f0f10",
    "--primary":    "#2563eb",
    "--primary-hover": "#1d4ed8",
    "--muted":      "#6b7280",
    "--surface":    "rgba(255,255,255,0.70)",
    "--border":     "rgba(0,0,0,0.08)",
  },
  dark: {
    "--background": "#09090b",
    "--foreground": "#f1f1f3",
    "--primary":    "#3b82f6",
    "--primary-hover": "#60a5fa",
    "--muted":      "#9ca3af",
    "--surface":    "rgba(255,255,255,0.04)",
    "--border":     "rgba(255,255,255,0.08)",
  },
}

export default {
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        primary: { DEFAULT: "var(--primary)", hover: "var(--primary-hover)" },
        muted:   "var(--muted)",
        surface: "var(--surface)",
        border:  "var(--border)",
      },
    },
  },
  plugins: [
    plugin(({ addBase }) => {
      addBase({ ":root": tokens.light, ".dark": tokens.dark })
    }),
  ],
}
```

**Token roles:**

| Token | Role |
|---|---|
| `background` | Page/app background |
| `foreground` | Primary text |
| `primary` | CTAs, links, icons, highlights |
| `muted` | Secondary text, placeholders, labels |
| `surface` | Card/panel backgrounds — semi-transparent |
| `border` | Dividers, card borders — semi-transparent |

**Rules:**
- Use semantic tokens (`text-foreground`, `bg-surface`) not raw Tailwind palette (`text-gray-800`).
- Exception: one-off decorative values (gradient stops, blob colors) may use palette directly.
- Opacity modifiers on tokens are fine: `bg-primary/10`, `border-border/50`.

---

## Dark Mode

- Toggle class `.dark` on `<html>`.
- Read system preference on first load; persist to `localStorage`.
- Animate the toggle icon (rotate + fade), never just swap.

```tsx
// ThemeToggle.tsx — floating fixed button, top-right
const getInitialDark = () => {
  const stored = localStorage.getItem("theme")
  if (stored) return stored === "dark"
  return window.matchMedia("(prefers-color-scheme: dark)").matches
}

export const ThemeToggle = () => {
  const [dark, setDark] = useState(getInitialDark)

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark)
    localStorage.setItem("theme", dark ? "dark" : "light")
  }, [dark])

  return (
    <motion.button
      onClick={() => setDark(d => !d)}
      whileTap={{ scale: 0.88 }}
      className="fixed top-4 right-4 z-50 w-9 h-9 flex items-center justify-center
                 rounded-lg bg-surface border border-border backdrop-blur-sm
                 text-muted hover:text-foreground transition-colors shadow-sm"
    >
      <AnimatePresence mode="wait" initial={false}>
        <motion.span
          key={dark ? "sun" : "moon"}
          initial={{ opacity: 0, rotate: -30, scale: 0.7 }}
          animate={{ opacity: 1, rotate: 0, scale: 1 }}
          exit={  { opacity: 0, rotate:  30, scale: 0.7 }}
          transition={{ duration: 0.18 }}
        >
          {dark ? <Sun size={16} /> : <Moon size={16} />}
        </motion.span>
      </AnimatePresence>
    </motion.button>
  )
}
```

---

## Typography

No custom font — system stack is fine if the weights are used intentionally.

| Use | Classes |
|---|---|
| Hero headline | `text-5xl md:text-7xl font-black tracking-tight leading-none` |
| Section heading | `text-3xl md:text-4xl font-bold` |
| Sub-heading | `text-xl font-bold` |
| Body | `text-base leading-relaxed` |
| Small body / card desc | `text-sm leading-snug` |
| Label / eyebrow | `text-sm font-semibold uppercase tracking-widest text-primary` |
| Muted | `text-muted` |

**Rules:**
- Eyebrow label above section headings: small, uppercase, primary color, wide tracking. Sets context before the heading lands.
- Headings are `font-black` (hero) or `font-bold` (sections). Nothing in between.
- Body text is never full `text-foreground` — use `text-muted` or `text-gray-500 dark:text-gray-400` for prose.
- Gradient text for the key differentiating word: `bg-gradient-to-r from-blue-500 to-indigo-500 bg-clip-text text-transparent`.

---

## Layout

```
max-w-4xl mx-auto px-6    ← standard section content
max-w-5xl mx-auto px-6    ← wide (docs, feature alternating rows)
max-w-3xl mx-auto         ← hero copy (narrow for readability)
```

Section vertical rhythm: `py-24` or `py-28`. Don't vary wildly between sections.

Section dividers: `border-t border-gray-200/60 dark:border-white/[0.07]` — subtle, not solid.

Responsive column pattern for feature alternation:
```tsx
className={`flex flex-col ${i % 2 === 0 ? "md:flex-row" : "md:flex-row-reverse"} gap-10 md:gap-14 items-center`}
```

---

## Background

Fixed behind all content (`z-0`), pointer-events none.
Two layers: animated dot grid + soft gradient blobs.

```tsx
export const Background = () => (
  <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
    {/* dot grid — subtle texture */}
    <div className="absolute inset-0 opacity-[0.15] dark:opacity-[0.07]">
      <svg className="w-full h-full animate-slowPan" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <pattern id="dots" x="0" y="0" width="24" height="24" patternUnits="userSpaceOnUse">
            <circle cx="2" cy="2" r="1.2" fill="currentColor" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#dots)"
              className="text-gray-500 dark:text-gray-400" />
      </svg>
    </div>

    {/* blobs — color atmosphere */}
    <div className="absolute -top-40 -left-40 w-[500px] h-[500px]
                    bg-gradient-to-br from-blue-400 to-indigo-500
                    rounded-full mix-blend-multiply dark:mix-blend-screen
                    filter blur-3xl opacity-20 dark:opacity-10 animate-blob" />
    <div className="absolute -bottom-40 -right-40 w-[420px] h-[420px]
                    bg-gradient-to-tr from-violet-400 to-purple-500
                    rounded-full mix-blend-multiply dark:mix-blend-screen
                    filter blur-3xl opacity-20 dark:opacity-10 animate-blob [animation-delay:3s]" />
  </div>
)
```

Keyframes needed in tailwind config:
```js
keyframes: {
  pan:  { "0%": { transform: "translate(0,0) scale(1)" }, "100%": { transform: "translate(-12px,-12px) scale(1.05)" } },
  blob: { "0%": { transform: "translate(0,0) scale(1)" }, "33%": { transform: "translate(20px,-30px) scale(1.05)" },
          "66%": { transform: "translate(-15px,15px) scale(0.97)" }, "100%": { transform: "translate(0,0) scale(1)" } },
},
animation: {
  slowPan: "pan 8s alternate infinite",
  blob:    "blob 7s infinite",
},
```

---

## Motion & Animation

Stack: **Framer Motion**. No CSS animation for interactive elements.

### Entrance pattern

For page-load elements (above the fold): use `animate` directly.
For scroll-revealed elements: use `whileInView` with `once: true`.

```tsx
// Page load — stagger by delay
const item = (delay: number) => ({
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.6, delay, ease: "easeOut" },
})

// Scroll reveal
const fadeUp = (delay = 0) => ({
  initial:    { opacity: 0, y: 20 },
  whileInView:{ opacity: 1, y: 0 },
  viewport:   { once: true, margin: "-80px" },
  transition: { duration: 0.55, delay, ease: "easeOut" },
})
```

Stagger delay increments: `0.08–0.12s` between siblings. Never more than `~0.6s` total delay.

### Interactive elements

```tsx
// Buttons — always whileTap
<motion.button whileTap={{ scale: 0.92 }}>

// Cards — optional hover lift
<motion.div whileHover={{ y: -2 }} transition={{ duration: 0.15 }}>

// Primary CTA — scale on hover, shadow deepens
className="hover:scale-[1.02] active:scale-[0.99] transition-all duration-200
           shadow-md shadow-primary/20 hover:shadow-primary/35"
```

### Icon transitions (AnimatePresence)

When swapping icons (toggle states, loading states):
```tsx
<AnimatePresence mode="wait" initial={false}>
  <motion.span
    key={state}   // key change triggers exit/enter
    initial={{ opacity: 0, rotate: -30, scale: 0.7 }}
    animate={{ opacity: 1, rotate: 0,   scale: 1   }}
    exit={  { opacity: 0, rotate:  30,  scale: 0.7 }}
    transition={{ duration: 0.18 }}
  >
    <Icon />
  </motion.span>
</AnimatePresence>
```

### Scroll indicator (looping)

```tsx
<motion.div
  animate={{ y: [0, 7, 0] }}
  transition={{ repeat: Infinity, duration: 2.2, ease: "easeInOut" }}
>
  <ChevronDown size={22} />
</motion.div>
```

**Rules:**
- `duration` for entrances: `0.5–0.7s`. Never faster (cheap), never slower (sluggish).
- `ease: "easeOut"` for entrances. `easeInOut` for loops.
- Hover transitions: `duration: 150–200ms`. Fast.
- Never animate layout properties (`width`, `height`) if transform works.
- `will-change` only if you measure a jank problem — don't preemptively add it.

---

## Cards / Surface Pattern

Glass-morphism surface: semi-transparent background + subtle border + backdrop blur.

```tsx
// Standard feature card
<div className="flex gap-4 p-5 rounded-xl
                bg-white/70 dark:bg-white/[0.04]
                border border-gray-200/80 dark:border-white/[0.08]
                backdrop-blur-sm">
  {/* icon badge */}
  <div className="shrink-0 w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center">
    <Icon size={18} className="text-primary" />
  </div>
  <div>
    <p className="font-semibold text-foreground text-sm">{title}</p>
    <p className="text-sm text-muted mt-1 leading-snug">{desc}</p>
  </div>
</div>
```

Image/screenshot containers:
```tsx
<div className="rounded-xl overflow-hidden
                border border-gray-200/80 dark:border-white/[0.08]
                shadow-2xl shadow-black/8 dark:shadow-black/40">
  <img src={img} alt={title} className="w-full h-auto block" />
</div>
```

---

## Buttons

Two variants only. No variants beyond these without a clear reason.

```tsx
// Primary — gradient, shadow, scale
<button className="inline-flex items-center gap-2 px-6 py-2.5 rounded-lg
                   bg-gradient-to-r from-blue-500 to-indigo-600
                   text-white font-semibold text-sm
                   shadow-md shadow-blue-500/20 hover:shadow-blue-500/35
                   hover:scale-[1.02] active:scale-[0.99] transition-all duration-200">
  <Icon size={16} className="group-hover:-translate-y-0.5 transition-transform" />
  Label
</button>

// Ghost — border, no fill
<button className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg
                   border border-gray-200 dark:border-gray-700
                   text-sm font-medium text-muted
                   hover:border-gray-400 dark:hover:border-gray-500
                   hover:text-foreground transition-colors">
  <Icon size={16} />
  Label
</button>
```

Large hero CTA: same as primary but `px-9 py-4 text-lg rounded-2xl`.

---

## Section Structure Pattern

```tsx
// Every section follows this skeleton
<section className="py-28 px-6 [border-t border-gray-200/60 dark:border-white/[0.07]]">
  <div className="max-w-4xl mx-auto space-y-16">

    {/* Eyebrow + heading block */}
    <motion.div {...fadeUp(0)} className="space-y-2 text-center">
      <p className="text-sm font-semibold text-primary uppercase tracking-widest">
        Context label
      </p>
      <h2 className="text-3xl md:text-4xl font-bold text-foreground">
        The actual claim
      </h2>
      {/* optional subtext */}
      <p className="text-muted max-w-xl mx-auto text-lg leading-relaxed">
        Supporting detail. Short. No filler.
      </p>
    </motion.div>

    {/* Content */}
    ...

  </div>
</section>
```

---

## Icons

Use **lucide-react** exclusively. Consistent size convention:

| Context | Size |
|---|---|
| Inline with text | `size={16}` |
| Icon badge inside card | `size={18}` |
| Standalone / UI control | `size={20}–22` |
| Decorative / scroll indicator | `size={22}–24` |

Icon badge pattern:
```tsx
<div className="w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center">
  <Icon size={18} className="text-primary" />
</div>
```

---

## Footers & Utility Chrome

Footer: minimal, one line, centered. No sitemap, no newsletter, no social grid.
```tsx
<footer className="py-8 px-6 border-t border-gray-200/60 dark:border-white/[0.07] text-center">
  <p className="text-sm text-muted flex items-center justify-center gap-2">
    AppName ·{" "}
    <a href={GITHUB_URL} className="inline-flex items-center gap-1 hover:text-primary transition-colors">
      <Github size={13} /> owner/repo
    </a>
  </p>
</footer>
```

Floating utility buttons (theme toggle, etc.): `fixed`, `z-50`, top corners.
Size: `w-9 h-9`. Style: `bg-surface border border-border backdrop-blur-sm shadow-sm`.

---

## Copy Tone

- Short. Direct. No filler words.
- Headlines make a claim, not a description. ("Privacy shouldn't be an afterthought." not "About our privacy features.")
- Subtext supports in one sentence. No paragraph walls.
- Feature names: noun or short verb phrase. No adjectives that don't add info.
- No exclamation marks. No emoji in UI copy.

---

## What Not To Do

- ❌ Hardcode colors (`#2563eb`, `gray-800`) in components — use tokens
- ❌ Animate `opacity` alone on entrances — pair with `y` movement
- ❌ `transition-all` on anything that changes layout — use specific properties
- ❌ More than two CTA variants on one page
- ❌ Section headings without an eyebrow label — context is lost
- ❌ Cards without `backdrop-blur-sm` when over the animated background
- ❌ Scroll-reveal with `once: false` — re-animating on scroll-up is distracting
- ❌ Framer Motion on elements that don't need it — static layout elements don't need `motion.div`
- ❌ Blob/background effects in light mode without `mix-blend-multiply` — colors bleed harshly
