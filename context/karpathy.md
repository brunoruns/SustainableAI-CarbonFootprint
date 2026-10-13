# Karpathy's Behavioral Guidelines for AI Agents

> **Goal:** Avoid common LLM coding mistakes.
> **Rule of thumb:** These guidelines are cautionary. For trivial tasks, use your judgment.

---

## 1. Think before you code

**Assume nothing. Hide no confusion. Make trade-offs visible.**

Before you implement:

- State your assumptions explicitly. If you are unsure, ask.
- Are there multiple interpretations? Lay them out — do not choose in silence.
- Is there a simpler approach? Say so. Dare to push back.
- If something is unclear, stop. Name what is confusing. Ask.

## 2. Simplicity first

**Minimal code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for one-off code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- Writing 200 lines when 50 would suffice? Rewrite.

Ask yourself: "Would a senior engineer find this too complicated?" If yes, simplify.

## 3. Surgical changes

**Touch only what you need to touch. Clean up only your own mess.**

When editing existing code:

- Do not "improve" adjacent code, comments, or formatting.
- Do not refactor what isn't broken.
- Match the existing style, even if you would do it differently.
- Spot unrelated dead code? Report it — do not remove it.

When your changes make something redundant:

- Remove imports/variables/functions that **your** changes rendered unused.
- Do not remove existing dead code unless asked.
+
The test: every changed line must be directly traceable to the request.

## 4. Goal-Driven Execution

**Define success criteria. Iterate until verified.**

Turn tasks into testable goals:

- "Add validation" → "Write tests for invalid input, make them pass"
- "Fix the bug" → "Write a test that reproduces the bug, make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, make a short plan:

```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you iterate independently. Weak criteria ("make it work") constantly ask for clarification.

---
