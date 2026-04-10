import { motion } from "framer-motion"

const features = [
  {
    label: "01",
    title: "Workbench",
    desc: "Paste text or drop files into the workbench. Select which entity types to detect — names, locations, dates, IDs, and more. Hit run and watch the output stream in real time with highlighted segments showing every redaction.",
    img: "/preview.png",
  },
  {
    label: "02",
    title: "Entity control & profiles",
    desc: "Fine-tune detection per run or save named profiles for repeated workflows. Each profile remembers your entity selection, model choice, and settings. Switch profiles in one click.",
    img: "/preview.png",
  },
  {
    label: "03",
    title: "Export anywhere",
    desc: "Copy the output, save as text, download processed files individually, or zip everything for handoff. The original filenames are preserved with a clean suffix.",
    img: "/preview.png",
  },
]

const fadeUp = (delay: number) => ({
  initial: { opacity: 0, y: 20 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: "-80px" },
  transition: { duration: 0.55, delay, ease: "easeOut" },
})

export const DocsSection = () => (
  <section className="py-28 px-6 border-t border-gray-200/60 dark:border-white/[0.07]">
    <div className="max-w-4xl mx-auto space-y-24">
      <motion.div {...fadeUp(0)} className="space-y-2 text-center">
        <p className="text-sm font-semibold text-primary uppercase tracking-widest">
          Features
        </p>
        <h2 className="text-3xl md:text-4xl font-bold text-foreground">
          How it works
        </h2>
      </motion.div>

      {features.map((f, i) => (
        <motion.div
          key={f.label}
          {...fadeUp(0.1)}
          className={`flex flex-col ${
            i % 2 === 0 ? "md:flex-row" : "md:flex-row-reverse"
          } gap-10 md:gap-16 items-center`}
        >
          <div className="flex-1 space-y-4 min-w-0">
            <p className="text-4xl font-black text-gray-100 dark:text-white/10 select-none">
              {f.label}
            </p>
            <h3 className="text-xl font-bold text-foreground -mt-2">{f.title}</h3>
            <p className="text-gray-500 dark:text-gray-400 leading-relaxed text-sm md:text-base">
              {f.desc}
            </p>
          </div>

          <div className="flex-1 w-full min-w-0">
            <div className="rounded-xl overflow-hidden border border-gray-200/80 dark:border-white/[0.08] shadow-xl shadow-black/5 dark:shadow-black/30">
              <img
                src={f.img}
                alt={f.title}
                className="w-full h-auto block"
              />
            </div>
          </div>
        </motion.div>
      ))}
    </div>
  </section>
)
