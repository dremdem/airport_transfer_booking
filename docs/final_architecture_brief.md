# Final Architecture Brief

## Purpose

This document defines how the final architecture document should be produced for the Transfer Booking Service project.

It clarifies:

- which existing documents serve which purpose
- which document is the source of truth
- how to resolve conflicts between prior architecture drafts
- which steps should be followed to produce the final architecture

## Source Documents

### `initial_assignment.md`

This file contains the original project requirements.

Use it as the baseline for:

- required API endpoints
- required technology choices already implied by the assignment
- required deliverables
- scope boundaries

### `claude_architecture.md`

This file contains one proposed architecture draft.

It should be treated as the primary source of implementation detail and architectural structure for the final architecture, unless it conflicts with decisions already recorded in `project_decisions.md`.

### `openai_architecture.md`

This file contains another proposed architecture draft.

It should be treated as a secondary reference that helps with:

- scope framing
- simplicity of delivery
- monolithic deployment assumptions
- explaining trade-offs at a high level

### `project_decisions.md`

This file contains the decisions that have already been reviewed and explicitly accepted during planning.

This is the single source of truth for the final architecture.

If either `claude_architecture.md` or `openai_architecture.md` conflicts with `project_decisions.md`, the decision recorded in `project_decisions.md` must win.

## Working Principle

The final architecture should be based primarily on `claude_architecture.md`, because it contains the most complete layered structure and the most detailed implementation reasoning.

However, all final choices must be aligned with `project_decisions.md`.

`openai_architecture.md` should be used only as a supporting reference where it improves clarity, keeps the scope realistic, or helps explain why a simpler monolithic implementation is appropriate for this project.

## Conflict Resolution Rule

When drafting the final architecture, resolve inputs in this order:

1. `project_decisions.md`
2. `initial_assignment.md`
3. `claude_architecture.md`
4. `openai_architecture.md`

Meaning:

- accepted project decisions override draft architecture proposals
- original assignment requirements define the mandatory scope
- Claude's draft provides the main structural foundation
- OpenAI's draft may refine framing, but should not override accepted decisions

## Final Architecture Drafting Steps

### 1. Re-read the assignment

Start from `initial_assignment.md` and extract the non-negotiable requirements:

- endpoints
- MySQL and SQLAlchemy usage
- Alembic migrations
- background task
- tests
- layered folder structure
- README expectations

### 2. Re-read accepted decisions

Review `project_decisions.md` and treat it as binding.

Pay particular attention to:

- naming conventions
- selected entities and tables
- ID strategy
- status workflow
- background task behavior
- status history requirements
- indexing decisions
- domain-layer responsibility
- notes already captured from `claude_architecture.md`

### 3. Use Claude's draft as the main architecture base

Take from `claude_architecture.md`:

- the layered architecture shape
- the explanation of service boundaries
- the state transition logic
- the repository and integration separation
- the testing split between unit and integration tests
- the operational reasoning for using FastAPI BackgroundTasks

Only keep these parts when they do not contradict `project_decisions.md`.

### 4. Use OpenAI's draft as a scope and delivery reference

Take from `openai_architecture.md` only where useful for:

- keeping the implementation appropriately monolithic
- preserving short-delivery pragmatism
- describing deployment in a simple way
- framing non-functional requirements without unnecessary complexity

Do not let this document weaken or replace decisions already captured in `project_decisions.md`.

### 5. Resolve known mismatches explicitly

Before writing the final architecture, check and resolve any known mismatches from earlier drafts.

Examples include:

- table naming choices
- ID strategy
- inclusion of `booking_status_history`
- index strategy
- API schema to domain input boundaries
- background task database session boundaries

These must be made consistent before the final architecture is considered complete.

### 6. Produce a single coherent architecture document

The final architecture should read as one intentional design, not as a merge of competing notes.

It should:

- avoid duplicated reasoning
- avoid unresolved contradictions
- explain architectural boundaries clearly
- stay within the assignment scope
- be detailed enough to guide implementation

### 7. Keep implementation readiness in mind

The final architecture is not only a design artifact. It should be directly usable as the implementation blueprint for the development phase.

That means it should leave no ambiguity about:

- layers and responsibilities
- database entities
- background task behavior
- testing strategy
- migration approach
- local development setup

## Expected Outcome

The output of this process should be one final architecture document in `docs/` that:

- satisfies the original assignment
- follows the accepted project decisions
- uses Claude's draft as the main structural base
- uses OpenAI's draft only as a supporting reference
- is internally consistent and implementation-ready
