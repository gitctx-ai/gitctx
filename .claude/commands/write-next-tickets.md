---
description: Find and write next incomplete tickets through iterative requirement capture
allowed-tools: "*"
---

# Write Next Tickets: Intelligent Ticket Discovery and Creation

You are tasked with discovering incomplete or missing tickets in the project hierarchy and working interactively with the user to write/update them with complete, actionable detail.

## Overall Workflow

1. **Gather User Intent** - Ask if full discovery or specific ticket focus
2. **Discovery & Gap Analysis** - Invoke specialized agents for comprehensive analysis
3. **Present Gap Report** - Show findings and get approval on what to work on
4. **Iterative Ticket Writing Loop** - For each ticket to write/update:
   - Present context and current state
   - Interactive Q&A via requirements-interviewer agent
   - Validate quality via specification-quality-checker agent
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

Launch specialized agents in parallel for comprehensive analysis.

### 1.1 Invoke ticket-analyzer Agent

Use Task tool (general-purpose) with ticket-analyzer agent:

```markdown
You are the ticket-analyzer specialized agent. Analyze the ticket hierarchy to identify gaps.

**Analysis Type**: hierarchy-gaps
**Target**: {SCOPE == "full" ? "all" : FOCUS_AREA}
**Scope**: {SCOPE == "full" ? "full-hierarchy" : "epic-and-stories" or "story-and-tasks" depending on FOCUS_AREA}
**Mode**: pre-work

## Your Mission

Analyze docs/tickets/ hierarchy and return gap analysis:

1. Read all relevant ticket files (INIT, EPIC, STORY, TASK)
2. Score completeness against criteria for each ticket type
3. Identify missing tickets, incomplete detail, vague specs
4. Classify gaps by type (missing, incomplete, vague, broken hierarchy, out of sync)
5. Assess readiness (blocked vs ready to write)
6. Prioritize gaps (P0-P3 based on urgency, readiness, impact)

**Output Format**: Structured markdown with:
- Executive summary (ticket counts, gap counts)
- Gap details by priority with completeness scores
- Dependency map showing hierarchy
- Recommended work order

Execute the analysis now.
```

Store output as `TICKET_ANALYSIS`.

### 1.2 Invoke pattern-discovery Agent

Use Task tool (general-purpose) with pattern-discovery agent in parallel:

```markdown
You are the pattern-discovery specialized agent. Survey the codebase for reusable patterns.

**Discovery Type**: full-survey
**Domain**: all
**Context**: Planning to write tickets for {FOCUS_AREA if focused, else "full project"}

## Your Mission

Survey the codebase and return pattern inventory:

1. Read ALL conftest.py files (root, unit, e2e) - catalog fixtures
2. Survey test patterns (AAA, parametrization, mocking, step definitions)
3. Scan src/gitctx/ modules (utilities, helpers, abstractions, protocols)
4. Review nested CLAUDE.md files for anti-patterns
5. Calculate pattern reuse opportunities

**Output Format**: Structured markdown with:
- Test fixtures inventory (name, file:line, purpose, composition)
- Test patterns catalog (AAA, parametrization, factories)
- Source patterns (utils, helpers, abstractions)
- Documented anti-patterns from CLAUDE.md files
- Pattern reuse score (0-10)

Execute the survey now.
```

Store output as `PATTERN_INVENTORY`.

### 1.3 Invoke design-guardian Agent

Use Task tool (general-purpose) with design-guardian agent in parallel:

```markdown
You are the design-guardian specialized agent. Check for overengineering in the ticket hierarchy.

**Review Type**: epic-review (or story-review if focused on specific story)
**Target**: {FOCUS_AREA if focused, else "all incomplete tickets"}
**Context**: Reviewing incomplete/draft tickets for unnecessary complexity

## Your Mission

Review incomplete tickets and flag overengineering:

1. Detect unnecessary abstraction (single impl, no roadmap evidence)
2. Flag premature optimization (no metrics, no user requirement)
3. Identify unnecessary caching (small files, CLI tools, rarely accessed)
4. Detect scope creep beyond acceptance criteria
5. Distinguish valid complexity (security, type safety) from overengineering

**Output Format**: Structured markdown with:
- Complexity flags by ticket (severity: low/med/high)
- Simpler alternatives
- Justification requirements
- Overengineering score per ticket (0-10, lower is simpler)

Execute the review now.
```

Store output as `COMPLEXITY_ANALYSIS`.

### 1.4 Aggregate Agent Results

Wait for all three agents to complete, then combine their outputs:

```markdown
# 📊 Combined Gap Analysis

## From ticket-analyzer:
{TICKET_ANALYSIS}

## From pattern-discovery:
{PATTERN_INVENTORY}

## From design-guardian:
{COMPLEXITY_ANALYSIS}

---

**Analysis complete. Proceeding to present findings...**
```

---

## Step 2: Present Gap Report

⚠️ **MANDATORY STOP POINT**

Present combined findings to user for approval.

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

{From TICKET_ANALYSIS - hierarchy overview}

**Gaps Found**: {total_gaps}

| Type | Count | Ready Now | Blocked |
|------|-------|-----------|---------|
{From TICKET_ANALYSIS - gap type table}

**Pattern Reuse Score**: {from PATTERN_INVENTORY}/10
**Average Overengineering Risk**: {from COMPLEXITY_ANALYSIS}

═══════════════════════════════════════════════════════════

## Priority Gaps

{From TICKET_ANALYSIS - show P0, P1, P2, P3 gaps}

For each gap, also show:
- **Pattern Opportunities**: {from PATTERN_INVENTORY - relevant fixtures/patterns}
- **Complexity Flags**: {from COMPLEXITY_ANALYSIS if any}

═══════════════════════════════════════════════════════════

## Dependency Map

{From TICKET_ANALYSIS - visual tree}

═══════════════════════════════════════════════════════════

## Recommended Work Order

{From TICKET_ANALYSIS - prioritized list with reasoning}

═══════════════════════════════════════════════════════════

## Reusable Patterns Available

{From PATTERN_INVENTORY - summary of key fixtures/patterns to reuse}

═══════════════════════════════════════════════════════════

## Next Steps

**Option 1: Work Top Priority**
Start with {top_gap_id} - highest impact, ready now

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
{Show current file content from TICKET_ANALYSIS}
```

**Completeness**: {score}% ({N}/{total} criteria met)
{ELSE}
**Status**: Ticket doesn't exist yet - we'll create it
{ENDIF}

---

## What's Missing

{From TICKET_ANALYSIS - missing details list}

---

## Pattern Reuse Opportunities

{From PATTERN_INVENTORY - relevant fixtures/patterns for this gap}

**Avoid Overengineering**:
{From COMPLEXITY_ANALYSIS - any warnings for this gap}

---

## What We'll Do

1. Interactive Q&A to capture requirements (using requirements-interviewer agent)
2. Validate specification quality (using specification-quality-checker agent)
3. Draft the ticket with complete detail
4. Review together and refine
5. Save the ticket file
6. Update parent ticket references

Ready to start? (yes/no)
```

Wait for user confirmation. If "no", ask why and address concerns or skip to next gap.

### 3.2 Interactive Requirement Capture

Launch requirements-interviewer agent for Q&A session:

**Task Agent Prompt:**

```markdown
You are the requirements-interviewer specialized agent. Conduct an interactive interview.

**Interview Type**: {initiative | epic | story | task - based on gap type}
**Ticket ID**: {ticket_id or "NEW"}
**Parent Context**: {parent_id and description}
**Current State**: {from TICKET_ANALYSIS}
**Gap Analysis**: {specific gap details from TICKET_ANALYSIS}
**Pattern Context**: {relevant patterns from PATTERN_INVENTORY}
**Missing Details**: {from TICKET_ANALYSIS}
**Interview Goal**: 95% completeness

## Your Mission

Work interactively with the user to gather ALL information needed for a complete ticket.

Follow your documented interview guidelines:
1. Ask specific, focused questions (one at a time)
2. Build progressively (high-level → details)
3. Probe vague responses until concrete
4. Reflect understanding back to user
5. Capture user's exact language/terminology
6. Challenge any overengineering (reference patterns from pattern-discovery)
7. Validate completeness against criteria before finishing

**Pattern Reuse Questions** (important):
{For each relevant pattern from PATTERN_INVENTORY, ask:}
- "I found fixture `{name}` that does {purpose}. Can we use that?"
- "There's a similar test at {file:line}. Should we follow that pattern?"

**Anti-Overengineering Questions** (if COMPLEXITY_ANALYSIS flagged risks):
- "Do we need {proposed complexity} now, or can we start simpler?"
- "Is this optimization necessary before we have metrics?"

**Output Format**: Captured requirements in structured markdown:

```markdown
## Captured Requirements for {TICKET-ID}

{Follow your agent specification output format}

### User's Exact Quotes
{Preserve user's language}

### Completeness Analysis
Score: {X}% vs target 95%
{If <95%, continue interviewing}
```

Conduct the interview now. Be patient, thorough, and specific.
```

**Monitor Interview:**
- Agent asks questions
- User provides answers
- Agent builds requirements
- Agent validates completeness
- Agent signals when ready (≥95% complete)

Store output as `CAPTURED_REQUIREMENTS`.

### 3.3 Validate Specification Quality

Before drafting, validate the captured requirements for clarity:

**Task Agent Prompt:**

```markdown
You are the specification-quality-checker specialized agent. Validate requirement clarity.

**Check Type**: full-ticket
**Target**: {TICKET-ID for gap}
**Strictness**: strict

**Content to Check**:
{CAPTURED_REQUIREMENTS from interview}

## Your Mission

Analyze the captured requirements for vague/ambiguous language:

1. Detect vague terms (handle, support, manage, simple, basic, etc.)
2. Find missing details (TBD, etc., as needed)
3. Identify implicit assumptions (obviously, clearly, simply)
4. Flag unquantified requirements (fast, efficient, user-friendly)
5. Check for missing edge cases
6. Verify error handling specifications
7. Score agent-executability (can autonomous agent implement this?)

**Output Format**: Markdown report with:
- Ambiguity score (0-100%, higher is clearer)
- List of vague terms with locations and concrete replacements
- Missing quantifications
- Agent-executability score (0-100%)
- Required improvements to reach 95%+ clarity

Target: 95%+ ambiguity score before proceeding to draft.

Execute the check now.
```

Store output as `QUALITY_CHECK`.

**If quality score < 95%:**
- Show issues to user
- Ask: "Would you like to clarify these issues now, or proceed with draft anyway?"
- If clarify: Go back to 3.2 with specific missing details
- If proceed: Continue to 3.4 with warning

**If quality score ≥ 95%:**
- Proceed to 3.4

### 3.4 Draft Ticket

With validated requirements, draft the complete ticket:

```markdown
# 📄 Drafting Ticket: {TICKET-ID}

Using captured requirements (quality score: {QUALITY_CHECK score}%)...

**Determining file path and ID...**
{IF new ticket}
- Analyzing parent directory for next sequential ID
- File will be: {determined_path}
{ELSE}
- Updating existing ticket: {existing_path}
{ENDIF}

**Applying template from docs/tickets/CLAUDE.md...**

**Incorporating pattern reuse recommendations...**
{From PATTERN_INVENTORY - specific fixtures/patterns to reference}

**Ensuring specification clarity...**
{Using concrete language from QUALITY_CHECK}

---

**DRAFT COMPLETE**
```

Generate the full ticket content following the templates from the original command (lines 1107-1346), but incorporating:
- All details from CAPTURED_REQUIREMENTS
- Concrete language (no vague terms from QUALITY_CHECK)
- Pattern reuse references from PATTERN_INVENTORY
- Proper parent/child links
- Current date stamps

Store as `TICKET_DRAFT`.

### 3.5 Review Draft with User

⚠️ **MANDATORY STOP POINT**

Present the draft:

```markdown
═══════════════════════════════════════════════════════════

# 📄 Draft Ticket Review: {TICKET-ID}

**File**: `{file_path}`
**Action**: {Write new file | Update existing file}
**Completeness**: {score}% (all criteria met)
**Quality Score**: {from QUALITY_CHECK}%

---

## Ticket Content Preview

```markdown
{Show first 50-100 lines of TICKET_DRAFT}

{if longer}
... ({N} more lines)
{endif}
```

═══════════════════════════════════════════════════════════

## Quality Check

**Strengths**:
- All {initiative|epic|story|task} criteria met
- Specification clarity: {QUALITY_CHECK score}%
- Pattern reuse: {N} existing fixtures/patterns referenced
- No overengineering flags

{IF issues from QUALITY_CHECK}
**Remaining Clarity Issues** ({N}):
{List from QUALITY_CHECK}
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
- Proceed to 3.6 (save ticket)

**If "revise":**
- Ask: "What needs to change?"
- User describes changes
- Make edits directly (Edit tool) for small changes
- Re-run requirements-interviewer for major changes
- Re-validate with specification-quality-checker
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
- Display complete TICKET_DRAFT
- Ask for review choice again

### 3.6 Save Ticket File

**Only proceed if user approved draft.**

#### 3.6.1 Create Directory if Needed

```bash
{IF new story or epic}
# Check if directory exists
ls {parent_directory_path}

{IF doesn't exist}
# Create directory structure
mkdir -p {full_directory_path}
{ENDIF}
{ENDIF}
```

#### 3.6.2 Write/Edit Ticket File

```python
{IF new ticket}
# Use Write tool
Write(
    file_path="{absolute_path_to_ticket_file}",
    content="{TICKET_DRAFT}"
)
{ELSE}
# Use Edit tool - replace entire file
Read existing file first, then:
Edit(
    file_path="{absolute_path_to_ticket_file}",
    old_string="{entire_current_content}",
    new_string="{TICKET_DRAFT}"
)
{ENDIF}
```

#### 3.6.3 Verify Save

```bash
# Verify file exists and show size
ls -la {file_path}
wc -l {file_path}
```

Output:
```markdown
✅ Saved: {TICKET-ID}

File: {file_path}
Size: {N} lines
Action: {Created new file | Updated existing file}
```

### 3.7 Update Parent Ticket

**If ticket has parent, update parent to reference new/updated child.**

Follow the parent update logic from original command (lines 1638-1716):
- Read parent README
- Update appropriate table (epics, stories, or tasks)
- Use Edit tool with specific OLD/NEW
- Verify parent update

Output:
```markdown
✅ Updated parent: {PARENT-ID}

File: {parent_path}
Change: Added/updated reference to {TICKET-ID}
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

{For each created ticket - show summary from original command format}

═══════════════════════════════════════════════════════════

## Quality Metrics

**Completeness Scores**:
- Average: {avg_score}%
- Lowest: {min_score}% ({TICKET-ID})
- Highest: {max_score}% ({TICKET-ID})

**Specification Quality**:
- Average ambiguity score: {avg from QUALITY_CHECK}%
- All tickets: ≥95% clarity ✅

**Pattern Reuse**:
- Fixtures reused: {N}
- New patterns justified: {N}
- Overengineering flags avoided: {N}

═══════════════════════════════════════════════════════════

## Next Steps

{Follow next steps logic from original command based on what was created}

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

**Analysis**: {from TICKET_ANALYSIS}

Your ticket hierarchy is in excellent shape! 🎉

Next steps:
- Review current work with `/review-story`
- Start next task with `/start-next-task`
```

Exit successfully.

### Error: User Exits During Interview

```markdown
⚠️ Interview Incomplete

**Gap**: {GAP-ID}
**Progress**: {from requirements-interviewer - what was captured}

**Partial Requirements Captured**:
{show CAPTURED_REQUIREMENTS if any}

You can run `/write-next-tickets focused` on {GAP-ID} to resume.

Session paused. No files were modified.
```

Exit cleanly.

### Error: Quality Score Too Low

If QUALITY_CHECK returns <80% and user chose "proceed anyway":

```markdown
⚠️ Warning: Specification quality below recommended threshold

**Quality Score**: {score}% (recommended: ≥95%)
**Issues**:
{from QUALITY_CHECK}

This ticket may need refinement before implementation.

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

You must create parent ticket first or check hierarchy structure.

Session paused for this gap. No files modified.
```

Skip to next gap or exit.

---

## Success Criteria

- ✅ Discovers all gaps using ticket-analyzer agent
- ✅ Identifies pattern reuse opportunities via pattern-discovery agent
- ✅ Detects overengineering via design-guardian agent
- ✅ Conducts thorough interview via requirements-interviewer agent
- ✅ Validates specification quality via specification-quality-checker agent
- ✅ Generates tickets meeting 100% of criteria
- ✅ Creates proper file structure and paths
- ✅ Updates parent tickets with child references
- ✅ Handles errors gracefully
- ✅ Produces actionable, concrete tickets ready for implementation

---

## Agent Coordination Summary

This command uses 5 specialized agents:

1. **ticket-analyzer** (Step 1.1): Hierarchy scanning, gap identification, completeness scoring
2. **pattern-discovery** (Step 1.2): Codebase pattern survey, fixture inventory
3. **design-guardian** (Step 1.3): Anti-overengineering detection
4. **requirements-interviewer** (Step 3.2): Interactive requirement capture
5. **specification-quality-checker** (Step 3.3): Ambiguity detection, clarity validation

**Context Reduction**: ~73% (2,187 lines → ~590 lines)

---

## Begin Execution

Follow the workflow steps 0-4 in order. Stop at approval gates and wait for user input. Track progress with TodoWrite. Report clearly and concisely.

**Start with Step 0: Gather User Intent**
