# CLAUDE.md - Ticket Workflow Guidelines for docs/tickets/

This document defines the ticket hierarchy, workflow, and standards for gitctx development.

## 🚨 Ticket Philosophy

**Every ticket drives BDD/TDD development and maintains full traceability.**

Tickets should:

1. Form a clear hierarchy (Initiative → Epic → Story → Task)
2. Include testable acceptance criteria
3. Link to parent and child tickets
4. Track progress transparently

## Ticket Hierarchy

```bash
Initiative (INIT-N)           # Strategic goal (quarters/years)
└── Epic (EPIC-N.N)          # Feature set (weeks/months)
    └── Story (STORY-N.N.N)  # User story (days)
        └── Task (TASK-N.N.N.N) # Technical task (hours)

Bug (BUG-N)                  # Independent of hierarchy
```

## Ticket ID Format

### Hierarchical IDs (with 4-digit zero-padded initiative numbers)

| Type | Format | Example | File Path |
|------|--------|---------|-----------|
| Initiative | INIT-{NNNN} | INIT-0001 | initiatives/INIT-0001/README.md |
| Epic | EPIC-{NNNN}.{E} | EPIC-0001.2 | initiatives/INIT-0001/epics/EPIC-0001.2.md |
| Story | STORY-{NNNN}.{E}.{S} | STORY-0001.2.3 | initiatives/INIT-0001/stories/STORY-0001.2.3.md |
| Task | TASK-{NNNN}.{E}.{S}.{T} | TASK-0001.2.3.4 | initiatives/INIT-0001/tasks/TASK-0001.2.3.4.md |
| Bug | BUG-{NNNN} | BUG-0015 | bugs/BUG-0015.md |

Where:

- {NNNN} = Initiative number (4-digit zero-padded)
- {E} = Epic number within initiative (no padding)
- {S} = Story number within epic (no padding)
- {T} = Task number within story (no padding)
- {NNNN} = Sequential number (4-digit zero-padded)

### ID Examples

```bash
INIT-0001 (MVP Foundation)
├── EPIC-0001.1 (CLI Foundation)
│   ├── STORY-0001.1.1 (Config Command)
│   │   ├── TASK-0001.1.1.1 (YAML Parser)
│   │   └── TASK-0001.1.1.2 (Environment Variables)
│   └── STORY-0001.1.2 (Index Command)
│       └── TASK-0001.1.2.1 (Progress Bar)
└── EPIC-0001.2 (Real Indexing)
    └── STORY-0001.2.1 (File Scanner)
```

## Directory Structure

```bash
docs/tickets/
├── CLAUDE.md              # This file
├── initiatives/
│   ├── INIT-0001/        # Each initiative gets a folder
│   │   ├── README.md     # Initiative overview
│   │   ├── epics/        # All epics for this initiative
│   │   ├── stories/      # All stories for this initiative
│   │   └── tasks/        # All tasks for this initiative
│   └── INIT-0002/
│       └── ...
└── bugs/                 # All bugs (not tied to initiatives)
    └── BUG-NNNN.md
```

## Ticket Templates

### Initiative Template (README.md)

```markdown
# INIT-NNNN: [Title]
**Timeline**: Q1-Q2 2025 | **Status**: 🟡 | **Owner**: [Team]

## Objective
[Strategic goal paragraph]

## Key Results
- [ ] Measurable outcome 1
- [ ] Measurable outcome 2

## Epics
- [EPIC-NNNN.1](epics/EPIC-NNNN.1.md): Title
- [EPIC-NNNN.2](epics/EPIC-NNNN.2.md): Title
```

### Epic Template

```markdown
# EPIC-NNNN.N: [Title]
**Parent**: [INIT-NNNN](../README.md) | **Status**: 🔵 | **Points**: 8-13

## Overview
[What this epic delivers]

## Child Stories
- [STORY-NNNN.N.1](../stories/STORY-NNNN.N.1.md): Title

## BDD Spec
​```gherkin
Scenario: [Key behavior]
  Given [context]
  When [action]
  Then [outcome]
​```
```

### Story Template

```markdown
# STORY-NNNN.N.N: [Title]
**Parent**: [EPIC-NNNN.N](../epics/EPIC-NNNN.N.md) | **Status**: 🔵 | **Points**: 3-5

## User Story
As a [user] I want [goal] so that [benefit]

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2

## Tasks
- [TASK-NNNN.N.N.1](../tasks/TASK-NNNN.N.N.1.md)
```

### Task Template

```markdown
# TASK-NNNN.N.N.N: [Title]
**Parent**: [STORY-NNNN.N.N](../stories/STORY-NNNN.N.N.md) | **Hours**: 2-4

## Implementation
- [ ] Step 1
- [ ] Step 2
- [ ] Tests pass
```

### Bug Template

```markdown
# BUG-NNNN: [Title]
**Severity**: 🔴/🟡/🟢 | **Status**: 🔵

## Reproduction
1. Step 1
2. Step 2
3. Observe: [actual vs expected]

## Environment
- OS: [System]
- Version: [gitctx version]
```

## Status Tracking

### Status Indicators

| Status | Symbol | Description | Applies To |
|--------|--------|-------------|------------|
| Not Started | 🔵 | Planned but not begun | All |
| In Progress | 🟡 | Active development | All |
| Complete | 🟢 | Done and verified | All |
| Blocked | 🔴 | Waiting on dependency | All |
| Archived | 📦 | Moved to archive | Initiative, Epic |

### Progress Tracking

Use visual progress bars for initiatives and epics:

```markdown
Progress: ████████░░ 80%
```

Calculate based on:

- Initiatives: % of epics complete
- Epics: % of stories complete
- Stories: % of tasks complete

## Estimation Guidelines

### Story Points (Fibonacci)

| Points | Effort | Time | Example |
|--------|--------|------|---------|
| 1 | Trivial | <1 hour | Fix typo, update config |
| 2 | Very Small | 1-2 hours | Simple validation |
| 3 | Small | 2-4 hours | Basic feature |
| 5 | Medium | 1 day | Standard feature |
| 8 | Large | 2-3 days | Complex feature |
| 13 | Very Large | 1 week | Major feature |
| 21 | Huge | 2+ weeks | Consider breaking down |

### Estimation Rules

1. **Stories**: Estimate in story points (Fibonacci)
2. **Tasks**: Estimate in hours (2-8 hours max)
3. **Epics**: Sum of story estimates
4. **Initiatives**: Rough timeline (quarters)

## BDD/TDD Requirements

### By Ticket Type

| Type | BDD Required | TDD Required | Test Level |
|------|--------------|--------------|------------|
| Initiative | Overview only | N/A | N/A |
| Epic | Key scenarios | N/A | E2E/Integration |
| Story | Full scenarios | N/A | E2E |
| Task | N/A | Yes | Unit |
| Bug | Reproduction | Fix verification | Unit/E2E |

### BDD for Stories

Every story MUST include:

```gherkin
Scenario: [User-visible behavior]
  Given [precondition]
  When [user action]
  Then [observable outcome]
```

### TDD for Tasks

Every task MUST include:

```python
def test_[functionality]():
    """Test that [expected behavior]."""
    # RED: Write failing test
    # GREEN: Implement to pass
    # REFACTOR: Clean up
```

## Workflow

### Creating Tickets

1. **Initiative**: Created during quarterly planning
2. **Epic**: Created when initiative is approved
3. **Story**: Created during epic breakdown
4. **Task**: Created during story planning
5. **Bug**: Created when issue discovered

### Ticket Lifecycle

```bash
Created → Not Started → In Progress → Review → Complete
                ↓                        ↑
              Blocked ←→→→→→→→→→→→→→→→→→→┘
```

### Parent-Child Relationships

- Every epic MUST have a parent initiative
- Every story MUST have a parent epic
- Every task MUST have a parent story
- Bugs are independent (no parent required)

### Moving Tickets

When moving a ticket to a different parent:

1. Update the ticket ID to match new hierarchy
2. Move the file to appropriate directory
3. Update parent reference in ticket
4. Update child references in old and new parents
5. Update any cross-references

## Best Practices

### DO

- ✅ Keep tickets focused and small
- ✅ Always link parent and children
- ✅ Include clear acceptance criteria
- ✅ Update status immediately
- ✅ Write BDD/TDD specs first

### DON'T

- ❌ Create tasks >8 hours
- ❌ Skip parent-child links
- ❌ Leave vague descriptions
- ❌ Batch status updates
- ❌ Implement without tests

## Querying Tickets

### Find all epics

```bash
find docs/tickets/initiatives/*/epics -name "EPIC-*.md"
```

### Find in-progress stories

```bash
grep -r "Status: 🟡" docs/tickets/initiatives/*/stories/
```

### Find blocked items

```bash
grep -r "Status: 🔴" docs/tickets/
```

### Count by type

```bash
# All stories
find docs/tickets -name "STORY-*.md" | wc -l

# Stories in INIT-0001
find docs/tickets/initiatives/INIT-0001/stories -name "*.md" | wc -l
```

## Archiving

### When to Archive

- Initiative: 6 months after completion
- Epic: 3 months after completion
- Story/Task: With parent epic
- Bug: 1 year after resolution

### Archive Process

1. Create `docs/tickets/archive/YYYY/`
2. Move entire initiative folder
3. Update any references
4. Add to archive index

## Resources

- [User Story Mapping](https://www.jpattonassociates.com/user-story-mapping/)
- [Agile Estimation](https://www.atlassian.com/agile/project-management/estimation)
- [BDD in Action](https://www.manning.com/books/bdd-in-action)
