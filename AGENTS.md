# AGENT.md

## Purpose

This file defines the operating rules for AI coding agents working anywhere in the **Surge repository**.

These instructions apply to:

* Source-code changes
* Bug fixes
* Refactoring
* Testing
* Documentation
* Configuration
* Dependency management
* Build and deployment files
* Scripts and developer tooling
* Repository investigation
* Code reviews
* Architecture-related tasks

The goal is to ensure that every agent makes safe, minimal, verifiable, and repository-consistent changes.

---

## 1. Scope and Instruction Priority

This file applies to the entire repository unless a more specific `AGENT.md` exists inside a subdirectory.

When multiple instruction files apply, use the following priority:

1. Explicit instructions from the user
2. The nearest subdirectory-level `AGENT.md`
3. This root-level `AGENT.md`
4. Existing repository conventions
5. General language or framework best practices

A nested `AGENT.md` may add to or override these instructions for its own directory.

Do not ignore existing repository conventions merely because another implementation appears cleaner.

---

## 2. Core Agent Behaviour

Every agent must:

1. Understand the task before editing files.
2. Inspect the relevant code and configuration.
3. Identify the smallest correct change.
4. Preserve existing behaviour unless a change is explicitly required.
5. Follow existing architecture and naming conventions.
6. Validate changes using appropriate tests or checks.
7. Clearly report what was changed and what was not verified.

Do not start by rewriting large parts of the repository.

Do not assume that a task requires a new abstraction, dependency, service, or framework.

Prefer modifying existing components over creating parallel implementations.

---

## 3. Before Making Changes

Before editing code, inspect the relevant parts of the repository.

At minimum:

* Locate the affected module.
* Read nearby implementation files.
* Check related tests.
* Inspect relevant configuration files.
* Search for existing utilities solving the same problem.
* Identify public interfaces that may be affected.
* Check for directory-specific instructions.
* Determine the correct build, lint, formatting, and test commands.

Look for project configuration in files such as:

* `README.md`
* `pyproject.toml`
* `requirements.txt`
* `package.json`
* `tsconfig.json`
* `Makefile`
* `Dockerfile`
* `docker-compose.yml`
* CI workflow files
* Framework-specific configuration
* Existing scripts in `scripts/`, `tools/`, or similar directories

Never invent project commands when they can be discovered from the repository.

---

## 4. Repository Exploration Rules

Use targeted searches rather than reading unrelated files.

When investigating a feature or bug:

1. Search for the relevant symbol, route, model, component, or error message.
2. Trace its direct callers and dependencies.
3. Inspect tests that cover the same area.
4. Check configuration and environment usage.
5. Determine whether the behaviour is local or shared across services.

Avoid scanning generated, vendored, cached, or dependency directories unless necessary.

Common directories that should generally not be edited directly include:

* `.git/`
* `.venv/`
* `venv/`
* `node_modules/`
* `dist/`
* `build/`
* `.next/`
* `.pytest_cache/`
* `__pycache__/`
* Generated SDKs or generated schema outputs
* IDE metadata directories

If generated files must change, update the source definition and regenerate them using the repository’s established workflow.

---

## 5. Change Discipline

Make the smallest coherent change that fully solves the task.

Agents must not:

* Perform unrelated cleanup.
* Rename unrelated files or symbols.
* Reformat entire files without need.
* Replace working architecture unnecessarily.
* Introduce speculative features.
* Remove code merely because it appears unused without verifying usage.
* Change public interfaces without evaluating downstream impact.
* Silently change defaults or environment behaviour.
* Mix large refactoring with a functional bug fix unless required.

Keep diffs focused and reviewable.

If a broader refactor is required, separate mechanical changes from behavioural changes wherever practical.

---

## 6. Preserve Existing Behaviour

Unless explicitly instructed otherwise:

* Maintain backward compatibility.
* Preserve API request and response formats.
* Preserve CLI arguments and command behaviour.
* Preserve environment-variable names.
* Preserve configuration defaults.
* Preserve database schemas.
* Preserve file formats.
* Preserve error-handling behaviour relied upon by callers.
* Preserve supported runtime versions.

When a breaking change is unavoidable, document:

* What breaks
* Why it is necessary
* Which consumers are affected
* What migration is required

---

## 7. Architecture and Module Boundaries

Respect the repository’s existing architecture.

Do not bypass established layers merely to produce a faster implementation.

Examples:

* Routes or controllers should not directly contain complex persistence logic when a service or repository layer already exists.
* UI components should not duplicate domain logic already provided by shared modules.
* Shared utilities should remain independent from application-specific code.
* Database access should use the repository’s established data-access pattern.
* External integrations should remain behind existing adapters or clients.
* Configuration should flow through the repository’s established settings system.

Before creating a new shared abstraction, confirm that:

* The logic is genuinely reused.
* Existing abstractions cannot reasonably support it.
* The new abstraction reduces rather than increases complexity.

---

## 8. Coding Standards

Follow the style already used in the affected module.

General expectations:

* Use clear and descriptive names.
* Keep functions focused.
* Avoid deeply nested control flow.
* Prefer explicit behaviour over hidden side effects.
* Avoid duplicated business logic.
* Add comments only when they explain why something is necessary.
* Do not add comments that merely repeat the code.
* Use type annotations where the project already uses them.
* Keep error messages useful and actionable.
* Handle expected failure cases explicitly.
* Avoid swallowing exceptions without logging or handling them.
* Avoid broad exception catches unless there is a clear boundary reason.

Do not introduce clever code when a straightforward implementation is easier to maintain.

---

## 9. Python Rules

For Python projects in this repository:

* Use the Python version declared by the relevant project configuration.
* Use a virtual environment local to the Python project.
* Do not install project dependencies globally.
* Do not manually edit files inside `.venv`.
* Prefer existing dependency-management files and workflows.
* Keep imports organized according to the repository’s formatter or linter.
* Use type hints consistently with nearby code.
* Validate external input before using it.
* Avoid mutable default arguments.
* Use context managers for files, connections, and managed resources.
* Preserve synchronous or asynchronous boundaries already established by the application.

For `optimisation-python`:

* Keep its virtual environment inside `optimisation-python/.venv`.
* Use a supported Python version such as Python 3.11 or Python 3.13 unless the project configuration specifies otherwise.
* Do not rely on Python 3.14 compatibility unless it has been explicitly tested and enabled.
* Ensure IDE interpreter paths point to the active local virtual environment.

When adding dependencies:

1. Confirm that the dependency is necessary.
2. Check whether the functionality already exists in the standard library or current dependencies.
3. Add it through the project’s dependency-management mechanism.
4. Update lockfiles when the repository uses them.
5. Verify imports and runtime startup.

---

## 10. JavaScript and TypeScript Rules

For JavaScript or TypeScript projects:

* Use the package manager indicated by the existing lockfile.
* Do not mix `npm`, `yarn`, `pnpm`, or other package managers.
* Preserve strictness settings in `tsconfig.json`.
* Avoid introducing `any` when an appropriate type can be defined.
* Reuse existing shared types.
* Keep client-side and server-side boundaries explicit.
* Do not expose server secrets to browser bundles.
* Preserve existing component, state-management, and data-fetching patterns.
* Avoid adding a new state-management library for a local problem.

When changing UI behaviour, verify:

* Loading states
* Empty states
* Error states
* Form validation
* Keyboard accessibility
* Responsive behaviour where relevant
* Existing design-system usage

---

## 11. API Changes

When modifying an API:

* Validate request data.
* Preserve established status codes.
* Preserve response schemas unless the task requires otherwise.
* Avoid exposing internal exceptions or sensitive implementation details.
* Use the existing authentication and authorization mechanisms.
* Confirm that authorization is enforced at the correct boundary.
* Update schema definitions and documentation where applicable.
* Add or update tests for success and failure cases.

Do not treat authentication as authorization.

A valid authenticated user must still be checked for permission to perform the requested action.

---

## 12. Database and Migration Rules

Agents must not make destructive database changes casually.

For schema changes:

* Use the repository’s migration system.
* Do not edit previously applied migrations unless the project explicitly permits it.
* Prefer additive and backward-compatible migrations.
* Consider existing production data.
* Define defaults or nullable transitions safely.
* Add indexes only after considering write and storage costs.
* Avoid irreversible data transformations without a rollback or recovery plan.

Never delete tables, columns, or user data unless explicitly requested and clearly justified.

When changing queries:

* Consider performance.
* Avoid unbounded reads.
* Avoid unnecessary repeated queries.
* Preserve transaction boundaries.
* Verify concurrency-sensitive behaviour.

---

## 13. Configuration and Environment Variables

Use the existing configuration mechanism.

Do not hardcode:

* Secrets
* Passwords
* API keys
* Tokens
* Private endpoints
* Machine-specific absolute paths
* User-specific directories
* Environment-specific credentials

When adding a new environment variable:

* Use a clear and consistent name.
* Add it to the appropriate example environment file.
* Document whether it is required or optional.
* Define a safe default only when appropriate.
* Validate it during application startup if it is required.
* Avoid silently falling back when misconfiguration could be dangerous.

Local configuration files containing secrets must not be committed.

---

## 14. Security Rules

Treat all external input as untrusted.

Agents must consider:

* Injection vulnerabilities
* Path traversal
* Unsafe file uploads
* Cross-site scripting
* Cross-site request forgery
* Server-side request forgery
* Broken access control
* Insecure deserialization
* Command execution
* Secret leakage
* Unsafe redirects
* Excessive data exposure
* Dependency vulnerabilities

Never:

* Disable security controls to make a test pass.
* Log passwords, tokens, API keys, or sensitive personal data.
* Commit secrets.
* Build shell commands through unsafe string concatenation.
* Trust client-provided authorization claims without server verification.
* Return full internal stack traces to external clients.

Use parameterized queries and established validation libraries.

---

## 15. Dependency Management

Do not add a dependency without a clear need.

Before adding one:

1. Check whether the repository already includes an equivalent dependency.
2. Check whether a small local implementation is simpler and safer.
3. Confirm compatibility with supported runtime versions.
4. Consider maintenance status and security implications.
5. Add it through the correct package manager.
6. Update the appropriate lockfile.
7. Run relevant tests.

Do not upgrade unrelated dependencies as part of a focused task.

Do not remove a dependency without confirming all direct and indirect usage.

---

## 16. Testing Requirements

Every behavioural change should be validated.

Use the narrowest relevant checks first:

1. Tests for the affected module
2. Integration tests for connected components
3. Linting and static analysis
4. Type checking
5. Build verification
6. Broader test suites when practical

Add or update tests when:

* Fixing a reproducible bug
* Adding behaviour
* Changing validation
* Modifying API contracts
* Changing data transformations
* Altering authorization
* Handling a new edge case

A bug fix should preferably include a regression test that fails before the fix and passes afterward.

Do not delete or weaken tests simply to make the suite pass.

If an existing test is incorrect, explain why before changing it.

---

## 17. Test Quality

Tests should verify externally meaningful behaviour.

Prefer tests that:

* Are deterministic
* Have clear names
* Exercise one logical behaviour
* Include failure and edge cases
* Avoid unnecessary implementation coupling
* Clean up created resources
* Mock only external boundaries where appropriate

Avoid tests that merely duplicate the implementation line by line.

Do not rely on live production services in normal automated tests.

---

## 18. Validation When Tests Cannot Run

If tests or checks cannot be executed:

* State exactly which command could not run.
* Explain why it could not run.
* Report any alternative checks performed.
* Do not claim the change is fully verified.
* Do not hide environment, dependency, or tooling failures.

Examples of valid alternatives include:

* Static inspection
* Import validation
* Syntax compilation
* Targeted unit execution
* Schema validation
* Configuration parsing
* Manual call-path analysis

Alternative checks do not replace full testing when the full test suite is available.

---

## 19. Logging and Error Handling

Use the repository’s existing logging system.

Logs should:

* Provide enough context to diagnose problems.
* Use appropriate log levels.
* Avoid sensitive data.
* Avoid excessive noise in normal operation.
* Include stable identifiers where useful.
* Preserve original exception context where appropriate.

Errors exposed to users should be understandable without revealing internal details.

Do not replace actionable errors with generic messages unless security requires it.

---

## 20. Performance and Reliability

Do not introduce avoidable performance regressions.

Consider:

* Repeated database or network calls
* Blocking work inside asynchronous code
* Unbounded loops or collections
* Large in-memory copies
* Missing pagination
* Repeated model or configuration initialization
* Excessive serialization
* Expensive work in request-critical paths
* Missing timeouts and retry limits

Retries must:

* Be bounded
* Use appropriate delay or backoff
* Avoid retrying non-retryable errors
* Avoid duplicating non-idempotent operations

Optimizations should be based on a demonstrated or credible bottleneck, not speculation.

---

## 21. Documentation

Update documentation when a change affects:

* Setup
* Commands
* Configuration
* Environment variables
* API usage
* Architecture
* Deployment
* User-visible behaviour
* Developer workflows

Documentation must match the implemented behaviour.

Do not document features that do not exist.

Prefer editing the nearest relevant documentation instead of adding duplicate explanations elsewhere.

---

## 22. Git and Repository Hygiene

Keep changes easy to review.

Do not:

* Commit generated caches.
* Commit virtual environments.
* Commit editor-specific files unless intentionally tracked.
* Commit secrets.
* Modify lockfiles without a dependency-related reason.
* Include unrelated formatting changes.
* Delete user work.
* Rewrite repository history.
* Force-push.
* Create commits unless explicitly requested.

Before completing a task, inspect the final diff and confirm that every changed line is relevant.

---

## 23. Existing User Changes

Assume that uncommitted changes may belong to the user.

Do not discard, overwrite, reset, or revert changes that were not created as part of the current task.

When a target file already contains unrelated modifications:

* Preserve them.
* Make a focused edit.
* Avoid replacing the entire file unless necessary.
* Report potential conflicts or ambiguity.

Never use destructive Git commands without explicit user authorization.

Examples of destructive commands include:

```bash
git reset --hard
git clean -fd
git checkout -- .
git restore .
```

---

## 24. Commands and Tool Execution

Before running a command:

* Confirm the working directory.
* Confirm which project or service it targets.
* Prefer repository-provided scripts.
* Avoid destructive flags.
* Avoid commands that modify the global machine environment.
* Avoid installing system-wide packages unless explicitly requested.
* Do not run deployment or production commands without explicit instruction.

For long-running services, use the repository’s documented startup method.

Do not leave unnecessary background processes running.

---

## 25. Platform Awareness

The repository may be developed on different operating systems.

Avoid machine-specific assumptions.

When providing or changing commands:

* Distinguish between Command Prompt, PowerShell, Bash, and other shells.
* Do not provide PowerShell-only commands as Command Prompt commands.
* Use path handling compatible with the target platform.
* Avoid hardcoded separators when language utilities provide portable path handling.
* Account for executable locations inside Windows virtual environments.

Examples:

Windows Command Prompt:

```cmd
rmdir /s /q .venv
```

Windows PowerShell:

```powershell
Remove-Item -Recurse -Force .venv
```

Linux or macOS shell:

```bash
rm -rf .venv
```

Use destructive removal commands only when the task explicitly requires recreating generated environments or directories.

---

## 26. Prohibited Agent Behaviour

Agents must not:

* Fabricate files, APIs, commands, test results, or repository structure.
* Claim tests passed when they were not run.
* Hide errors or incomplete verification.
* Make unrelated changes.
* Commit secrets.
* Disable validation or security to bypass a problem.
* Replace working code without understanding it.
* Create duplicate implementations instead of integrating with existing code.
* Change dependency versions without need.
* Delete user modifications.
* Run destructive Git operations without permission.
* Assume production access.
* Deploy changes without explicit instruction.
* Introduce fake data into production paths.
* Leave placeholder code presented as complete.
* Add broad `TODO` comments instead of completing an achievable task.
* Silence linters using blanket ignores when the underlying issue can be fixed.
* Use unsafe type casts merely to satisfy the type checker.
* suppress exceptions without a documented reason.

---

## 27. Handling Ambiguity

When requirements are incomplete, first inspect the repository for context.

Use existing:

* Behaviour
* Tests
* Naming
* Types
* Documentation
* Configuration
* Similar features

Choose the interpretation that:

1. Requires the fewest unsupported assumptions.
2. Preserves existing behaviour.
3. Produces the smallest safe change.
4. Matches established repository conventions.

When multiple materially different implementations remain possible, clearly state the assumption used.

Do not invent business rules.

---

## 28. Definition of Done

A task is complete only when:

* The requested behaviour is implemented.
* The change follows existing architecture.
* Relevant tests have been added or updated.
* Appropriate validation has been performed.
* No unrelated files were modified.
* Documentation and configuration are updated when necessary.
* The final diff has been reviewed.
* Limitations or unverified areas are disclosed.

---

## 29. Final Response Requirements

After completing a repository task, report:

### Changed

A concise description of the implemented changes.

### Files

The files that were created or modified.

### Validation

The commands or checks that were run and their outcomes.

### Notes

Any assumptions, limitations, follow-up risks, or checks that could not be completed.

Do not provide vague statements such as “everything should work.”

Be precise about what was verified.

---

## 30. Standard Agent Workflow

For each task, follow this sequence:

1. Read applicable instructions.
2. Inspect repository structure.
3. Locate relevant implementation and tests.
4. Understand the existing behaviour.
5. Plan the smallest correct change.
6. Implement the change.
7. Add or update tests.
8. Run focused validation.
9. Run broader checks when practical.
10. Review the final diff.
11. Report changes and verification honestly.

---

## Guiding Principle

**Understand first, change minimally, preserve compatibility, verify thoroughly, and report honestly.**
