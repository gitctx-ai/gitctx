# STORY-0001.1.0: Development Environment Setup

**Parent Epic**: [EPIC-0001.1](../epics/EPIC-0001.1.md)  
**Status**: 🔵 Not Started  
**Story Points**: 5  
**Progress**: ░░░░░░░░░░ 0%

## User Story

As a **developer**  
I want **a complete project structure with BDD/TDD framework and quality gates**  
So that **I can develop gitctx following best practices from the start**

## Acceptance Criteria

- [ ] Project can be installed with `uv sync --all-extras`
- [ ] All quality gates run successfully with single command
- [ ] BDD framework set up with pytest-bdd and first test passing
- [ ] TDD framework ready with pytest and coverage configured
- [ ] Pre-commit hooks working for ruff, mypy, and tests
- [ ] GitHub Actions CI pipeline running on all pushes
- [ ] Project structure follows Python best practices
- [ ] All configurations in pyproject.toml (no separate config files)

## Child Tasks

| ID | Title | Status | Hours |
|----|-------|--------|-------|
| [TASK-0001.1.0.1](../tasks/TASK-0001.1.0.1.md) | Project Structure Setup | 🔵 Not Started | 2 |
| [TASK-0001.1.0.2](../tasks/TASK-0001.1.0.2.md) | pyproject.toml Configuration | 🔵 Not Started | 3 |
| [TASK-0001.1.0.3](../tasks/TASK-0001.1.0.3.md) | BDD/TDD Framework Setup | 🔵 Not Started | 4 |
| [TASK-0001.1.0.4](../tasks/TASK-0001.1.0.4.md) | Pre-commit Hooks Configuration | 🔵 Not Started | 2 |
| [TASK-0001.1.0.5](../tasks/TASK-0001.1.0.5.md) | CI/CD Pipeline Setup | 🔵 Not Started | 3 |

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
