# STORY-0001.1.0: Development Environment Setup

**Parent Epic**: [EPIC-0001.1](../epics/EPIC-0001.1.md)
**Status**: ✅ Complete
**Story Points**: 5
**Progress**: ██████████ 100%

## User Story

As a **developer**  
I want **a complete project structure with BDD/TDD framework and quality gates**  
So that **I can develop gitctx following best practices from the start**

## Acceptance Criteria

- [x] Project can be installed with `uv sync --all-extras`
- [x] All quality gates run successfully with single command
- [x] BDD framework set up with pytest-bdd and first test passing
- [x] TDD framework ready with pytest and coverage configured
- [x] Pre-commit hooks working for ruff, mypy, and tests
- [x] GitHub Actions CI pipeline running on all pushes
- [x] Project structure follows Python best practices
- [x] All configurations in pyproject.toml (except .coveragerc for subprocess coverage)

## Child Tasks

| ID | Title | Status | Hours |
|----|-------|--------|-------|
| [TASK-0001.1.0.1](../tasks/TASK-0001.1.0.1.md) | Project Structure Setup | ✅ Complete | 2 |
| [TASK-0001.1.0.2](../tasks/TASK-0001.1.0.2.md) | pyproject.toml Configuration | ✅ Complete | 3 |
| [TASK-0001.1.0.3](../tasks/TASK-0001.1.0.3.md) | BDD/TDD Framework Setup | ✅ Complete | 6 |
| [TASK-0001.1.0.4](../tasks/TASK-0001.1.0.4.md) | Pre-commit Hooks Configuration | ✅ Complete | 2 |
| [TASK-0001.1.0.5](../tasks/TASK-0001.1.0.5.md) | CI/CD Pipeline Setup | ✅ Complete | 3 |

## Post-Story Enhancements

After completing all 5 tasks, we made additional improvements during PR review:

### Workflow Documentation (Commit: docs(STORY-0001.1.0))

- Updated `CLAUDE.md` with comprehensive "Story-Driven Development Workflow" section
  - Core principles: 1 task = 1 commit, manual approval gates, continuous tracking
  - Workflow steps for each task with quality gates
  - PR creation guidelines with cross-references
- Added "PR Workflow and GitHub Links" guide to `docs/tickets/CLAUDE.md`
  - Documented proper GitHub blob URL format for PR bodies
  - Provided complete example PR body structure
  - Added PR creation commands and review checklist
- Documented commit message standards with TASK-ID scope pattern
- Locked in story-driven workflow for future development sessions

### Security Hardening (2 Commits on TASK-0001.1.0.3)

**Issue Discovered**: E2E tests were using `CliRunner.invoke()` (in-process), not true subprocess execution. This did not provide complete isolation from developer SSH keys, GPG keys, and git config.

**Fixes Applied**:
1. **Subprocess Isolation** - Changed E2E step definitions to use `subprocess.run()`
   - Now executes `python -m gitctx` as actual subprocess
   - Provides REAL isolation matching how users run gitctx
2. **Comprehensive Validation** - Added 4 new security validation tests
   - Tests verify git operations, GPG isolation, and gitctx subprocess execution
3. **Subprocess Coverage** - Enabled coverage tracking for subprocess calls
   - Created `.coveragerc` and `sitecustomize.py` for subprocess coverage
   - Passes coverage env vars to subprocesses via fixtures

**Impact**:
- Tests increased from 12 → **16**
- Coverage maintained at **85.00%** (meets 85% threshold)
- True subprocess security isolation verified
- Workflow fully documented for future development

## BDD Specifications

Not applicable to this story

## Technical Design

### Project Structure

```bash
gitctx/
├── src/
│   └── gitctx/
│       ├── __init__.py
│       ├── __main__.py       # Entry point
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── main.py       # Typer app
│       │   ├── config.py     # Config command
│       │   ├── index.py      # Index command
│       │   ├── search.py     # Search command
│       │   └── clear.py      # Clear command
│       ├── core/
│       │   ├── __init__.py
│       │   └── ...           # Core logic (future)
│       └── utils/
│           ├── __init__.py
│           └── ...           # Utilities
├── tests/
│   ├── __init__.py
│   ├── conftest.py           # Shared fixtures
│   ├── e2e/
│   │   ├── features/         # Gherkin files
│   │   ├── steps/            # Step definitions
│   │   └── conftest.py
│   └── unit/
│       └── ...               # Unit tests
├── docs/                      # Documentation
├── pyproject.toml            # All configuration
├── .gitignore
├── .pre-commit-config.yaml
├── README.md
└── CLAUDE.md                 # Development guide
```

### Quality Gates Command

```bash
# Single command to run all checks (to be configured via poe)
uv run quality

# Which runs:
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src
uv run pytest

# And to apply automatic fixes
uv run fix

# Which runs
uv run ruff check --fix src tests
uv run ruff format src tests
```

## Dependencies

### Core Dependencies

- `typer[all]` - CLI framework
- `rich` - Terminal formatting
- `pyyaml` - Configuration management

### Development Dependencies

- `pytest` - Testing framework
- `pytest-bdd` - BDD testing
- `pytest-cov` - Coverage reporting
- `mypy` - Type checking
- `ruff` - Linting and formatting
- `pre-commit` - Git hooks
- `poethepoet` - Development tasks via `uv run`

## Success Metrics

- **Setup Time**: <5 minutes for a new developer
- **CI Build Time**: <2 minutes for full pipeline
- **Test Coverage**: >90% from the start
- **Documentation**: Complete setup guide in README

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Complex setup deters contributors | Clear documentation, single install command |
| CI pipeline too slow | Parallelize jobs, cache dependencies |
| Configuration conflicts | Everything in pyproject.toml |
| Platform-specific issues | Test on Linux, macOS, Windows in CI |

## Notes

- This story establishes the foundation for all future development
- Following BDD/TDD strictly from the beginning ensures quality
- All developers should be able to get started within 5 minutes
- The setup should be foolproof and well-documented

---

**Created**: 2025-09-28  
**Last Updated**: 2025-09-28
