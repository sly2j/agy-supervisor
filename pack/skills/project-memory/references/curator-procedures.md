# Curator Procedures

Follow these procedures when `curator` updates `.supervisor/` after milestones or on
close-out.

## Update Checklist

1. **Inspect current state**:
   - Read `.supervisor/roadmap.md`, `.supervisor/history.md` (tail ~60 lines), and run
     `git status --short` plus `git log -n 5 --oneline` to verify what actually landed.
2. **Append `.supervisor/history.md`**:
   - Add a dated entry (`## YYYY-MM-DD — <Short Title>`) summarizing verified changes,
     commit SHAs (if committed), and key verification commands observed.
   - Keep entries concise (3–8 bullets). Never overwrite or rewrite older history entries.
3. **Update `.supervisor/roadmap.md`**:
   - Move completed items out of Active / Open into Recently Completed (or prune stale ones).
   - Record concrete next steps, blockers, and verified test status accurately.
4. **Add ADRs / conventions when warranted**:
   - Create `.supervisor/memory/decisions/YYYY-MM-DD-<slug>.md` using `../templates/entry.md`
     for non-obvious architectural choices, trade-offs, or invariants.
   - Update `.supervisor/memory/conventions/` only for durable project-wide rules discovered
     during real work.
5. **Verify store hygiene**:
   - Ensure no temporary scratch paths, secrets, or speculative unverified test claims
     entered `.supervisor/`.
   - Confirm `.supervisor/` edits stay crisp; never run `git commit` (`git-ops` commits when
     requested).
