# Specialized Agent Architecture

This directory contains specialized agents used by gitctx slash commands to provide focused, reliable analysis while reducing context size.

## Overview

Instead of monolithic slash commands with embedded analysis logic, we use **specialized agents** that:

1. **Focus on one type of analysis** - Each agent is an expert in its domain
2. **Have clear input/output contracts** - Predictable, structured data
3. **Can be composed** - Commands invoke multiple agents and aggregate results
4. **Reduce context size** - Analysis logic lives in agents, not commands
5. **Are reusable** - Multiple commands can use the same agent

## Architecture Pattern

```text
Slash Command (Orchestrator)
    ↓
    ├─→ Agent 1 (analyze X) → returns structured data
    ├─→ Agent 2 (analyze Y) → returns structured data
    ├─→ Agent 3 (analyze Z) → returns structured data
    ↓
Aggregate results → Present to user → Execute actions
```

## Available Agents

### 1. ticket-analyzer.md

**Purpose**: Deep analysis of ticket structure, hierarchy, completeness, and state accuracy.

**Use Cases**:
- Analyze story completeness before starting work
- Validate task readiness
- Identify gaps in ticket hierarchy
- Compare ticket documentation to git reality

**Input Format**:
```markdown
**Analysis Type**: {story-deep | ticket-completeness | hierarchy-gaps | task-readiness}
**Target**: {branch name | ticket ID | directory path}
**Scope**: {single-ticket | story-and-tasks | epic-and-stories | full-hierarchy}
**Mode**: {pre-work | in-progress}
```

**Output**: Structured markdown with completeness scores, issues, and recommendations.

**Used By**: `/start-next-task`, `/write-next-tickets`, `/review-story`

---

### 2. design-guardian.md

**Purpose**: Enforce anti-overengineering principles and validate pattern reuse.

**Use Cases**:
- Detect unnecessary abstractions (only one implementation)
- Flag premature optimization (no metrics showing need)
- Identify unnecessary caching (small data, CLI tools)
- Distinguish valid complexity from overengineering

**Input Format**:
```markdown
**Review Type**: {story-review | task-review | epic-review}
**Target**: {ticket ID or path}
**Context**: {brief description of what's being built}
**Proposed Work**: {ticket content to analyze}
```

**Output**: Markdown with complexity flags, simpler alternatives, and overengineering scores.

**Used By**: `/write-next-tickets`, `/review-story`, `/start-next-task`

---

### 3. git-state-analyzer.md

**Purpose**: Analyze git commits and file changes, compare to ticket documentation.

**Use Cases**:
- Detect ticket drift (status doesn't match commits)
- Validate progress percentages
- Find undocumented changes
- Identify uncommitted work

**Input Format**:
```markdown
**Analysis Type**: {commit-history | ticket-drift | progress-validation}
**Branch**: {branch name}
**Ticket Context**: {story/epic ID and path}
**Include uncommitted**: {true | false}
```

**Output**: Git activity summary, drift items with proposed fixes, progress accuracy.

**Used By**: `/review-story`, `/start-next-task`

---

### 4. specification-quality-checker.md

**Purpose**: Detect vague/ambiguous language, enforce quantified requirements.

**Use Cases**:
- Find vague terms (handle, support, simple, basic)
- Detect missing details (TBD, etc., as needed)
- Flag unquantified requirements (fast, efficient)
- Score agent-executability (can autonomous agent implement this?)

**Input Format**:
```markdown
**Check Type**: {full-ticket | acceptance-criteria | technical-design | task-steps}
**Target**: {ticket ID or path}
**Strictness**: {lenient | standard | strict}
**Content to Check**: {ticket content}
```

**Output**: Ambiguity scores, vague terms with concrete replacements, clarity recommendations.

**Used By**: `/write-next-tickets`, `/review-story`, `/start-next-task`

---

### 5. pattern-discovery.md

**Purpose**: Survey codebase for reusable patterns, fixtures, helpers, and anti-patterns.

**Use Cases**:
- Find existing test fixtures to reuse
- Identify similar tests as patterns to follow
- Discover utility functions and helpers
- Note documented anti-patterns to avoid

**Input Format**:
```markdown
**Discovery Type**: {full-survey | focused-domain | fixture-lookup | test-pattern-search}
**Domain**: {e2e-testing | unit-testing | source-code | documentation}
**Context**: {what you're trying to accomplish}
**Related modules**: {list}
```

**Output**: Fixture inventory, test patterns, source patterns, anti-patterns, reuse score.

**Used By**: `/start-next-task`, `/write-next-tickets`

---

### 6. requirements-interviewer.md

**Purpose**: Conduct interactive requirement capture to transform vague ideas into concrete specs.

**Use Cases**:
- Gather complete requirements for new tickets
- Ask progressive questions (high-level → details)
- Probe vague responses until concrete
- Challenge overengineering proposals

**Input Format**:
```markdown
**Interview Type**: {initiative | epic | story | task}
**Ticket ID**: {TICKET-XXXX or "NEW"}
**Parent Context**: {parent ticket ID and summary}
**Gap Analysis**: {from ticket-analyzer}
**Pattern Context**: {from pattern-discovery}
**Missing Details**: {list}
**Interview Goal**: {target completeness %}
```

**Output**: Captured requirements in structured markdown, completeness analysis.

**Used By**: `/write-next-tickets`

---

## Agent Composition Patterns

### Pattern 1: Sequential Analysis

Use when each agent needs output from the previous one:

```text
1. ticket-analyzer → identifies gaps
2. requirements-interviewer → fills gaps (using gap analysis)
3. specification-quality-checker → validates clarity (using captured requirements)
4. Draft ticket with validated requirements
```

### Pattern 2: Parallel Analysis

Use when agents can run independently:

```text
Launch in parallel:
├─→ ticket-analyzer (completeness)
├─→ pattern-discovery (reusable patterns)
├─→ design-guardian (complexity check)
└─→ specification-quality-checker (clarity)

Wait for all → Aggregate results → Present combined report
```

### Pattern 3: Conditional Invocation

Use when some agents are only needed in certain modes:

```text
Always invoke:
├─→ ticket-analyzer
└─→ specification-quality-checker

IF in-progress mode:
└─→ git-state-analyzer

Aggregate and present
```

## How to Use Agents in Slash Commands

### Step 1: Invoke Agent via Task Tool

```markdown
Use Task tool (general-purpose) with specialized agent:

**Agent Type**: {agent-name}

{Provide input according to agent's specification}

## Your Mission

{Agent-specific instructions from agent file}

Execute the analysis now.
```

### Step 2: Store Agent Output

```markdown
Store output as variable for later use:

`TICKET_QUALITY = {output from ticket-analyzer}`
`PATTERN_ANALYSIS = {output from pattern-discovery}`
```

### Step 3: Aggregate Multiple Agent Results

```markdown
# Combined Analysis

## From ticket-analyzer:
{TICKET_QUALITY}

## From pattern-discovery:
{PATTERN_ANALYSIS}

## From design-guardian:
{COMPLEXITY_CHECK}

---

**Synthesis**: {How findings relate to each other}
```

### Step 4: Present to User

```markdown
Show aggregated analysis to user with:
- Clear summary
- Prioritized findings
- Proposed actions
- Request for approval
```

## Best Practices

### DO

- ✅ Use agents for analysis, commands for orchestration
- ✅ Invoke agents in parallel when possible
- ✅ Store agent outputs for later reference
- ✅ Aggregate results before presenting to user
- ✅ Pass context between agents (e.g., gap analysis → interviewer)

### DON'T

- ❌ Duplicate agent logic in slash commands
- ❌ Invoke agents sequentially if they can run in parallel
- ❌ Skip agent validation in commands
- ❌ Ignore agent recommendations
- ❌ Mix orchestration and analysis logic

## Error Handling Strategy

### Agent Output Validation

**Always validate agent outputs before using them:**

```python
import json
from typing import Any

def validate_agent_output(
    output: str,
    agent_name: str,
    required_keys: list[str]
) -> dict[str, Any]:
    """
    Validate agent output is valid JSON with required keys.

    Args:
        output: Raw agent output string
        agent_name: Name of agent for error messages
        required_keys: List of required top-level keys

    Returns:
        Parsed and validated JSON dict

    Raises:
        ValueError: If output is invalid or missing keys
    """
    # Parse JSON
    try:
        data = json.loads(output)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"{agent_name} returned invalid JSON: {str(e)}\n"
            f"Output preview: {output[:200]}"
        )

    # Validate required keys
    missing = set(required_keys) - set(data.keys())
    if missing:
        raise ValueError(
            f"{agent_name} output missing required keys: {missing}\n"
            f"Available keys: {list(data.keys())}"
        )

    return data


# Usage in slash commands
try:
    ticket_analysis = invoke_agent("ticket-analyzer", input_spec)
    validated = validate_agent_output(
        ticket_analysis,
        "ticket-analyzer",
        ["analysis_type", "completeness_score", "issues"]
    )
except ValueError as e:
    # Handle validation error
    show_error(f"Agent validation failed: {e}")
    return
```

### Graceful Degradation

**When agents fail, commands should degrade gracefully:**

```python
def invoke_agent_safe(
    agent_name: str,
    input_spec: str,
    timeout: int = 300
) -> dict[str, Any] | None:
    """
    Invoke agent with error handling and timeout.

    Returns None if agent fails, allowing command to continue
    with reduced functionality.
    """
    try:
        output = invoke_agent(agent_name, input_spec, timeout=timeout)
        return validate_agent_output(output, agent_name, EXPECTED_KEYS[agent_name])
    except TimeoutError:
        log.warning(f"{agent_name} timed out after {timeout}s")
        return None
    except ValueError as e:
        log.warning(f"{agent_name} validation failed: {e}")
        return None
    except Exception as e:
        log.error(f"{agent_name} unexpected error: {e}")
        return None


# Usage: Continue with reduced analysis
ticket_analysis = invoke_agent_safe("ticket-analyzer", spec)
pattern_analysis = invoke_agent_safe("pattern-discovery", spec)

if not ticket_analysis:
    show_warning("Ticket analysis unavailable - continuing with limited checks")
    # Proceed with basic validation instead

if pattern_analysis:
    show_patterns(pattern_analysis["fixtures_available"])
else:
    show_warning("Pattern discovery failed - manual pattern search required")
```

### Parallel Agent Error Handling

**When running agents in parallel, decide on fail-fast vs continue:**

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def invoke_agents_parallel(
    agents: list[tuple[str, str]],  # [(agent_name, input_spec), ...]
    fail_fast: bool = False
) -> dict[str, dict[str, Any]]:
    """
    Invoke multiple agents in parallel.

    Args:
        agents: List of (agent_name, input_spec) tuples
        fail_fast: If True, cancel remaining on first failure

    Returns:
        Dict mapping agent_name to output (or None if failed)
    """
    results = {}

    with ThreadPoolExecutor(max_workers=len(agents)) as executor:
        # Submit all agent invocations
        futures = {
            executor.submit(invoke_agent_safe, name, spec): name
            for name, spec in agents
        }

        # Collect results
        for future in as_completed(futures):
            agent_name = futures[future]

            try:
                result = future.result()
                results[agent_name] = result

                if fail_fast and result is None:
                    # Cancel remaining agents
                    for f in futures:
                        f.cancel()
                    raise RuntimeError(f"{agent_name} failed (fail-fast mode)")

            except Exception as e:
                log.error(f"{agent_name} failed: {e}")
                results[agent_name] = None

                if fail_fast:
                    raise

    return results


# Usage: Continue-on-error mode (default)
results = invoke_agents_parallel([
    ("ticket-analyzer", ticket_spec),
    ("pattern-discovery", pattern_spec),
    ("design-guardian", design_spec),
])

# Check which agents succeeded
successful = [name for name, result in results.items() if result is not None]
failed = [name for name, result in results.items() if result is None]

if failed:
    show_warning(f"Some agents failed: {failed}. Continuing with {successful}.")
```

### User-Facing Error Messages

**Translate technical errors into actionable guidance:**

```python
def handle_agent_error(agent_name: str, error: Exception) -> str:
    """Generate user-friendly error message with action steps."""

    error_guidance = {
        "ticket-analyzer": (
            "Unable to analyze ticket completeness.\n"
            "**Action**: Manually review story README and task files for:\n"
            "  - Missing acceptance criteria\n"
            "  - Incomplete technical design\n"
            "  - Vague task descriptions"
        ),
        "pattern-discovery": (
            "Pattern discovery failed.\n"
            "**Action**: Manually search for reusable fixtures:\n"
            "  - Check tests/conftest.py for existing fixtures\n"
            "  - Search for similar tests: grep -r 'test_similar' tests/\n"
            "  - Review existing helpers in src/gitctx/utils/"
        ),
        "git-state-analyzer": (
            "Git analysis unavailable.\n"
            "**Action**: Manually verify ticket status matches commits:\n"
            "  - Run: git log main..HEAD --oneline\n"
            "  - Compare commits to task checklist\n"
            "  - Update task statuses if drift detected"
        ),
    }

    default_message = (
        f"{agent_name} analysis failed.\n"
        f"**Action**: Proceed with manual review or skip this validation."
    )

    return error_guidance.get(agent_name, default_message)
```

### Retry Strategy

**For transient failures, implement retry with backoff:**

```python
import time

def invoke_agent_with_retry(
    agent_name: str,
    input_spec: str,
    max_retries: int = 2,
    backoff: float = 2.0
) -> dict[str, Any] | None:
    """
    Invoke agent with exponential backoff retry.

    Useful for transient failures (network, rate limits, etc.)
    """
    for attempt in range(max_retries + 1):
        try:
            output = invoke_agent(agent_name, input_spec)
            return validate_agent_output(output, agent_name, EXPECTED_KEYS[agent_name])

        except (TimeoutError, ConnectionError) as e:
            if attempt < max_retries:
                wait_time = backoff ** attempt
                log.warning(
                    f"{agent_name} attempt {attempt + 1} failed: {e}. "
                    f"Retrying in {wait_time}s..."
                )
                time.sleep(wait_time)
            else:
                log.error(f"{agent_name} failed after {max_retries + 1} attempts")
                return None

        except ValueError as e:
            # Validation errors don't benefit from retry
            log.error(f"{agent_name} validation error (not retrying): {e}")
            return None
```

### Error Reporting to Users

**When presenting analysis results, clearly indicate partial results:**

```text
# Story Analysis Report

## ✅ Completed Analyses
- **Ticket Structure**: 85% complete (see details below)
- **Pattern Discovery**: 12 reusable fixtures found

## ⚠️ Partial Analyses
- **Design Complexity**: Analysis timed out
  - **Impact**: Cannot validate against overengineering patterns
  - **Action**: Manual review recommended for abstractions and caching

## ❌ Failed Analyses
- **Git State**: Analysis failed (not a git branch)
  - **Impact**: Cannot detect ticket drift
  - **Action**: Ensure you're on the correct story branch

---

**Overall Confidence**: Medium (2/3 analyses completed)
```

## Context Reduction Achieved

| Command | Before | After | Reduction |
|---------|--------|-------|-----------|
| /write-next-tickets | 2,187 lines | 898 lines | 59% |
| /start-next-task | 1,941 lines | 1,126 lines | 42% |
| /review-story | 1,171 lines | 754 lines | 36% |
| /review-pr-comments | 361 lines | 361 lines | 0% (already focused) |
| **TOTAL** | **5,660 lines** | **3,139 lines** | **45% overall** |

**Agent files**: 6 agents, ~3,500 lines total (reusable across commands)

## Troubleshooting

**For systematic error handling patterns, see [Error Handling Strategy](#error-handling-strategy) above.**

### Agent returns unexpected format

**Problem**: Agent output doesn't match expected structure.

**Solution**:
- Check that input format is correct
- Verify agent file has clear output format specification
- Review agent's completeness checklist
- Implement output validation (see [Agent Output Validation](#agent-output-validation))

### Agent analysis incomplete

**Problem**: Agent doesn't analyze all required aspects.

**Solution**:
- Ensure input provides all necessary context
- Check if scope parameter is set correctly
- Verify agent file covers all analysis requirements

### Multiple agents give conflicting recommendations

**Problem**: design-guardian says "too complex", but ticket-analyzer says "needs more detail".

**Solution**:
- Review the specific flags from each agent
- Valid complexity (security, testing) is different from overengineering
- Agent recommendations complement each other, not compete

### Agent takes too long

**Problem**: Agent analysis runs for >5 minutes.

**Solution**:
- Reduce scope (use focused vs full)
- Check if agent is reading too many files
- Consider breaking analysis into smaller chunks

## Contributing New Agents

When creating a new specialized agent:

1. **Single Responsibility**: Agent should do ONE type of analysis well
2. **Clear Contract**: Document input format and output format explicitly
3. **Completeness Checklist**: Agent validates its own output
4. **Examples**: Include examples in agent file
5. **Reusability**: Design for use by multiple commands
6. **Error Handling**: Specify what to do when analysis fails

### Agent Template

```markdown
# {Agent Name}

**Purpose**: {One-sentence description}

**Used by**: {List of slash commands}

**Context Reduction**: Removes ~X lines from each command

---

## Agent Mission

{Detailed description of what agent does}

---

## Input Format

```markdown
**Field 1**: {description}
**Field 2**: {description}
**Optional Field**: {description}
```

---

## Output Format

```markdown
{Expected structure}
```

---

## Analysis Logic

{Step-by-step what agent does}

---

## Completeness Checklist

Before returning, agent must:
- [ ] {Criterion 1}
- [ ] {Criterion 2}

---

## Examples

### Example 1: {scenario}

**Input**:
```
{example input}
```

**Output**:
```
{example output}
```

---

## See Also

- {Related agent}
- {Related command}
```

---

## References

- **Refactoring Plan**: `SUBAGENT_REFACTOR_PLAN.md`
- **Command Directory**: `.claude/commands/`
- **Agent Directory**: `.claude/agents/` (you are here)
- **Root Workflow**: `CLAUDE.md`
