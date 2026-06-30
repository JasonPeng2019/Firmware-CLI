# P-Wave-C Markdown To Code/Run Map

This map was created during the P-Wave-C audit on June 30, 2026. It ties active
non-`tmp` markdowns to the implementation or run evidence they describe.

| Markdown | Primary code/run anchors | Audit status |
|---|---|---|
| `markdowns/R12_P_SPLIT.md` | `src/pyocd_debug_mcp/brain/events.py`, `brain/timeout_policy.py`, `brain/timeout_runtime.py`, `timeouts.py`, `brain/loop.py`, `server.py`, `tests/harness/branch_c_tests.py` | Current for Branch C ownership and pending proof. |
| `markdowns/current-progress.md` | Branch C modules above; run roots `20260629T214134Z-58c1405a`, `20260629T214212Z-19199e0e`, `20260630T012135Z-8a5780dc`, `20260630T012206Z-292bb340`, `20260630T011733Z-ae2eb3ee`, `20260630T011814Z-4c33bc87`, `20260630T011858Z-f269f813`, `20260630T011944Z-7b9c4186` | Updated to separate historical scoped-pair proof from current Windows Branch C proof. |
| `markdowns/repo_file_index.md` | Repo paths listed in the index | Current for Branch C files. |
| `markdowns/ROADMAP.md` | Product stage/G7/R12 direction | Reference document; no direct Branch C code claim found stale. |
| `markdowns/firmware_agent_build_plan_concrete (10).md` | Authority plan for R12; Branch C target | Reference authority; not edited. |
| `markdowns/firmware_agent_mcp_architecture.md` | MCP/server architecture docs; `src/pyocd_debug_mcp/server.py` and service modules | Reference architecture; no Branch C status drift found. |
| `markdowns/UXLayer.md` | `src/pyocd_debug_mcp/ux/renderer.py`, `tests/test_ux_cli.py` | Branch D/UX-adjacent reference; not a Branch C completion claim. |
| `markdowns/R-12_P_Explanations.md` | Historical R12 explanation | Legacy/reference content; not used as current Branch C proof. |
| `markdowns/curr/branch_c_test_plan.md` | `tests/harness/branch_c_tests.py`, `tests/test_branch_c_harness.py`, `tests/test_timeout_policy.py`, run roots listed above | Current. |
| `markdowns/curr/r12-branch-c-completion_spec.md` | Branch C modules and tests listed above | Updated from proposal wording to current Windows attached-board status. |
| `markdowns/curr/r12-branch-c-completion_process.md` | Validation commands and run roots in Branch C process ledger | Updated stale limits/pending provider wording. |
| `markdowns/curr/r12-branch-c-completion_review.md` | Branch C tests, provider matrix, public CLI smokes | Updated stale review result and findings. |
| `markdowns/curr/r12-branch-c-provider-portability-coverage_spec.md` | `tests/harness/branch_c_tests.py`, provider factory path, CLI smoke run roots | Updated from proposal wording to implemented current-host scope. |
| `markdowns/curr/r12-branch-c-provider-portability-coverage_process.md` | Provider-neutral harness and validation run roots | Current. |
| `markdowns/curr/r12_turnkey_spec.md` | `src/pyocd_debug_mcp/brain/*`, turnkey CLI/benchmark paths | Broader R12 spec; Branch C implementation remains within its scope. |
| `markdowns/curr/things-to-change.md` | Broad product/change list | Requirements source; no direct run claim edited. |
| `markdowns/curr/uxlayer_gap_checklist.md` | UX/progress layer gap tracking | Branch D/UX-adjacent; Branch C event spine is an input. |
| `markdowns/curr/post-bootstrap-portability-contract_spec.md` | host/bootstrap scripts, portability rules | Reference portability contract; Branch C code obeys path/subprocess/provider portability constraints. |
| `markdowns/curr/post-bootstrap-portability-contract_process.md` | portability validation ledger | Reference ledger; no Branch C-specific stale run claim found. |
| `markdowns/curr/post-bootstrap-portability-contract_review.md` | portability review | Reference review; current Branch C macOS/fresh-host proof still pending. |
| `markdowns/curr/portability-playbook-suite_spec.md` | portability playbook suite | Reference spec; no direct Branch C run claim. |
| `markdowns/curr/p0_0_layered_validation_plan.md` | P0 validation ladder | Historical/foundation validation plan. |
| `markdowns/curr/p0_0_validation_report.md` | P0 run evidence | Historical/foundation evidence; not Branch C completion proof. |
| `markdowns/curr/p0-wave0-main-reconcile_spec.md` | Wave 0 reconcile spec | Historical/foundation reference. |
| `markdowns/curr/p0-wave0-main-reconcile_process.md` | Wave 0 process ledger | Historical/foundation reference. |
| `markdowns/curr/p0-0-static-audit-fix_spec.md` | static audit work | Historical/foundation reference. |
| `markdowns/curr/p0-0-doc-sync-superpowers-audit_spec.md` | docs/superpowers audit work | Historical/foundation reference. |
| `markdowns/curr/nrf52840dk-windows-mcp-jlink-connect_spec.md` | retained `nrf52840dk` Windows/J-Link connection proof | Supports retained-board Branch C proof boundary, not official `nrf52833dk`. |

