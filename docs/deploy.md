# Deploying Supervisor for Antigravity

This runbook is for a human or an agent asked to "deploy Supervisor for Antigravity". It works on
macOS and Linux and needs `python3` (3.9 or newer), `git` (to clone, and for `update`), and
Google Antigravity (`agy` CLI or IDE).

## Steps

First time:

```bash
git clone https://github.com/sly2j/agy-supervisor.git ~/Work/agy-supervisor
REPO=~/Work/agy-supervisor
```

From an existing checkout (see Update):

```bash
REPO=~/Work/agy-supervisor
cd "$REPO" && git pull
```

Then, in either case, install into a global plugin: `~/.gemini/config/plugins/agy-supervisor`,
registered in `~/.gemini/config/config.json`, with its own launcher wrapper in
`~/.local/bin/agy-supervisor`; plain `agy` is untouched.

```bash
"$REPO/deploy" doctor        # preflight: python, agy version, pack validation (warns "not installed yet" on a fresh machine)
"$REPO/deploy" install --dry-run
"$REPO/deploy" install       # plugin in ~/.gemini/config/plugins/agy-supervisor + launcher in ~/.local/bin/agy-supervisor
"$REPO/deploy" status
"$REPO/deploy" doctor        # should now report no FAIL
```

Start it with `agy-supervisor`. The session runs as `supervisor` because the launcher passes
`--agent supervisor` to `agy`.

If `install` prints `WARNING <bin> is not on your PATH; add export PATH="<bin>:$PATH" to your shell
profile, then open a new terminal`, `agy-supervisor` will not be found until that line is in the
shell profile (`<bin>` is `~/.local/bin` by default).

`doctor`, `status`, `update` and `uninstall` take the same `--tag`, `--workspace`, or `--target`
(and `--prefix`) as the install.

## What Install Does

- Copies the pack's plugin definition, agents, and skills into the target:
  - Global install (default): `~/.gemini/config/plugins/agy-supervisor` (or `agy-<tag>`), and
    registers the plugin in `~/.gemini/config/config.json` (`plugins.agy-<tag>.enabled = true`).
  - Workspace install: `--workspace DIR` installs into `DIR/.agents/plugins/agy-<tag>`.
  - Explicit target: `--target DIR` installs into any target directory.
- Re-running `install` is the update path and is safe to repeat. Install tracks the files it
  wrote in a SHA-256 manifest (`.agy-supervisor-manifest.json`), so your edits survive:

| Situation | Action |
|---|---|
| File not installed yet | copied |
| Installed and unmodified, source changed | updated |
| You edited the installed file | kept, with a warning (`--overwrite-local` backs it up as `<file>.bak-<timestamp>` and replaces it) |
| An unmanaged file with that name exists | refused, exit code 1 (`--overwrite-local` backs it up and replaces it) |
| File removed from the pack | deleted if unmodified, otherwise kept and handed over to you |

- Sets the default model in the manifest (`--default-model`, default `gemini-4-carbon-medium`).
- Writes the launcher `<prefix>/bin/agy-<tag>` (`--prefix P`, default `~/.local`, launcher path
  `~/.local/bin/agy-supervisor`), which manages subcommands (`update`, `uninstall`, `status`,
  `list`, `doctor`, `critic`, `memory`) and forwards everything else to `agy --agent supervisor`.
  Later `install` and `uninstall` runs must use the same `--prefix`; the error names it. Install
  refuses a tag whose launcher path holds a file it did not write.
- Adds scoped permissions to `~/.gemini/antigravity-cli/settings.json`:
  - An allow rule for the external critic review script
    (`Bash(<target>/skills/supervisor-config/scripts/external-critic review *)`), so external
    critic reviews run without repeated interactive prompts while keeping `enable` and
    `disable` gated behind user consent.
  - The external memory root (see [Memory](#memory)) in `permissions.additionalDirectories` and
    an allow rule, so stores reached through `.supervisor` and `GEMINI.local.md` symlinks do not
    prompt on every write.
  Entries already present are left alone; uninstall removes only those install recorded adding.
- Runs `agy plugin validate --strict --json` on the pack before writing anything (skip with
  `--skip-agy-validate`).
- Prints `Version: <version>`, with `(was <old>)` on an update (see Versions).

### Versions

An install shows the pack's `VERSION` (e.g. `1.1`). `status`, `list`, and `--version` report the
recorded version.

## The Launcher

```bash
agy-supervisor update              # this profile's pack
agy-supervisor update --all        # every install in this launcher's prefix
agy-supervisor uninstall           # remove this install and launcher
agy-supervisor status              # this profile's version and file states
agy-supervisor list                # every install in this launcher's prefix
agy-supervisor doctor              # run preflight diagnostics for this install
agy-supervisor memory externalize|link|status  # keep project memory outside repo (see Memory)
agy-supervisor critic enable|disable|status    # Claude or Codex reviewer (see External Critic)
agy-supervisor --version           # pack version (or -v)
agy-supervisor -h                  # launcher help (or --help)
```

The launcher handles `update`, `uninstall`, `status`, `list`, `doctor`, `memory`, `-v`, and `-h`
for its own install, and `critic` through the install's external critic script. Anything else goes
to `agy`, passing `--agent supervisor` and the resolved model, so `agy-supervisor` works as usual.
Use `./deploy` for other installs or custom targets without a launcher. Replace `supervisor` with
your `--tag`.

- `update` updates this install from the cached pack snapshot (or `--from DIR`). `--dry-run`
  shows what would change.
- `uninstall` removes this install (its plugin directory, launcher, and registry entry). It asks
  you to type the tag to confirm; `--yes` skips confirmation.
- Without a terminal, `uninstall` needs `--yes` (exit code 1 otherwise); `update` runs
  non-interactively.
- If the install's copy of `deploy` (see [Update](#update)) is missing, the launcher prints an
  error and exits 1; run `./deploy install` from your checkout to restore it.
- Workspace installs (`--workspace`) or custom targets (`--target`) without launchers use the
  deploy tool (`./deploy <verb> --target DIR` from a checkout).

## Update

Every install records itself in a registry and keeps a copy of `deploy` beside it, both in
`<prefix>/state/agy-supervisor/`, so `update` does not need the checkout. Each `--prefix` has its
own registry. The commands below use the default prefix.

```bash
~/.local/state/agy-supervisor/deploy update                # the default profile; or "$REPO/deploy" update
~/.local/state/agy-supervisor/deploy update --tag work     # another profile (--target DIR, or --workspace)
~/.local/state/agy-supervisor/deploy update --all          # every registered install
~/.local/state/agy-supervisor/deploy list                  # what is registered
```

`list` shows each install's tag, target, version, mode, and target status.

`update` reinstalls from the pack snapshot in state, or from a directory passed with `--from DIR`.
`--all` updates every registered install; `--dry-run` shows what would change.

If an install has locally modified files, `update` preserves them with a warning; `--force` (or
`--overwrite-local`) backs them up (`<file>.bak.<timestamp>`) and replaces them.

`status` reports file states and warns when managed files are missing or modified.

### Dev Worktree Install

To try a feature branch next to your normal install, give it its own worktree (in-repo, under
`.agents/worktrees/`, which this repo ignores) and tag:

```bash
git -C "$REPO" worktree add .agents/worktrees/my-feature -b my-feature
"$REPO/.agents/worktrees/my-feature/deploy" install --tag supervisor-dev
agy-supervisor-dev            # runs the branch's pack
```

To update the test install after editing in the worktree, re-run
`./deploy install --tag supervisor-dev` from the worktree. Remove the test install with
`agy-supervisor-dev uninstall`.

## Launcher Model Configuration

Antigravity structures agent execution across four model tiers:

| Tier | Model Family | Role in Pack |
|---|---|---|
| `inherit` | Gemini 4 Carbon medium | Supervisor session default; high-complexity planning, subtle refactoring, long prose |
| `pro` | Gemini Pro | Autonomous leads (`planner`, `researcher`, `executor`), native `critic`, `scope-critic`, `writer-worker` |
| `flash` | Gemini Flash | Scoped parallel workers (`curator`, `planner-worker`, `researcher-worker`, `executor-worker`) |
| `flash_lite` | Gemini Flash Lite | Fast, deterministic quick agents (`fixer`, `git-ops`, `scout`) |

### Launcher Model Resolution Hierarchy

When you invoke the `agy-supervisor` launcher wrapper, it determines the active model in order of
priority:

1. **Explicit command-line flag**: `--model <id>` or `-m <id>` passed to `agy-supervisor` overrides
   all defaults for that session.
2. **Environment variable**: `AGY_SUPERVISOR_MODEL` (e.g.
   `export AGY_SUPERVISOR_MODEL="gemini-4-carbon-medium"`) in your shell profile or environment.
3. **Installed default model**: Configured at install time via
   `./deploy install --default-model <id>` (default `gemini-4-carbon-medium`), recorded in
   `.agy-supervisor-manifest.json`.

If `--model` or `-m` is present in the arguments passed to the launcher, the launcher forwards
`$@` directly to `agy --agent supervisor "$@"`. If omitted, it passes `--model "$MODEL"`.

### Dynamic Caller Overrides

Within an active session, subagents run at their declared tier by default. Dynamic caller
overrides (documented in `pack/agents/supervisor.md`) allow leads and callers to adjust a worker's
model tier based on task complexity:

- **Planner escalation**: `planner` escalates to `inherit` (Carbon) when handling open-ended
  multi-package programs, cross-module architectural refactors, or unfamiliar domains.
- **Writer downgrade**: `writer` downgrades to `pro` for short, low-stakes prose (commit notes,
  meeting minutes, simple updates).
- **Executor adjustments**: `executor` adjusts to `inherit` for subtle debugging, delicate
  concurrency, or agent authoring, and can downgrade mechanical workers to `flash`.
- **Scope critic inheritance**: `scope-critic` inherits Carbon from Carbon callers to maintain
  evaluation parity.

## External Critic (Claude or Codex)

An opt-in mode in which the lead's critic step runs an external CLI (Anthropic Claude Code CLI
`claude` or OpenAI Codex CLI `codex`) instead of the native Gemini `critic` subagent. Only the
critic changes: `scope-critic` stays on Google Antigravity, and any failed external review falls
back to the native `critic` for that round, automatically. It needs the respective CLI (`claude`
or `codex`) on `PATH` and an authenticated session; `enable` checks both before asking for
consent.

### Consent, Cost, And Data Flow

- External reviews spend your Anthropic or OpenAI API quota / subscription credits.
- Repository content under the current directory, the review brief, and diffs are sent to Anthropic
  or OpenAI.

`enable` prints this consent text and asks for confirmation; without a terminal it needs `--yes`.
External reviews run read-only and ephemeral.

Install adds one rule to `permissions.allow` in `~/.gemini/antigravity-cli/settings.json` that
allows the review script's `review` command, so external reviews never prompt you for permission:

```json
{
  "permissions": {
    "allow": [
      "Bash(<target>/skills/supervisor-config/scripts/external-critic review *)"
    ]
  }
}
```

Commands `enable`, `disable`, and `status` are not in the allow rule, so turning an external critic
on or off from a session requires explicit user confirmation and no agent can do it unasked.

### Switching

```bash
./deploy critic enable [claude|codex] [MODEL]   # also: disable, status; takes --tag, --target
agy-supervisor critic status                    # the launcher forwards to the same script
/supervisor-config critic claude|codex [model] | status   # inside a session
```

No reinstall is needed. The mode lives in `supervisor-config.json` at the plugin root, and a switch
takes effect from the next task. `install` prints a hint to enable an external critic when `claude`
or `codex` is on `PATH` and the mode is off. To return to the native Gemini critic, run
`./deploy critic disable` or `agy-supervisor critic disable`.

### Models

For Claude, models default to `claude-opus-5-5` or `claude-sonnet-5-5`. For Codex, the default is
`gpt-6.1-sol` or `gpt-6-astra`. Per-domain overrides can be configured via `--domain` or edited
into `supervisor-config.json`. The supported domains are `research`, `plan`, `code`, `prose`, and
`agent-definition`:

```json
{
  "critic": {
    "enabled": true,
    "backend": "claude",
    "domains": {
      "code": "codex",
      "prose": "claude",
      "plan": {"backend": "codex", "model": "gpt-6-astra", "effort": "high"}
    }
  }
}
```

### Fallback And Which Engine Reviewed

When an external critic is disabled for a domain, missing, fails, or times out (default 240 s),
that round falls back to the native `critic` subagent. The lead's report names the engine per
round (e.g. `critic: claude claude-opus-5-5`, `critic: codex gpt-6.1-sol high`, or
`critic: native (<reason>)`). `critic status` shows the backend, models, domain overrides, CLI
auth state, and whether the allow rule is present; `doctor` reports external-critic status.

### Caveats

- Model IDs are account-specific. An invalid or unavailable model ID causes reviews to fall back
  to the native critic, with the reason reported in the lead's report.
- The allow rule in `settings.json` must match the installed script path. If `critic status`
  indicates the rule is missing, re-run `./deploy install` to add it.
- External CLIs run in read-only mode and do not mutate repository state.
- Reviews take from tens of seconds to several minutes; after the timeout (default 240 s) the
  round falls back to the native critic.

## Memory

```bash
agy-supervisor memory externalize [--root DIR] [--name N]
agy-supervisor memory link [DIR] [--root DIR] [--name N]
agy-supervisor memory status
```

Use this to keep a local memory store outside the repo, shared by all its worktrees
([local-memory.md](local-memory.md)). Run it inside a git project. `externalize` moves the
project's `.supervisor/` and `GEMINI.local.md` (or creates them) to `<root>/<name>/`, replaces
them with absolute symlinks, and lists both in `.git/info/exclude`. `link` attaches a checkout, a
linked worktree, or a fresh machine to an existing external directory, and `status` reads without
writing and exits 1 with a repair hint. The root is `$AGY_SUPERVISOR_MEMORY_ROOT`, else
`${XDG_DATA_HOME:-~/.local/share}/agy-supervisor/memory`.

`externalize` also adds permission grants for its root to `~/.gemini/antigravity-cli/settings.json`
when missing (or the store itself with `--dir`). Uninstall leaves these entries.

`externalize` and `link` check everything before they write, are safe to repeat, and never
overwrite or delete your files. Windows is not supported. Setup, git history for the memory, fresh
machines, worktrees, and moving back are covered in [local-memory.md](local-memory.md).

## Doctor Checks

| Check | Level | Meaning and remedy |
|---|---|---|
| python >= 3.9 | FAIL | Deploy needs 3.9 or newer |
| `agy` CLI on `PATH` | WARN | Install Antigravity CLI and open a new terminal |
| `agy --version` readable | FAIL | Antigravity CLI failed to report version; reinstall or check CLI path |
| `agy plugin validate` on pack | FAIL | Source pack failed strict validation; check pack structure and manifests |
| Manifest readable | FAIL | Restore it from a backup, or delete it and re-run `./deploy install` (existing files then need `--overwrite-local`) |
| Pack installed (manifest exists) | WARN | Pack not installed in target yet; run `./deploy install` from your checkout |
| Managed files missing | FAIL | Run `./deploy install` |
| Managed files modified | WARN | Keep them, or run `./deploy install --overwrite-local` |
| Default model configured | PASS | Active default model recorded in manifest |
| `config.json` `plugins.<tag>.enabled = true` | WARN | Plugin is not enabled in `~/.gemini/config/config.json`; re-run `./deploy install` |
| Launcher present | WARN | Launcher missing at `<prefix>/bin/agy-<tag>`; run `./deploy install` |
| `settings.json` critic review rule | WARN | Scoped external-critic review rule missing from `settings.json`; run `./deploy install` |
| External critic status | WARN | External critic CLI missing, not logged in, or misconfigured; run `critic disable` or check credentials |
| `git` | WARN | Needed for `./deploy update` and to clone; optional otherwise (`git-ops` uses it) |
| `zip` | WARN | Optional; used by `project-backup` |

Doctor exits 1 if any row is FAIL; WARN rows do not change the exit code. Pass `--json` to output
machine-readable diagnostics.

## Uninstall

```bash
"$REPO/deploy" uninstall --dry-run
"$REPO/deploy" uninstall --yes
"$REPO/deploy" uninstall --all --yes
```

Uninstall deletes the target plugin directory (`~/.gemini/config/plugins/agy-<tag>`), removes the
launcher wrapper (`<prefix>/bin/agy-<tag>`), unregisters the plugin from
`~/.gemini/config/config.json`, removes added permission rules from
`~/.gemini/antigravity-cli/settings.json`, and prunes the install from the registry
(`<prefix>/state/agy-supervisor/installs.json`).

`uninstall --all` removes every install registered under the given `--prefix` after one confirmation
that lists them.

Unmodified managed files are removed; if files were locally edited, uninstall preserves them unless
`--force` is passed. Local memory stores under `.supervisor/` and user projects are never touched.

## Exit Codes

- `0`: success.
- `1`: a file or settings step failed (see the output), a `doctor` row was FAIL, or a prompt was
  declined or aborted (Ctrl-D).
- `2`: a usage error, a failed source validation, or an OS error such as an unreadable path.

## Notes For Agents Running This

- Run the commands through a shell exactly as shown. Without a terminal, `uninstall`,
  `install --overwrite-local`, and `agy-supervisor uninstall` need `--yes`.
- If install reports kept local modifications or unmanaged collisions, show the user the list and
  ask before re-running with `--overwrite-local` (or `--force`).
- If doctor reports a FAIL, report it and its fix. Do not edit the user's shell profile (including
  the PATH line `install` prints) or environment variables without asking.
- Exit codes are listed under [Exit Codes](#exit-codes).

## Routing Check

For contributors: if you edit agent descriptions in your checkout, run the routing check suite.
The supervisor decides where each request goes from the agent descriptions it sees, so a reworded
description can silently change routing. `tests/test_routing_scenarios.py` guards against that:
it checks 28 canonical requests covering quick specialists, direct questions, research,
planning, implementation, writing, escalations, and model tier selections.

By default, running the test suite offline executes deterministic contract and schema checks:

```bash
/usr/bin/python3 -m unittest discover -s tests -t . -v
```

To run the live routing check against the deployed supervisor:

```bash
AGY_LIVE_ROUTING=1 /usr/bin/python3 -m unittest tests/test_routing_scenarios.py -v
```

- Live routing calls the model 28 times through `agy-supervisor` (or `agy -p`). Run
  `./deploy install` first so it tests the pack you mean to test.
- It consumes API quota and model context.
- Live invocation is strictly opt-in: without `AGY_LIVE_ROUTING=1`, the suite runs the 28 offline
  deterministic contract checks. Run it after changing an agent description or the supervisor's
  routing rules.
