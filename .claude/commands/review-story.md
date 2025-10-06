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
3. **Deep Analysis** - Use Task agent to analyze story quality + git state
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
- Branch name must match pattern `STORY-NNNN.N.N` (e.g., STORY-0001.1.2)
- If NOT on a story branch:
  - Ask user: "Not on a story branch. Current branch: [BRANCH]. Would you like to:"
    1. Create a new story branch (provide story ID)
    2. Switch to existing story branch (list available)
    3. Exit
  - Wait for user decision before proceeding

**Extract Story Info:**

From the branch name (e.g., `STORY-0001.1.2`), construct the necessary paths:

**Example for STORY-0001.1.2:**
- Story ID: `STORY-0001.1.2`
- Epic ID: `EPIC-0001.1` (first two numbers)
- Initiative ID: `INIT-0001` (first number)
- Story path: `docs/tickets/INIT-0001/EPIC-0001.1/STORY-0001.1.2/README.md`
- Epic path: `docs/tickets/INIT-0001/EPIC-0001.1/README.md`
- Initiative path: `docs/tickets/INIT-0001/README.md`

**Pattern:**
- For `STORY-NNNN.E.S`:
  - Initiative: `INIT-NNNN`
  - Epic: `EPIC-NNNN.E`
  - Story: `STORY-NNNN.E.S`
  - Story dir: `docs/tickets/INIT-NNNN/EPIC-NNNN.E/STORY-NNNN.E.S/`

**Detect Mode:**

```bash
# Count commits on current branch vs main
git rev-list --count main..HEAD
```

- **0 commits** → `pre-work` mode (story not started)
- **N commits** → `in-progress` mode (work underway)

---

## Step 2: Gather Context with Task Agent

Use the Task agent (general-purpose) to perform deep analysis:

```markdown
**Task Agent Prompt:**

Perform comprehensive story review combining quality validation and git reality analysis.

**Story Context:**
- Story ID: [STORY_ID from branch]
- Story path: docs/tickets/INIT-[NNNN]/EPIC-[NNNN.E]/STORY-[NNNN.E.S]/README.md
- Epic ID: EPIC-[NNNN.E]
- Epic path: docs/tickets/INIT-[NNNN]/EPIC-[NNNN.E]/README.md
- Initiative ID: INIT-[NNNN]
- Initiative path: docs/tickets/INIT-[NNNN]/README.md
- Mode: {pre-work | in-progress}

**IMPORTANT:** Construct paths from the branch name. For example, branch `STORY-0001.1.2` means:
- Initiative: INIT-0001
- Epic: EPIC-0001.1
- Story: STORY-0001.1.2

**Review Type:** {REVIEW_TYPE from Step 0}

{IF REVIEW_TYPE == "focused"}
**User Focus Context:**

{USER_CONTEXT from Step 0}

**Instructions:**
- Perform all standard validation checks
- Pay special attention to areas mentioned in user focus
- In your output, create a dedicated "Focus Area Analysis" section
- Highlight findings that directly relate to user's context
- Prioritize these findings in proposed edits
{ENDIF}

**Analysis Required:**

### Part 1: Quality Validation (ALWAYS)

**Read All Context Files:**
1. Story README: ${STORY_DIR}/README.md
2. All task files: ${STORY_DIR}/TASK-*.md
3. Parent epic: ${EPIC_DIR}/README.md
4. Sibling stories: All other STORY-${INIT}-${EPIC}.* in same epic directory
5. Initiative: ${INIT_DIR}/README.md
6. Roadmap: docs/vision/ROADMAP.md
7. Root CLAUDE.md and relevant nested CLAUDE.md files

**Validation Categories:**

#### 1. Story Completeness (10 checks)
- ✅ User story follows "As a/I want/So that" format
- ✅ All acceptance criteria are testable (not vague)
- ✅ All child tasks listed and linked
- ✅ Story points estimated and match task hours sum
- ✅ BDD scenarios written in Gherkin (if applicable)
- ✅ Technical design section present and detailed
- ✅ Success metrics defined and measurable
- ✅ Dependencies documented
- ✅ Risks identified with mitigations
- ✅ Example code/schemas provided for complex logic

#### 2. Hierarchy Consistency (6 checks base + 2 if in-progress)
- ✅ Story aligns with parent epic's goals
- ✅ Story doesn't duplicate sibling stories
- ✅ Story contributes to epic's completion criteria
- ✅ Story points fit within epic's total
- ✅ Prerequisites from other stories identified
- ✅ No conflicting assumptions with siblings
{IF in-progress}
- ✅ New tasks (if any) align with story scope
- ✅ Task additions documented in story progress/notes
{ENDIF}

#### 3. Roadmap Alignment (5 checks base + 1 if in-progress)
- ✅ Story contributes to initiative objectives
- ✅ Story aligns with version planning milestones
- ✅ Story supports success metrics from roadmap
- ✅ Story doesn't contradict core design principles
- ✅ Technology choices match approved stack
{IF in-progress}
- ✅ Scope changes (if any) align with roadmap priorities
{ENDIF}

#### 4. Implementation Readiness (10 checks base + 1 if in-progress)
- ✅ Every task has concrete steps (not "implement X")
- ✅ File paths and module names specified
- ✅ BDD scenarios have corresponding step definitions planned
- ✅ Test coverage targets specified (e.g., ≥85%)
- ✅ Example code/pseudocode provided for complex logic
- ✅ Edge cases identified in scenarios
- ✅ Error handling paths specified
- ✅ All external APIs/libraries identified
- ✅ Solution complexity matches problem scope (not over-architected)
- ✅ Tasks avoid premature optimization (implement MVP first, optimize when metrics show need)
{IF in-progress}
- ✅ Implementation matches task specifications
{ENDIF}

**Anti-Overengineering Detection Patterns:**

For checks 9-10, flag issues when tasks propose complexity without clear justification:

- **Caching/Memoization** for:
  - Small files (<10KB) loaded once per process
  - CLI tools where each invocation is a new process
  - Data that changes frequently
  - No performance metrics showing it's needed

- **Abstraction Layers** when:
  - Only one concrete implementation exists
  - No indication multiple implementations will be needed
  - Adds complexity without solving a real problem
  - Uses terms like "future-proof" without roadmap evidence

- **Performance Optimizations** before:
  - Performance metrics exist showing a problem
  - Profiling data identifies the bottleneck
  - User-facing performance requirements exist
  - MVP implementation is complete

- **Premature Refactoring** such as:
  - Large refactors when targeted fixes would work
  - Breaking working code "for cleanliness" without quality threshold violations
  - Architectural changes without clear requirements driving them

**Valid Complexity** (do NOT flag):
- Security hardening (always appropriate)
- Type safety and validation (catches bugs early)
- Error handling for user-facing features
- Test coverage improvements
- Documentation
- Fixing actual quality threshold violations (complexity, line limits, etc.)

When flagging overengineering, propose specific edits like:
- Remove unnecessary task entirely
- Reduce task scope (e.g., "refactor entire module" → "fix specific complexity violation")
- Move to future story with "if metrics show need" condition

#### 5. Specification Ambiguity Detection (8 checks)
- 🔍 Vague terms: "simple", "basic", "handle", "support", "improve"
- 🔍 Missing details: "TBD", "etc.", "and so on", "as needed"
- 🔍 Implicit assumptions: "obviously", "clearly", "simply"
- �� Unquantified requirements: "fast", "efficient", "user-friendly"
- 🔍 Missing acceptance criteria for edge cases
- 🔍 Incomplete error handling specifications
- 🔍 Missing validation rules
- 🔍 Newly added tasks with vague descriptions

{IF in-progress}
#### 6. Coherence Validation (6 checks - IN-PROGRESS MODE ONLY)
- 🔍 Git commits match story scope (no scope creep)
- 🔍 Completed tasks align with acceptance criteria
- 🔍 New tasks don't conflict with completed work
- 🔍 Task sequence makes logical sense
- 🔍 Progress percentage matches reality
- 🔍 Story status reflects actual state
{ENDIF}

**For Each Failed Check:**
- Document: Location (file:line), Current state, Issue description, Proposed fix, Impact/Priority

### Part 2: Ticket Sync Analysis (IN-PROGRESS MODE ONLY)

**Analyze Git State:**
- Committed changes: `git diff main...HEAD --stat`
- Committed changes detail: `git diff main...HEAD`
- Uncommitted changes: `git status --short`
- Uncommitted changes detail: `git diff`
- Recent commits: `git log --oneline main..HEAD`

**Compare Ticket vs Reality:**

For each task in the story:
- What does the task say it should accomplish?
- What files should be modified according to task description?
- Are those files actually modified in git diff?
- Are task checkboxes accurate?
- Is task status accurate (🔵 Not Started / 🟡 In Progress / ✅ Complete)?
- Are actual hours recorded?

**Identify Ticket Drift:**
- Tasks marked incomplete but code is done
- Tasks marked complete but code is missing
- Progress percentages that don't match reality
- Missing context or documentation in tickets
- Status inconsistencies (task complete but story not updated)
- Parent epic/initiative progress bars out of sync
- New tasks added but not documented in story header
- Task additions not explained in story notes

**For Each Drift Item:**
- Specify: Which file needs updating (exact path), What section/field needs changing, Old value vs new value, Justification based on git diff

---

**Output Format:**

Return a structured analysis with:

## 1. Review Configuration
- Review Type: {standard | focused}
- Mode: {pre-work | in-progress}
- Commits on branch: {0 | N}
{IF focused}
- User Focus: "{USER_CONTEXT}"
{ENDIF}

{IF focused}
## 2. Focus Area Analysis

**User Requested Focus:**
"{USER_CONTEXT}"

**Findings Related to Focus:**
[List specific findings that directly address user's focus context]
[If no issues found in focus area, explicitly state that]

**Priority Recommendations:**
[Recommendations specifically for the focus area]

---
{ENDIF}

## {2 or 3}. Quality Validation Summary

**Overall Quality Score**: XX% ({Ready | Ready with Issues | Needs Review | Not Ready})

### Category Scores:
- Story Completeness: XX% (N/10 checks)
- Hierarchy Consistency: XX% ({6 | 8} checks)
- Roadmap Alignment: XX% ({5 | 6} checks)
- Implementation Readiness: XX% ({10 | 11} checks)
- Specification Ambiguity: XX% (8 checks - higher is better)
{IF in-progress}
- Coherence Validation: XX% (6 checks)
{ENDIF}

### Quality Issues Found: [count]
[List each issue with: Type, Priority (High/Medium/Low), Location, Current state, Proposed fix, Impact]

## 3. Ticket Sync Analysis (IN-PROGRESS ONLY)

**Git Activity Summary:**
- Files modified: [count]
- Lines added/removed: +X -Y
- Commits on branch: [count]
- Uncommitted changes: [yes/no with count]

**Task Status Validation Table:**

| Task | Ticket Status | Git Evidence | Match? |
|------|---------------|--------------|--------|
| TASK-X.X.X.X | ✅ Complete | ✅ Commit abc123 | ✅ |
| TASK-Y.Y.Y.Y | 🔵 Not Started | ❌ No commit | ✅ |

**Ticket Drift Found**: [count]
[List each drift with: Type, Location, Current value, Git reality, Proposed fix]

## 4. Proposed File Edits

**Total Edits**: [count quality + count sync] across [N] files

### Quality Fix Edits ([count])
For each quality issue that can be fixed with an edit:
- File: [exact path]
- Edit type: [Add missing section | Replace vague text | etc.]
- OLD: [exact current text to find]
- NEW: [exact replacement text]
- Reason: [why this fixes the issue]

{IF in-progress}
### Ticket Sync Edits ([count])
For each ticket drift that needs fixing:
- File: [exact path]
- Edit type: [Update status | Update progress | etc.]
- OLD: [exact current text]
- NEW: [exact replacement text]
- Reason: [git evidence justifying change]
{ENDIF}

## 5. Comparative Analysis

**Sibling Stories:**
- STORY-X.X.X: Quality XX% (status)
- STORY-Y.Y.Y: Quality YY% (status)
- Current story: Quality ZZ%

**Best Practices:**
- Applied: [list practices found in story]
- Missing: [list practices missing vs high-quality siblings]

## 6. Recommendations

{IF pre-work}
**Before Starting Work:**
[List specific actions with time estimates to improve quality score]
{ELSE}
**Before Next Commit:**
[List quality fixes and ticket sync actions with time estimates]
{ENDIF}

**Estimated Time to Address All Issues**: [X] minutes
**Quality Score Improvement**: XX% → YY%
{IF in-progress}
**Ticket Accuracy Improvement**: [N] drift → 0 drift
{ENDIF}
```

**Agent Configuration:**
- Type: general-purpose
- Mode: Research only (no code changes yet)
- Output: Detailed analysis with exact file edit specifications

---

## Step 3: Present Combined Report to User

⚠️ **MANDATORY STOP POINT**

After receiving the Task agent's analysis, present the complete findings to the user.

### Report Format

```markdown
# 📋 Story Review Report: ${STORY_ID}

**Branch**: ${BRANCH}
**Review Type**: {Standard | Focused}
{IF focused}
**Focus Area**: "{USER_CONTEXT}"
{ENDIF}
**Review Mode**: {Pre-Work (0 commits) | In-Progress (N commits)}
**Story Status**: {🔵 Not Started | 🟡 In Progress | ✅ Complete}

═══════════════════════════════════════════════════════════

{IF focused}
## Focus Area Analysis

**You asked us to focus on:**
> {USER_CONTEXT}

**Findings Related to Your Focus:**

{agent's focus area findings}

**Recommendations:**

{agent's focus area recommendations}

═══════════════════════════════════════════════════════════
{ENDIF}

## Quality Validation

**Overall Quality Score**: ████████░░ XX% ({Ready | Ready with Issues | Needs Review})

### Readiness Breakdown

[For each category, show progress bar + score + list of checks with ✅/⚠️]

#### 1. Story Completeness: ██████████ 100% (10/10 checks)
✅ User story format correct
✅ Acceptance criteria testable
...

#### 2. Hierarchy Consistency: ████████░░ 83% (5/6 checks)
✅ Aligns with epic goals
⚠️ **ISSUE**: [Description]
...

[Continue for all categories]

---

### 🚨 Quality Issues Found ([count] total)

#### High Priority ([count])
1. **[Issue Title]** (Category)
   - **Location**: [file:line]
   - **Current**: [what's there now]
   - **Fix**: [what it should be]
   - **Impact**: [why this matters]

[List all high priority issues]

#### Medium Priority ([count])
[List all medium priority issues]

#### Low Priority ([count])
[List all low priority issues]

═══════════════════════════════════════════════════════════

{IF in-progress}
## Ticket Synchronization

**Git Activity Summary**:
- Commits: [N] commits on ${BRANCH}
- Files: [N] files modified
- Changes: +[additions] -[deletions]
- Uncommitted: [N files or "None"]

### Task Status Validation

[Show table from agent analysis]

### Ticket Drift

{IF drift found}
**Status**: ⚠️ [N] discrepancies found

[List each drift item with details]
{ELSE}
**Status**: ✅ All tickets match git reality (0 discrepancies)

All ticket documentation is accurate and matches implementation:
- Task statuses are correct
- Progress percentages match reality
- All checkboxes reflect actual work completed
- Parent epic/initiative properly updated
{ENDIF}

═══════════════════════════════════════════════════════════
{ENDIF}

## Proposed File Edits

{IF no edits needed}
✅ **No edits needed** - Story is {ready | accurate}

{IF pre-work}
Story meets quality standards for starting work.
{ELSE}
All documentation matches git reality.
{ENDIF}

{ELSE}
**Total**: {N quality + M sync} edits proposed across [X] files

### Quality Fix Edits ([N] edits)

[For each quality fix:]

**File**: `[path]`

Edit: [Description]
\`\`\`
OLD (line [N]):
[exact current text]

NEW:
[exact replacement text]
\`\`\`
Reason: [explanation]

---

{IF in-progress}
### Ticket Sync Edits ([M] edits)

[For each sync fix:]

**File**: `[path]`

Edit: [Description]
\`\`\`
OLD (line [N]):
[exact current text]

NEW:
[exact replacement text]
\`\`\`
Reason: [git evidence]

---
{ENDIF}

### Impact Assessment

{IF pre-work}
**Quality Improvement**: XX% → YY% (after fixes)
**Time to Execute**: ~[N] minutes
{ELSE}
**Quality Improvement**: XX% → YY%
**Ticket Accuracy**: [M] drift → 0 drift ✅
**Time to Execute**: ~[N] minutes
{ENDIF}

═══════════════════════════════════════════════════════════

## Comparative Analysis

### Sibling Stories in ${EPIC_ID}:
[Show quality scores from agent analysis]

### Best Practices Applied/Missing:
[Show from agent analysis]

═══════════════════════════════════════════════════════════

## Recommended Actions

{IF pre-work}
### Before Starting Work:
[Numbered list from agent recommendations with time estimates]

**Total Time**: ~[X] minutes to reach [target]% readiness
{ELSE}
### Before Next Commit:
[Numbered list from agent recommendations]

**Total Time**: ~[X] minutes to restore quality/accuracy
{ENDIF}

═══════════════════════════════════════════════════════════

## Approval & Execution

{IF edits proposed}
**Do you approve these file edits?** (yes/no/modify)

Options:
- **yes**: Execute all proposed edits
- **no**: Skip all edits (issues documented for manual fix)
- **modify**: Discuss which edits to apply
{ELSE}
**No edits required - story is {ready | accurate}! ✨**

{IF pre-work}
Proceed with starting work on TASK-${FIRST_TASK}.
{ELSE}
Continue with next pending task or create PR if story complete.
{ENDIF}
{ENDIF}
```

**CRITICAL:** Do not make any file edits until user explicitly approves with "yes".

---

## Step 4: Execute Edits (After Approval)

**Only proceed if:**
- User approved with "yes"
- Edits were proposed in Step 3

**Update Order:** (dependencies matter)
1. Task files (TASK-*.md) - lowest level
2. Story README.md - aggregates tasks
3. Epic README.md - aggregates stories
4. Initiative README.md - aggregates epics

**For Each Edit from Agent Analysis:**

Use the Edit tool with exact OLD and NEW strings from agent's "Proposed File Edits" section.

```python
# Example: Quality fix
Edit(
    file_path="docs/tickets/INIT-0001/EPIC-0001.1/STORY-0001.1.2/README.md",
    old_string="## Dependencies\n\n- Parent story created",
    new_string="## Dependencies\n\n- Requires STORY-0001.1.1 (CLI Framework) complete\n- Parent story created"
)

# Example: Ticket sync fix
Edit(
    file_path="docs/tickets/INIT-0001/EPIC-0001.1/STORY-0001.1.2/README.md",
    old_string="**Progress**: ████░░░░░░ 40% (2/5 tasks complete)",
    new_string="**Progress**: ████████░░ 80% (4/5 tasks complete)"
)
```

**Error Handling:**
- If Edit fails (non-unique string), show error and ask user for guidance
- Continue with remaining edits even if one fails
- Track which edits succeeded vs failed

---

## Step 5: Print Final Report

Print a comprehensive report based on whether edits were made.

### Variant A: Edits Were Made

If edits were executed (came from Step 4):

```markdown
# ✨ Story Review Complete: ${STORY_ID}

**Branch**: ${BRANCH}
**Review Type**: {Standard | Focused}
{IF focused}
**Focus Area**: "{USER_CONTEXT}"
{ENDIF}
**Date**: [current date]
**Mode**: {Pre-Work | In-Progress}

---

{IF focused}
## Focus Area Summary

**Your Focus:** "{USER_CONTEXT}"

**Status:**
{IF issues found in focus area}
⚠️  Issues found and addressed (see edits below)
{ELSE}
✅ No issues found in focus area - meets expectations
{ENDIF}

---
{ENDIF}

## Summary

✅ **Edits Completed**: [N] files modified
⚠️ **Edit Failures**: [M] failures (if any)

### Quality Improvement
- **Before**: [XX]% quality score
- **After**: [YY]% quality score
- **Improvement**: +[ZZ] points ✨

{IF in-progress}
### Ticket Accuracy Improvement
- **Before**: [N] discrepancies
- **After**: 0 discrepancies ✅
- **Progress**: Now matches git reality
{ENDIF}

---

## Files Updated

[List each file with changes made]

1. **[path]/TASK-X.md**
   - Added step definition plan
   - Clarified vague description

2. **[path]/README.md**
   - Added prerequisite documentation
   - Quantified acceptance criteria
   {IF in-progress}
   - Updated progress percentage
   - Documented task additions
   {ENDIF}

3. **[path]/EPIC-X.md** (if in-progress)
   - Updated epic progress bar
   - Updated story status in table

---

{IF pre-work}
## Story Readiness

**Status**: ✅ Ready to Start Work

Story is now complete, cohesive, and unambiguous:
- All specifications measurable
- Implementation steps concrete
- Dependencies documented
- Aligned with epic/roadmap

### Next Steps

1. **Begin work**: Start with [FIRST_TASK_ID]
2. **Follow BDD/TDD**: Write tests first, then implement
3. **Commit after each task**: Use format `feat([TASK_ID]): description`
4. **Run `/review-story` again**: If adding tasks mid-work

{ELSE}
## Story Status

**Status**: ✅ Documentation Accurate

All ticket documentation now matches implementation reality:
- Task statuses reflect git commits
- Progress percentages accurate
- New tasks properly documented
- Parent tickets updated

### Next Steps

{IF story complete}
**Story appears complete! Consider:**
1. Push branch: `git push -u origin ${BRANCH}`
2. Create PR: `gh pr create --title "${STORY_ID}: [title]"`
3. Monitor CI: `gh run watch`
{ELSE}
**Continue implementation:**
1. Review next pending task: [NEXT_TASK_ID]
2. Run quality gates: `uv run poe quality`
3. Commit when task complete
{ENDIF}
{ENDIF}

---

## Quality Metrics

**Specification Quality**: [YY]% (Agent-Friendly)
- Strengths: [from analysis]
- Improvements made: [what was fixed]

{IF in-progress}
**Tracking Discipline**: [score]% (Excellent/Good/Needs Work)
- Commits reference task IDs: ✅
- Statuses match reality: ✅
- Progress tracking accurate: ✅
{ENDIF}

---

**Review completed successfully! ✨**
```

### Variant B: No Edits Made

If user declined edits OR no edits were needed:

```markdown
# 📋 Story Review Complete: ${STORY_ID}

**Branch**: ${BRANCH}
**Review Type**: {Standard | Focused}
{IF focused}
**Focus Area**: "{USER_CONTEXT}"
{ENDIF}
**Date**: [current date]
**Mode**: {Pre-Work | In-Progress}

---

{IF focused}
## Focus Area Summary

**Your Focus:** "{USER_CONTEXT}"

**Status:**
{IF issues exist in focus area}
⚠️  Issues remain (see above for details)
{ELSE}
✅ No issues found in focus area - meets expectations
{ENDIF}

---
{ENDIF}

## Summary

{IF user declined}
⏭️ **Edits Skipped** - Issues remain in documentation

You chose not to apply the proposed edits. Issues are documented above for manual resolution.
{ELSE}
✅ **No Edits Needed** - Story {meets quality standards | matches git reality}

{IF pre-work}
Story is complete and ready for implementation.
{ELSE}
All ticket documentation accurately reflects implementation.
{ENDIF}
{ENDIF}

---

## Current Status

{IF pre-work}
**Quality Score**: [XX]% ({Ready | Ready with Issues | Needs Review})

{IF issues exist}
**Remaining Issues**: [N] issues documented
- High priority: [count]
- Medium priority: [count]
- Low priority: [count]

You can:
- Address issues manually before starting work
- Run `/review-story` again after manual fixes
- Proceed with work (quality improvements optional)
{ELSE}
**Quality**: Excellent - all validation checks passed ✅
{ENDIF}

### Next Steps

{IF issues exist}
**Option 1 (Recommended)**: Fix issues manually ([X] min)
**Option 2**: Proceed with work (accept current quality)
{ELSE}
1. **Begin work**: Start with [FIRST_TASK_ID]
2. **Follow BDD/TDD**: Write tests first
3. **Commit after each task**: Use format `feat([TASK_ID]): description`
{ENDIF}

{ELSE}
**Quality Score**: [XX]%
{IF quality issues}
**Quality Issues**: [N] specification issues remain
{ELSE}
**Quality**: Excellent ✅
{ENDIF}

{IF drift exists}
**Ticket Drift**: [N] discrepancies remain
- Task status mismatches: [count]
- Progress inaccuracies: [count]
- Undocumented changes: [count]

You can:
- Run `/review-story` again and approve edits
- Update tickets manually
- Continue work (tracking optional, not blocking)
{ELSE}
**Ticket Accuracy**: Perfect - matches git reality ✅
{ENDIF}

### Next Steps

{IF story complete}
**Story appears complete!**
1. Push branch: `git push -u origin ${BRANCH}`
2. Create PR: `gh pr create --title "${STORY_ID}: [title]"`
{ELSE}
**Continue implementation:**
1. Review next task: [NEXT_TASK_ID]
2. {Address quality/tracking issues | } Run quality gates
3. Commit when complete
{ENDIF}
{ENDIF}

---

**Review completed! {✨ | Run again with approval to apply fixes.}**
```

---

## Important Notes

1. **Dual Validation**: Always check quality; add sync check if in-progress
2. **Single Approval Gate**: Present complete edit plan, get one approval, then execute all
3. **Update Order Matters**: Tasks → Story → Epic → Initiative (bottom-up)
4. **Quality Scoring**:
   - Pre-work: 5 categories, 39 total checks
   - In-progress: 6 categories, 49 total checks
   - Each category scored independently, average = overall score
5. **Edit Precision**: Use exact OLD/NEW strings from agent analysis
6. **Error Recovery**: Continue updates even if one fails, report all failures
7. **Mode Auto-Detection**: Based on commit count, no user input needed
8. **Flexibility**: User can decline edits and fix manually
9. **No File Creation**: This command only EDITS existing tickets, never creates

---

## Thresholds & Scoring

### Quality Score Interpretation
- 95-100%: Ready to start / Ready to continue
- 85-94%: Ready with minor issues
- 70-84%: Needs review before proceeding
- Below 70%: Not ready - significant work needed

### Edit Types

**Quality Fixes** (both modes):
- Add missing documentation sections
- Replace vague terms with concrete specifications
- Quantify unquantified requirements
- Add missing step definitions/examples
- Clarify ambiguous task descriptions

**Ticket Sync** (in-progress only):
- Update task statuses to match commits
- Adjust progress percentages
- Document new task additions
- Update parent epic/initiative progress
- Record actual hours worked

---

## Example Complete Flow

### Example 1: Standard Review

```bash
# User on story branch with 6 commits
$ /review-story

# 0. Gather user context
Which type of review? (standard/focused)
> standard

# 1. Verify branch & detect mode
Current branch: STORY-0001.1.2 ✓
Mode: in-progress (6 commits)

# 2. Launch Task agent (internal - user sees "Analyzing...")
Analyzing story quality and git state...

# 3. Present combined report
# 📋 Story Review Report: STORY-0001.1.2
# Review Type: Standard
# Quality Score: 85%
# Ticket Sync: 2 discrepancies
# 5 edits proposed (3 quality + 2 sync)
# [Shows all details...]
Do you approve these file edits? (yes/no/modify)

# 4. User approves
yes

# 5. Execute edits (user sees progress)
Updating STORY-0001.1.2/README.md (3 edits)... ✓
Updating TASK-0001.1.2.1.md (1 edit)... ✓
Updating EPIC-0001.1/README.md (1 edit)... ✓

# 6. Print final report
# ✨ Story Review Complete: STORY-0001.1.2
# Quality: 85% → 93% (+8 points)
# Ticket accuracy: 2 drift → 0 drift ✅
# [Shows improvements...]
```

### Example 2: Focused Review

```bash
# User on story branch, pre-work
$ /review-story

# 0. Gather user context
Which type of review? (standard/focused)
> focused

What should this review focus on?
> Check if BDD scenarios match acceptance criteria and have step definitions planned

# 1. Verify branch & detect mode
Current branch: STORY-0001.1.3 ✓
Mode: pre-work (0 commits)

# 2. Launch Task agent with focus context
Analyzing story with focus on BDD scenarios...

# 3. Present combined report
# 📋 Story Review Report: STORY-0001.1.3
# Review Type: Focused
# Focus Area: "Check if BDD scenarios match acceptance criteria and have step definitions planned"

## Focus Area Analysis

**You asked us to focus on:**
> Check if BDD scenarios match acceptance criteria and have step definitions planned

**Findings Related to Your Focus:**
- ✅ BDD scenarios exist and cover all 5 acceptance criteria
- ⚠️  Step definition plan missing in TASK-0001.1.3.2
- ⚠️  Scenario for edge case "empty config file" not found

**Recommendations:**
- Add step definition plan to TASK-0001.1.3.2
- Add BDD scenario for edge case handling

## Quality Validation
# Overall Quality: 78%
# 3 edits proposed (all focused on BDD alignment)
# [Shows all details...]
Do you approve these file edits? (yes/no/modify)

# 4. User approves
yes

# 5. Execute edits
Updating TASK-0001.1.3.2.md (1 edit)... ✓
Updating STORY-0001.1.3/README.md (2 edits)... ✓

# 6. Print final report
# ✨ Story Review Complete: STORY-0001.1.3
# Review Type: Focused
# Focus Area: BDD scenarios alignment
# Quality: 78% → 92% (+14 points)
# Focus issues: 2 found and fixed ✅
```

---

## Begin Execution

1. **Gather user context** - Ask standard vs focused, collect context if focused
2. **Verify branch & detect mode** - Check STORY-* branch, count commits
3. **Launch Task agent** - Analyze quality (always) + sync (if in-progress), with optional focus context
4. **Present combined report** - Show quality + sync + proposed edits (+ focus area if focused)
5. **Two paths:**
   - **If edits proposed**: Get approval → Execute edits → Print report (Variant A)
   - **If no edits OR user declines**: Print status report (Variant B)

**Remember:** Always present findings to user. Only make edits after explicit approval with "yes".
