import { motion, Variants } from "framer-motion"
import { ShieldCheck, Cpu, Files, Link2, Download } from "lucide-react"

const RELEASES_URL = "https://github.com/jayf0x/DeID/releases/latest"

const features = [
  {
    icon: ShieldCheck,
    title: "Fully local",
    desc: "No cloud. No telemetry. Your data never leaves the machine.",
  },
  {
    icon: Cpu,
    title: "AI-powered detection",
    desc: "Entity recognition via spaCy. Accurate across text, PDFs, and documents.",
  },
  {
    icon: Files,
    title: "Batch processing",
    desc: "Drop multiple files. Process in one run. Queue management built in.",
  },
  {
    icon: Link2,
    title: "Narrative coherence",
    desc: "Same entity → same alias across all files, every run. No inconsistencies.",
  },
]

const fadeUp = (delay: number): Variants & { initial: object; whileInView: object; viewport: object } => ({
  initial: { opacity: 0, y: 20 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: "-80px" },
  transition: { duration: 0.55, delay, ease: "easeOut" },
})

export const InfoSection = () => (
  <section className="py-28 px-6">
    <div className="max-w-4xl mx-auto space-y-16">
      <motion.div
        {...fadeUp(0)}
        className="space-y-4 text-center"
      >
        <p className="text-sm font-semibold text-primary uppercase tracking-widest">
          Why DeID
        </p>
        <h2 className="text-3xl md:text-5xl font-bold text-foreground">
          Privacy shouldn't be<br className="hidden sm:block" /> an afterthought.
        </h2>
        <p className="text-gray-500 dark:text-gray-400 max-w-2xl mx-auto text-lg leading-relaxed">
          Sharing clinical notes, legal documents, or research data means stripping
          names, locations, and identifiers first. DeID does that automatically —
          no internet required, no data leaving your machine.
        </p>
      </motion.div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {features.map((f, i) => (
          <motion.div
            key={f.title}
            {...fadeUp(0.08 + i * 0.07)}
            className="flex gap-4 p-5 rounded-xl bg-white/70 dark:bg-white/[0.04] border border-gray-200/80 dark:border-white/[0.08] backdrop-blur-sm"
          >
            <div className="shrink-0 mt-0.5 w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center">
              <f.icon size={18} className="text-primary" />
            </div>
            <div>
              <p className="font-semibold text-foreground text-sm">{f.title}</p>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1 leading-snug">
                {f.desc}
              </p>
            </div>
          </motion.div>
        ))}
      </div>

      <motion.div {...fadeUp(0.35)} className="flex justify-center">
        <a
          href={RELEASES_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="group inline-flex items-center gap-3 px-9 py-4 rounded-2xl bg-gradient-to-r from-blue-500 to-indigo-600 text-white font-bold text-lg shadow-lg shadow-blue-500/20 hover:shadow-blue-500/35 hover:scale-[1.02] active:scale-[0.99] transition-all duration-200"
        >
          <Download size={22} className="group-hover:-translate-y-0.5 transition-transform" />
          Download
        </a>
      </motion.div>
    </div>
  </section>
)
