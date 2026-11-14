# Deploying Supervisor for Antigravity (`./deploy`)

`./deploy` is a Python 3.9+ stdlib-only deployment and lifecycle tool for `agy-supervisor`. It
requires no external dependencies and runs on macOS and Linux.

## Requirements

- Python 3.9+ (`/usr/bin/python3` or active virtualenv)
- Google Antigravity CLI (`agy`) installed and available on `PATH`
- Git (for cloning, updating, and worktree operations)

## Deployment Runbook

### 1. Preflight Diagnostics
Inspect your environment without mutating any files:

```bash
./deploy doctor
./deploy install --dry-run
```

`doctor` verifies Python version, Antigravity binary availability, plugin directory structure,
`PATH` configuration, and `settings.json` permission grants.

### 2. Global Installation (Default)
Install the plugin globally into `~/.gemini/config/plugins/agy-supervisor` and write the launcher
wrapper to `~/.local/bin/agy-supervisor`:

```bash
./deploy install
```

If `~/.local/bin` is not on your `PATH`, add it to your shell configuration (`~/.zshrc` or
`~/.bashrc`):

```bash
export PATH="$HOME/.local/bin:$PATH"
```

### 3. Launching Supervisor
Launch an interactive session using the isolated launcher:

```bash
agy-supervisor
```

This starts Antigravity with `--agent supervisor`. Plain `agy` remains completely untouched.

## Installation Targets & Options

| Target Mode | Flags | Installed Plugin Location | Launcher Path |
|---|---|---|---|
| **Global** | `deploy install` | `~/.gemini/config/plugins/agy-supervisor` | `bin/agy-supervisor` |
| **Tagged** | `--tag dev` | `~/.gemini/config/plugins/agy-dev` | `bin/agy-dev` |
| **Workspace** | `--workspace .` | `<repo>/.agents/plugins/agy-supervisor` | *(none)* |
| **Custom** | `--target /path` | `/path` | *(none)* |

### Common CLI Flags
- `--tag TAG`: Profiles allow multiple parallel installs (e.g. `stable`, `dev`). Default:
  `supervisor`.
- `--workspace DIR`: Installs the plugin into `<dir>/.agents/plugins/` for repository isolation.
- `--prefix PREFIX`: Prefix for `bin/` and `state/`. Default: `~/.local`.
- `--default-model MODEL`: Default model for the launcher script (default:
  `gemini-4-carbon-medium`).
- `--force` / `--overwrite-local`: Overwrites existing or locally modified files, creating
  timestamped backups (`<file>.bak.<timestamp>`).
- `--dry-run`: Previews actions and file copies without making changes.
- `--no-launcher`: Skips launcher script generation.
- `--disable-siblings`: Disables other `agy-*` supervisor plugins in `config.json`.

## 3-Way Baseline Manifest & File Conflict Safety

Every install records a SHA-256 hash manifest (`.agy-supervisor-manifest.json`):

| File State | Update Behavior |
|---|---|
| **Unmodified** | Automatically updated to the new pack version |
| **Locally Modified** | Preserved with a warning; overwritten with backup if `--force` is used |
| **Unmanaged Collision** | Refused with exit code 1; overwritten with backup if `--force` is used |
| **Removed from Pack** | Deleted if unmodified; preserved and handed to user if locally modified |

`<target>/supervisor-config.json` is user configuration and is never overwritten or removed.

## Launcher Wrapper Capabilities

The generated launcher (`agy-supervisor` or `agy-<tag>`) forwards core administrative verbs
directly to `./deploy`:

```bash
agy-supervisor update              # Updates this profile's pack
./deploy update --all              # Updates every registered install in prefix
agy-supervisor update --from <src> # Updates from a local directory or Git repository
agy-supervisor status              # Shows version, model, and file statuses
agy-supervisor list                # Lists all registered supervisor profiles
agy-supervisor doctor              # Runs preflight diagnostics
agy-supervisor uninstall           # Removes installed pack and launcher
agy-supervisor critic <action>     # Configures external critic (status, enable, disable)
agy-supervisor memory <action>     # Manages externalized project memory
```

Any unrecognized argument is forwarded directly to `agy --agent supervisor "$@"`.

### Runtime Model Resolution
The launcher script determines the active model in order of priority:
1. User-supplied `--model` or `-m` command-line argument.
2. `AGY_SUPERVISOR_MODEL` environment variable.
3. The installed default model (`gemini-4-carbon-medium`).

## Settings & Permission Grants

`deploy install` configures Antigravity's `settings.json`
(`~/.gemini/antigravity-cli/settings.json`) with scoped review permissions:

```json
{
  "permissions": {
    "allow": [
      "Bash(<target>/skills/supervisor-config/scripts/external-critic review *)"
    ]
  }
}
```

This allows leads to probe and execute read-only reviews without triggering repeated interactive
prompts, while preventing unauthorized execution of `enable` or `disable`.

## Upgrading Installs

Update a profile in place:

```bash
# Update default profile
agy-supervisor update

# Update all registered profiles across the prefix
./deploy update --all

# Update from a specific directory or git repository
agy-supervisor update --from ~/Work/agy-supervisor
```

## Clean Uninstallation

Remove a profile completely:

```bash
agy-supervisor uninstall
```

`uninstall` removes the plugin directory, cleans up the launcher binary, unregisters the
profile from `installs.json`, and cleans up added permission rules from `settings.json`.
Local memory stores under `.supervisor/` and user projects are never touched.
