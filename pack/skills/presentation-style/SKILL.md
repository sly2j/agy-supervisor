---
name: presentation-style
description: Design standards for technical slide decks, executive briefings, and architecture walkthroughs.
---

# Presentation & Slide Design Style

Structure slides so each slide communicates one clear point quickly without wall-of-text clutter.

## Slide Structure Rules

1. **Action titles**: write each slide headline as the takeaway assertion (e.g., "Worktree
   isolation cuts merge conflicts across parallel agents") rather than a vague topic label
   ("Worktrees").
2. **30-second scannability**: keep body bullets concise (3–5 bullets per slide, <= 12 words
   per bullet where possible) and move deep implementation notes into speaker notes.
3. **Visual hierarchy**: pair claims with architecture diagrams (`mermaid` or clean block
   schematics), concrete before/after examples, or compact comparison tables.
4. **Honest metrics**: cite exact tested configurations, dates, and denominators on any chart
   or summary table.
5. **Narrative arc**: open with Problem & Stakes -> Architecture / Mechanism -> Verified
   Evidence & Trade-offs -> Concrete Next Steps.
