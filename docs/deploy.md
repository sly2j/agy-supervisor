# Deployment & Launcher (`./deploy`)

`./deploy` is a Python 3.9+ stdlib-only installer managing Antigravity plugin bundles,
3-way SHA-256 baseline manifests, launchers, settings rules, and diagnostics.

## Install Targets

| Mode | Flags | Resolved Target |
| :--- | :--- | :--- |
| Global (default) | *(none)* | `$AGY_CONFIG_DIR/plugins/agy-supervisor` (`~/.gemini/config/plugins/agy-supervisor`) |
| Tagged Global | `--tag dev` | `$AGY_CONFIG_DIR/plugins/agy-dev` (`plugin.json` `"name": "agy-dev"`) |
| Workspace | `--workspace <dir>` | `<dir>/.agents/plugins/agy-<tag>` |
| Custom Dir | `--target <dir>` | `<dir>` |

Environment overrides for testing and custom prefixes:
- `AGY_CONFIG_DIR`: overrides `~/.gemini/config`
- `AGY_CLI_DIR`: overrides `~/.gemini/antigravity-cli`
- `AGY_SUPERVISOR_PREFIX` (or `--prefix`): overrides `~/.local`
- `AGY_BIN`: overrides `agy` binary lookup for validation and launching

## 3-Way Baseline Manifest (`.agy-supervisor-manifest.json`)

Every managed file stores its installed SHA-256 hash and file mode. On `update`:
- Clean files matching the manifest update to the new pack version.
- Locally modified files are preserved unless `--force` is passed.
- Unmanaged file collisions block `install` unless `--force` is passed.
- `<target>/supervisor-config.json` is never managed or overwritten by `install`/`update`.

## Launcher Wrapper & Settings Sync

For global installs (unless `--no-launcher`), `./deploy install` installs `<prefix>/bin/agy-<tag>`:
- Forwards `update`, `uninstall`, `status`, `list`, `doctor`, `critic`, `memory`, `-v/--version`
  to the snapshotted `<prefix>/state/agy-supervisor/deploy`.
- Otherwise executes `exec "${AGY_BIN:-agy}" --agent supervisor "$@"`, leaving plain `agy`
  completely unchanged.

In `$AGY_CLI_DIR/settings.json`, `./deploy` adds ONLY a scoped review permission rule:
`Bash(<target>/skills/supervisor-config/scripts/external-critic review *)`.
Agents can invoke `review` without prompts while remaining unable to silently run `enable` or
`disable`.
