# Server-Side Subprocess Timeout Hardening Hard Bar Spec

> Status: proposed hard bar  
> Scope: Firmware-CLI server/runtime-owned subprocess execution paths  
> Enforcement boundary: server-side / execution-side, not model-side  
> Purpose: make subprocess timeout enforcement a hard runtime guarantee, not merely a brain/client waiting policy.

## 1. Plain-English Summary

This hardening step is **server-side in spirit and execution-side in implementation**.

The brain may propose timeout budgets. The CLI/operator may configure timeout budgets. But the **hard enforcement must happen in the code that actually launches and owns the subprocess**.

That means:

**If Firmware-CLI starts an external command, the component that starts that command must also enforce the timeout, terminate the process tree, capture output, and return typed timeout evidence.**

The brain must not be the only timeout boundary.

A brain-side timeout that merely stops waiting is not enough. A true hard bar requires the subprocess owner to kill or clean up the launched process and its descendants.

## 2. The Important Clarification: One Runner, Many Execution Owners

The execution layer is not one file.

It spans several trusted local modules:

- MCP server helpers;
- workspace/build execution;
- Codex CLI provider execution;
- Claude CLI provider execution;
- provider memory summarizers;
- model-native skill init scripts;
- Zephyr/bootstrap helpers;
- future repo-owned helper commands.

That is okay.

**“Single shared bounded-process runner” does not mean “only the MCP server launches subprocesses.”**

It means:

**Every module that needs to launch a subprocess must call the same low-level bounded-process runner.**

The execution layer can stay distributed. The subprocess launch primitive must be centralized.

Think of it like this:

```text
MCP server helper commands
        |
workspace builds
        |
Codex CLI provider
        |
Claude CLI provider
        |
model-native skill init scripts
        |
Zephyr/bootstrap helpers
        |
        v
src/pyocd_debug_mcp/processes.py
        |
        v
run_bounded_process(...)
```

Each caller still owns its product meaning.

For example:

- workspace builds still return build results or raise `WorkspaceError`;
- Codex provider calls still parse Codex output and raise provider-specific errors;
- Claude provider calls still preserve Claude session/fork/resume behavior;
- server helper commands can still return `(returncode, stdout, stderr)`;
- skill init scripts can still raise `ModelNativeSkillError`.

But none of those callers should own raw subprocess mechanics anymore.

They should not each decide separately how to:

- launch the process;
- set a timeout;
- kill the process;
- kill children;
- capture stdout/stderr;
- decode output;
- represent timeout evidence.

That behavior belongs in one shared runner.

## 3. What “Server-Side” Means Here

This spec uses **server-side** to mean:

> the trusted local runtime layer that owns execution of host commands, tools, builds, provider CLIs, helper CLIs, or any other subprocess.

That includes the MCP server when the MCP server launches helper commands.

It also includes the local turnkey runtime/brain process when that process launches subprocesses such as provider CLIs or workspace builds.

So this is not only about `src/pyocd_debug_mcp/server.py`.

It is about every trusted runtime component below the model that can launch an OS process.

### In scope as server-side / execution-side subprocess owners

- MCP server helper commands.
- Workspace/build command execution.
- Codex CLI provider execution.
- Claude CLI provider execution.
- Provider memory summarizer subprocesses.
- Model-native skill init scripts.
- Zephyr/bootstrap/helper commands.
- Any future repo-owned subprocess call.

### Out of scope

- The model deciding to wait.
- The brain merely giving up on an MCP call.
- In-process pyOCD calls that do not launch subprocesses.
- A full pyOCD worker/process isolation architecture.

## 4. Core Principle

The hard bar is:

**The component that launches a subprocess must own its timeout and cleanup, and it must do so through the shared bounded-process runner.**

Do not rely on an upstream caller to abandon the request.

Do not rely on the brain loop timing out.

Do not rely on the MCP client read timeout as the only guard.

Do not let every module invent its own subprocess timeout pattern.

The subprocess owner must enforce, through the shared runner:

1. timeout budget;
2. direct-child termination;
3. process-tree cleanup;
4. partial stdout/stderr capture;
5. typed timeout result;
6. artifact/evidence recording where appropriate.

## 5. Current Problem

The repo already uses `subprocess.run(..., timeout=...)` in several places. That is useful, but it is not the hard bar.

The current shape is incomplete because:

1. subprocess timeout logic is scattered across multiple modules;
2. there is no single server/runtime-owned subprocess runner;
3. process-tree cleanup is not clearly guaranteed;
4. some paths capture stdout/stderr and some do not;
5. timeout failure types differ by call site;
6. child/grandchild cleanup is not uniformly tested;
7. the distinction between “caller stopped waiting” and “process was killed” is not enforced by architecture;
8. future contributors can accidentally add another raw subprocess path with weaker behavior.

This hardening step turns subprocess timeout behavior into a single server/runtime contract.

## 6. Required Product Claim After This Step

After this step, the repo may claim:

**All repo-owned subprocesses are executed through a shared server/runtime bounded-process runner. On timeout, the runner terminates the launched process, attempts process-tree cleanup, captures available output, reports cleanup status, and returns typed timeout evidence.**

The repo may not claim:

**All hardware operations are killable.**

That broader claim requires a separate pyOCD worker/process isolation design.

## 7. Non-Claim: Brain Timeout Is Not Enough

A brain/client timeout means:

> the caller stopped waiting.

A server/runtime subprocess timeout means:

> the process owner enforced the deadline and attempted cleanup.

This hard bar requires the second one.

The brain may still compute or pass timeout budgets, but it must not be the only enforcement point.

## 8. Required Architecture

### 8.1 New shared execution module

Add a shared module such as:

```text
src/pyocd_debug_mcp/processes.py
```

This module owns all subprocess execution behavior.

No production code should call `subprocess.run(...)`, `subprocess.Popen(...)`, `asyncio.create_subprocess_exec(...)`, or equivalent directly outside this module unless explicitly approved.

### 8.2 Required public API

The module should expose a typed command object, result object, and timeout error.

Suggested shape:

```python
@dataclass(frozen=True)
class BoundedProcessCommand:
    argv: tuple[str, ...]
    cwd: Path | None = None
    env: Mapping[str, str] | None = None
    stdin_text: str | None = None
    timeout_seconds: float = 30.0
    label: str | None = None
```

```python
@dataclass(frozen=True)
class BoundedProcessResult:
    command: tuple[str, ...]
    cwd: str | None
    label: str | None
    exit_code: int | None
    timed_out: bool
    timeout_seconds: float
    elapsed_seconds: float
    stdout: str
    stderr: str
    direct_child_pid: int | None
    direct_child_terminated: bool
    process_tree_terminated: bool
    cleanup_errors: tuple[str, ...]
```

```python
class BoundedProcessTimeout(RuntimeError):
    result: BoundedProcessResult
```

```python
class BoundedProcessLaunchError(RuntimeError):
    command: tuple[str, ...]
    cwd: str | None
    message: str
```

Public entry point:

```python
def run_bounded_process(command: BoundedProcessCommand) -> BoundedProcessResult:
    ...
```

Required behavior:

- return `BoundedProcessResult` for normal completion, including nonzero exit;
- raise `BoundedProcessTimeout` on timeout;
- raise `BoundedProcessLaunchError` on launch failure.

## 9. How Distributed Callers Use the Single Runner

The shared runner should be low-level and boring.

Each call site should become a thin adapter.

### 9.1 Workspace build adapter

```python
result = run_bounded_process(
    BoundedProcessCommand(
        argv=shell_command_for_host(build_command),
        cwd=self.root,
        timeout_seconds=timeout_seconds,
        label="workspace-build",
    )
)
```

Then `workspace.py` maps the result back into `BuildResult` or `WorkspaceError`.

### 9.2 Codex provider adapter

```python
result = run_bounded_process(
    BoundedProcessCommand(
        argv=tuple(codex_command),
        cwd=working_dir,
        stdin_text=current_prompt,
        timeout_seconds=self._timeout_seconds,
        label="codex-provider-turn",
    )
)
```

Then `provider_codex_cli.py` parses the output exactly as before.

### 9.3 Claude provider adapter

```python
result = run_bounded_process(
    BoundedProcessCommand(
        argv=tuple(claude_command),
        cwd=working_dir,
        stdin_text=current_prompt,
        timeout_seconds=self._timeout_seconds,
        label="claude-provider-turn",
    )
)
```

Then `provider_claude_cli.py` preserves its current session/resume/fork parsing.

### 9.4 MCP server helper adapter

```python
result = run_bounded_process(
    BoundedProcessCommand(
        argv=tuple(cmd),
        timeout_seconds=timeout_seconds,
        label="mcp-server-helper",
    )
)
```

Then `server.py` can preserve its current `(returncode, stdout, stderr)` helper shape.

### 9.5 Skill init adapter

```python
result = run_bounded_process(
    BoundedProcessCommand(
        argv=tuple(command),
        cwd=runtime_root,
        env=env,
        timeout_seconds=timeout_seconds,
        label=f"skill-init:{manifest.skill_id}",
    )
)
```

Then `model_native_skills.py` maps timeout or nonzero exit into `ModelNativeSkillError`.

### 9.6 Zephyr/bootstrap adapter

```python
result = run_bounded_process(
    BoundedProcessCommand(
        argv=tuple(cmd),
        cwd=cwd,
        env=env,
        timeout_seconds=timeout_seconds,
        label="zephyr-helper",
    )
)
```

Then `zephyr_build.py` keeps its user-facing progress messages and error behavior.

## 10. Domain Errors Still Exist

The shared runner should not erase domain-specific errors.

Instead, it should become the common source of execution evidence.

Mapping examples:

```text
BoundedProcessTimeout
        |
        v
WorkspaceError
```

```text
BoundedProcessTimeout
        |
        v
ProviderResponseError
```

```text
BoundedProcessTimeout
        |
        v
server helper return code 124
```

```text
BoundedProcessTimeout
        |
        v
ModelNativeSkillError
```

This gives the product two things at once:

1. consistent execution semantics;
2. caller-specific user-facing errors.

## 11. Required Server/Runtime Semantics

### 11.1 Timeout ownership

Each subprocess owner must pass an explicit timeout into `run_bounded_process(...)`.

Timeouts may originate from:

- default server/runtime policy;
- Branch C effective timeout config;
- CLI flags;
- test-specific overrides.

But enforcement happens in the subprocess owner, not in the brain alone.

### 11.2 Process-tree cleanup

On timeout, the runner must attempt to terminate:

1. the direct child;
2. all descendants created by that child.

POSIX hard bar:

- launch the child in a new session/process group;
- send `SIGTERM` to the process group on timeout;
- wait a short grace period;
- send `SIGKILL` if still alive;
- report cleanup status.

Windows hard bar:

- use a reliable Windows process-tree strategy, such as:
  - Job Object based cleanup; or
  - a process group plus recursive child termination; or
  - an internal helper process that owns and kills the tree.
- do not claim process-tree cleanup if only the direct child was killed.
- report partial cleanup honestly.

### 11.3 Output capture

The runner must capture:

- stdout;
- stderr;
- partial stdout/stderr on timeout when available.

Text decoding must use:

```python
encoding="utf-8"
errors="replace"
```

### 11.4 Evidence

For long-running or user-visible subprocesses, timeout evidence must be available as structured metadata.

At minimum:

- command label;
- argv;
- cwd;
- timeout seconds;
- elapsed seconds;
- stdout;
- stderr;
- direct child pid;
- direct child termination status;
- process-tree termination status;
- cleanup errors.

Where a run directory exists, write this to an artifact file.

## 12. Required Call-Site Migrations

### 12.1 MCP server helper commands

The MCP server’s helper command path must become a thin wrapper around the shared bounded runner.

Current tuple-style callers may keep their interface, but internally the server must use the shared runner.

Required behavior:

- helper command timeout maps to a deterministic failure code, such as `124`;
- partial output is preserved;
- process-tree cleanup is attempted;
- cleanup status is logged or included in stderr/evidence.

### 12.2 Workspace builds

Workspace builds must use the shared bounded runner.

Required behavior:

- build timeout kills the build process tree;
- stdout/stderr are preserved;
- `WorkspaceError` includes or references typed bounded-process metadata;
- existing `BuildResult` behavior remains compatible for normal completion.

### 12.3 Codex CLI provider

Codex provider calls must use the shared bounded runner.

Required behavior:

- timeout kills the Codex process tree;
- partial stdout/stderr are preserved;
- provider error wraps typed bounded-process timeout evidence;
- provider metadata can include timeout evidence when a run artifact exists.

### 12.4 Claude CLI provider

Claude provider calls must use the shared bounded runner.

Required behavior:

- timeout kills the Claude process tree;
- partial stdout/stderr are preserved;
- provider error wraps typed bounded-process timeout evidence;
- provider metadata can include timeout evidence when a run artifact exists.

### 12.5 Provider memory summarizers

Codex and Claude summarizer subprocesses must use the shared bounded runner.

Required behavior:

- timeout behavior matches normal provider calls;
- partial output is preserved;
- timeout result is typed.

### 12.6 Model-native skill init scripts

Skill init scripts must use the shared bounded runner.

Required behavior:

- policy checks remain before execution;
- timeout kills script process tree;
- `ModelNativeSkillError` carries bounded-process timeout metadata;
- failure record includes stdout/stderr and cleanup status.

### 12.7 Zephyr/bootstrap/helper commands

Zephyr and bootstrap helper commands must use the shared bounded runner.

Required behavior:

- long commands keep their intended timeout budgets;
- output is captured or artifacted;
- timeout cleanup status is reported;
- user-facing progress output remains useful.

## 13. Static Guard

Add a regression test such as:

```text
tests/test_no_raw_subprocess_calls.py
```

This test scans production code and fails on direct subprocess execution outside the approved shared module.

Forbidden outside the shared runner unless explicitly allowlisted:

- `subprocess.run`;
- `subprocess.Popen`;
- `subprocess.call`;
- `subprocess.check_call`;
- `subprocess.check_output`;
- `asyncio.create_subprocess_exec`;
- `asyncio.create_subprocess_shell`.

Allowed:

- `src/pyocd_debug_mcp/processes.py`;
- tests specifically validating process behavior;
- documented exceptions with explicit hard-bar justification.

This static guard is what makes “single shared runner” real across a distributed execution layer.

Without this guard, future work can accidentally reintroduce scattered subprocess timeout behavior.

## 14. Required Test Matrix

### 14.1 Shared runner tests

The shared runner must test:

1. successful command;
2. nonzero exit;
3. missing executable;
4. timeout of direct child;
5. timeout after partial stdout;
6. timeout after partial stderr;
7. timeout with child process;
8. timeout with grandchild process;
9. cleanup metadata;
10. UTF-8 replacement behavior;
11. cwd handling;
12. env override handling;
13. stdin handling.

### 14.2 POSIX process-tree test

On POSIX:

- start a helper process that spawns a sleeping child;
- timeout the parent;
- assert the process group is gone;
- assert cleanup metadata reports tree cleanup.

### 14.3 Windows process-tree test

On Windows:

- start a helper process that spawns a sleeping child;
- timeout the parent;
- assert the child is gone using the selected Windows cleanup strategy;
- assert cleanup metadata reports complete or partial cleanup honestly.

### 14.4 Call-site tests

Tests must prove the migrated call sites use the bounded runner:

- MCP server helper timeout;
- workspace build timeout;
- Codex CLI timeout using a fake CLI/helper;
- Claude CLI timeout using a fake CLI/helper;
- provider summarizer timeout;
- skill init script timeout;
- Zephyr helper timeout.

### 14.5 Static guard test

Add a test fixture or sample check proving the static guard catches a new direct `subprocess.run(...)` call outside the approved runner.

## 15. Acceptance Criteria

This hardening step is complete only when:

1. A shared server/runtime bounded-process runner exists.
2. All production subprocess call sites are migrated to it.
3. No product code outside the runner directly calls subprocess execution APIs, except explicit reviewed exceptions.
4. The runner enforces wall-clock timeout.
5. The runner attempts direct-child termination.
6. The runner attempts process-tree termination.
7. The runner reports whether process-tree cleanup succeeded.
8. The runner captures stdout and stderr using UTF-8 replacement.
9. The runner preserves partial output on timeout when available.
10. Timeout produces typed evidence, not only a string.
11. MCP server helper commands use the runner.
12. Workspace builds use the runner.
13. Codex CLI provider calls use the runner.
14. Claude CLI provider calls use the runner.
15. Provider summarizers use the runner.
16. Skill init scripts use the runner.
17. Zephyr/bootstrap helpers use the runner.
18. Tests prove direct-child timeout.
19. Tests prove child/grandchild cleanup or honestly fail/mark platform limitation.
20. Static guard prevents new scattered subprocess calls.
21. Existing non-hardware tests remain green.
22. Existing provider/build behavior remains compatible.
23. Documentation clearly states the guarantee and the non-guarantee.

## 16. What This Still Does Not Solve

This spec does not solve in-process pyOCD hangs.

The MCP server currently owns blocking, stateful pyOCD operations that do not necessarily launch subprocesses. To make those killable, the repo needs a separate hard bar:

```text
PyOCD Worker Isolation Hard Bar
```

That future hard bar should define:

- a separate worker process owns pyOCD;
- the MCP server talks to the worker over IPC;
- every hardware operation has a server-side deadline;
- timeout terminates or quarantines the worker;
- session state is marked dirty;
- reconnect/recover policy is explicit;
- no orphan probe/session state remains after timeout.

Do not conflate that future work with subprocess hardening.

## 17. Final One-Sentence Requirement

**The execution layer can span many modules, but subprocess launching cannot: every repo-owned subprocess must go through one shared bounded runner that owns timeout, process-tree cleanup, output capture, typed evidence, and regression-tested behavior.**
