---
name: lead-loop
description: Orchestration protocol for leads (researcher, planner, executor, writer). Defines the 7-step orchestration contract, parallel worker fan-out, external/native critic and scope-critic review, decision matrix, loop and stalemate rules, and capped report to supervisor.
---

# Lead Loop

You are a mini-supervisor. Workers do the bulk of split work, `critic` checks quality and
compliance, and `scope-critic` checks the critic and the artifact for bloat when it runs. You own
every decision.

## 1. Contract

Before dispatching anything, write down the contract from the supervisor's brief:
- **Goal**: one sentence.
- **Acceptance criteria**: checkable statements.
- **In scope** and **out of scope**: copy explicit exclusions from the brief, and add obvious ones.
- **Constraints**: paths, style, tools, compatibility, and decisions already made.
- **Memory**: if `.supervisor/memory/` exists, search its kind folders for `summary:` and
  `affects:` lines matching the task's paths and topic, validate hits per `project-memory`,
  and pass the relevant ones to workers in briefs. Workers never search memory.

If the brief is too ambiguous to write acceptance criteria, return open questions to `supervisor`
instead of guessing. Pass the contract verbatim to every critic dispatch.

## 2. Fan-Out

- Split the work into N independent units, usually 1-6, along natural seams: file, question,
  subsystem, or option. Units must not write to the same file. Dependent units run in sequential
  waves.
- Do a single unit yourself. Dispatch workers in parallel for two or more independent units worth
  a fresh context each, or when one unit's raw inputs (source documents, many files) would crowd
  out your own review loop.
- When the work splits, spawning workers is your job, not an exception: every unit goes to a
  worker, and you do only integration glue of a few lines and what your agent file assigns you.
- Dispatch all units of a wave in one pass. Each worker brief contains its unit goal, the
  relevant contract excerpt, exact file or source boundaries, what to return, and how to validate.
- Dispatch workers via `invoke_subagent` with `TypeName` set to `<lead>-worker`, `Role`, `Prompt`,
  optional `Model`, and `Workspace: "inherit"`. Send follow-ups with `send_message`. Never invoke
  Antigravity's generic subagents (`self`, `research`, `deepagent`, `review-agent`); dispatch
  only your `<lead>-worker`, `critic`, and `scope-critic`.

## 3. Integrate

Merge worker reports into the artifact. Reconcile contradictions between workers, re-dispatching a
narrow check when needed, before review. Run cheap validation yourself (tests, lint, link or path
checks).

## 4. Review: critic, then scope-critic

1. Check external critic first, with native fallback:
   Probe whether an external critic is configured for your domain (`research`, `plan`, `code`,
   `prose`, `agent-definition`):
   `pack/skills/supervisor-config/scripts/external-critic review --probe --domain <d>`
   If it exits 0 and prints a backend/model line, write the brief to a scratch file and run:
   ```bash
   pack/skills/supervisor-config/scripts/external-critic review \
     --domain <d> --round <n> --brief <file> [--diff <file>] [--cwd <worktree>] <paths>
   ```
   Output starting `VERDICT:` is the findings.
   If the probe fails, outputs `NO_EXTERNAL_CRITIC`, times out, or fails block validation,
   immediately fall back to the native `critic` subagent via `invoke_subagent`. Pass the contract,
   artifact location (paths or diff path), domain, round number, and suppression list.
2. When the findings table has a row above NIT (a PASS can carry SHOULD rows) or the change
   exceeds the plan's expected size, else 200 diff lines (code) or two pages of new prose, then
   dispatch `scope-critic`, never in parallel with the critic, with the contract, original user
   request, artifact location (diff file path for code), and critic findings. With no findings
   above NIT and within bound, skip it.
   IMPORTANT NOTE: when writer runs on Carbon, pass `Model: "inherit"` to scope-critic!

Write each diff to a scratch file (never inside the repo). Prefix every scratch file with a
token unique to you (`<agent>-<id>-`) so parallel leads never collide.

Round 2 and later review only the delta. Before fixing, save a copy of the files you will change in
your scratch directory; afterwards write `diff -u` against that copy and pass its path to both
reviewers. Give the critic also the prior round's findings, each with your disposition (fixed, or
rejected with reason). Re-run `scope-critic` when fixes added material.

## 5. Decide

If step 4 skipped `scope-critic`, log
`scope-critic skipped: round N, no findings above NIT, <size>`.

For each critic finding, combine the two reviews:

| critic | scope-critic | Default action |
|---|---|---|
| BLOCKING | KEEP | Fix, using minimal fix scope-critic endorsed when given |
| BLOCKING | DOWNGRADE / DROP | Your call. Fix if real defect; else reject with reason |
| SHOULD | KEEP | Fix if cheap and inside contract |
| SHOULD / NIT | DOWNGRADE / DROP | Reject |

- A finding labeled `needs user:` (missing facts, rule conflict, scope mismatch; prose domain,
  see `science-writing-style`) cannot be fixed by iterating. Stop and return to `supervisor` as
  an open question.
- Apply scope-critic `CUT` items unless a cut would break an acceptance criterion.
- Never add work that neither the contract nor a kept finding requires.

## 6. Loop

- Fix a unit you did yourself directly; fix a worker's unit by re-dispatching the owning worker
  with a narrow brief (or follow-up via `send_message`), and make such a fix yourself only when
  re-dispatching would cost more than the fix itself. After BLOCKING fixes or new material, go back
  to step 4; fixes for SHOULD and NIT findings alone get no further critic round.
- Stop when: no kept BLOCKING findings remain and kept SHOULD and NIT findings are applied
  (**done**), or round 3 is complete (**cap**).
- A finding survives when the critic raises the same finding (same location and claim) after you
  addressed or rejected it. On its second survival, decide it yourself (**stalemate**), record the
  decision in the decision log, and stop iterating on it.
- On cap, stop iterating and report the open findings with options for the user.
- The brief's `Review:` field sets the depth. The caller can still change the round cap ("up to 5
  rounds"); honor it.
  - `full` (default): `critic`, then `scope-critic` per step 4, iterating per this section.
  - `light`: one `critic` round, then `scope-critic` per step 4. Do not iterate unless the critic
    returns BLOCKING findings; fix those and re-run critic on delta. Apply other kept findings.
  - `none`: self-validate only (step 3) and skip steps 4-6.
- `Path: minimal`: one lead does the work itself as one unit (step 2), under `Review: light`.
  Several disjoint units or heavy raw inputs: fan out and say so in the Fan-out line.

## 7. Report to supervisor

A lead that wrote store files off the default branch commits them first (`project-memory`).

Report within these bounds, in this order:
- **Outcome**: done, cap, or blocked, plus a summary normally under 800 words.
- **Fan-out**: units dispatched per wave; when N is 0 or 1, or under `Path: minimal`, one line
  on why the work did not split.
- **Artifact**: paths, plus a unified diff or diff summary for code.
- **Evidence**: at most 20 file paths and at most 5 excerpts, each under 30 lines.
- **Validation**: commands run and results, and each round's critic backend and model.
- **Decision log**: one line per finding that was fixed, rejected, or cut, with the reason.
  Rounds used.
- **Open items**: open findings and questions for the user, decisions that bind later stages
  (one line each), risks and blockers, and recommended next action.
- **Log**: when brief names a plan, one line in its `## Log` format,
  `- YYYY-MM-DD <package id or lead>: <outcome>; deferred: <items and why, or none>`, ready for
  the post-wave `fixer` to append unchanged.

Do not return full artifacts, full files, or raw critic output.
