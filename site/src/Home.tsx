import { HeroSection } from "./sections/HeroSection"
import { DocsSection } from "./sections/DocsSection"
import { Github } from "lucide-react"

const GITHUB_URL = "https://github.com/jayf0x/DeID"

export const Home = () => (
  <>
    <HeroSection />
    <DocsSection />

    <footer className="py-8 px-6 border-t border-gray-200/60 dark:border-white/[0.07] text-center">
      <p className="text-sm text-gray-400 flex items-center justify-center gap-2">
        DeID ·{" "}
        <a
          href={GITHUB_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 hover:text-primary transition-colors"
        >
          <Github size={13} />
          jayf0x/DeID
        </a>
      </p>
    </footer>
  </>
)
