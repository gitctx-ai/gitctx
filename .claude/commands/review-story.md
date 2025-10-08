---
description: Comprehensive story review - quality validation with optional file edits
allowed-tools: "*"
---

# Story Review: Quality Validation + Ticket Synchronization

You are tasked with performing a comprehensive review of a story with dual capabilities:

1. **Quality Validation** (always): Check story completeness, coherence, alignment with roadmap
2. **Ticket Sync** (optional, in-progress only): Update tickets to match git reality

## Overall Workflow

1. **Gather User Context** - Ask if standard or focused review
2. **Verify Story Branch & Detect Mode** - Check branch, count commits
3. **Deep Analysis** - Invoke specialized agents for quality + git state analysis
4. **Present Combined Report** - Show quality score + issues + proposed edits
5. **Get User Approval** ⚠️ **REQUIRED** - Present all edits and wait for approval
6. **Execute Edits** - Apply approved changes to ticket files
7. **Print Final Report** - Show improvements and next steps

---

## Step 0: Gather User Context

⚠️ **INITIAL PROMPT**

Before starting the review, ask the user what type of review they want:

```markdown
# 📋 Story Review Setup

You're about to review the story on this branch.

**Review Options:**

1. **standard** - Complete quality validation + ticket sync
   - Checks all quality categories (completeness, hierarchy, roadmap alignment, etc.)
   - Validates ticket accuracy vs git commits (if in-progress)
   - Comprehensive but no specific focus

2. **focused** - Targeted review with your specific context
   - Same checks as standard, but prioritizes your concerns
   - You provide context about what to focus on
   - Agent highlights findings related to your focus areas

**Which type of review?** (standard/focused)
```

Wait for user response.

**If "standard":**
- Set `REVIEW_TYPE = "standard"`
- Set `USER_CONTEXT = ""`
- Proceed to Step 1

**If "focused":**
- Set `REVIEW_TYPE = "focused"`
- Ask follow-up:
  ```markdown
  **What should this review focus on?**

  Examples:
  - "Check if BDD scenarios match acceptance criteria"
  - "Validate task estimates are realistic"
  - "Ensure technical design is complete"
  - "Review new tasks added during implementation"

  Your focus (or press Enter for standard review):
  ```

  Wait for user input.
  - If user provides text: Set `USER_CONTEXT = <their input>`
  - If user presses Enter (empty): Treat as standard review
  - Proceed to Step 1

**If neither:**
- Ask again with validation: "Please choose 'standard' or 'focused'"

---

## Step 1: Verify Story Branch & Detect Mode

Check that we're on a story branch and determine mode:

```bash
git branch --show-current
```

**Validation:**
- Branch name must match pattern `STORY-NNNN.N.N` or `plan/STORY-NNNN.N.N` (e.g., STORY-0001.1.2 or plan/STORY-0001.1.2)
- If NOT on a story branch:
  - Ask user: "Not on a story branch. Current branch: [BRANCH]. Would you like to:"
    1. Create a new story branch (provide story ID)
    2. Switch to existing story branch (list available)
    3. Exit
  - Wait for user decision before proceeding

**Extract Story Info:**

From branch `STORY-0001.1.2`:
- Story ID: `STORY-0001.1.2`
- Epic ID: `EPIC-0001.1` (first two numbers)
- Initiative ID: `INIT-0001` (first number)

**Construct paths:**
- Story dir: `docs/tickets/INIT-0001/EPIC-0001.1/STORY-0001.1.2/`
- Story README: `docs/tickets/INIT-0001/EPIC-0001.1/STORY-0001.1.2/README.md`
- Task pattern: `docs/tickets/INIT-0001/EPIC-0001.1/STORY-0001.1.2/TASK-*.md`
- Epic README: `docs/tickets/INIT-0001/EPIC-0001.1/README.md`
- Initiative README: `docs/tickets/INIT-0001/README.md`

**Detect Mode (pre-work vs in-progress):**

```bash
# Count commits on this branch
git rev-list --count main..HEAD
```

- If count == 0: `MODE = "pre-work"` (no commits yet, planning only)
- If count > 0: `MODE = "in-progress"` (has commits, can sync tickets)

Output:
```markdown
📋 Story Review: {STORY_ID}

**Mode**: {pre-work | in-progress}
{IF in-progress}
**Commits**: {count} commits on branch
{ENDIF}
**Review Type**: {standard | focused}
{IF focused}
**Focus**: {USER_CONTEXT}
{ENDIF}

Starting analysis...
```

---

## Step 2: Deep Analysis with Specialized Agents

Launch specialized agents in parallel for comprehensive analysis.

### 2.1 Invoke ticket-analyzer Agent

Use Task tool (general-purpose) with ticket-analyzer agent:

```markdown
You are the ticket-analyzer specialized agent. Analyze story and task quality.

**Analysis Type**: story-deep
**Target**: {STORY_ID from branch}
**Scope**: story-and-tasks
**Mode**: {pre-work | in-progress from commit count}

{IF REVIEW_TYPE == "focused"}
**Focus areas**: {USER_CONTEXT}
{ENDIF}

## Your Mission

Perform deep analysis of the story and all its tasks:

1. Score story completeness (14 criteria)
2. Score each task completeness (10 criteria per task)
3. Validate story-task alignment
4. Check parent epic goals alignment
5. Compare to sibling stories for consistency
6. Validate progress accuracy
7. Check status consistency

{IF focused}
Prioritize findings related to: {USER_CONTEXT}
{ENDIF}

**Output Format**: Structured markdown with:
- Story completeness score and breakdown
- Task completeness scores (each task)
- Issues found (priority, location, fix)
- Hierarchy validation results
- Progress accuracy analysis
- Recommendations

Execute the analysis now.
```

Store output as `TICKET_QUALITY`.

### 2.2 Invoke specification-quality-checker Agent

Use Task tool (general-purpose) with specification-quality-checker agent in parallel:

```markdown
You are the specification-quality-checker specialized agent. Validate specification clarity.

**Check Type**: full-ticket
**Target**: {STORY_ID}
**Strictness**: strict

**Content to Check**:
{Story README.md content}
{All TASK-*.md content}

## Your Mission

Analyze the story and task specifications for vague/ambiguous language:

1. Detect vague terms in acceptance criteria (handle, support, manage, etc.)
2. Find missing details in technical design (TBD, etc., as needed)
3. Identify implicit assumptions (obviously, clearly, simply)
4. Flag unquantified requirements (fast, efficient, user-friendly)
5. Check BDD scenarios for specificity
6. Verify task steps are concrete (not "implement X")
7. Score agent-executability (can autonomous agent implement this?)

**Output Format**: Markdown report with:
- Ambiguity score per ticket (0-100%, higher is clearer)
- List of vague terms with locations and concrete replacements
- Missing quantifications
- Agent-executability score
- Improvements needed to reach 95%+ clarity

Execute the check now.
```

Store output as `SPECIFICATION_QUALITY`.

### 2.3 Invoke git-state-analyzer Agent (if in-progress)

**Only if MODE == "in-progress"** (commit count > 0):

Use Task tool (general-purpose) with git-state-analyzer agent in parallel:

```markdown
You are the git-state-analyzer specialized agent. Analyze git state and compare to tickets.

**Analysis Type**: ticket-drift
**Branch**: {current branch}
**Ticket Context**: {STORY_ID and path}
**Include uncommitted**: true

## Your Mission

Analyze git commits and file changes, compare to ticket documentation:

1. Parse git commit history (`git log main..HEAD`)
2. Analyze file changes (`git diff main...HEAD --stat`)
3. Extract commit metadata (message, files, author, date)
4. Compare task statuses to commit evidence
5. Detect ticket drift (status mismatch, undocumented changes)
6. Validate progress percentages against reality
7. Identify uncommitted work

**Output Format**: Markdown report with:
- Git activity summary (commits, files, lines changed)
- Task status validation table (ticket vs git)
- Drift items with OLD/NEW proposed fixes
- Progress accuracy analysis
- Uncommitted changes summary

Execute the analysis now.
```

Store output as `GIT_STATE`.

**If MODE == "pre-work":**
- Skip git-state-analyzer
- Set `GIT_STATE = null`

### 2.4 Invoke design-guardian Agent

Use Task tool (general-purpose) with design-guardian agent in parallel:

```markdown
You are the design-guardian specialized agent. Check for overengineering in the story.

**Review Type**: story-review
**Target**: {STORY_ID}
**Context**: {Story user story and description}

**Proposed Work**:
{Story technical design}
{All task checklists}

## Your Mission

Review the story and tasks for unnecessary complexity:

1. Detect premature abstraction (single impl, no roadmap evidence)
2. Flag premature optimization (no metrics showing need)
3. Identify unnecessary caching (small data, CLI tool, rarely accessed)
4. Detect scope creep beyond acceptance criteria
5. Distinguish valid complexity (security, testing, validation) from overengineering

**Output Format**: Markdown with:
- Complexity flags (severity, what, why, simpler alternative)
- Per-task overengineering scores (0-10, lower is simpler)
- Valid complexity justifications
- Recommendations to simplify

Execute the review now.
```

Store output as `COMPLEXITY_ANALYSIS`.

### 2.5 Aggregate Agent Results

Wait for all agents to complete, then synthesize:

```markdown
# 📊 Story Review Analysis: {STORY_ID}

## Quality Assessment
{From TICKET_QUALITY}

**Story Completeness**: {score}%
**Average Task Completeness**: {avg_score}%

## Specification Clarity
{From SPECIFICATION_QUALITY}

**Story Ambiguity Score**: {score}% (target: ≥95%)
**Average Task Clarity**: {avg_score}%

{IF MODE == "in-progress"}
## Ticket Sync Status
{From GIT_STATE}

**Commits Analyzed**: {count}
**Ticket Drift Items**: {count}
**Progress Accuracy**: {analysis}
{ENDIF}

## Complexity Check
{From COMPLEXITY_ANALYSIS}

**Overengineering Risks**: {count} flags
**Average Complexity Score**: {avg_score}/10

---

**Analysis complete. Preparing report...**
```

Store as `COMBINED_ANALYSIS`.

---

## Step 3: Present Combined Report to User

⚠️ **MANDATORY STOP POINT**

Present comprehensive findings and proposed edits (if any):

```markdown
# 📋 Story Review Report: {STORY_ID}

**Review Type**: {standard | focused}
{IF focused}
**Focus**: {USER_CONTEXT}
{ENDIF}
**Mode**: {pre-work | in-progress}
**Date**: {date}

═══════════════════════════════════════════════════════════

## Quality Score: {overall_score}%

{Based on combined metrics}

**Story Completeness**: {from TICKET_QUALITY}/100
**Specification Clarity**: {from SPECIFICATION_QUALITY}/100
{IF in-progress}
**Ticket Accuracy**: {from GIT_STATE}/100
{ENDIF}
**Complexity (lower is better)**: {from COMPLEXITY_ANALYSIS}/10

**Assessment**: {Ready | Ready with Minor Issues | Needs Improvement | Not Ready}

═══════════════════════════════════════════════════════════

## Quality Issues ({count})

{From TICKET_QUALITY - issues sorted by priority}

### P0 Critical ({count})
{List critical issues with locations and fixes}

### P1 High ({count})
{List high-priority issues}

### P2 Medium ({count})
{List medium issues - collapsed}

═══════════════════════════════════════════════════════════

## Specification Clarity Issues ({count})

{From SPECIFICATION_QUALITY}

**Vague Terms Found**: {count}
{List with locations and concrete replacements}

**Missing Quantifications**: {count}
{List with suggestions}

**Agent-Executability**: {score}%
{If <95%, list what makes it hard for autonomous agent}

═══════════════════════════════════════════════════════════

{IF MODE == "in-progress"}
## Ticket Drift ({count} discrepancies)

{From GIT_STATE}

**Status Mismatches**:
{Table showing ticket status vs git evidence}

**Undocumented Changes**:
{List commits/changes not reflected in tickets}

**Progress Inaccuracies**:
{List where progress % doesn't match reality}

═══════════════════════════════════════════════════════════
{ENDIF}

## Complexity Warnings ({count})

{From COMPLEXITY_ANALYSIS}

{FOR each flag}
**{TASK_ID or "Story"}**: {issue}
- **Severity**: {low | med | high}
- **Problem**: {description}
- **Simpler Alternative**: {recommendation}
{ENDFOR}

═══════════════════════════════════════════════════════════

## Proposed File Edits ({count} files)

{IF any edits needed from agent analysis}

{FOR each file with proposed edits}
### {file_path}

**Edit 1**: {description}
```diff
-OLD: {old_text}
+NEW: {new_text}
```

{More edits for same file...}
{ENDFOR}

═══════════════════════════════════════════════════════════

## Quality Improvement

**Before**: {old_score}%
**After** (if edits applied): {projected_new_score}%
**Improvement**: +{delta}%

═══════════════════════════════════════════════════════════

## Approval Required

{IF edits proposed}
**I've identified {count} issues with proposed fixes.**

Options:
- **yes**: Apply all proposed edits
- **selective**: Review each edit individually
- **no**: Don't apply edits (manual fixes only)
- **report**: Just show report, no edits

Your choice:
{ELSE}
**No edits needed!** ✅

Story quality is {score}% - {assessment}.

{IF issues exist but no edits}
**Manual attention needed for**:
{List issues that need manual review}
{ENDIF}
{ENDIF}
```

**CRITICAL**: Wait for user response.

**Response Handling:**

**If "yes":**
- Proceed to Step 4 (execute all edits)

**If "selective":**
- For each proposed edit:
  - Show edit in detail
  - Ask: "Apply this edit? (yes/no/modify)"
  - If yes: Add to execute list
  - If no: Skip it
  - If modify: Let user suggest change, update edit
- After reviewing all: Proceed to Step 4 with approved edits

**If "no":**
- Skip to Step 5 (final report without edits)

**If "report":**
- Print detailed report
- Exit without making changes

---

## Step 4: Execute Edits (After Approval)

**Only proceed if user approved edits.**

For each approved edit:

```python
# Read target file
content = Read(file_path="{file_path}")

# Apply edit
Edit(
    file_path="{file_path}",
    old_string="{old_text}",
    new_string="{new_text}"
)

# Verify
print(f"✅ Applied edit to {file_path}")
```

After all edits:

```bash
# Show what changed
git diff --stat
```

Output:
```markdown
✅ All edits applied ({count} edits across {N} files)

**Files modified**:
{List with edit counts}

**Changes summary**:
{git diff --stat output}
```

---

## Step 5: Print Final Report

Print comprehensive summary:

```markdown
# ✨ Story Review Complete: {STORY_ID}

**Review Type**: {standard | focused}
**Mode**: {pre-work | in-progress}
**Date**: {date}

═══════════════════════════════════════════════════════════

## Quality Score

**Before**: {old_score}%
{IF edits applied}
**After**: {new_score}%
**Improvement**: +{delta}%
{ENDIF}

**Current Assessment**: {Ready | Ready with Minor Issues | Needs Improvement}

═══════════════════════════════════════════════════════════

## Metrics Breakdown

**Story Completeness**: {score}/100
- User story format: {✓ | ✗}
- Acceptance criteria: {✓ | ✗}
- BDD scenarios: {✓ | ✗}
- Technical design: {✓ | ✗}
- Task breakdown: {✓ | ✗}
- Dependencies: {✓ | ✗}

**Specification Clarity**: {score}/100
- Vague terms: {count} {✓ if 0, else ✗}
- Missing details: {count} {✓ if 0, else ✗}
- Ambiguity score: {score}% {✓ if ≥95%, else ✗}

{IF in-progress}
**Ticket Accuracy**: {score}/100
- Task status matches commits: {✓ | ✗}
- Progress bars accurate: {✓ | ✗}
- All changes documented: {✓ | ✗}
{ENDIF}

**Complexity**: {score}/10
- Overengineering flags: {count} {✓ if 0, else ✗}
- Pattern reuse validated: {✓ | ✗}
- Scope appropriate: {✓ | ✗}

═══════════════════════════════════════════════════════════

{IF edits applied}
## Changes Applied

**Files modified**: {count}
{List files with edit descriptions}

**Quality improvements**:
{List specific improvements}

═══════════════════════════════════════════════════════════
{ENDIF}

{IF remaining issues}
## Remaining Issues ({count})

{List issues that need manual attention}

**Recommendations**:
{Specific next steps to address issues}

═══════════════════════════════════════════════════════════
{ENDIF}

## Next Steps

{IF quality >= 95%}
### Story Ready! ✅

{IF MODE == "pre-work"}
**Start implementation**:
1. Create story branch: `git checkout -b {STORY_ID}`
2. Run `/start-next-task` to begin first task
3. Follow BDD/TDD workflow

{ELSE}
**Continue implementation**:
1. Run `/start-next-task` for next pending task
2. Or create PR if all tasks complete

{ENDIF}

{ELSE}
### Improvements Needed

**Before starting work**:
1. Address P0/P1 issues listed above
2. Run `/review-story` again to validate
3. Target quality score: ≥95%

{ENDIF}

═══════════════════════════════════════════════════════════

**Review complete!** 📋
```

**Exit successfully.**

---

## Error Recovery

### Error: Not on Story Branch

```markdown
✗ Not on a story branch

Current branch: {branch_name}

Options:
1. Checkout existing story branch
2. Create new story branch
3. Exit

Choose:
```

### Error: Story Files Not Found

```markdown
✗ Story files not found

Expected: {STORY_README_PATH}
Status: File does not exist

This story may not have been created yet.

Run `/write-next-tickets` to create it.
```

Exit.

### Error: Agent Analysis Failed

```markdown
⚠️ Agent analysis incomplete

{Agent_name} analysis failed:
{Error details}

Partial results available:
{Show what succeeded}

Continue with partial analysis? (yes/no)
```

---

## Success Criteria

- ✅ Validates story quality using ticket-analyzer
- ✅ Checks specification clarity using specification-quality-checker
- ✅ Compares tickets to git reality using git-state-analyzer (if in-progress)
- ✅ Detects overengineering using design-guardian
- ✅ Produces comprehensive quality score (0-100%)
- ✅ Proposes specific file edits with OLD/NEW
- ✅ Gets user approval before making changes
- ✅ Applies edits accurately
- ✅ Reports before/after quality improvement
- ✅ Provides actionable next steps

---

## Agent Coordination Summary

This command uses 4 specialized agents:

1. **ticket-analyzer** (Step 2.1): Story completeness, task quality, hierarchy validation
2. **specification-quality-checker** (Step 2.2): Ambiguity detection, clarity scoring
3. **git-state-analyzer** (Step 2.3): Ticket drift detection (if in-progress)
4. **design-guardian** (Step 2.4): Overengineering and complexity check

**Context Reduction**: ~66% (1,171 lines → ~400 lines)

---

## Begin Execution

Follow the workflow steps 0-5 in order. Stop at approval gates and wait for user input.

**Start with Step 0: Gather User Context**
