> STATUS: PROPOSAL - not authority, pending reconciliation with build_plan_concrete and user sign-off.

# Post-Bootstrap Portability Contract

## Goal in plain English

This spec narrows the portability claim to the contract that the current
Firmware-CLI product actually wants to satisfy:

- a developer performs a short, documented bootstrap equivalent to the setup
  they would already need for manual embedded debugging
- after that bootstrap, the repo-owned scripts, MCP server, and turnkey brain
  should behave portably across the supported host and board matrix

This is a specification and audit artifact, not an implementation pass. It
defines the contract the repo should claim, the acceptance gate for that
contract, and the remaining code-visible gaps against it.

Roadmap anchor: `R0`, `R2-R7`, `R9-R12`, and the deferred portability proof
boundary called out in `ROADMAP.md` / `current-progress.md`.

## Scope and non-scope

In scope:

- define the supported-host / supported-board portability claim in plain English
- reconcile that claim against the build plan, current code, and current docs
- define what the developer bootstrap is allowed to contain
- define what the repo must own after bootstrap
- list remaining code-only gaps visible from the current source tree
- classify each visible gap by fixability with the user's current resources:
  one Windows host and the two currently attached boards

Out of scope:

- changing the build plan's settled architecture in this spec pass
- claiming fresh-machine portability for macOS or arbitrary Windows hosts
- claiming support for arbitrary boards outside the tracked support surface
- implementing the fixes listed here
- proving any gap closed on hardware not attached in the current session

## Reconciliation summary

- Build plan:
  - the build plan's Stage 0 / Stage 1 / driver notes already distinguish
    Python/runtime dependencies from OS-level vendor drivers
  - the build plan explicitly says shipped product behavior should
    detect-and-instruct for proprietary probe software rather than bundling it
  - the active open proof gap in the plan is fresh-machine portability proof,
    not a claim that every vendor installer must be silently automated

- Current code:
  - `setup_host.ps1` and `setup_host.sh` provide OS bootstrap helpers
  - `host_bootstrap.py` checks host readiness and explicitly does not install
    OS drivers or vendor probe software
  - `stage0_check.py` owns board-level Stage 0 validation after bootstrap
  - `pyocd-zephyr-build` can provision or reuse the Zephyr build substrate
  - runtime proof and docs already describe a mixed contract:
    some bootstrap may be manual, but post-bootstrap operation should be
    repo-owned and consistent

- Other docs or notes:
  - `agent_portability_playbook.md` is stricter than the current intended
    product contract and frames the target audience as an absent stranger on a
    fresh machine with minimal manual setup
  - `init.md` and `stage0_setup.md` already read closer to the narrower
    engineer-bootstrap contract the user wants

- Disagreements:
  - WARNING CONFLICT: `agent_portability_playbook.md` pushes toward
    "self-installing / no manual setup after install", while the build plan's
    concrete Stage 0 and vendor-driver guidance already assumes that
    proprietary probe drivers and comparable manual-debug prerequisites may
    remain a short human bootstrap step. Per the authority order, the build plan
    wins. This spec therefore treats proprietary OS driver / vendor probe setup
    as allowed bootstrap, not as a portability defect.
  - WARNING AMBIGUITY: the current top-level docs use both "fresh machine" language
    and "developer bootstrap" language. This spec resolves that by narrowing the
    claim to a bounded supported matrix plus a short documented bootstrap, but
    the authoritative docs should be harmonized if this contract is accepted.

## Design

The portability contract should be stated as:

Firmware-CLI is intended to run portably across supported hosts and supported
boards after a short documented developer bootstrap equivalent to the basic
setup required for manual board debugging on that machine.

The contract is bounded, not universal.

Supported hosts for the contract:

- Windows host path through `setup_host.ps1`, `host_bootstrap.py`,
  `stage0_check.py`, the MCP server, and the turnkey brain
- macOS host path through `setup_host.sh`, `host_bootstrap.py`,
  `stage0_check.py`, the MCP server, and the turnkey brain
- if local firmware rebuilds are part of the task, managed-Zephyr support is
  included where the current helper supports it; macOS Intel remains a bounded
  exception unless a preinstalled SDK is supplied

Supported boards for the public contract:

- `nrf52833dk`
- `nucleo_l476rg`

Retained alternate boards such as `nrf52840dk` may be proven and used, but they
should not silently expand the public portability claim unless the build plan
and current-progress ledger are updated to promote them.

Allowed bootstrap contents:

- installing vendor probe drivers
- installing vendor probe software required for manual debugging on that host
- granting OS permissions or approvals the OS requires
- optionally installing or reusing toolchain prerequisites for local rebuilds

Repo-owned behavior after bootstrap:

- canonical Python environment reconciliation
- board-config loading and validation
- pinned pack provisioning
- probe discovery and board-aware probe selection
- serial discovery and board-aware serial resolution
- Stage 0 flash / UART / recover validation according to board capabilities
- MCP server runtime behavior
- turnkey brain / CLI runtime behavior
- explicit, bounded diagnostics when prerequisites are missing or the bench is
  not ready

The implementation should keep the current layering:

- setup helpers
- host readiness checks
- Stage 0 validation
- shared services / MCP server
- turnkey brain / UX

No new portability logic should bypass that structure.

## Board-facts-as-data and origin tags

- supported-board identity remains data in `boards/<board>.yaml`
- machine-local facts remain local overrides or runtime discovery
- the supported-board contract itself is `PROJECT-DEFINED`
- board USB/probe/driver/toolchain requirements are a mix of:
  - `HW-FIXED` for silicon / probe-family realities
  - `VENDOR-FIXED` for pyOCD targets, helper CLI names, and vendor installer
    behavior
  - `PROJECT-DEFINED` for default timeouts, fallback policies, and the chosen
    support matrix
- no new portability fix should add scattered `if board == ...` logic outside
  the existing board-config / shared-service design

## Documentation plan

- if this contract is accepted, the authoritative portability wording needs to
  be aligned in:
  - `README.md` high-level support/portability language
  - `init.md` bootstrap contract wording
  - `stage0_setup.md` operator contract wording
  - `markdowns/current-progress.md` proof-boundary language
- the build plan itself only needs an update if the team wants this narrower
  bootstrap contract recorded as the settled interpretation of portability,
  rather than leaving it implicit in Stage 0 / driver sections
- no MCP tool docstrings need to move for this spec alone

## Portability

For this repo, portability should mean:

- no committed machine-local ports, paths, or probe IDs
- clear OS-specific bootstrap wrappers where needed
- board-aware runtime behavior driven by config and discovery
- bounded, explicit failure modes when prerequisite software or drivers are
  missing
- consistent post-bootstrap behavior on supported hosts and supported boards

It should not mean:

- arbitrary-board support
- arbitrary-computer support
- silent installation of every vendor driver or proprietary probe package
- a claim that the repo can replace the normal one-time embedded-toolchain setup
  an engineer would already need

Current code-visible gaps against that narrower contract:

1. `setup_host.ps1` and `setup_host.sh` still treat Nordic `nrfjprog` as a
   required setup success path for Nordic J-Link boards, even though the shared
   runtime degrades gracefully without it through generic matching or manual
   `--port` selection. This overstates the bootstrap requirement relative to the
   actual runtime contract.
   Fixability: high. Detectable now from code only and fixable on the current
   Windows host.

2. `stage0_check.py`, `target_control.py`, and the guardrails still phrase
   `manual_only` recover as "automate later" instead of clearly treating it as a
   support-boundary decision for unsupported recover families.
   Fixability: high. Mostly wording / policy cleanup, no new hardware needed.

3. The docs and helper behavior still mix "fresh-machine self-installing" and
   "short developer bootstrap" language, which makes the claim hard to state
   precisely.
   Fixability: high. Mostly documentation sync.

4. macOS Intel managed SDK install remains outside the helper's supported
   no-bootstrap path because of the upstream Zephyr support boundary.
   Fixability: low from repo code alone. This is mostly an upstream/toolchain
   limitation, not a local bug.

5. STM32CubeProgrammer unattended install is still not a verified setup-helper
   path on Windows or macOS. Under this narrower contract that is acceptable,
   but the setup scripts should classify it as an allowed manual prerequisite
   rather than implying incomplete portability.
   Fixability: medium. Messaging/path-policy fix is easy; verified unattended
   automation is probably unnecessary for the intended contract.

6. The supported-board claim and the currently attached-board proof surface are
   different: the public contract still wants `nrf52833dk + nucleo_l476rg`,
   while the currently attached Windows alternate Nordic proof uses
   `nrf52840dk + nucleo_l476rg`.
   Fixability: not a code fix. This is a proof-scope issue and requires the
   official Nordic board to be reattached for full closure on the scoped pair.

## Verification plan

- non-hardware verification for this spec:
  - reconcile the contract against the build plan, current code, and current
    bootstrap/operator docs
  - identify gaps visible from code without requiring another host

- current-hardware verification possible with the user's resources:
  - re-run the Windows bootstrap and Stage 0 path on the attached Nordic and
    STM32 boards after any bootstrap-contract code changes
  - re-run representative MCP connect / UART / flash / reset smoke on the same
    Windows host

- pending verification that cannot be closed with the current resources:
  - macOS bootstrap and post-bootstrap runtime proof
  - fresh-machine proof on a second Windows or macOS host
  - official scoped Nordic re-proof on `nrf52833dk` if that board is not
    attached

- if implementation follows this spec, the cheapest-first validation ladder is:
  - `uv run pytest -q`
  - `uv run ruff check .`
  - `uv run mypy src`
  - dry-run / argument checks for setup scripts where applicable
  - Windows rerun of `setup_host.ps1`, `host_bootstrap.py`, `stage0_check.py`,
    and representative MCP/runtime smoke on the two attached boards
  - later macOS rerun when that host is available

## Acceptance criteria

- the repo has one explicit portability claim:
  "supported hosts + supported boards + short documented developer bootstrap +
  repo-owned post-bootstrap behavior"
- the docs no longer imply a stronger claim than the code actually intends to
  satisfy
- setup helpers do not require optional vendor helper tools unless the runtime
  truly depends on them for the supported matrix
- unsupported recover or vendor-installer gaps are phrased as support-boundary
  facts, not as silent future obligations
- Windows runtime behavior remains green on the user's current attached boards
  after any code changes made to align with this contract
- remaining unclosed claims are explicitly listed as pending proof, not implied
  as already portable

## Verified

- non-hardware verified here:
  - the build plan already supports a narrower "manual vendor bootstrap is
    acceptable" interpretation better than the stricter portability playbook
  - the current codebase is already structured around bootstrap -> readiness ->
    Stage 0 -> runtime ownership
  - the code-only gaps listed above are visible from the current source tree

## Pending verification

- hardware verification on the current Windows host after any implementation
  changes made from this spec
- official scoped-pair closure if `nrf52833dk` is not the currently attached
  Nordic board
- macOS post-bootstrap proof
- any broader "fresh machine with no meaningful manual setup" claim
