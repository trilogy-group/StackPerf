# Implementation Tasks

This directory contains implementation tasks, one file per task.

## Structure

Each task file follows this schema:

```markdown
---
title: Task title
milestone: M1
priority: 1
estimate: 3
blockedBy: []
blocks: []
parent: null
---

## Summary
Brief description

## Scope
### In scope
- Item

### Out of scope
- Item

## Deliverables
- File

## Acceptance Criteria
- [ ] Criterion

## Test Plan
- Command

## Context
- Relevant repo paths
- Docs or specs to read first
- External constraints or decisions

## Definition of Ready
- [ ] Hidden assumptions are written down
- [ ] Required files, docs, and dependencies are referenced
- [ ] A coding agent can execute without missing planning context
```

## File Naming

Use `NNN-brief-description.md` format:
- `001-bootstrap-project.md`
- `002-setup-testing.md`
- `003-configure-ci.md`

## Next Steps

1. Create task files in this directory
2. Use the repo's `convert-tasks-to-linear` skill to create the corresponding Linear issues, or create them manually from these task files
3. Verify issues appear in Linear

Each task should include enough repo and documentation context that a coding agent can implement it without relying on hidden chat history.
