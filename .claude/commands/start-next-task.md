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
5. **Deep Analysis** - Use Task agent to create detailed implementation plan
6. **Present Plan** ⚠️ **REQUIRED APPROVAL** - Wait for user "yes" before proceeding
7. **Execute Implementation** - Use Task agent to implement (BDD/TDD workflow)
8. **Run Quality Gates** - All must pass (ruff, mypy, pytest, coverage)
9. **Human QA Checkpoint** ⚠️ **REQUIRED APPROVAL** - Wait for user "yes" before ticket updates
10. **Update Tickets** - Task status, hours, story progress, epic (if needed)
11. **Commit Changes** - Create atomic commit with proper format (tickets + implementation)
12. **Push to Remote** - Optional, user confirms
13. **Final Report** - Summary and next steps

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

## Step 5: Deep Analysis with Task Agent

Launch a Task agent (general-purpose) to create detailed implementation plan:

**Agent Prompt:**
```markdown
Create a detailed implementation plan for TASK-{TASK_ID}: {Title}

**Context Provided:**

You have access to:
- Story README with acceptance criteria, BDD scenarios, technical design
- Task file with implementation checklist and requirements
- Parent epic goals and context
- Initiative objectives
- Roadmap alignment
- Root CLAUDE.md and nested CLAUDE.md files with workflow rules
- TUI_GUIDE.md (if CLI-related task)

**Task Details:**
- Task ID: {TASK_ID}
- Title: {Title}
- Status: {Status}
- Estimated Hours: {Hours}
- Parent Story: {STORY_ID}
- Parent Epic: {EPIC_ID}
- Initiative: {INIT_ID}

**Codebase Pattern Discovery (REQUIRED FIRST):**

Before creating your implementation plan, you MUST discover and analyze existing patterns:

1. **Test Fixtures Survey**
   - Read ALL conftest.py files: `tests/conftest.py`, `tests/unit/conftest.py`, `tests/e2e/conftest.py`
   - List all available fixtures with their purposes
   - Identify fixture composition patterns (fixtures using other fixtures)
   - Note factory fixtures for creating test data

2. **Existing Test Patterns**
   - Find similar test files in tests/unit/ and tests/e2e/
   - Read 2-3 examples of tests similar to your task
   - Extract common patterns: setup, assertions, mocks, parametrization
   - Identify reusable step definitions (for E2E) or test helpers

3. **Module Organization**
   - Read existing modules in src/gitctx/ related to your task
   - Note import patterns, class structure, error handling
   - Find utility functions and common helpers
   - Identify shared constants or configuration

4. **Documentation Context**
   - Read relevant nested CLAUDE.md files for your domain
   - Note documented patterns and anti-patterns
   - Extract fixture usage examples
   - Understand security constraints (esp. for git operations)

**Pattern Reuse Checklist:**

Before proposing ANY new fixture, helper, or pattern, verify:

- [ ] No existing fixture provides this functionality
- [ ] Cannot compose existing fixtures to achieve this
- [ ] Cannot use existing factory to generate test data
- [ ] Not duplicating existing test patterns
- [ ] Not reimplementing platform abstraction helpers

**Your Mission:**

Create a comprehensive implementation plan following strict BDD/TDD workflow principles.

## Required Output Format

### 1. Understanding
- **What this task accomplishes** (1-2 sentences)
- **How it fits in story/epic/initiative** (alignment)
- **Dependencies and prerequisites** (already validated, just confirm)

### 2. Pattern Reuse Analysis & BDD/TDD Strategy

**First: List Discovered Reusable Patterns**

From your pattern discovery, list what you found that applies to this task:

**Available Fixtures:**

- [List fixtures from conftest.py files relevant to this task]
- [Specify which fixtures to use and why]

**Existing Test Patterns:**

- [List 2-3 similar test files found]
- [Specify patterns to copy/adapt from those files]

**Reusable Helpers:**

- [List utility functions or platform helpers to use]
- [Specify helper modules to import]

**Then: Identify Your Development Phase**

#### If BDD Phase (scenario writing):

- Which scenarios to add/modify in tests/e2e/features/
- **REUSE**: Which existing step definitions to reuse from tests/e2e/steps/
- **NEW**: Which step definitions are truly new (justify why no existing step works)
- **FIXTURES**: Which e2e fixtures to use (`e2e_git_repo`, `e2e_cli_runner`, etc.)
- Exact file locations and Gherkin structure

#### If TDD Phase (unit tests):

- Which test files to create/modify in tests/unit/
- **REUSE**: Which existing fixtures to use (`isolated_env`, `config_factory`, etc.)
- **REUSE**: Which test patterns to copy from similar test files
- **NEW**: What new fixtures needed (justify why existing ones insufficient)
- **FIXTURES**: Specify exact fixture composition strategy
- Expected failures and coverage targets

#### If Implementation Phase:

- Which source files to create/modify in src/
- **REUSE**: Which existing modules/helpers to import and use
- **REUSE**: Which patterns to follow from similar modules
- Module structure and organization
- Key classes/functions to implement
- Error handling strategy

#### If Refactoring Phase:

- What to refactor and why
- **REUSE**: Which patterns from other modules to adopt
- Tests must stay green throughout
- Code quality improvements (readability, maintainability)

### 3. Step-by-Step Implementation Plan

Provide concrete, actionable steps. Each step MUST include:

1. **Step Number & Description**
2. **File**: Exact absolute path (e.g., `/Users/bram/Code/gitctx-ai/gitctx/src/...`)
3. **Action**: Read, Write (new file), or Edit (existing file)
4. **Pattern Reuse**: State what existing pattern/fixture/helper this step uses
   - Example: "Uses `isolated_env` fixture from tests/unit/conftest.py"
   - Example: "Follows AAA pattern from tests/unit/core/test_config.py:10-28"
   - Example: "Reuses `e2e_git_repo_factory` with custom params"
   - Example: "Imports `is_windows()` helper from tests/conftest.py:38"
5. **Content**: Specific changes (not vague like "implement X")
   - For Write: Show file structure/skeleton
   - For Edit: Show OLD and NEW content
6. **Verification**: Exact command to verify this step worked

**Example Good Step:**
```
**Step 3: Add BDD scenario for config init**
- File: `tests/e2e/features/cli.feature`
- Action: Edit (append new scenario after existing config scenarios)
- Content:
  ```gherkin
  Scenario: config init creates repo structure (default terse output)
    When I run "gitctx config init"
    Then the exit code should be 0
    And the output should be exactly "Initialized .gitctx/"
    And the file ".gitctx/config.yml" should exist
  ```
- Verification: `uv run pytest tests/e2e/ -k "config init" --collect-only`
  (should show 1 test collected)
```

**Example Bad Step (too vague):**
```
**Step 3: Add BDD scenarios**
- File: cli.feature
- Action: Edit
- Content: Add scenarios for config init
- Verification: Run tests
```

### 4. Quality Gates Checklist

All of these MUST pass before task is considered complete:

- [ ] **Ruff check**: `uv run ruff check src tests` (exit code 0)
- [ ] **Ruff format**: `uv run ruff format src tests` (exit code 0)
- [ ] **Mypy**: `uv run mypy src` (exit code 0)
- [ ] **Pytest**: `uv run pytest -v` (all tests pass)
- [ ] **Coverage**: `uv run pytest --cov=src/gitctx --cov-report=term-missing` (≥85%)

### 5. Ticket Update Plan

Specify exact edits to ticket files (use OLD/NEW format):

**Task file** (`{TASK_FILE_PATH}`):

```markdown
OLD:
**Status**: 🔵 Not Started
**Actual Hours**: -

NEW:
**Status**: 🟡 In Progress
**Actual Hours**: -
```

Then after completion:

```markdown
OLD:
**Status**: 🟡 In Progress
**Actual Hours**: -

- [ ] Step 1 description
- [ ] Step 2 description

NEW:
**Status**: ✅ Complete
**Actual Hours**: {actual_hours}

- [x] Step 1 description
- [x] Step 2 description
```

**Story README** (`{STORY_README_PATH}`):

Calculate new progress:
- Current: {current_tasks_complete}/{total_tasks} = {current_percent}%
- After: {current_tasks_complete + 1}/{total_tasks} = {new_percent}%

```markdown
OLD:
**Progress**: ████░░░░░░ {current_percent}% ({current_tasks_complete}/{total_tasks} tasks complete)

NEW:
**Progress**: {new_progress_bar} {new_percent}% ({current_tasks_complete + 1}/{total_tasks} tasks complete)
```

Update task table:
```markdown
OLD:
| [TASK-{ID}]({filename}) | {Title} | 🔵 Not Started | {hours} |

NEW:
| [TASK-{ID}]({filename}) | {Title} | ✅ Complete | {hours} |
```

**Epic README** (ONLY if this task completes the story):

```markdown
OLD:
- [STORY-{STORY_ID}](../STORY-{STORY_ID}/README.md): 🟡 In Progress

NEW:
- [STORY-{STORY_ID}](../STORY-{STORY_ID}/README.md): ✅ Complete
```

Update epic progress bar accordingly.

### 6. Commit Message

Use conventional commits format with task ID scope:

```
feat(TASK-{TASK_ID}): {concise description of what was done}

{optional body explaining "why" this change was made}
```

Example:
```
feat(TASK-0001.1.2.3): Integrate CLI commands with persistent config

Added config init subcommand, updated set/get/list to use UserConfig and
RepoConfig with proper precedence and type validation.
```

### 7. Time Estimate Validation

- **Implementation**: {X} hours
- **Testing**: {Y} hours
- **Documentation**: {Z} hours
- **Total**: {W} hours

Compare to task estimate: {task_estimated_hours} hours
- If within ±0.5 hours: ✓ Estimate validated
- If exceeds by >0.5 hours: ⚠️  May need scope adjustment or estimate update

### 8. Risk Assessment

**Potential Risks:**
1. {Risk 1}: {Description}
   - Mitigation: {How to handle}
2. {Risk 2}: {Description}
   - Mitigation: {How to handle}

**Critical Success Factors:**
- {Factor 1}
- {Factor 2}

### 9. Pattern Reuse Compliance

**Fixtures Reused:**

- `isolated_env` (tests/unit/conftest.py) - Replaces manual HOME setup
- `config_factory` (tests/unit/conftest.py) - Generates test config YAML
- [List all fixtures reused with file location]

**Test Patterns Reused:**

- AAA pattern from tests/unit/core/test_config.py (lines 10-28)
- Parametrization pattern from [file:lines]
- [List all patterns with source reference]

**Helpers Reused:**

- `is_windows()` (tests/conftest.py) - Platform detection
- [List all helpers with source]

**New Patterns Introduced (Justify Each):**

- [Only list if absolutely necessary]
- [For each: explain why existing patterns insufficient]

**Pattern Reuse Score: X/10**

- 10/10 = 100% reuse, zero duplication
- 7-9/10 = Mostly reuse, minimal new patterns
- 4-6/10 = Mixed reuse/new (needs justification)
- 0-3/10 = Mostly new patterns (SHOULD BE RARE - requires strong justification)

---

**IMPORTANT RULES:**

1. **Be Specific**: No vague terms like "implement X", "handle Y", "add support for Z"
2. **Exact Paths**: Always use full absolute paths for files
3. **Exact Changes**: Show OLD/NEW for edits, full content for writes
4. **Exact Verification**: Provide exact commands with expected output
5. **Follow Patterns**: Reference existing code patterns from context files
6. **Respect Workflow**: Strictly follow BDD/TDD principles from CLAUDE.md
7. **Test First**: If TDD task, tests must be written before implementation
8. **Scenario First**: If BDD task, scenarios must be written before step definitions
9. **Pattern Reuse First**: Always use existing fixtures, helpers, and patterns before creating new ones
10. **Discovery Before Planning**: Read conftest.py files and similar tests BEFORE planning implementation
11. **Composition Over Creation**: Compose existing fixtures rather than creating new ones
12. **Reference Sources**: For every pattern used, cite the source file and line numbers
13. **Justify New Patterns**: Any new fixture/helper requires written justification explaining why existing ones don't work
14. **Platform Helpers**: Use existing `is_windows()`, `get_platform_*()` helpers, never reimplement
15. **Fixture Hierarchy**: Respect the 3-level fixture organization (root/unit/e2e conftest.py)
```

**Agent Configuration:**
- Type: general-purpose
- Mode: Research only (creating plan, not executing yet)
- Output: Detailed implementation plan in markdown

Wait for agent to complete analysis.

---

## Step 6: Present Implementation Plan to User

⚠️ **MANDATORY STOP POINT**

Format and present the agent's plan for approval:

```markdown
# 📋 Implementation Plan: {TASK_ID}

**Branch**: {BRANCH}
**Task**: {TASK_ID}: {Title}
**Story**: {STORY_ID}: {Story Title}
**Epic**: {EPIC_ID}: {Epic Title}
**Estimated Hours**: {hours}

═══════════════════════════════════════════════════════════

## Understanding

{agent's understanding section}

═══════════════════════════════════════════════════════════

## BDD/TDD Strategy

{agent's strategy section - identifies which phase}

═══════════════════════════════════════════════════════════

## Implementation Steps

{agent's step-by-step plan with exact files, actions, content, verification}

═══════════════════════════════════════════════════════════

## Quality Gates

{checklist of gates that must pass}

═══════════════════════════════════════════════════════════

## Ticket Updates

{exact OLD/NEW edits for task, story, epic files}

═══════════════════════════════════════════════════════════

## Commit Message

```
{proposed commit message}
```

═══════════════════════════════════════════════════════════

## Time Estimate vs Task Estimate

- **Plan estimate**: {W} hours
- **Task estimate**: {hours} hours
- **Variance**: {difference} hours ({within/exceeds} estimate)

{if exceeds by >0.5}
⚠️  Plan exceeds task estimate. Consider:
- Breaking task into smaller tasks
- Updating task estimate
- Removing scope
{endif}

═══════════════════════════════════════════════════════════

## Risk Assessment

{agent's risk assessment with mitigations}

═══════════════════════════════════════════════════════════

## Approval & Execution

**Do you approve this implementation plan?** (yes/no/modify)

Options:
- **yes**: Execute implementation (will pause for QA before commit)
- **no**: Cancel and exit
- **modify**: Discuss changes to plan (I'll revise and re-present)
```

**CRITICAL:** Wait for user response. Do NOT proceed until user types "yes".

**If "no"**: Exit cleanly with "Cancelled" message.

**If "modify"**: Ask user what to change, revise plan (possibly re-run agent), re-present. Loop until "yes" or "no".

**If "yes"**: Proceed to Step 7.

---

## Step 7: Execute Implementation

**Only proceed if user approved plan with "yes".**

Launch another Task agent to execute the approved plan:

**Agent Prompt:**
```markdown
Execute the approved implementation plan for TASK-{TASK_ID}.

**Approved Plan:**

{Full plan from Step 5 - all sections}

**Your Mission:**

Implement the task following the approved plan exactly.

## Execution Rules

### 1. Follow BDD/TDD Workflow Strictly

**If BDD Phase (writing scenarios):**
- Write Gherkin scenarios in tests/e2e/features/ FIRST
- Add step definitions in tests/e2e/steps/ SECOND
- Run pytest to verify scenarios are recognized: `uv run pytest --collect-only -k "scenario_name"`
- Scenarios should be recognized but steps may be undefined (that's expected)

**If TDD Phase (writing unit tests):**
- Write unit tests in tests/unit/ FIRST (RED phase)
- Tests should FAIL initially (no implementation exists)
- Run tests to confirm failures: `uv run pytest tests/unit/{module}/ -v`
- Verify tests fail for the right reason (not import errors)

**If Implementation Phase:**
- Tests already exist (from previous task)
- Write minimal code to make tests pass (GREEN phase)
- Run tests after each function/class: `uv run pytest -v`
- All tests must pass before proceeding

**If Refactoring Phase:**
- Tests already exist and are passing
- Refactor code for quality (REFACTOR phase)
- Run tests after each change to ensure they stay green
- No behavior changes, only code quality improvements

### 2. Tool Usage Order

For each step in the plan:

1. **Read before Edit**: Always use Read tool on existing files before Edit
2. **Verify after Change**: Run the verification command after each step
3. **Track Progress**: Use TodoWrite to track steps as you complete them
4. **Stop on Error**: If any verification fails, STOP and report to user

### 3. Progress Tracking

Use TodoWrite to track implementation steps:

```
[
  {"content": "Step 1: {description}", "status": "completed", "activeForm": "Completing step 1"},
  {"content": "Step 2: {description}", "status": "in_progress", "activeForm": "Working on step 2"},
  {"content": "Step 3: {description}", "status": "pending", "activeForm": "Working on step 3"},
  ...
]
```

Update as you go - mark steps complete one at a time.

### 4. Error Handling

**If a step fails:**
1. STOP immediately (do not continue to next step)
2. Show exact error message
3. Ask user:
   - **fix**: Attempt automatic fix
   - **manual**: User will fix manually (exit to terminal)
   - **skip**: Skip this step (NOT recommended, breaks plan)
   - **abort**: Cancel entire task

**Common errors:**
- **Import errors**: Usually means step order is wrong (check plan)
- **File not found**: Check path is correct (absolute vs relative)
- **Syntax errors**: Fix before proceeding
- **Test failures**: Expected in TDD RED phase, unexpected in GREEN/REFACTOR

### 5. Quality First

After implementation is complete:
- Run ALL quality gates in order
- Report results for each gate
- If any gate fails, offer to fix or let user fix manually
- Do NOT proceed to ticket updates if gates fail

### 6. Communication

For each step:
- **Starting**: "▶ Step {N}: {description}"
- **Running**: Show command being run
- **Output**: Show relevant output (truncate if long)
- **Result**: "✓ Step {N} complete" or "✗ Step {N} failed"

Keep output concise but informative.

## Output Format

```markdown
## Executing Implementation Plan

{list all steps from plan with status indicators}

═══════════════════════════════════════════════════════════

## Step 1: {description}
▶ Starting...

{show what you're doing}

{show command if running one}
```
$ {command}
{output}
```

✓ Step 1 complete

═══════════════════════════════════════════════════════════

{continue for each step}

═══════════════════════════════════════════════════════════

## Quality Gates

Running all quality gates...

### 1. Ruff Check
```
$ uv run ruff check src tests
{output}
```
{✓ Passed or ✗ Failed}

{continue for each gate}

═══════════════════════════════════════════════════════════

{if all passed}
## ✅ Implementation Complete

All steps executed successfully.
All quality gates passed.

Proceeding to ticket updates...
{endif}

{if any failed}
## ⚠️  Issues Found

{describe issues}

Options:
- **fix**: Let me attempt automatic fix
- **manual**: I'll fix manually (exit to terminal)
- **continue**: Proceed anyway (NOT recommended)

{wait for user input}
{endif}
```

## Important Notes

1. **No shortcuts**: Follow the plan exactly, step by step
2. **Verify everything**: Run verification command after each step
3. **Tests first**: TDD/BDD means tests before implementation
4. **Stop on failure**: Don't proceed past errors
5. **Quality gates**: All must pass before ticket updates

Execute the plan now.
```

**Agent Configuration:**
- Type: general-purpose
- Mode: **Write mode** (full access to make changes)
- Tools: All (Read, Write, Edit, Bash, TodoWrite)

**Monitor agent execution:**
- Watch for errors
- If agent asks for decision (fix/manual/skip/abort), relay to user
- If agent completes successfully, proceed to Step 8
- If agent fails, show error and exit

---

## Step 8: Run Quality Gates

After implementation agent finishes, verify all quality gates pass:

**Run each gate in sequence:**

```bash
# 1. Linting
uv run ruff check src tests

# 2. Formatting
uv run ruff format src tests

# 3. Type checking
uv run mypy src

# 4. Tests
uv run pytest -v

# 5. Coverage
uv run pytest --cov=src/gitctx --cov-report=term-missing
```

**For each gate, check exit code:**
- Exit code 0: ✓ Passed
- Exit code ≠ 0: ✗ Failed

**If any gate fails:**
```markdown
✗ Quality gate failed: {gate_name}

{error output}

This must be fixed before proceeding.

Options:
- **fix**: Let me attempt automatic fix
- **manual**: I'll fix it manually (exit to terminal)
- **skip**: Continue anyway (NOT recommended - breaks workflow)

Choose: (fix/manual/skip)
```

Wait for user input.

- If "fix": Attempt to fix (e.g., `uv run ruff check src tests --fix`), then re-run gate
- If "manual": Exit cleanly with message "Fix issues manually, then re-run /start-next-task"
- If "skip": Warn strongly but proceed (mark in report that gates were skipped)

**If all gates pass:**
```markdown
✅ All Quality Gates Passed

✓ Ruff check: Passed
✓ Ruff format: Passed
✓ Mypy: Passed
✓ Pytest: {pass_count} passed
✓ Coverage: {coverage}% (threshold: 85%)

Proceeding to ticket updates...
```

---

## Step 9: Human QA Checkpoint

⚠️ **MANDATORY STOP POINT**

Present summary for human review:

```markdown
# ✅ Task Implementation Complete: {TASK_ID}

**All quality gates passed! ✨**

═══════════════════════════════════════════════════════════

## Summary

- **Task**: {TASK_ID}: {Title}
- **Story**: {STORY_ID}
- **Time**: {actual_hours} hours (estimated: {estimated_hours})
- **Files Changed**: {count} files
- **Tests**: All passing ({pass_count} passed)
- **Coverage**: {coverage}% (threshold: 85%)

═══════════════════════════════════════════════════════════

## Changes Made

### Source Files ({count})
{list each file with brief description of changes}

### Test Files ({count})
{list each test file with brief description}

═══════════════════════════════════════════════════════════

## Quality Gate Results

✓ Ruff check: Passed
✓ Ruff format: Passed
✓ Mypy: Passed
✓ Pytest: {pass_count} passed
✓ Coverage: {coverage}% (target: 85%)

{if any gates were skipped}
⚠️  Warning: Some gates were skipped at your request:
{list skipped gates}
{endif}

═══════════════════════════════════════════════════════════

## Git Status

```
{run: git status --short}
```

═══════════════════════════════════════════════════════════

## Diff Summary

```
{run: git diff --stat}
```

═══════════════════════════════════════════════════════════

## Ready to Commit

**Commit message:**
```
feat(TASK-{TASK_ID}): {description}

{optional body}

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

═══════════════════════════════════════════════════════════

## Human QA Required

Please review the changes:

1. **Verify implementation** matches task requirements
2. **Check tests** cover edge cases and scenarios
3. **Review diff** for any issues or unintended changes

**Approve for ticket updates and commit?** (yes/no/fix)

Options:
- **yes**: Update tickets, then commit everything (implementation + tickets)
- **no**: Discard all changes and exit (git reset --hard)
- **fix**: Describe issues, I'll fix them before updating tickets
```

**CRITICAL:** Wait for user response. Do NOT commit until user types "yes".

**If "no":**
```markdown
Discarding changes...

Are you sure? This will reset all changes. (yes/no)
```

If user confirms "yes":
```bash
git reset --hard
git clean -fd
```

Then exit with "Changes discarded. Task not committed."

**If "fix":**
Ask user to describe what needs fixing. Either:
- Make the fixes yourself (if clear instructions)
- Exit and let user fix manually: "Please fix the issues, then re-run /start-next-task"

**If "yes":** Proceed to Step 10.

---

## Step 10: Update Ticket Files

**Only proceed if user approved with "yes" in Step 9.**

Update ticket files in dependency order (bottom-up):

### 10.1 Update Task File

Use Edit tool to update task file:

**Edit 1: Mark task complete and record hours**

```markdown
OLD:
**Status**: 🟡 In Progress
**Actual Hours**: -

NEW:
**Status**: ✅ Complete
**Actual Hours**: {actual_hours}
```

**Edit 2: Check off implementation steps**

For each step in the task's Implementation Checklist:
```markdown
OLD:
- [ ] Step description

NEW:
- [x] Step description
```

Verify edits succeeded.

### 10.2 Update Story README

**Edit 1: Update progress bar and count**

Calculate new progress:
- Current tasks complete: {N}
- Total tasks: {M}
- New count: {N+1}
- New percentage: {(N+1)/M * 100}%
- New progress bar: {generate bar with █ and░}

```markdown
OLD:
**Progress**: {old_bar} {old_percent}% ({N}/{M} tasks complete)

NEW:
**Progress**: {new_bar} {new_percent}% ({N+1}/{M} tasks complete)
```

**Edit 2: Update task table status**

```markdown
OLD:
| [TASK-{ID}]({filename}) | {Title} | 🔵 Not Started | {hours} |

NEW:
| [TASK-{ID}]({filename}) | {Title} | ✅ Complete | {hours} |
```

### 10.3 Update Epic README (if story now complete)

Check if this was the last task:
- If {N+1} == {M} (all tasks complete), update epic

**Edit: Update story status in epic**

```markdown
OLD:
- [STORY-{STORY_ID}](path/to/story/README.md): 🟡 In Progress

NEW:
- [STORY-{STORY_ID}](path/to/story/README.md): ✅ Complete
```

Also update epic progress bar if needed (based on story completion).

### 10.4 Verify All Edits

After all edits:
```markdown
✓ Updated ticket files

Files updated:
- {TASK_FILE}: Status ✅, hours recorded, checklist complete
- {STORY_README}: Progress {old}% → {new}%, task table updated
{if epic updated}
- {EPIC_README}: Story status ✅, epic progress updated
{endif}
```

---

## Step 11: Commit Changes

**Only if user approved with "yes" in Step 9.**

**This commits BOTH implementation and updated tickets together (atomic commit).**

### 11.1 Stage All Changes

```bash
git add -A
```

Show what's staged (should include implementation + ticket updates):
```bash
git diff --cached --stat
```

### 11.2 Create Commit

Use the commit message from the plan (commits implementation + tickets):

```bash
git commit -m "$(cat <<'EOF'
feat(TASK-{TASK_ID}): {description}

{optional body}

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

### 11.3 Verify Commit

```bash
# Show commit
git log -1 --stat

# Get commit SHA
git rev-parse HEAD
```

**Output:**
```markdown
✓ Committed: feat(TASK-{TASK_ID}): {description}

Commit: {sha}
Author: {author}
Date: {date}

{files changed summary}

View commit: git show {sha}
```

---

## Step 12: Push to Remote (Optional)

Ask user if they want to push:

```markdown
═══════════════════════════════════════════════════════════

## Push to Remote?

**Branch**: {branch}
**Remote**: origin/{branch}
**Commits ahead of main**: {count}
**Latest commit**: {sha} - {message}

Push now? (yes/no)

- **yes**: Push to origin/{branch} and optionally monitor CI
- **no**: Commit stays local (push manually later with: git push)
```

Wait for user input.

**If "yes":**

```bash
# Push with upstream tracking
git push -u origin {branch}
```

Show result:
```markdown
✓ Pushed to origin/{branch}

Remote: {remote_url}
Branch: {branch}
Commit: {sha}
```

**If CI is configured (has GitHub Actions):**
```markdown
Monitor CI? (yes/no)

- **yes**: Watch CI run (blocks until complete)
- **no**: Continue (check CI later with: gh run list)
```

If user says "yes":
```bash
# Get latest run
gh run list --limit 1

# Watch it
gh run watch {run_id}
```

**If "no":**
```markdown
✓ Commit stays local

Push later with: git push
```

---

## Step 13: Final Report

Print comprehensive summary:

```markdown
# ✨ Task Complete: {TASK_ID}

**Status**: {Committed and pushed / Committed (not pushed)}
**Time**: {actual_hours} hours (estimated: {estimated_hours})
**Commit**: {sha}
{if pushed}
**Remote**: origin/{branch}
{endif}

═══════════════════════════════════════════════════════════

## What Was Done

**Task**: {TASK_ID}: {Title}

**Changes**:
- {summary of changes}
- {quality metrics}

**Ticket Updates**:
- Task status: 🔵 → ✅
- Story progress: {old}% → {new}%
{if epic updated}
- Epic progress: {epic_old}% → {epic_new}%
{endif}

═══════════════════════════════════════════════════════════

## Next Steps

{if more pending tasks in story}
### Continue Story

**Next task**: {NEXT_TASK_ID}: {Next Task Title}

Run: `/start-next-task`

{else if story complete}
### Story Complete! 🎉

All {M} tasks in {STORY_ID} are complete.

**Create Pull Request:**

1. {if not pushed}Push branch:
   ```
   git push -u origin {branch}
   ```

2. {endif}Create PR:
   ```
   gh pr create --title "{STORY_ID}: {story title}" \\
     --body "$(cat docs/tickets/{INIT}/{EPIC}/{STORY}/README.md)"
   ```

3. Fix GitHub links in PR body:
   - Replace relative paths with blob URLs
   - Format: `https://github.com/{org}/{repo}/blob/{branch}/{path}`

4. Monitor CI:
   ```
   gh run watch
   ```

5. Request review when CI passes

**Or run final validation:**
```
/review-story
```
{endif}

{if pushed and CI exists}
### Monitor CI

**Status**: `gh run list --limit 1`
**Watch**: `gh run watch {run_id}`
**Checks**: `gh pr checks` {if PR exists}
{endif}

═══════════════════════════════════════════════════════════

**Task completed successfully! 🎉**
```

**Exit successfully.**

---

## Error Recovery

### Error: Not on Story Branch

```markdown
✗ Not on a story branch

Current branch: {branch}

You must be on a STORY-* branch to use this command.

**Options:**

1. Switch to existing story branch:
   ```
   git checkout STORY-XXXX
   ```

2. Create new story branch:
   ```
   git checkout -b STORY-XXXX
   ```

3. List available story branches:
   ```
   git branch | grep STORY-
   ```
```

Exit with error.

### Error: No Pending Tasks

```markdown
✓ All tasks complete!

Story: {STORY_ID} (100% complete)

**Next steps:**

1. Run `/review-story` for final validation
2. Create PR: `gh pr create`
```

Exit successfully.

### Error: Prerequisites Not Met

```markdown
✗ Prerequisites not met for {TASK_ID}

**Required:**

{for each failed prerequisite}
  ✗ {PREREQUISITE}: {current_status} (expected: ✅ Complete)
{endfor}

**Passed:**

{for each passed prerequisite}
  ✓ {PREREQUISITE}: {status}
{endfor}

Complete prerequisites first, then retry `/start-next-task`.
```

Exit with error.

### Error: Quality Gate Failed (User Declined Fix)

```markdown
✗ Quality gate failed: {gate_name}

{error_output}

**You chose to exit and fix manually.**

After fixing, re-run: `/start-next-task`

Note: The task status is 🟡 In Progress. The command will detect this
and offer to continue from where it left off.
```

Exit cleanly.

### Error: User Declined Commit

```markdown
✗ Commit declined

You chose not to commit the changes.

**Changes are still in working directory.**

Options:
1. Review changes: `git diff`
2. Commit manually: `git commit -am "message"`
3. Discard changes: `git reset --hard`
4. Re-run `/start-next-task` to try again
```

Exit cleanly (don't discard changes automatically).

---

## Implementation Notes

### Agent Coordination

1. **Agent 1 (Planning)**:
   - Type: general-purpose
   - Mode: Research (read-only)
   - Output: Implementation plan
   - Runs in Step 5

2. **Agent 2 (Execution)**:
   - Type: general-purpose
   - Mode: Write (full access)
   - Input: Approved plan from Agent 1
   - Output: Implementation results
   - Runs in Step 7

### State Tracking

- Task status transitions: 🔵 → 🟡 (start) → ✅ (complete)
- Track actual hours vs estimate
- Update parent story/epic automatically when needed
- Maintain progress bars with accurate percentages

### TodoWrite Integration

- Create todos at start of execution (Step 7)
- Update as each step completes
- Clear todos at end of task
- Format: `[{"content": "...", "status": "...", "activeForm": "..."}]`

### Quality Enforcement

- ALL gates must pass (or user explicitly skips)
- No commits with failing tests
- Coverage threshold enforced (≥85%)
- Report which gates passed/failed clearly

### Git Hygiene

- One task = one commit (atomic)
- Proper format: `feat(TASK-ID): description`
- Co-authored-by Claude footer
- Optional push to remote with CI monitoring

---

## Success Criteria

- ✅ Validates story branch before starting
- ✅ Loads complete story context (story, tasks, epic, init, roadmap, CLAUDE.md)
- ✅ Identifies correct next pending task
- ✅ Validates all prerequisites before proceeding
- ✅ Creates detailed implementation plan via Task agent
- ✅ Presents plan for approval (REQUIRED)
- ✅ Executes plan via separate Task agent (only after approval)
- ✅ Follows strict BDD/TDD workflow (test-first)
- ✅ Runs all quality gates (must pass)
- ✅ Updates task/story/epic files correctly (in dependency order)
- ✅ Requires human QA before commit (REQUIRED)
- ✅ Creates properly formatted commit
- ✅ Optionally pushes to remote with CI monitoring
- ✅ One task = one commit (atomic)
- ✅ Handles errors gracefully with clear recovery steps
- ✅ Provides clear next steps after completion

---

## Begin Execution

Follow the workflow steps 1-13 in order. Stop at approval gates and wait for user input. Handle errors gracefully. Report progress clearly.

**Start with Step 1: Verify Story Branch**
