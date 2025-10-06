---
description: Find and write next incomplete tickets through iterative requirement capture
allowed-tools: "*"
---

# Write Next Tickets: Intelligent Ticket Discovery and Creation

You are tasked with discovering incomplete or missing tickets in the project hierarchy and working interactively with the user to write/update them with complete, actionable detail.

## Overall Workflow

1. **Gather User Intent** - Ask if full discovery or specific ticket focus
2. **Discovery & Gap Analysis** - Use Task agent to scan hierarchy and identify gaps
3. **Present Gap Report** - Show findings and get approval on what to work on
4. **Iterative Ticket Writing Loop** - For each ticket to write/update:
   - Present context and current state
   - Interactive Q&A to capture requirements
   - Draft ticket with Task agent
   - Review and refine until approved
   - Save ticket file and update parents
5. **Final Summary** - Report on what was created/updated and next steps

---

## Step 0: Gather User Intent

⚠️ **INITIAL PROMPT**

Before starting discovery, ask the user what scope they want:

```markdown
# 📝 Ticket Writing Session

This command helps you discover and write incomplete tickets across the project hierarchy.

**Scope Options:**

1. **full** - Scan entire ticket hierarchy for gaps
   - Analyzes all initiatives, epics, stories
   - Identifies all incomplete or missing tickets
   - Recommends prioritized work order
   - Best for: Planning sessions, new epic work

2. **focused** - Work on specific ticket or area
   - You provide ticket ID or area to focus on
   - Analyzes only that branch of hierarchy
   - Faster, more targeted
   - Best for: Adding stories to existing epic, detailing known gap

**Which scope do you want?** (full/focused)
```

Wait for user response.

**If "full":**
- Set `SCOPE = "full"`
- Set `FOCUS_AREA = ""`
- Proceed to Step 1 with full discovery

**If "focused":**
- Set `SCOPE = "focused"`
- Ask follow-up:
  ```markdown
  **What should we focus on?**

  Provide either:
  - Ticket ID: EPIC-0001.2, STORY-0001.2.1, etc.
  - Area description: "Real indexing epic", "vector search stories", etc.

  Your focus:
  ```

  Wait for user input.
  - If ticket ID: Set `FOCUS_AREA = <ticket_id>`
  - If description: Set `FOCUS_AREA = <description>`
  - Proceed to Step 1 with focused discovery

**If neither:**
- Ask again with validation: "Please choose 'full' or 'focused'"

---

## Step 1: Discovery & Gap Analysis

Use Task agent (general-purpose) to analyze the ticket hierarchy and identify gaps.

### Task Agent Prompt:

```markdown
Perform comprehensive ticket hierarchy analysis to identify incomplete or missing tickets.

**Scope**: {SCOPE}
{IF SCOPE == "focused"}
**Focus Area**: {FOCUS_AREA}
{ENDIF}

## Discovery Mission

Analyze the ticket hierarchy in docs/tickets/ to identify:
1. **Incomplete Tickets** - Exist but lack necessary detail
2. **Missing Tickets** - Should exist based on hierarchy but don't
3. **Readiness Assessment** - Which tickets are ready for work vs need detail
4. **Dependency Mapping** - What must be completed before what

## Required Analysis

### 1. Scan Ticket Hierarchy

**Read All Context:**
1. Roadmap: docs/vision/ROADMAP.md
2. Root CLAUDE.md: CLAUDE.md
3. Tickets CLAUDE.md: docs/tickets/CLAUDE.md
4. All initiatives: docs/tickets/INIT-*/README.md
5. All epics: docs/tickets/INIT-*/EPIC-*/README.md
6. All stories: docs/tickets/INIT-*/EPIC-*/STORY-*/README.md
7. All tasks: docs/tickets/INIT-*/EPIC-*/STORY-*/TASK-*.md

{IF SCOPE == "focused"}
**Focus Your Analysis:**

Only analyze tickets in the focus area and their immediate context:
- If FOCUS_AREA is ticket ID: Read that ticket + parent + children
- If FOCUS_AREA is description: Grep for matching tickets, read those + context

Limit scope to the branch of hierarchy relevant to the focus area.
{ENDIF}

### 2. Codebase Pattern Survey (REQUIRED BEFORE SCORING)

**Before scoring tickets, survey existing patterns to inform recommendations:**

**Discover Existing Patterns:**
1. Read ALL conftest.py files: `tests/conftest.py`, `tests/unit/conftest.py`, `tests/e2e/conftest.py`
   - List all available fixtures
   - Note fixture composition patterns
   - Identify factory fixtures

2. Survey test patterns in `tests/unit/` and `tests/e2e/`
   - Find common AAA (Arrange-Act-Assert) patterns
   - Note parametrization strategies
   - Identify reusable step definitions (E2E)
   - Extract mocking approaches

3. Scan source modules in `src/gitctx/`
   - Note common import patterns
   - Identify utility functions and helpers
   - Find shared constants/configuration
   - Document class structures and abstractions

4. Review nested CLAUDE.md files
   - `tests/e2e/CLAUDE.md` - BDD patterns
   - `tests/unit/CLAUDE.md` - TDD patterns
   - `docs/CLAUDE.md` - Documentation standards
   - Note documented anti-patterns to avoid

**Pattern Reuse Checklist:**

When analyzing gaps and recommending work, validate:
- [ ] No new fixture needed when existing one works
- [ ] No duplicate test patterns when similar tests exist
- [ ] No reimplementation of existing utilities
- [ ] No new abstractions when current ones fit
- [ ] No premature optimization without metrics
- [ ] No over-engineering simple problems
- [ ] Stories build on existing foundation

**Output Pattern Inventory** (include in gap analysis):

```markdown
## Discovered Reusable Patterns

**Test Fixtures** ({N} found):
- `fixture_name` (file:line) - {purpose}
- `fixture_name` (file:line) - {purpose}

**Test Patterns** ({N} found):
- AAA pattern: tests/unit/module/test_file.py (lines X-Y)
- Parametrization: tests/unit/module/test_file.py (lines X-Y)
- Factory pattern: tests/unit/conftest.py (lines X-Y)

**Source Patterns** ({N} found):
- Utility: src/gitctx/utils/module.py:function_name
- Helper: src/gitctx/core/module.py:helper_name
- Abstraction: src/gitctx/core/module.py:ClassName

**Documented Anti-Patterns** ({N} found):
- {Anti-pattern from CLAUDE.md}
- {Anti-pattern from CLAUDE.md}

---
```

### 3. Completeness Scoring

For each ticket found, score completeness (0-100%):

#### Initiative Completeness (8 criteria)
- ✅ Has clear strategic objective (not vague)
- ✅ Has measurable key results (not TBD)
- ✅ Has timeline defined (quarters/months)
- ✅ Lists all child epics with links
- ✅ Has success metrics section
- ✅ Has risk assessment
- ✅ Has dependencies documented
- ✅ Progress bar reflects reality

**Score**: N/8 = X%

#### Epic Completeness (10 criteria)
- ✅ Has clear overview (what it delivers)
- ✅ Parent initiative exists and links back
- ✅ Has BDD scenarios (at least 1 key scenario)
- ✅ Lists all child stories with links
- ✅ Has story point estimate
- ✅ Stories sum to epic estimate
- ✅ Has technical approach section
- ✅ Has deliverables checklist
- ✅ No vague terms (TBD, etc., handle, support)
- ✅ Progress bar reflects reality

**Score**: N/10 = X%

#### Story Completeness (14 criteria)
- ✅ Has user story in "As a/I want/So that" format
- ✅ Parent epic exists and links back
- ✅ Has concrete acceptance criteria (testable)
- ✅ Lists all child tasks with links
- ✅ Has BDD scenarios in Gherkin format
- ✅ BDD scenarios cover all acceptance criteria
- ✅ Has technical design section
- ✅ Has story point estimate
- ✅ Tasks sum to story estimate (1 point ~= 4 hours)
- ✅ Has dependencies section
- ✅ No vague acceptance criteria
- ✅ Progress bar reflects reality
- ✅ Technical design references existing patterns/fixtures to reuse
- ✅ No unnecessary complexity or premature optimization

**Score**: N/14 = X%

#### Task Completeness (10 criteria)
- ✅ Has clear title (what will be done)
- ✅ Parent story exists and links back
- ✅ Has implementation checklist (concrete steps)
- ✅ Has hour estimate (2-8 hours max)
- ✅ Steps are specific (not "implement X")
- ✅ Includes test requirements
- ✅ Has file paths or module names
- ✅ Has verification criteria
- ✅ Identifies which existing fixtures/patterns to reuse
- ✅ Justifies any new patterns (explains why existing insufficient)

**Score**: N/10 = X%

### 4. Anti-Overengineering Detection

For each incomplete/missing ticket, check for signs of unnecessary complexity:

**Red Flags for Stories/Tasks:**

❌ **Unnecessary Abstraction Layers**
- Proposing interfaces/abstractions with only one implementation
- Using "future-proof" without roadmap evidence
- Creating plugin systems before second use case exists

❌ **Premature Optimization**
- Caching for small, rarely-accessed data
- Performance tuning before metrics show problems
- Complex algorithms for simple operations

❌ **Over-Engineered Solutions**
- Large refactors when targeted fixes work
- Breaking working code "for cleanliness"
- Architectural changes without requirements driving them

❌ **Scope Creep**
- Tasks that do more than story requires
- Adding features not in acceptance criteria
- "While we're at it..." syndrome

**Valid Complexity** (DO NOT flag):
✅ Security hardening (always appropriate)
✅ Type safety and validation (catches bugs early)
✅ Error handling for user-facing features
✅ Test coverage improvements
✅ Documentation
✅ Fixing actual quality threshold violations

**When Flagging Overengineering:**

Document:
- Which ticket has unnecessary complexity
- What specific element is over-engineered
- Why it's not needed yet
- What simpler alternative would work
- Under what conditions it would be justified

**Recommendations:**
- Reduce task scope to MVP
- Remove unnecessary task entirely
- Move to future story with "if metrics show need"
- Replace abstraction with concrete implementation

### 5. Gap Classification

Classify each gap found:

**Type 1: Missing Ticket**
- Should exist based on parent but file doesn't exist
- Example: Epic says "3 stories" but only 1 story file exists

**Type 2: Incomplete Detail**
- Ticket exists but score <80%
- Example: Story has no tasks, BDD scenarios missing

**Type 3: Vague Specification**
- Contains TBD, placeholder text, vague terms
- Example: "Handle authentication" (not concrete)

**Type 4: Broken Hierarchy**
- Parent/child links broken or missing
- Example: Story references epic that doesn't exist

**Type 5: Out of Sync**
- Progress bars wrong, status doesn't match reality
- Example: Epic says 50% but all stories complete

**Type 6: Over-Engineered**
- Proposes unnecessary complexity
- Example: Caching layer for data loaded once per process

**Type 7: Pattern Duplication**
- Reimplements existing functionality
- Example: New fixture when existing one works with params

### 6. Dependency Analysis

For each gap, determine:

**Blocking Status:**
- **Ready**: All prerequisites complete, can write now
- **Blocked**: Depends on incomplete work
- **Unknown**: Not enough info to determine

**Blocker Examples:**
- Can't detail EPIC-0002.1 stories until INIT-0001 complete
- Can't write TASK-0001.2.1.3 until STORY-0001.2.1 detailed
- Can write EPIC-0001.2 stories now (EPIC-0001.1 complete)

### 7. Prioritization

Rank gaps by:
1. **Urgency**: On critical path for current work
2. **Readiness**: Not blocked, can work now
3. **Impact**: Enables other work when complete
4. **Completeness**: Closer to ready = higher priority

**Priority Levels:**
- **P0 Critical**: Blocking current development work
- **P1 High**: Needed soon, not blocking yet
- **P2 Medium**: Improves planning, not urgent
- **P3 Low**: Nice to have, can defer

### 8. Roadmap Alignment

Check each gap against docs/vision/ROADMAP.md:
- Does this fit current initiative timeline?
- Is parent initiative in right state for this?
- Does this align with strategic objectives?

## Output Format

Return structured analysis:

```markdown
# 📊 Ticket Hierarchy Gap Analysis

**Scope**: {full | focused}
{IF focused}
**Focus Area**: {FOCUS_AREA}
{ENDIF}
**Analysis Date**: {date}

---

## Executive Summary

**Total Tickets Found**: {N}
- Initiatives: {N_init} ({N_init_complete} complete, {N_init_incomplete} incomplete)
- Epics: {N_epic} ({N_epic_complete} complete, {N_epic_incomplete} incomplete)
- Stories: {N_story} ({N_story_complete} complete, {N_story_incomplete} incomplete)
- Tasks: {N_task} ({N_task_complete} complete, {N_task_incomplete} incomplete)

**Gaps Identified**: {total_gaps}
- Missing Tickets: {N}
- Incomplete Detail: {N}
- Vague Specifications: {N}
- Broken Hierarchy: {N}
- Out of Sync: {N}
- Over-Engineered: {N}
- Pattern Duplication: {N}

**Recommended Next Action**: {ticket_id or description}

---

## Gap Details by Priority

### P0 Critical ({count})

**GAP-001: {Title}**
- **Type**: {Missing Ticket | Incomplete Detail | etc.}
- **Ticket**: {ticket_id or "N/A - doesn't exist"}
- **Parent**: {parent_id}
- **Current State**: {what exists now}
- **Completeness Score**: {X}% ({N}/{total} criteria met)
- **Missing Details**:
  - {Detail 1}
  - {Detail 2}
- **Blocking**: {what work is blocked}
- **Ready**: {Yes | No - blocked by: ...}
- **Estimated Effort**: {X} hours to write/update

[Repeat for each P0 gap]

### P1 High ({count})

[Same format as P0]

### P2 Medium ({count})

[Same format as P0]

### P3 Low ({count})

[Same format as P0]

---

## Dependency Map

```
INIT-0001 (33% complete)
├── EPIC-0001.1 ✅ Complete (100%)
├── EPIC-0001.2 🔴 GAP-003 (missing stories)
│   └── Blocks: INIT-0001 completion
└── EPIC-0001.3 🔴 GAP-004 (missing stories)
    └── Blocks: INIT-0001 completion

INIT-0002 (0% complete)
├── EPIC-0002.1 🔴 GAP-005 (blocked by INIT-0001)
├── EPIC-0002.2 🔴 GAP-006 (blocked by INIT-0001)
└── EPIC-0002.3 🔴 GAP-007 (blocked by INIT-0001)
```

---

## Roadmap Alignment

**Current Phase**: {from ROADMAP.md}
**Active Initiative**: {INIT-XXXX}

**Gaps Aligned with Current Phase**: {N}
**Gaps for Future Phases**: {N}
**Gaps Misaligned**: {N} (should be moved/deleted)

---

## Recommended Work Order

1. **{GAP-ID}**: {Title} ({effort} hours)
   - Reason: {why this first}
   - Enables: {what becomes possible}

2. **{GAP-ID}**: {Title} ({effort} hours)
   - Reason: {why this second}
   - Enables: {what becomes possible}

[Continue for top 5-10 gaps]

---

## Quality Observations

**Strong Patterns** (keep doing):
- {Pattern 1}
- {Pattern 2}

**Weak Patterns** (needs improvement):
- {Anti-pattern 1}
- {Anti-pattern 2}

**Recommendations**:
- {Recommendation 1}
- {Recommendation 2}

---

## Detailed Gap Specifications

For each gap, provide:

### GAP-{ID}: {Title}

**Current State:**
```
[Show current ticket content if exists, or "N/A - ticket doesn't exist"]
```

**Missing/Needed:**
- **Objective**: {if missing/vague}
- **Acceptance Criteria**: {if missing/vague}
- **Child Tickets**: {list what should exist}
- **BDD Scenarios**: {if missing}
- **Technical Design**: {if missing}
- **Estimates**: {if missing}

**Pattern Reuse Opportunities:**
- Can reuse fixture: {fixture_name from conftest.py}
- Can follow pattern: {test_file.py:lines}
- Can import helper: {module.py:function}
- Avoid: {anti-pattern from CLAUDE.md}

**Questions to Ask User** (for interactive capture):
1. {Question 1}
2. {Question 2}
3. {Question 3}
4. "Do you know of existing code that does something similar?"

**Draft Template** (what structure to use):
{Show template from docs/tickets/CLAUDE.md appropriate for ticket type}

---
```

## Important Notes

1. **Be Thorough**: Read every ticket file, don't skip any
2. **No Assumptions**: If detail is missing, mark it as gap
3. **Check Links**: Verify parent/child references are correct
4. **Reality Check**: Compare progress bars to actual ticket states
5. **Roadmap Context**: Use ROADMAP.md to understand priorities
6. **Specific Questions**: For each gap, suggest specific questions to ask user
7. **Effort Estimation**: Estimate time to write each ticket (be realistic)

**Execute the analysis now.**
```

**Agent Configuration:**
- Type: general-purpose
- Mode: Research only (no writes yet)
- Output: Detailed gap analysis in markdown

Wait for agent to complete analysis.

---

## Step 2: Present Gap Report

⚠️ **MANDATORY STOP POINT**

After receiving the Task agent's analysis, present findings to user for approval.

### Report Format:

```markdown
# 📊 Ticket Gap Analysis Report

**Scope**: {full | focused}
{IF focused}
**Focus Area**: {FOCUS_AREA}
{ENDIF}
**Date**: {date}

═══════════════════════════════════════════════════════════

## Executive Summary

**Hierarchy Overview:**
- Initiatives: {N} total ({complete} complete, {incomplete} incomplete)
- Epics: {N} total ({complete} complete, {incomplete} incomplete)
- Stories: {N} total ({complete} complete, {incomplete} incomplete)
- Tasks: {N} total ({complete} complete, {incomplete} incomplete)

**Gaps Found**: {total_gaps}

| Type | Count | Ready Now | Blocked |
|------|-------|-----------|---------|
| Missing Tickets | {N} | {N_ready} | {N_blocked} |
| Incomplete Detail | {N} | {N_ready} | {N_blocked} |
| Vague Specs | {N} | {N_ready} | {N_blocked} |
| Broken Hierarchy | {N} | {N_ready} | {N_blocked} |
| Out of Sync | {N} | {N_ready} | {N_blocked} |

**Current Phase** (from Roadmap): {phase_description}
**Active Work**: {what's in progress}

═══════════════════════════════════════════════════════════

## Priority Gaps

### 🔴 P0 Critical ({count} gaps)

**GAP-001: EPIC-0001.2 Missing Stories**
- **Type**: Missing Tickets
- **Current**: Epic exists, no stories defined
- **Completeness**: 40% (4/10 criteria)
- **Impact**: Blocking INIT-0001 progress (stuck at 33%)
- **Ready**: ✅ Yes (EPIC-0001.1 complete)
- **Effort**: ~3 hours to write 3-4 stories
- **Missing**:
  - Child stories (should be 3-4 based on epic scope)
  - Story point breakdown
  - BDD scenarios per story
  - Task decomposition

**GAP-002: EPIC-0001.3 Missing Stories**
- **Type**: Missing Tickets
- **Current**: Epic exists, no stories defined
- **Completeness**: 40% (4/10 criteria)
- **Impact**: Blocking INIT-0001 completion
- **Ready**: ✅ Yes (EPIC-0001.2 can be parallel)
- **Effort**: ~3 hours to write 3-4 stories
- **Missing**: [similar to GAP-001]

[Continue for all P0 gaps]

### 🟡 P1 High ({count} gaps)

[Same format]

### 🟢 P2 Medium ({count} gaps)

[Collapsed - show just titles unless user requests detail]

### ⚪ P3 Low ({count} gaps)

[Collapsed - show just titles]

═══════════════════════════════════════════════════════════

## Dependency Map

[Show visual tree from agent analysis]

═══════════════════════════════════════════════════════════

## Recommended Work Order

Based on dependencies, readiness, and roadmap alignment:

1. ✅ **GAP-001: EPIC-0001.2 Stories** (~3h)
   - Ready now, blocking INIT-0001
   - Enables real indexing implementation
   - Aligns with Q4 2025 MVP timeline

2. ✅ **GAP-002: EPIC-0001.3 Stories** (~3h)
   - Ready now, blocking INIT-0001
   - Can work in parallel with GAP-001
   - Completes MVP foundation

3. 🔒 **GAP-005: EPIC-0002.1 Detail** (~4h)
   - Blocked until INIT-0001 complete
   - Pre-plan for Q1 2026
   - Low urgency, high value

[Continue for top 5-10]

═══════════════════════════════════════════════════════════

## Roadmap Alignment Check

**Current Focus**: {INIT-XXXX} - {title}
**Timeline**: {dates}

**Aligned Gaps** ({N}): These fit current phase
- {GAP-ID}: {title}
- {GAP-ID}: {title}

**Future Phase Gaps** ({N}): Not urgent but good to plan
- {GAP-ID}: {title} (for Q1 2026)

**Misaligned Gaps** ({N}): May need review
- {GAP-ID}: {title} - {why misaligned}

═══════════════════════════════════════════════════════════

## Next Steps

**Option 1: Work Top Priority**
Start with GAP-001 ({title}) - highest impact, ready now

**Option 2: Batch Similar Gaps**
Work on all {type} gaps together for consistency

**Option 3: Choose Specific Gap**
Select from the list above

**Option 4: Exit**
Review analysis and come back later

═══════════════════════════════════════════════════════════

**Which gap(s) would you like to work on?**

Provide:
- Gap ID (e.g., GAP-001)
- Multiple IDs (e.g., GAP-001,GAP-002)
- "top" (work recommended order)
- "exit" (stop here)

Your choice:
```

**CRITICAL**: Wait for user response. Do NOT start writing tickets until approved.

**Response Handling:**
- **GAP-ID(s)**: Set `WORK_QUEUE = [gap_ids]`, proceed to Step 3
- **"top"**: Set `WORK_QUEUE = [top 3 from recommended order]`, proceed to Step 3
- **"exit"**: Print summary, exit cleanly
- **Other**: Ask again with validation

---

## Step 3: Iterative Ticket Writing Loop

**Only proceed if user specified gaps to work on.**

For each gap in `WORK_QUEUE`:

### 3.1 Present Gap Context

Show the current state and what needs to be done:

```markdown
═══════════════════════════════════════════════════════════

# 📝 Working on: {GAP-ID}

**Gap**: {Title}
**Type**: {gap_type}
**Ticket**: {ticket_id or "N/A - will create"}
**Parent**: {parent_id}
**Effort Estimate**: {hours} hours

---

## Current State

{IF ticket exists}
**Current Ticket Content:**

```
[Show current file content]
```

**Completeness**: {score}% ({N}/{total} criteria met)
{ELSE}
**Status**: Ticket doesn't exist yet - we'll create it
{ENDIF}

---

## What's Missing

{List from gap analysis}

- {Missing item 1}
- {Missing item 2}
- {Missing item 3}

---

## What We'll Do

1. Interactive Q&A to capture requirements
2. Draft the ticket with complete detail
3. Review together and refine
4. Save the ticket file
5. Update parent ticket references

Ready to start? (yes/no)
```

Wait for user confirmation. If "no", ask why and address concerns or skip to next gap.

### 3.2 Interactive Requirement Capture

Launch Task agent for interactive Q&A session:

**Task Agent Prompt:**

```markdown
Conduct interactive requirement capture session for {GAP-ID}: {Title}

**Gap Context:**
- Type: {gap_type}
- Ticket ID: {ticket_id or "NEW"}
- Parent: {parent_id}
- Current State: {from gap analysis}
- Missing Details: {from gap analysis}

**Your Mission:**

Work interactively with the user to gather ALL information needed to write a complete, high-quality ticket.

## Interview Guidelines

### General Principles

1. **Ask Specific Questions**: Never ask "tell me about X" - ask concrete questions
2. **One Question at a Time**: Don't overwhelm with multiple questions
3. **Build Progressively**: Start high-level, drill into details
4. **Reflect Back**: Summarize what you heard, confirm understanding
5. **Capture Exact Words**: When user provides key terms/concepts, use their language
6. **Probe Vague Responses**: If user says "handle X" or "support Y", ask for specifics
7. **Validate Completeness**: Before finishing, review all criteria for ticket type

### Question Templates by Ticket Type

#### For Initiative Interviews:

**Strategic Questions:**
- "What's the core problem this initiative solves?"
- "What does success look like? How would we measure it?"
- "What's the timeline? When should this be complete?"
- "What are the 3-5 key results we must achieve?"

**Scope Questions:**
- "What epics make up this initiative? Can you name them?"
- "For each epic, what's the one-sentence description?"
- "What's explicitly out of scope for this initiative?"

**Dependency Questions:**
- "What must be true before we start this initiative?"
- "What other initiatives or work does this depend on?"
- "What risks could derail this?"

#### For Epic Interviews:

**Overview Questions:**
- "In 2-3 sentences, what does this epic deliver?"
- "Who's the primary user/beneficiary?"
- "What's the key behavior change this enables?"

**BDD Questions:**
- "What's the most important scenario this epic enables?"
- "Walk me through: Given [setup], when [user does X], what should happen?"
- "What are 2-3 edge cases we need to handle?"

**Breakdown Questions:**
- "What are the main stories in this epic? (aim for 3-5)"
- "For each story, what's the user-facing value?"
- "How many story points for each? (Fibonacci: 1,2,3,5,8,13)"

**Technical Questions:**
- "What's the technical approach? Any key technologies?"
- "What are the major technical risks?"
- "Are there any external dependencies (APIs, services)?"

#### For Story Interviews:

**User Story Questions:**
- "As a [who?], I want [what?], so that [why?]"
- "Let's refine: Who specifically is this for?"
- "What's the core action they want to take?"
- "What value do they get from this?"

**Acceptance Criteria Questions:**
- "How will we know this story is complete? List criteria."
- "For each criterion, how would we test it?"
- "What should NOT happen? (negative criteria)"

**BDD Scenario Questions:**
- "Let's write scenarios. First one: Given [what setup?]"
- "When the user does [what action?]"
- "Then what should happen? Be specific about output/state."
- "Any other scenarios? (happy path, error cases, edge cases)"

**Task Breakdown Questions:**
- "What are the implementation steps? (aim for 3-7 tasks)"
- "For each task, what's the deliverable?"
- "How many hours for each task? (2-8 hours max per task)"

**Technical Design Questions:**
- "What files/modules will be created or modified?"
- "What's the data model or key types?"
- "How will this be tested? (unit, integration, e2e)"
- "Are there existing patterns we should follow?"
- "What existing fixtures/helpers can we reuse?"

**Pattern Reuse Questions:**
- "I found fixture `{name}` that does {X}. Can we use that instead of creating new?"
- "There's a similar test in `{file}`. Should we follow the same pattern?"
- "Do we need {proposed abstraction} now, or can we start simpler?"
- "Is this optimization necessary, or should we wait for metrics?"

#### For Task Interviews:

**Implementation Questions:**
- "What are the concrete steps to implement this?"
- "For each step, which file(s) are affected?"
- "What test files will be created/modified?"

**Estimate Questions:**
- "How many hours for this task? (be specific)"
- "What could make this take longer?"
- "Are there unknowns we need to research first?"

**Verification Questions:**
- "How will we verify this task is done?"
- "What command would we run to test it?"
- "What should the output/behavior be?"

### Interview Flow

1. **Introduce**: "I'm going to ask you questions to gather complete requirements for {ticket}."

2. **Start High-Level**: Ask strategic/overview questions first

3. **Drill Down**: Based on answers, ask follow-up questions for details

4. **Probe Vagueness**: If answer contains vague terms:
   - "You mentioned 'handle authentication' - can you be more specific?"
   - "What exactly should happen when..."
   - "Can you give me an example?"

5. **Summarize**: After each section, reflect back:
   - "Let me make sure I understand: [summary]. Is that right?"

6. **Check Completeness**: Before finishing:
   - "Let's review the {initiative|epic|story|task} criteria..."
   - "We have: {list what's captured}"
   - "Still need: {list what's missing}"

7. **Final Confirmation**:
   - "I think I have everything. Let me draft the ticket and show you."

### Output Format

As you gather information, structure it:

```markdown
## Captured Requirements for {TICKET-ID}

### Core Information
- **Objective/Goal**: {from user}
- **Success Criteria**: {from user}
- **Timeline/Effort**: {from user}

{IF Initiative}
### Key Results
1. {result 1}
2. {result 2}

### Epics
- EPIC-{ID}: {title} - {description}
- EPIC-{ID}: {title} - {description}
{ENDIF}

{IF Epic}
### Overview
{paragraph description}

### BDD Scenarios
```gherkin
Scenario: {title}
  Given {context}
  When {action}
  Then {outcome}
```

### Child Stories
- STORY-{ID}: {title} ({points} points) - {description}
- STORY-{ID}: {title} ({points} points) - {description}

### Technical Approach
{technical details}
{ENDIF}

{IF Story}
### User Story
As a {user}
I want {action}
So that {benefit}

### Acceptance Criteria
- [ ] {criterion 1}
- [ ] {criterion 2}

### BDD Scenarios
```gherkin
Scenario: {title}
  Given {context}
  When {action}
  Then {outcome}
```

### Child Tasks
- TASK-{ID}: {title} ({hours}h) - {description}
- TASK-{ID}: {title} ({hours}h) - {description}

### Technical Design
{design details}

### Dependencies
{dependencies}
{ENDIF}

{IF Task}
### Implementation Steps
- [ ] {step 1} - {file path}
- [ ] {step 2} - {file path}

### Estimate
{hours} hours

### Verification
{how to verify complete}

### Test Requirements
{what tests needed}
{ENDIF}

### User's Exact Quotes
{Capture any key phrases user used – preserve their language. If the user's language is unclear or conflicting, seek clarification before recording. Note any clarifications made.}

---

**Ready to draft ticket? (internal decision)**
{Based on completeness criteria for ticket type}
```

## Important Notes

1. **Patient Interviewing**: Take time, don't rush
2. **No Assumptions**: Only write what user tells you
3. **Preserve Language**: Use user's terms, not generic descriptions
4. **Validate Understanding**: Reflect back frequently
5. **Check Criteria**: Ensure all completeness criteria will be met
6. **Note Unknowns**: If user says "I don't know", note it for follow-up

**Conduct the interview now.**
```

**Agent Configuration:**
- Type: general-purpose
- Mode: Interactive (ask questions, wait for responses)
- Output: Captured requirements in structured format

**Monitor Interview:**
- Let agent lead the questions
- User provides answers
- Agent builds up requirements
- Agent signals when ready to draft

### 3.3 Draft Ticket with Task Agent

After requirements captured, launch another Task agent to draft the ticket:

**Task Agent Prompt:**

```markdown
Draft a complete, high-quality ticket for {TICKET-ID} based on captured requirements.

**Ticket Type**: {Initiative | Epic | Story | Task}
**Ticket ID**: {ID or "NEW - assign next sequential"}
**Parent**: {parent_id}

**Captured Requirements:**

{Full output from interview agent}

**Your Mission:**

Write a complete ticket file that:
1. Follows the template from docs/tickets/CLAUDE.md
2. Includes ALL captured information
3. Meets 100% of completeness criteria for ticket type
4. Uses clear, specific language (no vague terms)
5. Has correct file structure and formatting
6. Includes proper parent/child links

## Drafting Guidelines

### File Naming and Path

**Determine Ticket ID:**
{IF new ticket}
- Look at existing tickets in parent directory
- Assign next sequential number
- Example: If STORY-0001.2.1, STORY-0001.2.2 exist, new one is STORY-0001.2.3
{ELSE}
- Use existing ticket ID: {ticket_id}
{ENDIF}

**Determine File Path:**
- Initiative: docs/tickets/INIT-{NNNN}/README.md
- Epic: docs/tickets/INIT-{NNNN}/EPIC-{NNNN}.{E}/README.md
- Story: docs/tickets/INIT-{NNNN}/EPIC-{NNNN}.{E}/STORY-{NNNN}.{E}.{S}/README.md
- Task: docs/tickets/INIT-{NNNN}/EPIC-{NNNN}.{E}/STORY-{NNNN}.{E}.{S}/TASK-{NNNN}.{E}.{S}.{T}.md

### Template Selection

Use the appropriate template from docs/tickets/CLAUDE.md:

{IF Initiative}
```markdown
# INIT-{NNNN}: {Title}

**Timeline**: {timeline}
**Status**: {🔵 Not Started | 🟡 In Progress | ✅ Complete}
**Owner**: {owner}
**Progress**: {progress_bar} {percent}%

## Objective

{Strategic goal paragraph - 3-5 sentences}

## Key Results

- [ ] {Measurable outcome 1}
- [ ] {Measurable outcome 2}
- [ ] {Measurable outcome 3}

## Epics

| ID | Title | Status | Progress | Owner |
|----|-------|--------|----------|-------|
| [EPIC-{NNNN}.1](EPIC-{NNNN}.1/README.md) | {Title} | 🔵 | ░░░░░░░░░░ 0% | - |

## Success Metrics

### Functional Requirements
{from captured requirements}

### Performance Targets
{from captured requirements}

### Quality Gates
{from captured requirements}

## Dependencies

{from captured requirements}

## Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| {risk} | {High|Med|Low} | {High|Med|Low} | {mitigation} |

## Timeline

{breakdown by month/quarter}

## Next Steps

{immediate next actions}

---

**Created**: {date}
**Last Updated**: {date}
```
{ENDIF}

{IF Epic}
```markdown
# EPIC-{NNNN}.{E}: {Title}

**Parent**: [INIT-{NNNN}](../README.md)
**Status**: {🔵 Not Started | 🟡 In Progress | ✅ Complete}
**Story Points**: {total} ({breakdown if in progress})
**Progress**: {progress_bar} {percent}%

## Overview

{2-3 paragraph description of what this epic delivers}

## BDD Scenarios

```gherkin
Scenario: {Key behavior 1}
  Given {context}
  When {action}
  Then {outcome}

Scenario: {Key behavior 2}
  Given {context}
  When {action}
  Then {outcome}
```

## Child Stories

| ID | Title | Status | Points |
|----|-------|--------|--------|
| [STORY-{NNNN}.{E}.1](STORY-{NNNN}.{E}.1/README.md) | {Title} | 🔵 | {points} |

## Technical Approach

{from captured requirements}

## Dependencies

{from captured requirements}

## Deliverables

- [ ] {Deliverable 1}
- [ ] {Deliverable 2}

## Success Criteria

{how we know this epic is complete}

---

**Created**: {date}
**Last Updated**: {date}
```
{ENDIF}

{IF Story}
```markdown
# STORY-{NNNN}.{E}.{S}: {Title}

**Parent**: [EPIC-{NNNN}.{E}](../README.md)
**Status**: {🔵 Not Started | 🟡 In Progress | ✅ Complete}
**Story Points**: {points}
**Progress**: {progress_bar} {percent}%

## User Story

As a {user type}
I want {action/feature}
So that {benefit/value}

## Acceptance Criteria

- [ ] {Testable criterion 1}
- [ ] {Testable criterion 2}
- [ ] {Testable criterion 3}

## BDD Scenarios

```gherkin
Feature: {Feature name}

  Scenario: {Happy path}
    Given {precondition}
    When {action}
    Then {expected outcome}

  Scenario: {Edge case}
    Given {precondition}
    When {action}
    Then {expected outcome}

  Scenario: {Error case}
    Given {precondition}
    When {invalid action}
    Then {error handling}
```

## Child Tasks

| ID | Title | Status | Hours |
|----|-------|--------|-------|
| [TASK-{NNNN}.{E}.{S}.1]({filename}) | {Title} | 🔵 | {hours} |

## Technical Design

### Modules/Files Affected
{from captured requirements}

### Data Model
{from captured requirements}

### Testing Strategy
{from captured requirements}

## Dependencies

{from captured requirements}

## Risks

{from captured requirements if any}

---

**Created**: {date}
**Last Updated**: {date}
```
{ENDIF}

{IF Task}
```markdown
# TASK-{NNNN}.{E}.{S}.{T}: {Title}

**Parent**: [STORY-{NNNN}.{E}.{S}](README.md)
**Status**: {🔵 Not Started | 🟡 In Progress | ✅ Complete}
**Estimated Hours**: {hours}
**Actual Hours**: -

## Implementation Checklist

- [ ] {Step 1} - {file/module}
- [ ] {Step 2} - {file/module}
- [ ] {Step 3} - {file/module}
- [ ] Tests pass
- [ ] Documentation updated

## Pattern Reuse

**Existing Fixtures:**
- `{fixture_name}` ({conftest.py:line}) - {purpose}

**Similar Tests:**
- {test_file.py:lines} - {follow this pattern}

{IF new patterns}
**New Patterns** (justified):
- {pattern}: {why needed}
{ENDIF}

## Test Requirements

{from captured requirements}

## Verification Criteria

{from captured requirements}

## Dependencies

{from captured requirements if any}

---

**Created**: {date}
**Last Updated**: {date}
```
{ENDIF}

## Content Quality Rules

1. **No Vague Terms**: Replace with specifics
   - ❌ "Handle authentication"
   - ✅ "Validate JWT tokens and return 401 for expired tokens"

2. **Concrete Acceptance Criteria**: Must be testable
   - ❌ "System should be fast"
   - ✅ "Search returns results in <2 seconds for 10K files"

3. **Specific BDD Scenarios**: Exact inputs/outputs
   - ❌ "When user searches, Then show results"
   - ✅ "When I search 'auth', Then display ≥3 results with file:line format"

4. **Detailed Steps**: File paths, not vague actions
   - ❌ "Implement the feature"
   - ✅ "Create src/gitctx/auth.py with validate_token() function"

5. **Realistic Estimates**: Based on scope
   - Tasks: 2-8 hours max
   - Stories: 1-13 points (Fibonacci)
   - Epics: Sum of stories

6. **Proper Links**: Use relative paths correctly
   - Parent: ../README.md or ../../README.md
   - Children: STORY-*/README.md or TASK-*.md

7. **Progress Bars**: Use █ and ░ characters
   - 10 chars total: ████░░░░░░ = 40%

## Output Format

```markdown
# 📄 Draft Ticket: {TICKET-ID}

**File Path**: {absolute_path}
**Action**: {Write new file | Update existing file}

---

**TICKET CONTENT:**

```
{Full ticket content using template above}
```

---

**Completeness Check:**

{IF Initiative}
- [ ] Strategic objective clear
- [ ] Key results measurable
- [ ] Timeline defined
- [ ] Child epics listed
- [ ] Success metrics included
- [ ] Risk assessment complete
- [ ] Dependencies documented
- [ ] Progress bar accurate
{ENDIF}

{IF Epic}
- [ ] Overview describes deliverable
- [ ] Parent initiative linked
- [ ] BDD scenarios present (≥1)
- [ ] Child stories listed
- [ ] Story points estimated
- [ ] Stories sum to epic estimate
- [ ] Technical approach described
- [ ] Deliverables checklist included
- [ ] No vague terms
- [ ] Progress bar accurate
{ENDIF}

{IF Story}
- [ ] User story in correct format
- [ ] Parent epic linked
- [ ] Acceptance criteria concrete
- [ ] Child tasks listed
- [ ] BDD scenarios in Gherkin
- [ ] Scenarios cover all criteria
- [ ] Technical design included
- [ ] Story points estimated
- [ ] Tasks sum to estimate
- [ ] Dependencies listed
- [ ] No vague criteria
- [ ] Progress bar accurate
{ENDIF}

{IF Task}
- [ ] Title clear
- [ ] Parent story linked
- [ ] Implementation checklist concrete
- [ ] Hour estimate (2-8h)
- [ ] Steps are specific
- [ ] Test requirements included
- [ ] File paths/modules named
- [ ] Verification criteria defined
{ENDIF}

**Score**: {N}/{total} = {percent}%

{IF score < 100%}
**Issues to Fix Before Saving:**
{list issues}
{ENDIF}
```

## Important Notes

1. **Use User's Language**: Preserve terms from captured requirements
2. **Be Specific**: Every detail should be concrete
3. **Link Correctly**: Verify parent/child paths
4. **Estimate Realistically**: Don't over or under estimate
5. **Check Template**: Follow docs/tickets/CLAUDE.md format exactly
6. **Date Stamps**: Use current date for created/updated

**Draft the ticket now.**
```

**Agent Configuration:**
- Type: general-purpose
- Mode: Research (generating content, not writing files yet)
- Output: Complete ticket draft with file path

Wait for agent to complete draft.

### 3.4 Review Draft with User

⚠️ **MANDATORY STOP POINT**

Present the draft to user for review:

```markdown
═══════════════════════════════════════════════════════════

# 📄 Draft Ticket Review: {TICKET-ID}

**File**: `{file_path}`
**Action**: {Write new file | Update existing file}
**Completeness**: {score}% ({N}/{total} criteria met)

---

## Ticket Content Preview

```markdown
{Show first 50-100 lines of draft}

{if longer}
... ({N} more lines)
{endif}
```

═══════════════════════════════════════════════════════════

## Quality Check

**Strengths**:
- {What's done well}
- {What's complete}

{IF issues}
**Issues Found** ({N}):
- {Issue 1}
- {Issue 2}
{ENDIF}

═══════════════════════════════════════════════════════════

## Review Options

**approve** - Save this ticket as-is
**revise** - Make changes before saving
**rewrite** - Start over with new interview
**skip** - Don't save, move to next gap
**show-full** - Show complete ticket content

Your choice:
```

**CRITICAL**: Wait for user response.

**Response Handling:**

**If "approve":**
- Proceed to 3.5 (save ticket)

**If "revise":**
- Ask: "What needs to change?"
- User describes changes
- Either:
  - Make edits directly (if small changes)
  - Re-run draft agent with revised requirements (if major changes)
- Re-present for review
- Loop until "approve" or "skip"

**If "rewrite":**
- Discard draft
- Go back to 3.2 (interview) with fresh start
- Loop until "approve" or "skip"

**If "skip":**
- Don't save ticket
- Mark gap as skipped
- Continue to next gap in queue

**If "show-full":**
- Display complete ticket content
- Ask for review choice again

### 3.5 Save Ticket File

**Only proceed if user approved draft.**

#### 3.5.1 Determine Action

```python
if ticket_file_exists:
    action = "Edit"
    # Use Edit tool to update existing file
else:
    action = "Write"
    # Use Write tool to create new file
    # May need to create parent directory first
```

#### 3.5.2 Create Directory if Needed

```bash
# Example for new story
# If creating STORY-0001.2.1, need directory:
# docs/tickets/INIT-0001/EPIC-0001.2/STORY-0001.2.1/

{IF new story or epic}
# Check if directory exists
ls docs/tickets/INIT-{NNNN}/EPIC-{NNNN}.{E}/STORY-{NNNN}.{E}.{S}/

{IF doesn't exist}
# Create directory structure
mkdir -p docs/tickets/INIT-{NNNN}/EPIC-{NNNN}.{E}/STORY-{NNNN}.{E}.{S}/
{ENDIF}
{ENDIF}
```

#### 3.5.3 Write/Edit Ticket File

```python
{IF action == "Write"}
# Use Write tool
Write(
    file_path="{absolute_path_to_ticket_file}",
    content="{full_ticket_content_from_draft}"
)
{ELSE}
# Use Edit tool
# Replace entire file content
Edit(
    file_path="{absolute_path_to_ticket_file}",
    old_string="{entire_current_content}",
    new_string="{full_ticket_content_from_draft}"
)
{ENDIF}
```

#### 3.5.4 Verify Save

```bash
# Verify file exists
ls -la {file_path}

# Show file size
wc -l {file_path}
```

Output:
```markdown
✅ Saved: {TICKET-ID}

File: {file_path}
Size: {N} lines
Action: {Created new file | Updated existing file}
```

### 3.6 Update Parent Ticket

**If ticket has parent, update parent to reference new/updated child.**

#### Find Parent File

```python
# Examples:
# If wrote STORY-0001.2.1, parent is EPIC-0001.2/README.md
# If wrote EPIC-0001.2, parent is INIT-0001/README.md
# If wrote TASK-0001.2.1.3, parent is STORY-0001.2.1/README.md
```

#### Read Parent

```python
Read(file_path="{parent_readme_path}")
```

#### Update Parent

Depending on ticket type:

**If added/updated Epic:**
```markdown
# Update initiative's epic table

OLD:
| [EPIC-{NNNN}.{E}](EPIC-{NNNN}.{E}/README.md) | {Old Title} | {Old Status} | {Old Progress} | - |

NEW:
| [EPIC-{NNNN}.{E}](EPIC-{NNNN}.{E}/README.md) | {New Title} | 🔵 Not Started | ░░░░░░░░░░ 0% | - |
```

Or if new epic:
```markdown
OLD:
{Last epic row in table}

NEW:
{Last epic row in table}
| [EPIC-{NNNN}.{NEW}](EPIC-{NNNN}.{NEW}/README.md) | {Title} | 🔵 | ░░░░░░░░░░ 0% | - |
```

**If added/updated Story:**
```markdown
# Update epic's story table

OLD:
{last story row or specific story row}

NEW:
{updated story row or new story row}
```

**If added/updated Task:**
```markdown
# Update story's task table

OLD:
{last task row or specific task row}

NEW:
{updated task row or new task row}
```

#### Save Parent Update

```python
Edit(
    file_path="{parent_readme_path}",
    old_string="{specific section to update}",
    new_string="{updated section}"
)
```

Verify:
```markdown
✅ Updated parent: {PARENT-ID}

File: {parent_path}
Change: Added/updated reference to {TICKET-ID}
```

### 3.7 Mark Gap Complete

Update TodoWrite to mark this gap complete:

```python
TodoWrite(
    todos=[
        {
            "content": "GAP-{ID}: {title}",
            "status": "completed",
            "activeForm": "Completed GAP-{ID}"
        },
        # ... other gaps still pending/in_progress
    ]
)
```

### 3.8 Loop to Next Gap

```markdown
═══════════════════════════════════════════════════════════

✅ Completed: {GAP-ID} - {TICKET-ID}

**Created/Updated**: {file_path}
**Parent Updated**: {parent_path}

{IF more gaps in queue}
---

**Next in queue**: {NEXT-GAP-ID} - {title}

Continue? (yes/no/defer)

- **yes**: Start next gap now
- **no**: Stop here, exit session
- **defer**: Show remaining queue, let me choose

{ELSE}
---

**All selected gaps complete!** 🎉

Proceeding to final summary...
{ENDIF}
```

If user says "yes", loop back to 3.1 for next gap.
If user says "no", go to Step 4 (final summary).
If user says "defer", show queue and let user pick or exit.

---

## Step 4: Final Summary

Print comprehensive summary of session:

```markdown
# ✨ Ticket Writing Session Complete

**Date**: {date}
**Scope**: {full | focused}
{IF focused}
**Focus Area**: {FOCUS_AREA}
{ENDIF}
**Duration**: {start_time} - {end_time}

═══════════════════════════════════════════════════════════

## Summary

**Gaps Addressed**: {N} of {total_in_queue}
**Tickets Created**: {N}
**Tickets Updated**: {N}
**Parent Updates**: {N}

═══════════════════════════════════════════════════════════

## Tickets Created

{FOR each created ticket}
### {TICKET-ID}: {Title}

**File**: `{file_path}`
**Type**: {Initiative | Epic | Story | Task}
**Parent**: {PARENT-ID}
**Completeness**: {score}%
**Status**: 🔵 Not Started (ready for work)

{IF Story or Epic}
**Contains**:
- {N} child {stories | tasks}
- {N} BDD scenarios
- {N} acceptance criteria
{ENDIF}

---
{ENDFOR}

═══════════════════════════════════════════════════════════

## Tickets Updated

{FOR each updated ticket}
### {TICKET-ID}: {Title}

**File**: `{file_path}`
**Changes**: {what was added/updated}
**Completeness**: {old_score}% → {new_score}%

---
{ENDFOR}

═══════════════════════════════════════════════════════════

## Parent Updates

{FOR each parent updated}
- **{PARENT-ID}**: Added/updated reference to {CHILD-ID}
{ENDFOR}

═══════════════════════════════════════════════════════════

## Remaining Gaps

{IF gaps not completed in this session}
**Skipped** ({N}):
- {GAP-ID}: {reason}
- {GAP-ID}: {reason}

**Not Started** ({N}):
- {GAP-ID}: {title} (still in backlog)
- {GAP-ID}: {title} (still in backlog)

Run `/write-next-tickets` again to continue.
{ELSE}
**All identified gaps addressed!** ✅

The ticket hierarchy is now complete and ready for work.
{ENDIF}

═══════════════════════════════════════════════════════════

## Next Steps

{IF created stories}
### Start Implementation

New stories are ready for work:
1. Review stories with `/review-story`
2. Start first task with `/start-next-task`
3. Follow BDD/TDD workflow

{ENDIF}

{IF created epics without stories}
### Detail Epics

New epics need stories:
1. Run `/write-next-tickets focused` on each epic
2. Break down into stories
3. Define BDD scenarios

{ENDIF}

{IF remaining gaps}
### Continue Planning

Still have {N} gaps to address:
1. Run `/write-next-tickets` again
2. Work on {highest_priority_remaining_gap}
3. Or focus on specific area with `focused` mode

{ENDIF}

{IF tickets aligned with current phase}
### Current Phase Work

These new tickets align with current roadmap phase:
- {TICKET-ID}: {title} (ready now)
- {TICKET-ID}: {title} (ready now)

Recommended: Start with {TICKET-ID}

{ENDIF}

═══════════════════════════════════════════════════════════

## Quality Metrics

**Completeness Scores**:
- Average: {avg_score}%
- Lowest: {min_score}% ({TICKET-ID})
- Highest: {max_score}% ({TICKET-ID})

**BDD Coverage**:
- Stories with scenarios: {N}/{total_stories} ({percent}%)
- Total scenarios written: {N}

**Estimation**:
- Total story points added: {N}
- Total task hours estimated: {N}

═══════════════════════════════════════════════════════════

**Session complete! ✨**

Your ticket hierarchy is more complete and ready for development.
```

**Exit successfully.**

---

## Error Recovery

### Error: No Gaps Found

```markdown
✅ Ticket Hierarchy Complete!

**Analysis**: Scanned {N} tickets across {N} initiatives.

**Findings**:
- All initiatives have detailed epics
- All epics have complete stories
- All stories have defined tasks
- All BDD scenarios present
- No vague specifications found

**Quality Score**: {avg}% average completeness

**Your ticket hierarchy is in excellent shape!** 🎉

Next steps:
- Review current work with `/review-story`
- Start next task with `/start-next-task`
- Monitor progress in ROADMAP.md
```

Exit successfully.

### Error: User Exits During Interview

```markdown
⚠️ Interview Incomplete

**Gap**: {GAP-ID}
**Progress**: Captured {N} of {total} required details
**Saved**: No (interview not complete)

**Partial Requirements Captured**:
{show what was captured}

You can:
- Run `/write-next-tickets focused` on {GAP-ID} to resume
- Start fresh with different gap
- Review what was captured above and continue manually

Session paused. No files were modified.
```

Exit cleanly.

### Error: Draft Quality Too Low

```markdown
⚠️ Draft Quality Below Threshold

**Ticket**: {TICKET-ID}
**Completeness**: {score}% (minimum: 80%)

**Missing**:
- {Missing item 1}
- {Missing item 2}

**Options**:
1. **revise**: Go back and fill in missing details
2. **save-anyway**: Save as-is (not recommended)
3. **skip**: Don't save, move to next gap

Choice:
```

If user chooses "save-anyway", warn:
```markdown
⚠️ Warning: Saving incomplete ticket

This ticket will need more detail before it's ready for work.
You'll need to update it later with:
{list missing items}

Confirm save anyway? (yes/no)
```

Only save if user confirms "yes".

### Error: Parent Ticket Not Found

```markdown
✗ Parent ticket not found

**Ticket to Create**: {TICKET-ID}
**Expected Parent**: {PARENT-ID}
**Parent Path**: {path}
**Status**: File does not exist

**This is a hierarchy error.**

You must create parent ticket first:
1. Run `/write-next-tickets focused` on {PARENT-ID}
2. Create/update parent ticket
3. Then retry creating {TICKET-ID}

Or:
1. Check if parent ID is correct
2. Update the hierarchy structure
3. Retry

Session paused. No files were modified for this gap.
```

Skip to next gap or exit.

---

## Implementation Notes

### Agent Coordination

**Agent 1: Discovery (Step 1)**
- Type: general-purpose
- Mode: Research (read-only)
- Input: Ticket hierarchy, roadmap, CLAUDE.md files
- Output: Gap analysis report
- Duration: 2-5 minutes depending on scope

**Agent 2: Interview (Step 3.2)**
- Type: general-purpose
- Mode: Interactive (ask questions, wait for responses)
- Input: Gap context, ticket templates
- Output: Captured requirements
- Duration: 5-30 minutes depending on ticket complexity

**Agent 3: Drafting (Step 3.3)**
- Type: general-purpose
- Mode: Research (generating content)
- Input: Captured requirements, templates
- Output: Complete ticket draft
- Duration: 1-2 minutes

### State Tracking

Use TodoWrite throughout:
```python
# After Step 2 (present gaps)
todos = [
    {"content": f"GAP-{id}: {title}", "status": "pending", "activeForm": f"Working on GAP-{id}"}
    for id, title in gaps_to_work_on
]

# During Step 3 (processing)
# Mark current as in_progress, others as pending
# Mark completed as completed

# After Step 4 (summary)
# Clear all todos (session complete)
```

### File Operations

**Creating Directories:**
```bash
mkdir -p docs/tickets/INIT-{N}/EPIC-{N}.{E}/STORY-{N}.{E}.{S}/
```

**Writing New Tickets:**
```python
Write(
    file_path="/absolute/path/to/ticket.md",
    content="# TICKET-ID: Title\n\n..."
)
```

**Updating Existing Tickets:**
```python
# Read first
content = Read(file_path="...")

# Edit with specific OLD/NEW
Edit(
    file_path="...",
    old_string="exact text to replace",
    new_string="new text"
)
```

### Quality Validation

Before saving any ticket, verify:
- Completeness score ≥80% (or get user confirmation)
- No vague terms (TBD, handle, support, etc.)
- All acceptance criteria testable
- BDD scenarios use proper Gherkin format
- Parent/child links are correct
- Estimates are realistic
- File path is correct

### Interview Best Practices

**Good Questions:**
- "What's the core problem this solves?"
- "How will we test this criterion?"
- "What should happen when the user clicks submit?"

**Bad Questions:**
- "Tell me about this feature." (too vague)
- "What do you want?" (too open-ended)
- "Anything else?" (lazy)

**Probing Vagueness:**
- User: "It should handle errors"
- Agent: "What specific errors? What should happen for each error type?"

**Building Progressively:**
1. High-level: What/why
2. Mid-level: Who/when
3. Detail: How/specifics
4. Verify: Test cases/edge cases

### Markdown Formatting

**Progress Bars** (10 chars):
- 0%: ░░░░░░░░░░
- 50%: █████░░░░░
- 100%: ██████████

**Status Indicators**:
- 🔵 Not Started
- 🟡 In Progress
- ✅ Complete
- 🔴 Blocked

**Tables**: Use pipe format with header separator

**Code Blocks**: Use triple backticks with language

---

## Success Criteria

- ✅ Discovers all gaps in ticket hierarchy
- ✅ Accurately scores ticket completeness
- ✅ Prioritizes gaps correctly by dependency and readiness
- ✅ Conducts thorough interview with specific questions
- ✅ Captures all required information before drafting
- ✅ Generates tickets meeting 100% of criteria
- ✅ Creates proper file structure and paths
- ✅ Updates parent tickets with child references
- ✅ Handles errors gracefully
- ✅ Works incrementally (can stop and resume)
- ✅ Produces actionable, concrete tickets ready for implementation

---

## Begin Execution

Follow the workflow steps 0-4 in order. Stop at approval gates and wait for user input. Track progress with TodoWrite. Report clearly and concisely.

**Start with Step 0: Gather User Intent**
