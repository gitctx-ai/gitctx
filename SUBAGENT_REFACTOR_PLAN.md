# Specialized Subagent Architecture - Refactoring Plan

**Status**: Phase 1 Complete (Agent Creation) | Phase 2 Pending (Slash Command Refactoring)

**Branch**: `mine-subagents-from-slash-commands`

**Last Updated**: 2025-10-08

---

## Executive Summary

We are refactoring the 4 complex slash commands (`/write-next-tickets`, `/start-next-task`, `/review-story`, `/review-pr-comments`) to use specialized subagents instead of monolithic prompts. This reduces context size by 71% while maintaining deep analysis capabilities.

**Why This Matters:**

- Current slash commands: 2,000+ lines each
- Context limits causing reliability issues
- After refactor: 400-600 lines each
- Specialized agents provide focused, reliable analysis

---

## The Problem

### Current State (Before Refactoring)

Each slash command is a massive monolithic prompt that contains:

- Ticket parsing and analysis logic (~300-400 lines)
- Git state analysis (~150-200 lines)
- Pattern discovery logic (~200-300 lines)
- Anti-overengineering detection (~250 lines)
- Specification quality checking (~100-150 lines)
- Interview/interaction logic (~400-500 lines)
- Workflow orchestration (~200-300 lines)

**Issues:**

1. **Context bloat**: Commands are 1,200-2,200 lines each
2. **Duplication**: Same analysis logic repeated across commands
3. **Maintenance**: Changes require updating multiple commands
4. **Reliability**: Large context increases hallucination risk
5. **Agent confusion**: Too many concerns in one agent

---

## The Solution

### Specialized Subagent Architecture

Extract analysis logic into 6 specialized agents that slash commands can invoke:

```
Slash Command (Orchestrator)
    ↓
    ├─→ ticket-analyzer (analyze structure/completeness)
    ├─→ design-guardian (detect overengineering)
    ├─→ git-state-analyzer (compare to git reality)
    ├─→ specification-quality-checker (ensure clarity)
    ├─→ pattern-discovery (find reusable patterns)
    └─→ requirements-interviewer (capture requirements)
```

**Benefits:**

1. **71% size reduction**: 5,635 lines → 1,650 lines across all commands
2. **Single source of truth**: Each analysis type has one canonical implementation
3. **Composability**: Commands use only the agents they need
4. **Maintainability**: Update agent once, all commands benefit
5. **Reliability**: Smaller context = more reliable execution

---

## Phase 1: Agent Creation ✅ COMPLETE

### Created Agents (6 total, 3,535 lines)

#### 1. ticket-analyzer.md (14K, ~450 lines)

**Location**: `.claude/agents/ticket-analyzer.md`

**Purpose**: Deep analysis of ticket structure, hierarchy, completeness, and state accuracy.

**Capabilities:**

- Parse ticket files (INIT, EPIC, STORY, TASK)
- Validate hierarchy relationships
- Score completeness against criteria (Initiative: 8 criteria, Epic: 10, Story: 14, Task: 10)
- Detect progress/status inconsistencies
- Compare sibling tickets for quality
- Identify missing dependencies

**Input Format:**

```markdown
**Analysis Type:** {story-deep | ticket-completeness | hierarchy-gaps | task-readiness}
**Target:** {branch name | ticket ID | directory path}
**Scope:** {single-ticket | story-and-tasks | epic-and-stories | full-hierarchy}
**Mode:** {pre-work | in-progress}
```

**Output**: Structured JSON-like markdown with:

- Completeness scores per category
- List of issues with priority/location/fix
- Hierarchy validation results
- Progress accuracy analysis

**Used By**: `/start-next-task`, `/write-next-tickets`, `/review-story`

**Context Reduction**: Removes ~300-400 lines from each command

---

#### 2. design-guardian.md (17K, ~550 lines)

**Location**: `.claude/agents/design-guardian.md`

**Purpose**: Enforce anti-overengineering principles and validate pattern reuse.

**Capabilities:**

- Detect unnecessary caching (small files, CLI tools, rarely accessed data)
- Flag premature abstraction (single implementation, no roadmap evidence)
- Identify premature optimization (no metrics, no user requirement)
- Detect unnecessary refactoring (no threshold violation, "cleanliness" only)
- Validate pattern reuse vs duplication
- Distinguish valid complexity from overengineering

**Red Flags Detected:**

- ❌ Caching for <10KB files or per-invocation CLI tools
- ❌ Interfaces/protocols with only one implementation
- ❌ Performance optimization before metrics exist
- ❌ Large refactors when targeted fixes work
- ❌ "Future-proofing" without roadmap evidence

**Valid Complexity (Won't Flag):**

- ✅ Security hardening
- ✅ Type safety and validation
- ✅ Error handling for user-facing features
- ✅ Test coverage improvements
- ✅ Fixing actual quality threshold violations

**Input Format:**

```markdown
**Review Type:** {story-review | task-review | epic-review}
**Target:** {ticket ID or path}
**Context:** {brief description of what's being built}

**Proposed Work:**
{Story/task content to analyze}
```

**Output**: Markdown report with:

- Complexity flags (with severity)
- Simpler alternatives
- Justification requirements
- Pattern reuse recommendations
- Overengineering score (0-10, lower is simpler)

**Used By**: `/write-next-tickets`, `/review-story`, `/start-next-task`

**Context Reduction**: Removes ~250 lines from each command

---

#### 3. git-state-analyzer.md (15K, ~480 lines)

**Location**: `.claude/agents/git-state-analyzer.md`

**Purpose**: Analyze git commits and file changes, compare to ticket documentation.

**Capabilities:**

- Parse git commit history (`git log main..HEAD`)
- Analyze file changes (`git diff main...HEAD`)
- Extract commit metadata (message, files, author, date)
- Compare ticket task statuses to commit evidence
- Detect ticket drift (status mismatch, undocumented changes)
- Validate progress percentages against reality
- Identify uncommitted work

**Input Format:**

```markdown
**Analysis Type:** {commit-history | ticket-drift | progress-validation}
**Branch:** {branch name}
**Ticket Context:** {story/epic ID and path}

**Optional:**
- Focus on: {specific concerns}
- Include uncommitted: {true | false}
```

**Output**: Markdown report with:

- Git activity summary (commits, files, lines changed)
- Task status validation table (ticket vs git)
- Drift items (with OLD/NEW proposed fixes)
- Progress accuracy analysis
- Uncommitted changes summary

**Used By**: `/review-story`, `/start-next-task`

**Context Reduction**: Removes ~150-200 lines from each command

---

#### 4. specification-quality-checker.md (14K, ~470 lines)

**Location**: `.claude/agents/specification-quality-checker.md`

**Purpose**: Detect vague/ambiguous language, enforce quantified requirements.

**Capabilities:**

- Detect vague terms: "simple", "basic", "handle", "support", "improve"
- Find missing details: "TBD", "etc.", "and so on", "as needed"
- Identify implicit assumptions: "obviously", "clearly", "simply"
- Flag unquantified requirements: "fast", "efficient", "user-friendly"
- Detect missing edge cases
- Find incomplete error handling specifications
- Identify missing validation rules
- Score agent-executability (can autonomous agent implement this?)

**Vague Term Detection Patterns:**

- Verbs: handle, support, manage, process, deal with, work with
- Adjectives: simple, basic, easy, straightforward, trivial, obvious
- Hedge words: probably, maybe, might, could, should, would
- Placeholders: TBD, TODO, placeholder, example, sample
- Implicit refs: this, that, it, them (without clear antecedent)

**Input Format:**

```markdown
**Check Type:** {full-ticket | acceptance-criteria | technical-design | task-steps}
**Target:** {ticket ID or path}
**Strictness:** {lenient | standard | strict}

**Content to Check:**
{Ticket content or specific section}
```

**Output**: Markdown report with:

- Ambiguity score (0-100%, higher is clearer)
- List of vague terms with locations
- Proposed concrete replacements
- Missing quantifications
- Agent-executability score
- Suggested improvements

**Used By**: `/write-next-tickets`, `/review-story`, `/start-next-task`

**Context Reduction**: Removes ~100-150 lines from each command

---

#### 5. pattern-discovery.md (17K, ~540 lines)

**Location**: `.claude/agents/pattern-discovery.md`

**Purpose**: Survey codebase for reusable patterns, fixtures, helpers, and anti-patterns.

**Capabilities:**

- Scan all conftest.py files (root, unit, e2e)
- Catalog test fixtures with purpose, parameters, composition
- Identify test patterns (AAA, parametrization, mocking)
- Find E2E step definitions for reuse
- Discover source code patterns (utils, helpers, protocols)
- Extract platform abstraction helpers (is_windows(), etc.)
- Catalog documented anti-patterns from CLAUDE.md files
- Calculate pattern reuse score (0-10)
- Recommend fixture composition over creation

**Discovery Types:**

1. `full-survey`: Complete codebase pattern inventory
2. `focused-domain`: Domain-specific (e2e, unit, source)
3. `fixture-lookup`: Find fixtures for specific functionality
4. `test-pattern-search`: Find similar test examples

**Input Format:**

```markdown
**Discovery Type:** {full-survey | focused-domain | fixture-lookup | test-pattern-search}
**Domain:** {e2e-testing | unit-testing | source-code | documentation}
**Context:** {what you're trying to accomplish}

**Optional Filters:**
- Related modules: {list}
- Related features: {list}
- Specific concerns: {list}
```

**Output**: Markdown report with:

- Fixture inventory (name, file:line, purpose, dependencies, usage)
- Test patterns (AAA, parametrization, mocking with examples)
- E2E step definitions (reusable steps with file:line)
- Source patterns (utilities, helpers, protocols)
- Platform helpers (is_windows(), skip decorators)
- Documented anti-patterns from CLAUDE.md
- Pattern reuse opportunities for context
- Pattern reuse score (0-10)
- New patterns required (with justification)

**Used By**: `/start-next-task`, `/write-next-tickets`

**Context Reduction**: Removes ~200-300 lines from each command

---

#### 6. requirements-interviewer.md (25K, ~800 lines)

**Location**: `.claude/agents/requirements-interviewer.md`

**Purpose**: Conduct interactive requirement capture to transform vague ideas into concrete specs.

**Capabilities:**

- Progressive questioning (high-level → details → validation)
- Ticket-type-specific question templates (Initiative, Epic, Story, Task)
- Probe vague responses until concrete
- Reflect understanding back to user
- Preserve user's exact language/terminology
- Detect and challenge overengineering proposals
- Reference pattern-discovery for reuse validation
- Calculate completeness score (target: 95%+)
- Don't stop until target completeness reached

**Interview Types:**

1. Initiative interview (strategic, key results, epics)
2. Epic interview (overview, BDD, stories, technical)
3. Story interview (user story, acceptance criteria, tasks, design)
4. Task interview (steps, estimates, verification, patterns)

**Interview Flow:**

1. Introduction (explain goal, get confirmation)
2. Progressive questioning (high → mid → detail → validation → patterns)
3. Summarize & confirm (reflect back each section)
4. Completeness check (against criteria for ticket type)
5. Final output (structured requirements ready for drafting)

**Anti-Overengineering Detection:**

- Red flags: caching (small/rare data), abstraction (single impl), optimization (no metrics), refactoring (no threshold)
- Probes necessity with specific questions
- Suggests simpler alternatives
- Documents justification requirements

**Input Format:**

```markdown
**Interview Type:** {initiative | epic | story | task}
**Ticket ID:** {TICKET-XXXX or "NEW"}
**Parent Context:** {parent ticket ID and summary}
**Current State:** {existing content or "N/A"}
**Gap Analysis:** {from ticket-analyzer}
**Pattern Context:** {from pattern-discovery}
**Missing Details:** {list}
**Interview Goal:** {target completeness %}
```

**Output**: Markdown with:

- Captured requirements (structured by section)
- Acceptance criteria / Key results
- BDD scenarios (Gherkin format)
- Child tickets (with estimates)
- Technical design (files, data model, testing)
- Pattern reuse (fixtures to use, patterns to follow)
- User's exact quotes
- Completeness analysis (score vs target)
- Next steps

**Used By**: `/write-next-tickets`

**Context Reduction**: Removes ~400-500 lines from each command

---

### Agent Summary Table

| Agent | Size | Lines | Removes | Used By |
|-------|------|-------|---------|---------|
| ticket-analyzer | 14K | ~450 | 300-400 | start-next-task, write-next-tickets, review-story |
| design-guardian | 17K | ~550 | 250 | write-next-tickets, review-story, start-next-task |
| git-state-analyzer | 15K | ~480 | 150-200 | review-story, start-next-task |
| specification-quality-checker | 14K | ~470 | 100-150 | write-next-tickets, review-story, start-next-task |
| pattern-discovery | 17K | ~540 | 200-300 | start-next-task, write-next-tickets |
| requirements-interviewer | 25K | ~800 | 400-500 | write-next-tickets |
| **TOTAL** | **102K** | **3,535** | | |

---

## Phase 2: Slash Command Refactoring ⬜ PENDING

### Refactoring Strategy

Each slash command becomes an **orchestrator** that:

1. Validates input and context
2. Invokes specialized agents for analysis
3. Aggregates agent results
4. Presents findings to user
5. Executes approved actions
6. Reports results

**Key Principle**: Commands contain only orchestration logic, no analysis logic.

---

### Command 1: /write-next-tickets (Priority: High - PoC)

**Current Size**: 2,188 lines
**Target Size**: 500-600 lines (73% reduction)
**Complexity**: Highest (discovery, interviewing, drafting)

#### Current Structure (Monolithic)

```
Step 0: Gather user intent (50 lines)
Step 1: Discovery & gap analysis (500 lines) ← EXTRACT to ticket-analyzer
         - Codebase pattern survey (200 lines) ← EXTRACT to pattern-discovery
         - Completeness scoring (150 lines) ← EXTRACT to ticket-analyzer
         - Anti-overengineering (100 lines) ← EXTRACT to design-guardian
         - Dependency analysis (50 lines) ← EXTRACT to ticket-analyzer
Step 2: Present gap report (150 lines)
Step 3: Iterative ticket writing (1200 lines)
         - Interview logic (500 lines) ← EXTRACT to requirements-interviewer
         - Drafting logic (400 lines) ← Keep (ticket-specific)
         - Review logic (300 lines) ← Keep (orchestration)
Step 4: Final summary (100 lines)
```

#### Refactored Structure (Orchestrated)

```
Step 0: Gather user intent (50 lines) ← Keep
Step 1: Invoke ticket-analyzer agent (20 lines)
         → Returns gap analysis
Step 2: Invoke pattern-discovery agent (20 lines)
         → Returns pattern inventory
Step 3: Invoke design-guardian agent (20 lines)
         → Returns complexity flags
Step 4: Present combined report (100 lines) ← Keep
Step 5: For each gap:
         - Invoke requirements-interviewer (30 lines)
         - Invoke specification-quality-checker (20 lines)
         - Draft ticket with agent output (150 lines) ← Keep
         - User review and save (100 lines) ← Keep
Step 6: Final summary (100 lines) ← Keep

Total: ~590 lines (73% reduction)
```

#### Agent Invocation Examples

**Invoke ticket-analyzer:**

```markdown
Use Task agent (general-purpose) with prompt:

**Agent Type**: ticket-analyzer
**Analysis Type**: hierarchy-gaps
**Target**: {FOCUS_AREA or "full"}
**Scope**: {full-hierarchy | epic-and-stories}
**Mode**: pre-work

Analyze the ticket hierarchy and return gap analysis report.
```

**Invoke pattern-discovery:**

```markdown
Use Task agent (general-purpose) with prompt:

**Agent Type**: pattern-discovery
**Discovery Type**: full-survey
**Domain**: all
**Context**: Planning to write tickets for {EPIC/STORY description}

Survey codebase and return pattern inventory.
```

**Invoke requirements-interviewer:**

```markdown
Use Task agent (general-purpose) with prompt:

**Agent Type**: requirements-interviewer
**Interview Type**: {story | task | epic}
**Ticket ID**: {NEW or existing}
**Parent Context**: {from gap analysis}
**Gap Analysis**: {from ticket-analyzer output}
**Pattern Context**: {from pattern-discovery output}
**Missing Details**: {list from gap analysis}
**Interview Goal**: 95% completeness

Conduct interactive interview and return structured requirements.
```

#### Refactoring Steps

1. **Read current command** (done - you have it in context)
2. **Identify extraction points**:
   - Step 1 Discovery → ticket-analyzer + pattern-discovery + design-guardian
   - Step 3.2 Interview → requirements-interviewer
   - Step 3.3 Drafting → Keep (uses agent outputs)
3. **Create new command structure**:
   - Write orchestration skeleton
   - Add agent invocations with proper input/output handling
   - Keep user interaction and file operations
4. **Test with example**:
   - Run on actual ticket hierarchy
   - Verify agents return expected output
   - Validate total line count
5. **Document changes**:
   - Update command description
   - Document which agents are used
   - Add troubleshooting guide

---

### Command 2: /start-next-task (Priority: Medium)

**Current Size**: 1,915 lines
**Target Size**: 400-500 lines (74% reduction)

#### Current Structure

```
Step 1: Verify story branch (50 lines) ← Keep
Step 2: Load story context (100 lines) ← Keep
Step 3: Identify next task (80 lines) ← Keep
Step 4: Validate prerequisites (60 lines) ← Keep
Step 5: Deep analysis (500 lines) ← EXTRACT to multiple agents
         - Pattern discovery (200 lines) ← EXTRACT to pattern-discovery
         - Task analysis (150 lines) ← EXTRACT to ticket-analyzer
         - Anti-overengineering check (150 lines) ← EXTRACT to design-guardian
Step 6: Present plan (150 lines) ← Keep
Step 7: Execute implementation (400 lines) ← Keep
Step 8: Quality gates (200 lines) ← Keep
Step 9: Human QA (100 lines) ← Keep
Step 10: Update tickets (100 lines) ← Keep
Step 11: Commit (100 lines) ← Keep
Step 12: CI watch (175 lines) ← Keep

Total current: 1,915 lines
```

#### Refactored Structure

```
Steps 1-4: Same (290 lines) ← Keep
Step 5: Agent invocations (80 lines)
         - Invoke pattern-discovery (20 lines)
         - Invoke ticket-analyzer for task (20 lines)
         - Invoke design-guardian (20 lines)
         - Aggregate results (20 lines)
Step 6: Present plan (100 lines) ← Keep (uses agent outputs)
Steps 7-12: Same (1,075 lines) ← Keep

Total refactored: ~445 lines (77% reduction)
```

#### Agent Invocations

**Pattern discovery:**

```markdown
**Agent Type**: pattern-discovery
**Discovery Type**: focused-domain
**Domain**: {unit-testing | e2e-testing based on task}
**Context**: {task description}
**Related modules**: {from task file}
```

**Task analysis:**

```markdown
**Agent Type**: ticket-analyzer
**Analysis Type**: task-readiness
**Target**: {TASK-ID}
**Scope**: single-ticket
**Mode**: pre-work
```

**Overengineering check:**

```markdown
**Agent Type**: design-guardian
**Review Type**: task-review
**Target**: {TASK-ID}
**Context**: {task description}
**Proposed Work**: {task checklist}
```

---

### Command 3: /review-story (Priority: Medium)

**Current Size**: 1,172 lines
**Target Size**: 350-400 lines (69% reduction)

#### Current Structure

```
Step 0: Gather user context (50 lines) ← Keep
Step 1: Verify branch & detect mode (80 lines) ← Keep
Step 2: Deep analysis (600 lines) ← EXTRACT to multiple agents
         - Quality validation (300 lines) ← EXTRACT to ticket-analyzer + specification-quality-checker
         - Git state analysis (150 lines) ← EXTRACT to git-state-analyzer
         - Ticket sync (150 lines) ← EXTRACT to git-state-analyzer
Step 3: Present report (200 lines) ← Keep (aggregates agent outputs)
Step 4: Execute edits (150 lines) ← Keep
Step 5: Final report (100 lines) ← Keep

Total current: 1,172 lines
```

#### Refactored Structure

```
Steps 0-1: Same (130 lines) ← Keep
Step 2: Agent invocations (100 lines)
         - Invoke ticket-analyzer (25 lines)
         - Invoke specification-quality-checker (25 lines)
         - Invoke git-state-analyzer (25 lines)
         - Invoke design-guardian (25 lines)
Step 3: Present combined report (120 lines) ← Keep
Steps 4-5: Same (250 lines) ← Keep

Total refactored: ~400 lines (66% reduction)
```

#### Agent Invocations

**Quality validation:**

```markdown
**Agent Type**: ticket-analyzer
**Analysis Type**: story-deep
**Target**: {STORY-ID from branch}
**Scope**: story-and-tasks
**Mode**: {pre-work | in-progress from commit count}
**Focus areas**: {USER_CONTEXT if focused review}
```

**Specification quality:**

```markdown
**Agent Type**: specification-quality-checker
**Check Type**: full-ticket
**Target**: {STORY-ID}
**Strictness**: strict
**Content**: {story README content}
```

**Git state analysis:**

```markdown
**Agent Type**: git-state-analyzer
**Analysis Type**: ticket-drift
**Branch**: {current branch}
**Ticket Context**: {STORY-ID and path}
**Include uncommitted**: true
```

---

### Command 4: /review-pr-comments (Priority: Low)

**Current Size**: 360 lines
**Target Size**: ~300 lines (17% reduction)

**Note**: This command is already relatively small and focused on GitHub API interactions. Minimal refactoring needed.

**Possible extractions**:

- Code analysis for fix proposals (~50 lines) → Could use pattern-discovery if suggesting pattern changes
- Most logic is orchestration (fetch, fix, test, commit, reply) which should stay

**Decision**: Refactor last, may not need significant changes.

---

## Phase 3: Documentation ⬜ PENDING

### Documents to Create

1. **Agent Usage Guide** (`.claude/agents/README.md`)
   - Overview of architecture
   - When to use each agent
   - Input/output format reference
   - Composition patterns
   - Troubleshooting

2. **Refactoring Changelog** (`REFACTORING_CHANGELOG.md`)
   - What changed in each command
   - Migration guide (old vs new structure)
   - Breaking changes (if any)
   - Performance improvements

3. **Developer Guide Update** (update `CLAUDE.md`)
   - Reference specialized agents
   - Explain orchestrator pattern
   - Best practices for agent composition

---

## Implementation Checklist

### Phase 1: Agent Creation ✅ COMPLETE

- [x] Create ticket-analyzer.md
- [x] Create design-guardian.md
- [x] Create git-state-analyzer.md
- [x] Create specification-quality-checker.md
- [x] Create pattern-discovery.md
- [x] Create requirements-interviewer.md

### Phase 2: Slash Command Refactoring ⬜ IN PROGRESS

- [ ] Refactor /write-next-tickets (PoC)
  - [ ] Create refactored command file
  - [ ] Test on real ticket hierarchy
  - [ ] Validate line count reduction
  - [ ] Compare output quality to original
  - [ ] Get user approval
- [ ] Refactor /start-next-task
  - [ ] Create refactored command file
  - [ ] Test on real story branch
  - [ ] Validate integration with agents
  - [ ] Compare to original functionality
- [ ] Refactor /review-story
  - [ ] Create refactored command file
  - [ ] Test pre-work and in-progress modes
  - [ ] Validate focused review mode
  - [ ] Compare to original
- [ ] Review /review-pr-comments (determine if refactoring needed)

### Phase 3: Documentation ⬜ PENDING

- [ ] Write `.claude/agents/README.md`
- [ ] Write `REFACTORING_CHANGELOG.md`
- [ ] Update root `CLAUDE.md` with agent references
- [ ] Add troubleshooting guide
- [ ] Document composition patterns

### Phase 4: Validation & Cleanup ⬜ PENDING

- [ ] Test all refactored commands end-to-end
- [ ] Compare output quality: original vs refactored
- [ ] Measure context size reduction
- [ ] Performance testing
- [ ] User acceptance testing
- [ ] Clean up old command files (archive or delete)
- [ ] Final documentation review

---

## Key Principles for Refactoring

### 1. Orchestration vs Analysis

**Orchestrators** (slash commands):

- Validate input
- Invoke agents
- Aggregate results
- Present to user
- Execute actions
- Report results

**Analyzers** (specialized agents):

- Perform deep analysis
- Return structured data
- No user interaction
- No file operations
- Pure analysis functions

### 2. Agent Composition

Commands can compose multiple agents:

```markdown
1. Invoke ticket-analyzer → Get gaps
2. Invoke pattern-discovery with gap context → Get reusable patterns
3. Invoke design-guardian with patterns → Get complexity flags
4. Aggregate all three → Present combined report
```

### 3. Input/Output Contracts

Each agent has:

- **Input Format**: Markdown with specific fields
- **Output Format**: Structured markdown report
- **Completeness Checklist**: Agent validates its own output
- **Success Criteria**: Clear definition of success

### 4. Preserve User Experience

After refactoring:

- Commands should work identically from user's perspective
- Same inputs produce same outputs
- Same approval gates
- Same error handling
- Same quality

### 5. Incremental Rollout

1. Refactor one command (PoC)
2. Test thoroughly
3. Compare to original
4. Get user feedback
5. Iterate on pattern
6. Apply to remaining commands

---

## Testing Strategy

### Unit Testing Agents

**Option 1: Manual testing**

- Create test tickets with known gaps
- Invoke agent via Task tool
- Validate output structure and quality

**Option 2: Integration testing**

- Use refactored command on real tickets
- Compare agent output to expected analysis
- Validate completeness scores

### Comparing Original vs Refactored

For each command:

1. Run original on test scenario
2. Run refactored on same scenario
3. Compare outputs (should be equivalent)
4. Measure context size (tokens used)
5. Measure execution time
6. Validate quality (completeness, accuracy)

### Acceptance Criteria

Refactored command is ready when:

- ✅ Produces equivalent output to original
- ✅ Reduces context by target % (65-75%)
- ✅ Maintains or improves quality
- ✅ Passes all approval gates
- ✅ User can't tell the difference (except faster/more reliable)

---

## Context Required to Continue

### Files to Reference

1. **Existing slash commands**:
   - `.claude/commands/write-next-tickets.md` (2,188 lines)
   - `.claude/commands/start-next-task.md` (1,915 lines)
   - `.claude/commands/review-story.md` (1,172 lines)
   - `.claude/commands/review-pr-comments.md` (360 lines)

2. **Created agents** (read for reference):
   - `.claude/agents/ticket-analyzer.md`
   - `.claude/agents/design-guardian.md`
   - `.claude/agents/git-state-analyzer.md`
   - `.claude/agents/specification-quality-checker.md`
   - `.claude/agents/pattern-discovery.md`
   - `.claude/agents/requirements-interviewer.md`

3. **Project context**:
   - `CLAUDE.md` (root - workflow rules)
   - `docs/tickets/CLAUDE.md` (ticket hierarchy structure)
   - Example tickets in `docs/tickets/` (for testing)

### Next Action

**Recommended**: Start with `/write-next-tickets` refactoring as proof-of-concept.

**Steps**:

1. Read `.claude/commands/write-next-tickets.md`
2. Read agent specifications to understand input/output
3. Create new file: `.claude/commands/write-next-tickets-v2.md`
4. Implement orchestration pattern:
   - Keep Steps 0, 2, 4 (orchestration)
   - Replace Step 1 with agent invocations
   - Replace Step 3.2 with requirements-interviewer invocation
   - Keep Step 3.3, 3.4, 3.5, 3.6 (file operations)
5. Test on real scenario
6. Compare to original
7. Document learnings

---

## Success Metrics

### Quantitative

- **Context reduction**: 71% overall (5,635 → 1,650 lines)
- **Per-command reduction**:
  - write-next-tickets: 73% (2,188 → 590)
  - start-next-task: 74% (1,915 → 445)
  - review-story: 69% (1,172 → 400)
- **Token usage**: Measure before/after
- **Execution time**: Should be similar or faster

### Qualitative

- **Maintainability**: Changes to analysis logic only require updating one agent
- **Reliability**: Smaller context reduces hallucination
- **Composability**: Commands can mix/match agents as needed
- **Clarity**: Separation of concerns makes code easier to understand

---

## Risk Mitigation

### Risk 1: Agent output doesn't match expected format

**Mitigation**:

- Define strict output formats in agent specs
- Include output validation in agents (completeness checklist)
- Test agent invocations independently before integrating

### Risk 2: Context still too large (agents invoked with full output)

**Mitigation**:

- Agents return structured markdown, not prose
- Commands can filter/summarize agent output
- Use multiple smaller agent calls vs one large call

### Risk 3: Loss of functionality during refactoring

**Mitigation**:

- Keep original commands until refactored versions validated
- Side-by-side testing (original vs refactored)
- Incremental rollout (one command at a time)
- User acceptance testing before archiving originals

### Risk 4: Agent coordination overhead

**Mitigation**:

- Clear input/output contracts
- Examples in each agent spec
- Composition patterns documented
- Troubleshooting guide

---

## Timeline Estimate

**Phase 1**: ✅ Complete (6 agents created)

**Phase 2**: 8-12 hours

- /write-next-tickets refactor: 4-5 hours (PoC - most complex)
- /start-next-task refactor: 2-3 hours (pattern established)
- /review-story refactor: 2-3 hours (pattern established)
- /review-pr-comments review: 1 hour (may not need refactoring)

**Phase 3**: 2-3 hours

- Agent usage guide: 1 hour
- Refactoring changelog: 30 minutes
- CLAUDE.md updates: 30 minutes
- Troubleshooting guide: 1 hour

**Phase 4**: 2-3 hours

- End-to-end testing: 1-2 hours
- Cleanup and final docs: 1 hour

**Total remaining**: 12-18 hours

---

## Questions for Decision

1. **Agent invocation method**: Use Task tool with "agent type" field, or separate tool per agent?
   - **Recommendation**: Use Task tool with agent type (keeps tool list manageable)

2. **Original command handling**: Archive or delete after refactoring?
   - **Recommendation**: Archive with `.bak` extension until validation complete

3. **Rollout strategy**: Replace all at once or gradual?
   - **Recommendation**: Gradual - refactor one, test, get feedback, iterate

4. **Agent versioning**: How to handle agent updates?
   - **Recommendation**: Version in filename if breaking change (e.g., `ticket-analyzer-v2.md`)

---

## References

- **Branch**: `mine-subagents-from-slash-commands`
- **Agents directory**: `.claude/agents/`
- **Commands directory**: `.claude/commands/`
- **This plan**: `SUBAGENT_REFACTOR_PLAN.md`

---

**Last Updated**: 2025-10-08
**Status**: Phase 1 complete, ready for Phase 2 (command refactoring)
**Next Step**: Refactor `/write-next-tickets` as proof-of-concept
