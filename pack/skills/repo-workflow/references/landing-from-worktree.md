# Landing Changes from a Git Worktree

Use this procedure when `executor` implements work inside `<toplevel>/.agents/worktrees/<slug>`.

## Creating the Worktree

1. Resolve repo root: `TOP=$(git rev-parse --show-toplevel)`.
2. Ensure local exclude exists:
   Check `.git/info/exclude` contains `.agents/worktrees/` and append if missing.
3. Create branch + worktree cleanly:
   `git worktree add "$TOP/.agents/worktrees/<slug>" -b "work/<slug>"`

## Running Inside the Worktree

- Run all edits, builds, unit tests, critic reviews, and `residue` sweeps inside
  `$TOP/.agents/worktrees/<slug>`.
- Commit clean logical commits on `work/<slug>` inside the worktree if needed before
  landing back to the primary checkout.

## Local Landing (No Unrequested Pushes)

1. Confirm primary checkout (`$TOP`) is on the target branch and free of conflicting dirty
   edits on overlapping files (`git -C "$TOP" status --short`).
2. Review full diff against target branch:
   `git diff <base>..work/<slug>` and run targeted tests.
3. Squash-merge locally into the primary checkout:
   ```bash
   git -C "$TOP" merge --squash "work/<slug>"
   git -C "$TOP" commit -m "<concise summary>" \
     -m "Co-Authored-By: Supervisor for Antigravity"
   ```
   Ask the user before committing if they prefer reviewing unstaged or staged changes first.
4. Re-run the verification test command in `$TOP` after landing.
5. Remove worktree and delete temporary branch:
   `git -C "$TOP" worktree remove "$TOP/.agents/worktrees/<slug>"`
   `git -C "$TOP" branch -D "work/<slug>"`
