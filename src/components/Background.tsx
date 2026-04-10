export const Background = () => (
  <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
    {/* dot grid */}
    <div className="absolute inset-0 opacity-[0.15] dark:opacity-[0.07]">
      <svg className="w-full h-full animate-slowPan" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <pattern id="dotPattern" x="0" y="0" width="24" height="24" patternUnits="userSpaceOnUse">
            <circle cx="2" cy="2" r="1.2" fill="currentColor" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#dotPattern)" className="text-gray-500 dark:text-gray-400" />
      </svg>
    </div>

    {/* top-left blob */}
    <div className="absolute -top-40 -left-40 w-[500px] h-[500px] bg-gradient-to-br from-blue-400 to-indigo-500 rounded-full mix-blend-multiply dark:mix-blend-screen filter blur-3xl opacity-20 dark:opacity-10 animate-blob" />

    {/* bottom-right blob */}
    <div className="absolute -bottom-40 -right-40 w-[420px] h-[420px] bg-gradient-to-tr from-violet-400 to-purple-500 rounded-full mix-blend-multiply dark:mix-blend-screen filter blur-3xl opacity-20 dark:opacity-10 animate-blob [animation-delay:3s]" />
  </div>
)
