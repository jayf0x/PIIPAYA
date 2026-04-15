You are refactoring a Svelte frontend codebase using a predefined backlog.

### Input files
- `backlog-frontend.md`
- `about-frontend.md`

### Core workflow (strict loop)
1. Find the **first incomplete item** in `backlog-frontend.md` (should be at the top of the file)
2. Fully resolve it
3. Remove completed item from backlog.
4. Move to the next item


### Non-negotiable rules
- Do NOT skip items
- Do NOT partially complete items
- Do NOT reorder items
- Always finish the current item before moving on


### Definition of done
An item is complete only if:

- All affected files are updated
- No duplicate or conflicting patterns remain
- The solution is applied consistently across the codebase
- The original problem described in the backlog is fully resolved


### Atomic execution
- Each backlog item is assumed to be atomic
- If an item turns out to be too large:
  - Split it into smaller backlog items
  - Complete the current item only if its scope is still valid

### Handling ambiguity
- If something is unclear but does not block progress:
  - Make a reasonable assumption and proceed

- If something blocks proper implementation:
  - Create a new backlog item with:
    type: research
  - Clearly describe what is unclear and why it blocks progress

### Refactoring rules
- Fix root causes, not symptoms
- Do not introduce unnecessary abstractions
- Do not duplicate logic
- Centralize shared logic, styles, and types where appropriate
- Avoid prop drilling when shared state is more suitable

### Autonomy constraints
- Do not explain what you are doing
- Do not produce summaries
- Only output code changes and backlog updates

### Consolidation rule (important)
When implementing backlog items:

- Prefer merging existing modules over creating new parallel ones that represent the same concept.
- If multiple implementations of the same domain concept exist, consolidate them into a single canonical module.
- Do not introduce additional stores, configs, or modules unless they clearly represent a distinct domain with separate responsibilities.
- Avoid splitting state across multiple new modules if it can remain cohesive in one place.


### Data ownership consistency
- Ensure each domain concept has a single source of truth across the codebase.
- All related logic, state, and configuration must reference that single source.
- Do not create duplicate or competing representations of the same data.


# Expected Result
Fully finished features, like a senior dev that took full ownership.