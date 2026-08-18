---
name: repair
description: Diagnose and repair a concrete SURGE defect, regression, failing test, CI failure, or incorrect implementation using the smallest correct change. Use when asked to fix, repair, debug-and-fix, resolve test failures, restore CI, or correct broken behavior.
---

# SURGE Repair Workflow

Repair the requested defect.

This is not a feature-development workflow.

This is not an architecture-design workflow.

The goal is:

REPRODUCE
    ↓
LOCALIZE
    ↓
IDENTIFY ROOT CAUSE
    ↓
DEFINE FIX BOUNDARY
    ↓
ADD REGRESSION PROTECTION
    ↓
MAKE MINIMAL REPAIR
    ↓
VERIFY
    ↓
REPORT

---

# Prime Directive

Fix the earliest incorrect state.

Do not patch downstream symptoms when the upstream producer is wrong.

Example:

BAD:

Report receives an invalid zero
→ change report to hide zero

BETTER:

Builder fabricates zero instead of representing unavailable measurement
→ correct the builder contract
→ ensure consumers handle the real state.

---

# Phase 1 — Protect Repository State

Before modifying code inspect:

- git status;
- current branch;
- changed files;
- relevant diff.

Do not:

- discard user changes;
- reset unrelated files;
- rewrite history;
- force push;
- overwrite concurrent work.

---

# Phase 2 — Reproduce

Reproduce the failure using the smallest useful command.

Capture:

EXPECTED
vs
ACTUAL

and exact failure evidence.

If reproduction is not possible, investigate the supplied evidence.

Do not claim reproduction succeeded when it did not.

---

# Phase 3 — Root Cause Analysis

Trace backwards:

VISIBLE FAILURE
      ↑
CONSUMER
      ↑
TRANSFORMATION
      ↑
PRODUCER
      ↑
FIRST INVALID STATE

Identify:

- root cause;
- propagation path;
- visible symptom.

Do not confuse them.

---

# Phase 4 — Establish Intended Contract

Determine intended behavior using:

1. executable behavior/tests;
2. current domain models;
3. interfaces;
4. ticket/specification;
5. ADRs;
6. repository documentation.

Explicitly identify the violated invariant.

---

# Phase 5 — Determine Blast Radius

Search for:

- callers;
- downstream consumers;
- serializers;
- reports;
- tests;
- cache fingerprints;
- similar code paths.

Determine whether the root cause affects other paths.

Do not turn this into an unrelated repository cleanup.

---

# Phase 6 — Define Repair Boundary

Before editing, establish:

ROOT CAUSE:
...

CONTRACT TO RESTORE:
...

MINIMUM COMPONENTS:
...

MUST PRESERVE:
...

MUST NOT CHANGE:
...

If the fix genuinely requires architecture redesign, STOP.

Return:

# ARCHITECTURE BLOCKER

## Existing Architecture

## Failed Assumption

## Evidence

## Why Local Repair Is Unsafe

## Decision Required

Do not invent a new architecture.

---

# Phase 7 — Regression Protection

Where practical, create or strengthen a regression test BEFORE the production fix.

The test should:

- fail against the defect;
- pass after repair;
- verify domain behavior;
- remain stable under reasonable refactoring.

Do not weaken existing tests.

Do not delete a valid failing test.

---

# Phase 8 — Apply Minimal Repair

Correct the root cause.

Prefer:

one precise correction

over:

multiple defensive compensations.

Preserve:

- deterministic behavior;
- candidate isolation;
- public contracts unless intentionally changed;
- cache correctness;
- canonical evaluation;
- state semantics;
- existing unrelated behavior.

Avoid:

- unrelated refactoring;
- renaming unrelated APIs;
- new abstractions without need;
- silent fallback behavior;
- broad exception swallowing;
- magic default values.

---

# Phase 9 — Targeted Verification

Immediately run the smallest test proving the repair.

If it fails:

DO NOT continue accumulating speculative changes.

Investigate the failure.

---

# Phase 10 — Regression Verification

After targeted verification passes, expand to:

- affected test module;
- affected subsystem;
- relevant integration tests.

Then run relevant static checks.

---

# Phase 11 — Full Verification

If appropriate for the scope, run the project's broader verification suite.

For Python this may include repository-defined:

- pytest;
- Ruff;
- strict mypy;
- workflow/integration verification.

Use actual repository configuration to determine commands.

---

# Phase 12 — Diff Audit

Inspect the final diff.

Remove:

- debug prints;
- temporary instrumentation;
- unused imports;
- accidental file modifications;
- test hacks.

Ensure the diff contains only justified repair work.

---

# Required Output

# Repair Report

## Problem

Concise defect description.

## Reproduction

**Command:**

```text
...
