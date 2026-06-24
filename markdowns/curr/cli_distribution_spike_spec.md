# CLI Distribution Spike (exploratory — not a Stage commitment)

## Status

`PROPOSAL` / spike. The build plan
(`markdowns/firmware_agent_build_plan_concrete (10).md`) explicitly defers
shipped-product OS matrix and packaging/distribution format to **Stage 4+**
and records that omission as intentional, to avoid premature lock-in. The
project is currently at the R11/R12 turnkey stage, well before Stage 4.

This doc exists because the operator asked to prototype a secure distributable
build of the CLI now, for evaluation purposes. It is scoped as a **spike**:
it does not change the Stage 4 decision, does not edit the build plan, and
should not be treated as the adopted packaging format until the operator
formally promotes it (at which point it moves into the build plan as a real
Stage 4 decision).

## Goal

Ship `pyocd-debug` (the operator-facing interactive shell entrypoint,
`src/pyocd_debug_mcp/ux/cli.py:main`) as a single compiled binary that:

- runs without a Python interpreter, source tree, or `.pyc` files on the
  target machine
- cannot be trivially decompiled back to source (no bytecode artifact to
  recover with `uncompyle6`/`pycdc`-class tools)
- can be rebuilt into a new versioned binary with one script after any
  change

## Scope decisions (asked, not assumed)

- Only `pyocd-debug` is packaged in this spike, not the other four
  entrypoints (`pyocd-debug-mcp`, `pyocd-debug-brain`, `pyocd-pack-repair`,
  `pyocd-zephyr-build`) — operator chose the narrower scope for a first pass.
- Distribution channel and code-signing are **documented, not automated** —
  see "What is NOT automated" below. They require operator-owned
  accounts/credentials this agent cannot create.

## Approach

**Nuitka**, not PyInstaller: Nuitka compiles Python to C and then to a native
binary, so there is no bundled `.pyc`/source sitting in an extractable
archive the way PyInstaller's onefile mode produces. This is the standard
tool for "ship Python without shipping source."

Caveat carried forward honestly: this raises the cost of reverse engineering
substantially, it does not make it impossible. No software that runs
entirely on a stranger's machine can be made unconditionally unreverseable.
`PROJECT-DEFINED` choice: accept "expensive to reverse" as the bar, not
"impossible."

## What gets built

1. **`pyproject.toml`** — add a `build` dependency group containing
   `nuitka` and `ordered-set` (Nuitka's recommended companion package for
   faster builds). Kept out of the shipped `dev` group and out of the wheel.
2. **`scripts/build_release.py`** — the one script that:
   - reads the current version from `pyproject.toml`
   - computes a content hash of `src/pyocd_debug_mcp/` to detect whether
     anything changed since the last recorded build (stored in
     `dist/.last_build_hash`, gitignored)
   - bumps the patch version in `pyproject.toml` automatically if the hash
     changed and no explicit `--bump` was given; honors `--bump
     {patch,minor,major}` and `--set-version X.Y.Z` for manual override
   - invokes `python -m nuitka` with `--onefile --standalone
     --remove-output --no-pyi-file`, targeting
     `src/pyocd_debug_mcp/ux/cli.py`, output named
     `pyocd-debug-<version>-<os>-<arch>[.exe]`
   - writes `dist/<name>.build_info.json` recording version, git commit
     hash, build timestamp (UTC), host OS/arch — `PROJECT-DEFINED`
     provenance record, not a security control
   - is idempotent: rerunning with no source changes and no explicit bump
     produces the same version's binary again (no silent re-bump)
3. **`.gitignore`** — add `dist/` (binaries are build output, never
   committed; `dist/.last_build_hash` and `*.build_info.json` follow the
   same rule).

## Platform limitation (origin: VENDOR-FIXED, Nuitka)

Nuitka cross-compiles, in practice, only by running on the target OS — there
is no supported "build the Windows binary from macOS" path. `AMBIGUITY`: the
plan has no shipped-product OS matrix yet, so this spike builds only for the
host OS it runs on (macOS, this machine) and documents that a Windows binary
requires running the same script on a Windows host (or a Windows CI
runner) — not something this agent can produce on this machine.

## What is NOT automated (and why — portability rule: don't silently bake in a manual step)

- **Code signing / notarization.** Apple notarization needs an Apple
  Developer account and signing identity; Windows Authenticode needs a
  purchased code-signing certificate. Both are operator-owned credentials
  this agent has no path to create. **STOP-and-ask item**, documented below
  under "Setting up real distribution," not silently skipped.
- **Publishing a release.** `scripts/build_release.py` only builds locally.
  Pushing the binary anywhere (GitHub Releases, a download server) is a
  separate, explicitly operator-confirmed action — never auto-run, per the
  "actions visible to others" rule.

## Verification plan (this session)

- `uv run python -m nuitka --version` succeeds (tool installed) — non-hardware check.
- Run `scripts/build_release.py` once, produce a real binary on this Mac.
- Execute the produced binary directly (no `uv run`, no Python on `PATH`
  assumption beyond what's already true of this dev machine) and confirm it
  launches the operator shell — verified by running here, this session.
- Re-run the script with no changes — confirm it reuses the existing version
  instead of bumping.
- Make a trivial source change, re-run — confirm it bumps the patch version
  and rebuilds.

## Setting up real distribution (operator action, documented here for the handoff)

See the end-of-task summary in conversation / repo follow-up doc for the
step-by-step (GitHub Releases as a private/signed channel, code-signing
credential setup, and the new-build-after-changes workflow). Not duplicated
here to avoid two sources of truth; this file owns the *build* mechanism,
not the *channel* setup steps.
