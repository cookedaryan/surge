# SURGE documentation

Documents are grouped by topic. Status and dates inside each document distinguish implemented behavior from plans and historical context.

Start with the [product overview](product/SURGE%20%E2%80%94%20Smart%20Utility%20Routing%20and%20Grid%20Evacuation.md), the [gap closure plan](planning/MVP%20Gap%20Closure%20Plan.md), or the [Python engine architecture](architecture/Python%20Engine%20-%20Architecture.md).

See [CONTEXT.md](../CONTEXT.md) for the repository progress record and [the Obsidian vault](../obsidian-vault/) for detailed design notes.

## Product

Product vision and MVP scope.

- [Application Flow Document (APP-FLOW)](product/APP-FLOW.md)
- [Two-Week MVP and AI-Assisted Development Workflow](product/MVP%20-%20Minimum%20Viable%20Product.md)
- [Product Requirements Document (PRD)](product/PRD.md)
- [SURGE — Smart Utility Routing and Grid Evacuation](product/SURGE%20%E2%80%94%20Smart%20Utility%20Routing%20and%20Grid%20Evacuation.md)

## Planning

Delivery plans, integration work, and ticket sequences.

- [Consumption Gap — Ticket Plan](planning/Consumption%20Gap%20Ticket%20Plan.md)
- [MVP Gap Closure Plan](planning/MVP%20Gap%20Closure%20Plan.md)
- [Python Engine Integration Plan](planning/Python%20Engine%20Integration%20Plan.md)
- [Surge MVP Ticket Plan](planning/Surge%20MVP%20Ticket%20Plan.md)
- [SURGE — Sunday KMZ-to-33 kV Network Delivery Plan](planning/whats-next.md)

## Architecture

Technical requirements, Python service architecture, and response contracts.

- [Python Presentation Boundary](architecture/presentation-boundary.md)
- [Python Engine Architecture and GIS Processing](architecture/Python%20Engine%20-%20Architecture.md)
- [Technical Requirements Document (TRD)](architecture/TRD.md)

## Routing

Geographic constraints and preliminary route scoring.

- [Constraint-aware routing](routing/Constraint-aware%20Routing.md)
- [Route Scoring Architecture](routing/Route%20Scoring%20Architecture.md)

## Optimisation

PNC assembly, candidate generation, engineering metrics, and ranking.

- [Candidate PNC Scenario Generation](optimisation/Candidate%20PNC%20Scenario%20Generation.md)
- [Canonical Candidate Engineering Metrics (SURGE-PY-026)](optimisation/Canonical%20Candidate%20Engineering%20Metrics.md)
- [Multi-Objective Candidate Scoring (PY-027 / PY-029)](optimisation/Multi-Objective%20Candidate%20Scoring.md)
- [PNC Network Assembly](optimisation/PNC%20Network%20Assembly.md)

## Electrical

AC load-flow validation and its architecture decision.

- [AC Load Flow Validation](electrical/AC%20Load%20Flow%20Validation.md)
- [ADR-007: Pandapower AC Load Flow Validation](electrical/ADR-007%20Pandapower%20AC%20Load%20Flow%20Validation.md)

## Land and Cost

Land acquisition decisions and lifecycle costing.

- [Lifecycle Cost Objective Model](land-and-cost/Cost%20Model.md)
- [Land Acquisition & Route Decision Engine — implementation analysis](land-and-cost/Land%20Acquisition%20and%20Route%20Decision%20Engine.md)

## Backend

Java backend and KMZ asset classification.

- [SURGE-JV-006 — KMZ Asset Classification](backend/SURGE-JV-006%20-%20KMZ%20Asset%20Classification%20Plan.md)

## Frontend

UX review, frontend design specifications, and implementation plans.

- [SURGE Web Map Frontend Redesign Implementation Plan](frontend/plans/2026-08-12-web-map-frontend-redesign.md)
- [SURGE Web Map Frontend Redesign — Design Spec](frontend/specs/2026-08-12-web-map-frontend-redesign-design.md)
- [SURGE Frontend — Interaction & Motion Polish](frontend/specs/2026-08-18-frontend-interaction-polish-design.md)
- [SURGE Frontend — UX Improvement Report](frontend/UX%20Improvement%20Report.md)
