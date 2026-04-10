import { motion } from "framer-motion"
import { TypeAnimation } from "react-type-animation";
import { Github, Download, ChevronDown } from "lucide-react"

const GITHUB_URL = "https://github.com/jayf0x/DeID"
const RELEASES_URL = "https://github.com/jayf0x/DeID/releases"

export const Banner = () => (
  <section className="min-h-screen flex flex-col items-center justify-center px-6 relative">
    <motion.div
      initial={{ opacity: 0, y: 28 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.7, ease: "easeOut" }}
      className="flex flex-col items-center gap-8 text-center max-w-3xl"
    >
      <motion.img
        src="/logo.png"
        alt="DeID"
        className="h-28 w-auto"
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.6, delay: 0.1 }}
      />

      <div className="space-y-4">
        <motion.h1
          className="text-5xl md:text-7xl font-black tracking-tight text-foreground leading-none flex lg:flex-row sm:flex-col"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
        >
          <div>De-Identify.</div>
            <TypeAnimation
              sequence={[
                "Local",
                2500,
                "Private",
                2500,
                "Offline",
                2500,
              ]}
              omitDeletionAnimation
              wrapper="div"
              speed={50}
              repeat={Infinity}
              className="bg-gradient-to-r from-blue-500 to-indigo-500 bg-clip-text text-transparent !w-[250px] text-left"
            />
        </motion.h1>

        <motion.p
          className="text-lg md:text-xl text-gray-500 dark:text-gray-400 max-w-xl mx-auto leading-relaxed"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.35 }}
        >
          AI-assisted anonymization that never leaves your machine.
          Strip PII from text and documents — offline, fast.
        </motion.p>
      </div>
    </motion.div>

    <motion.div
      className="absolute bottom-8 text-gray-400"
      animate={{ y: [0, 7, 0] }}
      transition={{ repeat: Infinity, duration: 2.2, ease: "easeInOut" }}
    >
      <ChevronDown size={22} />
    </motion.div>
  </section>
)
