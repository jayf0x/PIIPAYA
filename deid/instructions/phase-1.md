# Project: DeID — a local-first text anonymization workbench (Svelte 5 + Tauri + Python sidecar).

Read this file before anything `./about.md`

You are analyzing a Svelte frontend codebase in `./src`
Your task is to map structural issues and produce a backlog. You are NOT allowed to modify code in this phase.



### Output files

You must create or overwrite:
1. `backlog-frontend.md`
2. `about-frontend-backlog.md`

### Backlog format (strict)

Each item must follow this exact structure:
```
## [area: <area>] [name as UID]
type: feature | bug | research

[full detailed explanation]
```


### Rules for backlog items
- Each item must be **atomic**
  - It must be solvable in a single focused session
  - If it is too large, split it into multiple items

- Each item must include:
  - What the problem is
  - Why it is a problem (maintenance, consistency, scalability, etc.)
  - What “done” looks like (clear end condition)

- Do NOT create vague items like “refactor code” or “improve structure”

### Handling ambiguity

- If a problem cannot be clearly solved due to missing context or unclear direction:
  - Create a backlog item with:
    type: research

- Research items must clearly state:
  - What is unclear
  - What decision needs to be made
  - What parts of the codebase are affected

### What to look for

Focus only on structural and maintainability issues:

- Styling inconsistencies (e.g. hardcoded colors, lack of variables)
- Large components (e.g. very large `.svelte` files)
- Prop drilling and state flow issues
- Duplicated utilities or logic
- Inline configs and scattered constants
- Missing shared types
- Folder and file organization problems

Do NOT include performance optimizations unless clearly necessary.


### about-frontend-backlog.md

This file must describe:

- Target structure (folders, responsibilities)
- State management approach (e.g. stores usage)
- Styling strategy (e.g. CSS variables, theming)
- Rules for code reuse (utils, types, components)

Keep it concrete and implementation-focused. No abstract principles.


### Constraints

- Do not modify any source code
- Do not summarize your work
- Do not explain your reasoning
- Only produce the two files

Your output must be complete and actionable