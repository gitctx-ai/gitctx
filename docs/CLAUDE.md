# CLAUDE.md - Documentation Guidelines for docs/

This document defines documentation standards for the gitctx documentation directory.

**Related Documentation:**

- [Root CLAUDE.md](../CLAUDE.md) - Overview and workflow
- [Vision Guidelines](vision/CLAUDE.md) - Product strategy
- [Ticket Workflow](tickets/CLAUDE.md) - Development tracking
- [Architecture Standards](architecture/CLAUDE.md) - Technical design

## 🚨 Documentation Philosophy

**Build the CLI first. Test everything. Ship working software continuously.**

Documentation should:

1. Support BDD/TDD development workflow
2. Be actionable and specific
3. Focus on user outcomes
4. Track measurable progress

## Documentation Structure

The `docs/` directory organizes project documentation by concern:

- **vision/** - Product strategy, roadmap, and success metrics
- **tickets/** - Development tracking with initiative/epic/story hierarchy  
- **architecture/** - Technical design, ADRs, and system documentation
- **history/** - Historical documentation archive (future)

Each subdirectory has its own CLAUDE.md with specific guidelines.

## Success Metrics & Testing

For metrics tracking and canonical test suites, see:

- [Success Metrics Dashboard](vision/success-metrics.md) - Current metrics and KPIs
- [Vision Guidelines](vision/CLAUDE.md#canonical-test-suites) - Canonical test patterns
- [Test Configuration](../pyproject.toml) - Tool configurations (mypy, ruff, coverage)
- [Unit Testing](../tests/unit/CLAUDE.md) - TDD practices and performance testing
- [E2E Testing](../tests/e2e/CLAUDE.md) - BDD scenarios and patterns

## Writing Documentation

### Document Types

#### 1. Vision Documents (`docs/vision/*.md`)

- **ROADMAP.md** - Strategic initiatives and planning
- **success-metrics.md** - KPIs dashboard and tracking
- Future vision documents as needed

#### 2. Architecture Documents (`docs/architecture/*.md`)

Technical documentation including:

- System design diagrams (Mermaid)
- Component interactions
- Data flow documentation
- API specifications
- Architecture Decision Records (ADRs)

#### 3. Ticket Documents (`docs/tickets/*.md`)

Development tracking hierarchy:

- Initiatives (INIT-NNNN) - Strategic goals
- Epics (EPIC-NNNN.N) - Feature sets
- Stories (STORY-NNNN.N.N) - User stories
- Tasks (TASK-NNNN.N.N.N) - Technical work
- Bugs (BUG-NNNN) - Issues found

See [docs/tickets/CLAUDE.md](tickets/CLAUDE.md) for complete workflow.

### Writing Style Guidelines

#### Use Active Voice

✅ "The scanner respects .gitignore patterns"
❌ "Patterns are respected by the scanner"

#### Be Specific and Measurable

✅ "Search returns results in <2 seconds for 10K files"
❌ "Search should be fast"

#### Include Examples

✅ Show actual command usage and output
❌ Abstract descriptions without examples

#### Focus on Outcomes

✅ "So that users can find relevant code quickly"
❌ "To implement vector search"

## Development Tracking

For complete ticket hierarchy and status tracking:

- See [docs/tickets/CLAUDE.md](tickets/CLAUDE.md) for workflow
- Use the standardized status indicators defined there

## Technical Documentation Standards

### Code Examples

Always show complete, runnable examples:

```python
# Good - Complete example
from gitctx.core.chunker import Chunker

chunker = Chunker(max_tokens=500, overlap=50)
chunks = chunker.chunk("long text here...")
for chunk in chunks:
    print(f"Chunk: {chunk.content[:50]}...")
```

```python
# Bad - Incomplete snippet
chunker.chunk(text)  # What is chunker? What is text?
```

### Configuration References

For tool configurations, reference the source of truth:

- **Mypy settings**: See [pyproject.toml](../pyproject.toml)
- **Ruff configuration**: See [pyproject.toml](../pyproject.toml)
- **Coverage settings**: See [pyproject.toml](../pyproject.toml)

### Command Examples

Show actual command and expected output:

```bash
$ gitctx search "authentication"
Searching... ━━━━━━━━━━━━━━━━━━━━ 100% 0:00:02

auth.py:15 (score: 0.89)
def authenticate(user, password):
    """Authenticate a user against the database."""
    
login.py:23 (score: 0.76)  
def check_authentication():
    """Verify user is authenticated."""
```

## Markdown Standards

### File Naming

- Tickets: `{TYPE}-{ID}.md` (e.g., EPIC-0001.2.md, STORY-0001.2.3.md)
- Guides: `lowercase-with-dashes.md`
- CLAUDE files: Always `CLAUDE.md`

### Heading Hierarchy

```markdown
# Document Title
## Major Section
### Subsection
#### Detail Level
```

### Task Lists

```markdown
- [x] Completed task
- [ ] Pending task
- [ ] Future task
```

### Tables

```markdown
| Header 1 | Header 2 | Header 3 |
|----------|----------|----------|
| Data     | Data     | Data     |
```

### Code Blocks

Always specify language:

```markdown
​```python
code here
​```
```

## Documentation Review Checklist

Before committing documentation:

- [ ] Follows structure templates
- [ ] Includes concrete examples
- [ ] Has measurable success criteria
- [ ] Uses active voice
- [ ] Specifies BDD/TDD requirements
- [ ] Links to related documents
- [ ] Code examples are complete and runnable

## Maintaining Documentation

### When to Update

Update documentation:

- **Before** implementing new features (BDD)
- **During** implementation (clarifications)
- **After** completion (lessons learned)
- **Never** leave outdated docs

### Documentation Debt

Track documentation debt as technical debt:

- Missing epic specifications
- Outdated examples
- Incomplete architecture docs
- Untracked metrics

## Resources

- [Markdown Guide](https://www.markdownguide.org/)
- [Gherkin Reference](https://cucumber.io/docs/gherkin/)
- [Mermaid Diagrams](https://mermaid-js.github.io/) (for architecture diagrams)