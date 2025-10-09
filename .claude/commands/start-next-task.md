---
description: Execute next pending task with implementation plan approval and quality gates
allowed-tools: "*"
---

# Start Next Task: Implementation Execution with Quality Gates

You are tasked with executing the next pending task in a story-driven workflow with strict quality gates and manual approval checkpoints.

## Overall Workflow

1. **Verify Story Branch** - Check branch name matches STORY-* pattern
2. **Load Story Context** - Read story, tasks, epic, initiative, roadmap, CLAUDE.md files
3. **Identify Next Task** - Find first task with status "🔵 Not Started"
4. **Validate Prerequisites** - Ensure previous tasks complete, dependencies met
5. **Deep Analysis** - Invoke specialized agents for comprehensive plan
6. **Present Plan** ⚠️ **REQUIRED APPROVAL** - Wait for user "yes" before proceeding
7. **Execute Implementation** - Use Task agent to implement (BDD/TDD workflow)
8. **Run Quality Gates** - All must pass (ruff, mypy, pytest, coverage)
9. **Human QA Checkpoint** ⚠️ **REQUIRED APPROVAL** - Wait for user "yes" before ticket updates
10. **Update Tickets** - Task status, hours, story progress, epic (if needed)
11. **Commit Changes** - Create atomic commit with proper format (tickets + implementation)
11.5. **First Commit PR** - If first task, push and create draft PR with blob URLs
12. **CI Watch & Fix Loop** - Monitor all workflows (especially Windows), fix failures, iterate until 100% green
13. **Final Report** - Summary with PR URL, CI status, and next steps

---

## Step 1: Verify Story Branch

Check that we're on a story branch and extract IDs:

```bash
git branch --show-current
```

**Validation:**

- Branch name must match pattern `STORY-NNNN.N.N` (e.g., STORY-0001.1.2)
- If NOT on a story branch:
  - Error message: "Not on a story branch. Current branch: [BRANCH]"
  - Guidance: "Switch to story branch: git checkout STORY-XXXX"
  - Exit

**Extract IDs from branch name:**

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

---

## Step 2: Load Story Context

Read all context files to understand the work:

**Required files:**

1. Story README: `${STORY_DIR}/README.md`
2. All task files: `${STORY_DIR}/TASK-*.md` (use Glob to find)
3. Parent epic: `${EPIC_DIR}/README.md`
4. Initiative: `${INIT_DIR}/README.md`
5. Roadmap: `docs/vision/ROADMAP.md`
6. Root CLAUDE.md: `CLAUDE.md`
7. Relevant nested CLAUDE.md files based on task type:
   - If BDD/E2E: `tests/e2e/CLAUDE.md`
   - If TDD/Unit: `tests/unit/CLAUDE.md`
   - If Docs: `docs/CLAUDE.md`
   - If Architecture: `docs/architecture/CLAUDE.md`
   - Tickets workflow: `docs/tickets/CLAUDE.md` (always)
8. TUI_GUIDE.md (if CLI-related story): `TUI_GUIDE.md`

Use Read tool for each file. Track which files exist vs don't exist.

---

## Step 3: Identify Next Task

Find the first pending task:

**Logic:**

1. Parse all TASK-*.md files
2. Extract task ID and status from each
3. Sort tasks by ID (numerical order)
4. Find first task with status "🔵 Not Started"

**Status indicators to recognize:**

- `🔵 Not Started` or `**Status**: 🔵 Not Started`
- `🟡 In Progress` or `**Status**: 🟡 In Progress`
- `✅ Complete` or `**Status**: ✅ Complete`

**Edge cases:**

**Case A: Task already in progress**

```markdown
⚠️  Task {TASK_ID} is already 🟡 In Progress

This suggests work started but not completed.

Options:
1. **continue**: Continue from where it was left off
2. **restart**: Reset to 🔵 Not Started and start fresh
3. **cancel**: Exit (you can fix manually)

Choose: (continue/restart/cancel)
```

Wait for user input. If "restart", edit task file to change status to 🔵, then proceed. If "cancel", exit.

**Case B: All tasks complete**

```markdown
✓ All tasks complete!

Story: {STORY_ID} (100% complete)

Next steps:
1. Run `/review-story` for final validation
2. Create PR: `gh pr create --title "{STORY_ID}: {title}"`
```

Exit successfully.

**Case C: No next task (gaps in sequence)**

```markdown
⚠️  No pending tasks, but story not complete

Completed: {list}
In Progress: {list}
Missing: Possible gap in task sequence?

Manual review needed.
```

Exit.

---

## Step 4: Validate Prerequisites

Check that prerequisites are met for the next task:

**Checks:**

1. **Previous tasks complete**: All tasks with lower IDs must be "✅ Complete"
2. **Dependencies met**: Check Dependencies section in task/story
3. **Required files exist**: If task says "refactor X", check that X exists
4. **BDD scenarios exist**: If task is implementation, check that BDD scenarios exist

**If prerequisites fail:**

```markdown
✗ Prerequisites not met for {TASK_ID}

Required:
  ✗ TASK-0001.1.2.1 must be complete (currently: 🟡 In Progress)
  ✓ BDD scenarios exist in tests/e2e/features/cli.feature
  ✗ Dependency: Parent story created (currently: not found)

Complete prerequisites first, then retry.
```

Exit with error.

---

## Step 5: Deep Analysis with Specialized Agents

Launch specialized agents in parallel to create comprehensive implementation plan.

### 5.1 Invoke pattern-discovery Agent

Use Task tool (general-purpose) with pattern-discovery agent:

```markdown
You are the pattern-discovery specialized agent. Discover patterns for task implementation.

**Operation:** focused-domain
**Domain**: {unit-testing | e2e-testing | source-code - based on task type}
**Context**: Implementing TASK-{TASK_ID}: {Title}

**Task Description**:
{From task file}

**Related Modules** (from task):
{List modules/files mentioned in task}

## Your Mission

Survey the codebase for patterns relevant to this task:

1. Find existing test fixtures that can be reused
2. Identify similar tests as patterns to follow
3. Discover utility functions and helpers
4. Note BDD step definitions (if E2E task)
5. Find documented anti-patterns to avoid
6. Calculate pattern reuse opportunities

**Focus Areas**:
- Fixtures in conftest.py files relevant to {domain}
- Test patterns in similar modules
- Source utilities/helpers for {related functionality}
- Anti-patterns from CLAUDE.md to avoid

**Output Format**: Markdown with:
- **Fixtures to Reuse**: Name, location, purpose, how to use
- **Test Patterns**: File:lines, description, when to use
- **Source Helpers**: Module.function, purpose, parameters
- **Step Definitions** (if E2E): Existing steps to reuse
- **Anti-Patterns**: What NOT to do
- **Pattern Reuse Score**: 0-10 (how well we can reuse)
- **New Patterns Needed**: List with justification

Execute the discovery now.
```

Store output as `PATTERN_ANALYSIS`.

### 5.2 Invoke ticket-analyzer Agent

Use Task tool (general-purpose) with ticket-analyzer agent in parallel:

```markdown
You are the ticket-analyzer specialized agent. Analyze task readiness.

**Operation:** task-readiness
**Target**: TASK-{TASK_ID}
**Scope**: single-ticket
**Mode**: pre-work

## Your Mission

Analyze the task file for completeness and clarity:

1. Check all 10 task completeness criteria
2. Validate implementation checklist is concrete
3. Ensure file paths and module names are specified
4. Verify test requirements are clear
5. Check verification criteria are defined
6. Validate pattern reuse is documented
7. Score completeness (0-100%)

**Output Format**: Structured markdown with:
- Completeness score and breakdown
- Issues found (priority, location, fix)
- Missing details
- Vague specifications
- Recommendations for clarity

Execute the analysis now.
```

Store output as `TASK_READINESS`.

### 5.3 Invoke design-guardian Agent

Use Task tool (general-purpose) with design-guardian agent in parallel:

```markdown
You are the design-guardian specialized agent. Check for overengineering.

**Operation:** task-review
**Target**: TASK-{TASK_ID}
**Context**: {Task description}

**Proposed Work**:
{Task implementation checklist}

## Your Mission

Review the task for unnecessary complexity:

1. Detect premature abstraction (no second use case yet)
2. Flag premature optimization (no metrics showing need)
3. Identify unnecessary caching (small data, CLI tool, rarely accessed)
4. Detect scope creep beyond story acceptance criteria
5. Distinguish valid complexity (security, testing, validation) from overengineering

**Output Format**: Markdown with:
- Complexity flags (severity, what, why, simpler alternative)
- Overengineering score (0-10, lower is simpler)
- Valid complexity justifications
- Recommendations to simplify

Execute the review now.
```

Store output as `COMPLEXITY_CHECK`.

### 5.4 Aggregate Agent Results

Wait for all three agents to complete, then synthesize into implementation plan:

```markdown
# 🎯 Implementation Plan: TASK-{TASK_ID}

## Task Overview
{From task file - title, description, estimated hours}

## Readiness Assessment
{From TASK_READINESS}

**Completeness**: {score}%
{If <100%, list missing details}

## Pattern Reuse Strategy
{From PATTERN_ANALYSIS}

**Fixtures to Use**:
{List from PATTERN_ANALYSIS}

**Patterns to Follow**:
{List from PATTERN_ANALYSIS}

**Helpers Available**:
{List from PATTERN_ANALYSIS}

**Pattern Reuse Score**: {score}/10

## Complexity Check
{From COMPLEXITY_CHECK}

{IF any flags}
**Overengineering Risks**:
{List flags with simpler alternatives}
{ENDIF}

**Complexity Score**: {score}/10 (target: ≤3 for most tasks)

## Implementation Approach

Based on agent analysis, here's the recommended approach:

### BDD/TDD Workflow

1. **BDD Scenarios** (if applicable):
   {Reference scenarios from story}
   {Note which scenarios this task addresses}

2. **Unit Tests First** (TDD):
   - Test file: {from task or inferred}
   - Fixtures to use: {from PATTERN_ANALYSIS}
   - Pattern to follow: {from PATTERN_ANALYSIS}
   - Write failing tests for: {specific functionality}

3. **Implementation**:
   - Files to modify: {from task}
   - Helpers to use: {from PATTERN_ANALYSIS}
   - Keep it simple: {recommendations from COMPLEXITY_CHECK}

4. **Integration**:
   - BDD steps to implement: {if E2E task}
   - Integration points: {from task}

### Detailed Steps

{From task checklist, enhanced with pattern/complexity guidance}

{FOR each step in task checklist}
- [ ] {Step} - {file}
  - Use: {relevant fixture/helper from PATTERN_ANALYSIS}
  - Avoid: {anti-pattern from PATTERN_ANALYSIS if relevant}
{ENDFOR}

### Quality Gates

- [ ] All unit tests pass
- [ ] BDD scenarios pass (if applicable)
- [ ] ruff check passes
- [ ] ruff format passes
- [ ] mypy passes
- [ ] Coverage >90%

### Verification

{From task verification criteria}

---

**Plan ready for approval.**
```

Store as `IMPLEMENTATION_PLAN`.

---

## Step 6: Present Implementation Plan to User

⚠️ **MANDATORY STOP POINT - REQUIRED APPROVAL**

Present the plan and wait for explicit approval:

```markdown
# 📋 Implementation Plan: TASK-{TASK_ID}

**Task**: {Title}
**Estimated**: {hours} hours
**Status**: 🔵 Not Started → Starting now

═══════════════════════════════════════════════════════════

{IMPLEMENTATION_PLAN from Step 5.4}

═══════════════════════════════════════════════════════════

## Approval Required

**Review the plan above.**

Options:
- **yes**: Approve and begin implementation
- **revise**: Suggest changes to the plan
- **cancel**: Exit without starting

Your choice:
```

**CRITICAL**: Wait for user response. Do NOT start implementation until "yes".

**Response Handling:**

**If "yes":**
- Proceed to Step 7 (execute implementation)

**If "revise":**
- Ask: "What changes would you like to the plan?"
- User describes modifications
- Update IMPLEMENTATION_PLAN
- Re-present for approval
- Loop until "yes" or "cancel"

**If "cancel":**
- Exit cleanly without modifying any files

---

## Step 7: Execute Implementation

Launch Task agent (general-purpose) to implement following BDD/TDD workflow:

**Agent Prompt:**

```markdown
Implement TASK-{TASK_ID}: {Title} following the approved plan.

**Approved Implementation Plan**:
{IMPLEMENTATION_PLAN}

**Critical Workflow Rules** (from CLAUDE.md):

1. **BDD/TDD Cycle**:
   - Write BDD scenarios first (if E2E task)
   - Write failing unit tests (RED)
   - Write minimal code to pass (GREEN)
   - Refactor if needed (REFACTOR)
   - Run all quality gates after each cycle

2. **Pattern Reuse** (from pattern-discovery):
   {Specific fixtures/patterns to use from PATTERN_ANALYSIS}

3. **Avoid Overengineering** (from design-guardian):
   {Specific warnings from COMPLEXITY_CHECK}
   - Keep it simple - no abstractions without second use case
   - No caching unless performance metrics show need
   - No premature optimization

4. **Quality Gates** (must pass before proceeding):
   ```bash
   uv run ruff check src tests
   uv run ruff format src tests
   uv run mypy src
   uv run pytest
   ```

## Implementation Steps

{Follow the detailed steps from IMPLEMENTATION_PLAN}

For each step:
1. Make the change
2. Run relevant tests
3. Fix any failures
4. Continue to next step

## Important Notes

- NEVER skip or xfail tests
- NEVER modify tests to match broken code (fix the code!)
- Write tests BEFORE implementation (TDD)
- Use existing fixtures/patterns identified in plan
- Keep solutions simple unless complexity justified

**Execute the implementation now.**

Follow BDD/TDD workflow strictly. Report progress as you work.
```

**Monitor Implementation:**
- Agent implements step by step
- Agent runs tests after each change
- Agent reports progress
- Agent signals completion or blockers

---

## Step 8: Run Quality Gates

Run all quality gates after implementation:

```bash
# Combined quality check
uv run ruff check src tests && \
uv run ruff format src tests && \
uv run mypy src && \
uv run pytest --cov=src/gitctx
```

**All must pass before proceeding.**

**If any fail:**

```markdown
✗ Quality gates failed

{Show which gate failed and error output}

Options:
1. **fix**: Let me fix the issues
2. **manual**: You fix manually and re-run
3. **skip**: Skip this task (not recommended)

Choose:
```

If "fix", use Task agent to fix issues, then re-run gates. Loop until all pass.
If "manual", exit and let user fix.
If "skip", exit without completing task.

**When all pass:**

```markdown
✅ All quality gates passed!

- ruff check: ✓
- ruff format: ✓
- mypy: ✓
- pytest: ✓ ({N} tests, {coverage}% coverage)

Proceeding to QA checkpoint...
```

---

## Step 9: Human QA Checkpoint

⚠️ **MANDATORY STOP POINT - REQUIRED APPROVAL**

Present implementation for user review:

```markdown
# 🔍 Human QA Checkpoint: TASK-{TASK_ID}

**Implementation complete. Please review:**

═══════════════════════════════════════════════════════════

## Changes Made

{Summary of files modified/created}

## Tests Added/Modified

{Summary of test changes}

## Quality Gates

- ✅ ruff check
- ✅ ruff format
- ✅ mypy
- ✅ pytest ({N} tests, {coverage}% coverage)

═══════════════════════════════════════════════════════════

## Manual Testing Recommended

{From task verification criteria}

**Please test manually and verify the task is complete.**

═══════════════════════════════════════════════════════════

## Approval Required

Options:
- **approve**: Mark task complete and commit
- **revise**: Request changes before committing
- **reject**: Discard changes and exit

Your choice:
```

**CRITICAL**: Wait for user response. Do NOT commit until "approve".

**Response Handling:**

**If "approve":**
- Proceed to Step 10 (update tickets)

**If "revise":**
- Ask: "What needs to be changed?"
- User describes issues
- Use Task agent to make revisions
- Re-run quality gates (Step 8)
- Re-present for approval (Step 9)
- Loop until "approve" or "reject"

**If "reject":**
- Ask: "Discard all changes? (yes/no)"
- If yes: `git restore .` and exit
- If no: Exit without discarding (user can fix manually)

---

## Step 10: Update Ticket Files

Update task status, hours, and parent progress:

### 10.1 Update Task File

```python
# Read task file
task_content = Read(file_path="{TASK_FILE_PATH}")

# Update status
Edit(
    file_path="{TASK_FILE_PATH}",
    old_string="**Status**: 🔵 Not Started",
    new_string="**Status**: ✅ Complete"
)

# Update actual hours
Edit(
    file_path="{TASK_FILE_PATH}",
    old_string="**Actual Hours**: -",
    new_string="**Actual Hours**: {actual_hours}"
)
```

### 10.2 Update Story README

```python
# Read story README
story_content = Read(file_path="{STORY_README_PATH}")

# Update task status in table
Edit(
    file_path="{STORY_README_PATH}",
    old_string="| [{TASK_ID}]({task_file}) | {title} | 🔵 | {hours} |",
    new_string="| [{TASK_ID}]({task_file}) | {title} | ✅ | {actual_hours} |"
)

# Update progress bar and percentage
# Calculate: completed_tasks / total_tasks * 100
Edit(
    file_path="{STORY_README_PATH}",
    old_string="**Progress**: {old_bar} {old_pct}%",
    new_string="**Progress**: {new_bar} {new_pct}%"
)
```

### 10.3 Update Epic README (if story now complete)

```python
{IF all story tasks complete}
# Read epic README
epic_content = Read(file_path="{EPIC_README_PATH}")

# Update story status
Edit(
    file_path="{EPIC_README_PATH}",
    old_string="| [{STORY_ID}]({story_path}) | {title} | {old_status} | {old_points} |",
    new_string="| [{STORY_ID}]({story_path}) | {title} | ✅ | {points} |"
)

# Update epic progress
Edit(
    file_path="{EPIC_README_PATH}",
    old_string="**Progress**: {old_bar} {old_pct}%",
    new_string="**Progress**: {new_bar} {new_pct}%"
)
{ENDIF}
```

Output:
```markdown
✅ Tickets updated:
- Task: {TASK_ID} → ✅ Complete ({actual_hours}h)
- Story: {STORY_ID} → {new_pct}% complete
{IF epic updated}
- Epic: {EPIC_ID} → {new_pct}% complete
{ENDIF}
```

---

## Step 11: Commit Changes

Create atomic commit with both implementation and ticket updates:

```bash
# Stage all changes (implementation + tickets)
git add .

# Create commit with proper format
git commit -m "$(cat <<'EOF'
feat(TASK-{TASK_ID}): {task_title}

{Brief description of what was implemented}

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

Verify commit:
```bash
git log -1 --stat
```

Output:
```markdown
✅ Changes committed:

Commit: {hash}
Message: feat(TASK-{TASK_ID}): {title}
Files changed: {N}
- Implementation: {list source files}
- Tests: {list test files}
- Tickets: {list ticket files}
```

---

## Step 11.5: First Commit - Create Draft PR

**Only if this is the first commit on the branch (no prior commits on this story branch).**

Check commit count:
```bash
git rev-list --count main..HEAD
```

**If count == 1 (first commit):**

### Push Branch

```bash
git push -u origin {BRANCH_NAME}
```

### Create Draft PR with GitHub Blob URLs

Use gh CLI to create PR with proper formatting:

```bash
gh pr create --draft --title "{STORY_ID}: {story_title}" --body "$(cat <<'EOF'
# {STORY_ID}: {Story Title}

## User Story

{From story README}

## Acceptance Criteria

{From story README - checklist format}

## BDD Scenarios

{From story README - Gherkin scenarios}

## Technical Design

### Modules/Files Affected

{From story README - with GitHub blob URLs}

### Data Model

{From story README if applicable}

### Testing Strategy

{From story README}

## Progress

{Progress percentage}

**Tasks**:
{Task table from story with status}

## Related

- Initiative: {INIT_ID}
- Epic: {EPIC_ID}

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

**Important**: Convert file paths to GitHub blob URLs:
- Format: `https://github.com/{owner}/{repo}/blob/{branch}/{file_path}`
- Get owner/repo from `gh repo view --json nameWithOwner`
- Use current branch name

Output:
```markdown
✅ Draft PR created:

URL: {pr_url}
Status: Draft
Branch: {branch_name} → main
```

**If count > 1 (subsequent commit):**

Just push:
```bash
git push
```

---

## Step 12: CI Watch & Fix Loop (Mandatory)

**Watch ALL CI workflows until 100% green.**

### 12.1 List Recent Workflow Runs

```bash
gh run list --limit 5
```

### 12.2 Watch Latest Run

```bash
# Get latest run ID
RUN_ID=$(gh run list --limit 1 --json databaseId --jq '.[0].databaseId')

# Watch it
gh run watch $RUN_ID
```

### 12.3 Handle Failures

**If ANY workflow fails (especially Windows):**

```markdown
⚠️ CI Failure Detected

Workflow: {workflow_name}
Status: ❌ Failed
Platform: {platform}

Fetching logs...
```

```bash
gh run view $RUN_ID --log-failed
```

**Analyze failure and fix:**

```markdown
## Failure Analysis

{Show relevant error logs}

**Root Cause**: {analysis}

**Fix Required**: {description}

Applying fix...
```

Use Task agent to fix the issue:

```markdown
Fix the CI failure in {workflow_name} on {platform}.

**Error**:
{error logs}

**Context**:
- Latest commit: {hash}
- Files changed: {list}

Fix the issue, run quality gates locally, then we'll commit and push.
```

After fix:
1. Run quality gates locally (Step 8)
2. Commit fix: `git commit -m "fix(TASK-{TASK_ID}): {fix_description}"`
3. Push: `git push`
4. Watch new CI run (repeat 12.2)

**Loop until ALL workflows pass on ALL platforms.**

### 12.4 Success

```markdown
✅ All CI workflows passed!

{List of workflows with ✓}

Branch is ready for review.
```

---

## Step 13: Final Report

Print comprehensive summary:

```markdown
# ✨ Task Complete: TASK-{TASK_ID}

**Task**: {Title}
**Status**: ✅ Complete
**Actual Time**: {actual_hours} hours (estimated: {estimated_hours})
**Date**: {date}

═══════════════════════════════════════════════════════════

## Summary

**Implementation**:
- Files modified: {N}
- Tests added: {N}
- Coverage: {coverage}%

**Pattern Reuse**:
- Fixtures reused: {list from PATTERN_ANALYSIS}
- Patterns followed: {list from PATTERN_ANALYSIS}
- New patterns: {N} (justified in task file)

**Quality**:
- Complexity score: {from COMPLEXITY_CHECK}/10 ✓
- All quality gates: ✅ Passed
- All CI workflows: ✅ Green

**Tickets**:
- Task: {TASK_ID} → ✅ Complete
- Story: {STORY_ID} → {progress}% complete
{IF epic updated}
- Epic: {EPIC_ID} → {progress}% complete
{ENDIF}

═══════════════════════════════════════════════════════════

## Commits

{List commits created}

═══════════════════════════════════════════════════════════

## PR Status

{IF PR created}
**Draft PR**: {pr_url}
**Status**: ✅ All CI checks passing
{ELSE}
**Existing PR**: {pr_url} (updated with new commit)
**Status**: ✅ All CI checks passing
{ENDIF}

═══════════════════════════════════════════════════════════

## Next Steps

{IF more tasks pending}
### Continue Story

Next task: {NEXT_TASK_ID} - {title}

Run: `/start-next-task` to continue

{ELSE}
### Story Complete! 🎉

All tasks in {STORY_ID} are complete.

**Recommended**:
1. Run `/review-story` for final validation
2. Convert PR to ready for review:
   ```bash
   gh pr ready {pr_number}
   ```
3. Request reviews and merge when approved
{ENDIF}

═══════════════════════════════════════════════════════════

**Task execution complete!** ✨
```

**Exit successfully.**

---

## Error Recovery

### Error: Not on Story Branch

```markdown
✗ Not on a story branch

Current branch: {branch_name}

Switch to a story branch first:
git checkout STORY-XXXX
```

Exit.

### Error: Prerequisites Not Met

```markdown
✗ Prerequisites not met for {TASK_ID}

{List failed prerequisites}

Complete prerequisites first, then retry.
```

Exit.

### Error: Quality Gates Failed (After Retries)

```markdown
✗ Quality gates still failing after attempts

Manual intervention needed.

Current issues:
{List issues}

Fix manually, then run `/start-next-task` again.
```

Exit.

### Error: CI Perpetually Failing

```markdown
⚠️ CI failures persist after {N} fix attempts

This may require deeper investigation.

Options:
1. Continue fixing (not recommended if >3 attempts)
2. Manual review needed
3. Possible infrastructure issue

Check:
- CI logs at: gh run view {RUN_ID}
- Recent changes to CI config
- Platform-specific issues
```

---

## Success Criteria

- ✅ Identifies next task correctly
- ✅ Validates prerequisites before starting
- ✅ Creates comprehensive plan using specialized agents
- ✅ Follows BDD/TDD workflow strictly
- ✅ Reuses patterns identified by pattern-discovery
- ✅ Avoids overengineering flagged by design-guardian
- ✅ All quality gates pass
- ✅ User approval at all checkpoints
- ✅ Tickets updated accurately
- ✅ Atomic commits with proper format
- ✅ PR created/updated with proper format
- ✅ ALL CI workflows green before finishing
- ✅ Clear final report with next steps

---

## Agent Coordination Summary

This command uses 3 specialized agents:

1. **pattern-discovery** (Step 5.1): Find reusable fixtures, patterns, helpers for task
2. **ticket-analyzer** (Step 5.2): Validate task readiness and completeness
3. **design-guardian** (Step 5.3): Check for overengineering in task scope

**Context Reduction**: ~77% (1,941 lines → ~445 lines estimated)

---

## Begin Execution

Follow the workflow steps 1-13 in order. Stop at approval gates and wait for explicit user input. Track progress with TodoWrite.

**Start with Step 1: Verify Story Branch**
