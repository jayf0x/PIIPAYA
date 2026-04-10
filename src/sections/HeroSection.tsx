import { motion } from "framer-motion"
import { TypeAnimation } from "react-type-animation"
import { Github, Download, ChevronDown, ShieldCheck, Cpu, Files, Link2 } from "lucide-react"

const GITHUB_URL = "https://github.com/jayf0x/DeID"
const RELEASES_URL = "https://github.com/jayf0x/DeID/releases/latest"

const features = [
  {
    icon: ShieldCheck,
    title: "Fully local",
    desc: "No cloud. No telemetry. Data stays on your machine.",
  },
  {
    icon: Cpu,
    title: "AI-powered detection",
    desc: "Entity recognition via spaCy. Accurate across text and documents.",
  },
  {
    icon: Files,
    title: "Batch processing",
    desc: "Drop multiple files. Process in one run. Queue management built in.",
  },
  {
    icon: Link2,
    title: "Narrative coherence",
    desc: "Same entity → same alias across all files, every run.",
  },
]

export const HeroSection = () => (
  <section className="min-h-screen flex flex-col items-center justify-center px-6 pt-16 pb-12 relative gap-12">
    {/* Top: identity + CTAs */}
    <motion.div
      initial={{ opacity: 0, y: 28 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.7, ease: "easeOut" }}
      className="flex flex-col items-center gap-6 text-center max-w-3xl"
    >
      <motion.img
        src="./logo.png"
        alt="DeID"
        className="h-24 w-auto"
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.6, delay: 0.1 }}
      />

      <motion.h1
        className="text-5xl md:text-7xl font-black tracking-tight text-foreground leading-none flex flex-col sm:flex-row items-center gap-x-4 gap-y-1"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.2 }}
      >
        <span>De-Identify.</span>
        <TypeAnimation
          sequence={["Local", 2500, "Private", 2500, "Offline", 2500]}
          omitDeletionAnimation
          wrapper="span"
          speed={50}
          repeat={Infinity}
          className="bg-gradient-to-r from-blue-500 to-indigo-500 bg-clip-text text-transparent min-w-[220px] sm:text-left text-center"
        />
      </motion.h1>

      <motion.p
        className="text-lg md:text-xl text-gray-500 dark:text-gray-400 max-w-xl leading-relaxed"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.35 }}
      >
        AI-assisted anonymization that never leaves your machine.
        Strip PII from text and documents — offline, fast.
      </motion.p>

      <motion.div
        className="flex items-center gap-3"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.48 }}
      >
        <a
          href={GITHUB_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 px-4 py-2.5 rounded-lg border border-gray-200 dark:border-gray-700 text-sm font-medium text-gray-600 dark:text-gray-300 hover:border-gray-400 dark:hover:border-gray-500 hover:text-foreground transition-colors"
        >
          <Github size={16} />
          GitHub
        </a>
        <a
          href={RELEASES_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="group flex items-center gap-2 px-6 py-2.5 rounded-lg bg-gradient-to-r from-blue-500 to-indigo-600 text-white font-semibold text-sm shadow-md shadow-blue-500/20 hover:shadow-blue-500/35 hover:scale-[1.02] active:scale-[0.99] transition-all duration-200"
        >
          <Download size={16} className="group-hover:-translate-y-0.5 transition-transform" />
          Download
        </a>
      </motion.div>
    </motion.div>

    {/* Bottom: feature cards */}
    <motion.div
      className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-2xl"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay: 0.6 }}
    >
      {features.map((f) => (
        <div
          key={f.title}
          className="flex gap-3 p-4 rounded-xl bg-white/70 dark:bg-white/[0.04] border border-gray-200/80 dark:border-white/[0.08] backdrop-blur-sm"
        >
          <div className="shrink-0 mt-0.5 w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
            <f.icon size={16} className="text-primary" />
          </div>
          <div>
            <p className="font-semibold text-foreground text-sm">{f.title}</p>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 leading-snug">{f.desc}</p>
          </div>
        </div>
      ))}
    </motion.div>


    <div className="animate-arrow absolute bottom-6 text-gray-400">
      <ChevronDown size={22} />
    </div>

  </section>
)
