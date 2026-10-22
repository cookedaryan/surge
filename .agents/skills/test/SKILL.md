---
name: test
description: Verify a SURGE implementation, ticket, fix, module, or branch by running the appropriate tests, static analysis, behavioral checks, and regression verification. Use when asked to test, verify, validate, check CI readiness, or prove that an implementation works.
---

# SURGE Verification Workflow

Verify the requested implementation.

The optional user-provided scope may be:

- ticket number;
- feature;
- test file;
- module;
- changed files;
- current working tree;
- branch work.

Testing is an EVIDENCE-GATHERING operation.

Do not redesign architecture.

Do not repair failing code unless explicitly asked to proceed with repair.

---

# Core Rule

Do not conclude:

"Tests pass, therefore implementation is correct."

Verification must establish both:

1. the automated checks pass;
2. the important intended behavior is actually covered.

---

# Phase 1 — Establish Repository State

Inspect:

- current branch;
- git status;
- changed files;
- relevant diff;
- repository test configuration;
- AGENTS.md;
- relevant ticket/specification if available.

Preserve all existing user changes.

Do not reset, discard, or rewrite unrelated work.

---

# Phase 2 — Determine Test Scope

Identify which components changed.

Determine the smallest useful verification boundary.

Prefer this order:

TARGETED
    ↓
SUBSYSTEM
    ↓
REGRESSION
    ↓
FULL REPOSITORY

Do not begin with the most expensive suite unless necessary.

---

# Phase 3 — Targeted Behavioral Verification

Run tests directly related to the requested feature/change.

Check both:

## Positive cases

Expected valid input produces expected behavior.

## Boundary cases

Examples:

- zero;
- empty collection;
- None / unavailable;
- minimum/maximum values;
- ties;
- deterministic ordering;
- repeated evaluation.

## Negative cases

Examples:

- invalid configuration;
- infeasible candidate;
- missing data;
- routing failure;
- electrical failure;
- exhausted repair;
- invalid state.

---

# Phase 4 — SURGE Invariant Verification

Where relevant verify that the change preserves:

- deterministic behavior;
- candidate-level failure isolation;
- one canonical evaluation path;
- stable candidate identity/signatures;
- stable cache fingerprints;
- explicit state semantics;
- electrical validation authority;
- scoring consistency;
- lifecycle-cost consistency;
- reporting truthfulness.

Pay particular attention to distinctions such as:

None != 0

unmeasured != measured zero

unavailable != empty

failure != not evaluated

fallback != measured result

---

# Phase 5 — Regression Verification

Run broader tests covering affected modules and downstream consumers.

Consider effects on:

- candidate generation;
- routing;
- pole placement;
- cable sizing;
- Pandapower;
- metrics;
- costing;
- scoring;
- search;
- land assessment;
- reporting;
- serialization/API.

Only run relevant areas unless full regression is appropriate.

---

# Phase 6 — Static Verification

Discover repository-native commands.

Run appropriate checks such as:

- Ruff;
- mypy;
- formatting validation;
- build checks;
- repository verification scripts.

Never claim a check passed unless it was actually executed.

Do not invent commands when the repository already defines them.

---

# Phase 7 — Inspect Test Quality

Determine whether existing tests actually prove the intended behavior.

Look for:

- weak assertions;
- happy-path-only tests;
- tests coupled to implementation details;
- excessive mocking;
- missing regression coverage;
- fixtures masking real defects;
- tests verifying constants rather than behavior.

Do not modify tests simply to obtain green output.

---

# Phase 8 — Diff Hygiene

Inspect the final working diff.

Look for:

- debugging prints;
- temporary files;
- commented-out implementation;
- TODO placeholders;
- accidental file changes;
- test weakening;
- broad exception suppression;
- unnecessary ignores;
- unrelated refactors.

---

# Required Output

# Verification Report

## Scope

State exactly what was tested.

## Repository State

- Branch:
- Changed files:
- Relevant ticket/feature:

## Targeted Tests

| Check | Result |
|---|---|
| command | PASS / FAIL |

## Regression Tests

| Check | Result |
|---|---|

## Static Checks

| Check | Result |
|---|---|

## Behavioral Coverage

For each important requirement:

### Requirement

**Evidence:**  
...

**Result:** PASS / FAIL / NOT VERIFIED

## SURGE Invariants

Report relevant invariant checks.

## Test Gaps

List behavior that still lacks sufficient verification.

## Failures

For every failure include:

- command;
- test;
- error;
- likely failure area.

Do not repair it unless requested.

## Unverified Areas

Explicitly state what could not be proved.

## Verdict

Exactly one:

VERIFIED

VERIFIED WITH LIMITATIONS

VERIFICATION FAILED

BLOCKED
