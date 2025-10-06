# STORY-0001.1.2: Real Configuration Management

**Parent Epic**: [EPIC-0001.1](../README.md)
**Status**: ✅ Complete
**Story Points**: 5 (was 2, +1 for TUI, +1 for PR review, +1 for performance/docs/polish)
**Progress**: ██████████ 100% (10/10 tasks complete, 7.75/7.25 hours actual)

## User Story

As a **developer**
I want **persistent configuration with user and repo separation**
So that **my API keys stay secure in my home directory while team settings are shared in the repo, with my existing OPENAI_API_KEY automatically recognized**

## Acceptance Criteria

- [x] Config uses Pydantic Settings for type-safe validation
- [x] **User config** (`~/.gitctx/config.yml`) stores API keys only with file permissions 0600
- [x] **Repo config** (`.gitctx/config.yml`) stores team settings only (search, index, model) with file permissions 0644
- [x] NEW `config init` subcommand creates repo structure:
  - Creates `.gitctx/config.yml` with defaults
  - Creates `.gitctx/.gitignore` to exclude `db/`, `logs/`, `*.log`
- [x] User config precedence (API keys only):
  1. Provider standard env var (`OPENAI_API_KEY`)
  2. User YAML file (`~/.gitctx/config.yml`)
- [x] Repo config precedence (team settings only):
  1. gitctx-prefixed env var (`GITCTX_SEARCH__LIMIT`)
  2. Repo YAML file (`.gitctx/config.yml`)
- [x] Type validation prevents invalid configurations (e.g., `search.limit` must be int)
- [x] API keys auto-masked using SecretStr
- [x] CLI automatically routes config by key pattern (api_keys.* → user, else → repo)
- [x] **TUI: Progressive disclosure** - All config commands support `-v/--verbose` and `-q/--quiet` flags
- [x] **TUI: Default mode is terse** - `config init` shows single line, `config get` shows value only (git-like)
- [x] **TUI: Verbose mode shows details** - `config get --verbose` shows key and source, `config list --verbose` shows all sources
- [x] **TUI: Quiet mode suppresses output** - All commands support `--quiet` for scripting
- [x] **TUI: Platform-aware symbols** - Use ✓/✗/⚠️/💡 on modern terminals, [OK]/[X]/[!]/[i] on Windows cmd.exe
- [x] **TUI: First-run tips** - Show tip box once for config command, then hide forever
- [x] **TUI: Standard exit codes** - Exit code 2 for usage errors, 6 for permission denied, 1 for general errors
- [x] `config get` default shows value only (terse), `--verbose` shows key and source
- [x] `config list` default hides sources for defaults, `--verbose` shows all sources
- [x] **Security**: Impossible to store API keys in repo config (enforced by Pydantic models)
- [x] Maintain CLI interface contract (all STORY-0001.1.1 tests must pass - source indicators are additive enhancements, not breaking changes)
- [x] Cross-platform compatibility: Config paths work correctly on Windows/macOS/Linux
- [x] OpenAI only (no other providers in MVP)
- [x] All BDD scenarios pass (persistence, precedence, validation, security, TUI compliance) - 19/19 passing[^1]

[^1]: 19 scenarios = 10 core config (persistence/precedence) + 9 TUI compliance (progressive disclosure, symbols, tips)
- [x] Unit test coverage ≥ 85% (actual: 94.55%)
- [x] ~~Config caching reduces repeated file I/O~~ - **Eliminated**: CLI process model makes caching unnecessary (<1KB files, <10ms load time per commit d2c8899)
- [x] Code organization meets quality thresholds (no functions >50 lines, no modules >500 lines, cyclomatic complexity ≤10 except get_source()=11, addressed in TASK-7)
- [x] Edge cases are tested (Unicode [emoji, Chinese, RTL], corruption [truncated, malformed], auto-create directories)
- [x] Comprehensive user documentation exists in `docs/configuration.md`
- [x] Windows-specific tests pass in CI

## Child Tasks

| ID | Title | Status | Hours |
|----|-------|--------|-------|
| [TASK-0001.1.2.1](TASK-0001.1.2.1.md) | Write BDD Scenarios for User/Repo Config Separation | ✅ Complete | 1.0 |
| [TASK-0001.1.2.2](TASK-0001.1.2.2.md) | Implement User and Repo Config with Pydantic Settings | ✅ Complete | 1.0 |
| [TASK-0001.1.2.3](TASK-0001.1.2.3.md) | Integrate with CLI Commands and Add Config Init | ✅ Complete | 2.5 |
| [TASK-0001.1.2.4](TASK-0001.1.2.4.md) | Security Hardening - Permission Checks | ✅ Complete | 0.5 |
| [TASK-0001.1.2.5](TASK-0001.1.2.5.md) | Code Documentation Improvements | ✅ Complete | 0.25 |
| [TASK-0001.1.2.6](TASK-0001.1.2.6.md) | User-Friendly Validation Errors | ✅ Complete | 0.5 |
| [TASK-0001.1.2.7](TASK-0001.1.2.7.md) | Fix get_source() Complexity Violation | ✅ Complete | 0.25 |
| [TASK-0001.1.2.8](TASK-0001.1.2.8.md) | Add Essential Edge Case Tests | ✅ Complete | 0.25 |
| [TASK-0001.1.2.9](TASK-0001.1.2.9.md) | Create Configuration User Documentation | ✅ Complete | 1.0 |
| [TASK-0001.1.2.10](TASK-0001.1.2.10.md) | Add Windows CI Integration Tests | ✅ Complete | 0.5 |

**Total**: 7.25 hours (was 2.0, +2.5 TUI, +1.25 PR review, +1.5 essential polish)
**Removed**: 3.25 hours of overengineering eliminated

**Scope Changes**:
- TASK-7 (config caching, 1.0h) eliminated - CLI architecture makes caching unnecessary (commit d2c8899)
- TASK-8 reduction (1.5h → 0.25h) - Clean code needs focused complexity fix, not full refactor
- Net reduction: 2.25 hours of polish work deemed unnecessary after implementation review

## Story Evolution

**Initial Scope** (2025-10-04): Tasks 1-3 for core configuration implementation (2.0 hours)

**Scope Additions**:
- **2025-10-05 (TUI Compliance)**: Added TUI requirements to TASK-3, increased to 2.5 hours
- **2025-10-05 (PR #4 Review)**: Added TASK-4, TASK-5, TASK-6 for security, docs, UX (1.25 hours)
- **2025-10-05 (Performance & Polish)**: Added TASK-7 through TASK-11 for caching, refactoring, edge cases, documentation, Windows CI (4.5 hours)

**Scope Reductions**:
- **2025-10-05 (Overengineering Removal)**: Removed original TASK-7 (config caching, 1.0h) - CLI process model makes caching pointless. Redesigned original TASK-8 as focused complexity fix (1.5h → 0.25h) - config module is clean, needs targeted fix not refactor. Tasks renumbered 8→7, 9→8, 10→9, 11→10. Net reduction: 3.25 hours.

**Rationale**: PR review feedback identified gaps in security hardening, code documentation, user-friendly errors, edge case coverage, user documentation, and cross-platform testing. Subsequent focused review identified overengineering in proposed caching and refactoring tasks. Final scope balances production quality with pragmatic implementation.

## BDD Specifications

New scenarios to add to [tests/e2e/features/cli.feature](../../../../tests/e2e/features/cli.feature):

```gherkin
Scenario: config init creates repo structure (default terse output)
  When I run "gitctx config init"
  Then the exit code should be 0
  And the output should be exactly "Initialized .gitctx/"
  And the output should NOT contain "Created"
  And the file ".gitctx/config.yml" should exist
  And the file ".gitctx/.gitignore" should exist
  And ".gitctx/.gitignore" should contain "# LanceDB vector database - never commit"
  And ".gitctx/.gitignore" should contain "db/"
  And ".gitctx/.gitignore" should contain "# Application logs - never commit"
  And ".gitctx/.gitignore" should contain "logs/"
  And ".gitctx/.gitignore" should contain "*.log"

Scenario: API keys stored in user config only
  When I run "gitctx config set api_keys.openai sk-test123"
  Then the exit code should be 0
  And the output should contain "set api_keys.openai"
  And the user config file should exist at "~/.gitctx/config.yml"
  And the file "~/.gitctx/config.yml" should contain "api_keys:"
  And the file "~/.gitctx/config.yml" should contain "openai:"
  And the file "~/.gitctx/config.yml" should contain "sk-test123"
  And the file ".gitctx/config.yml" should NOT contain "api_keys"
  And the file ".gitctx/config.yml" should NOT contain "sk-test123"

Scenario: Repo settings stored in repo config only
  Given I run "gitctx config init"
  When I run "gitctx config set search.limit 20"
  Then the exit code should be 0
  And the output should contain "set search.limit"
  And the file ".gitctx/config.yml" should contain "search:"
  And the file ".gitctx/config.yml" should contain "limit: 20"
  And the file "~/.gitctx/config.yml" should NOT contain "search"
  And the file "~/.gitctx/config.yml" should NOT contain "limit"

Scenario: OPENAI_API_KEY env var overrides user config
  Given user config contains "api_keys:\n  openai: sk-file123"
  And environment variable "OPENAI_API_KEY" is "sk-env456"
  When I run "gitctx config get api_keys.openai --verbose"
  Then the output should contain "sk-...456"
  And the output should contain "(from OPENAI_API_KEY)"

Scenario: GITCTX env var overrides repo config
  Given repo config contains "search:\n  limit: 10"
  And environment variable "GITCTX_SEARCH__LIMIT" is "30"
  When I run "gitctx config get search.limit --verbose"
  Then the output should contain "30"
  And the output should contain "(from GITCTX_SEARCH__LIMIT)"

Scenario: config list shows both user and repo settings
  Given user config contains "api_keys:\n  openai: sk-test123"
  And repo config contains "search:\n  limit: 20"
  When I run "gitctx config list"
  Then the output should contain "api_keys.openai=sk-...123 (from user config)"
  And the output should contain "search.limit=20 (from repo config)"

Scenario: Config validation catches invalid values
  Given I run "gitctx config init"
  When I run "gitctx config set search.limit invalid"
  Then the exit code should be 2
  And the output should contain "validation error"

Scenario: Repo config is safe to commit (no secrets)
  Given I run "gitctx config init"
  And I run "gitctx config set search.limit 20"
  And I run "gitctx config set api_keys.openai sk-secret123"
  Then the file ".gitctx/config.yml" should contain "search:"
  And the file ".gitctx/config.yml" should contain "limit: 20"
  And the file ".gitctx/config.yml" should NOT contain "sk-"
  And the file ".gitctx/config.yml" should NOT contain "api_keys"
  And the file "~/.gitctx/config.yml" should contain "api_keys:"
  And the file "~/.gitctx/config.yml" should contain "sk-secret123"

Scenario: Malformed YAML file shows clear error
  Given repo config contains invalid YAML "search:\n  limit: [unclosed"
  When I run "gitctx config get search.limit"
  Then the exit code should be 1
  And the output should contain "Failed to parse config file"

Scenario: Permission denied on config save shows clear error
  Given repo config file exists with read-only permissions
  When I run "gitctx config set search.limit 30"
  Then the exit code should be 6
  And the output should contain "Permission denied"
```

## Technical Design

### Configuration Schema

**User Config** (`~/.gitctx/config.yml`) - Secrets only, never committed:
```yaml
# ~/.gitctx/config.yml
api_keys:
  openai: sk-abc123...  # Only OpenAI for MVP
```

**Repo Config** (`.gitctx/config.yml`) - Team settings, committed to git:
```yaml
# .gitctx/config.yml
# Default content created by 'gitctx config init'
search:
  limit: 10
  rerank: true

index:
  chunk_size: 1000
  chunk_overlap: 200

model:
  embedding: text-embedding-3-large
```

**Note**: The `config init` command creates `.gitctx/config.yml` with the above default values by calling `RepoConfig().save()`, which serializes the Pydantic model defaults to YAML.

**Repo Config Protection** (`.gitctx/.gitignore`) - Excludes local data:
```gitignore
# LanceDB vector database - never commit
db/

# Application logs - never commit
logs/
*.log
```

### Pydantic Settings Implementation

**Three separate modules for security separation:**

```python
# src/gitctx/core/user_config.py
"""User-level configuration (API keys only)."""
from pathlib import Path
from typing import Any
import os
from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
    PydanticBaseSettingsSource,
    YamlConfigSettingsSource,
)

class ApiKeys(BaseModel):
    """API key configuration."""
    openai: SecretStr | None = Field(default=None)

class ProviderEnvSource(PydanticBaseSettingsSource):
    """Custom source for OPENAI_API_KEY env var."""

    def get_field_value(self, field, field_name):
        # Not used - only __call__ is invoked
        raise NotImplementedError()

    def __call__(self) -> dict[str, Any]:
        d = {}
        if openai_key := os.getenv("OPENAI_API_KEY"):
            d["api_keys"] = {"openai": openai_key}
        return d

class UserConfig(BaseSettings):
    """User config (~/.gitctx/config.yml) - API keys only."""
    api_keys: ApiKeys = Field(default_factory=ApiKeys)

    model_config = SettingsConfigDict(
        yaml_file=str(Path.home() / ".gitctx" / "config.yml"),
        case_sensitive=False,
        validate_default=True,
    )

    @classmethod
    def settings_customise_sources(cls, settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings):
        return (
            init_settings,
            ProviderEnvSource(settings_cls),  # OPENAI_API_KEY
            YamlConfigSettingsSource(settings_cls),
        )
```

```python
# src/gitctx/core/repo_config.py
"""Repo-level configuration (team settings only)."""
from pathlib import Path
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class SearchSettings(BaseModel):
    limit: int = Field(default=10, gt=0, le=100)
    rerank: bool = True

class IndexSettings(BaseModel):
    chunk_size: int = Field(default=1000, gt=0)
    chunk_overlap: int = Field(default=200, ge=0)

class ModelSettings(BaseModel):
    embedding: str = "text-embedding-3-large"

class RepoConfig(BaseSettings):
    """Repo config (.gitctx/config.yml) - team settings only."""
    search: SearchSettings = Field(default_factory=SearchSettings)
    index: IndexSettings = Field(default_factory=IndexSettings)
    model: ModelSettings = Field(default_factory=ModelSettings)

    model_config = SettingsConfigDict(
        yaml_file=".gitctx/config.yml",
        env_prefix="GITCTX_",
        env_nested_delimiter="__",
        case_sensitive=False,
    )
```

```python
# src/gitctx/core/config.py
"""Aggregates user and repo config with smart routing."""
from pathlib import Path
from typing import Any

class GitCtxSettings:
    """Aggregator that routes config by key pattern."""

    def __init__(self):
        self.user = UserConfig()
        self.repo = RepoConfig()

    def get(self, key: str) -> Any:
        """Get config value, routing by key pattern."""
        if key.startswith("api_keys."):
            return self._get_from_user(key)
        else:
            return self._get_from_repo(key)

    def set(self, key: str, value: Any) -> None:
        """Set config value, routing by key pattern."""
        if key.startswith("api_keys."):
            self._set_in_user(key, value)
            self.user.save()  # → ~/.gitctx/config.yml
        else:
            self._set_in_repo(key, value)
            self.repo.save()  # → .gitctx/config.yml

def init_repo_config() -> None:
    """Initialize .gitctx/ structure."""
    gitctx_dir = Path(".gitctx")
    gitctx_dir.mkdir(exist_ok=True)

    # Create config.yml
    config_file = gitctx_dir / "config.yml"
    if not config_file.exists():
        RepoConfig().save()

    # Create .gitignore
    gitignore_content = """# LanceDB vector database - never commit
db/

# Application logs - never commit
logs/
*.log
"""
    (gitctx_dir / ".gitignore").write_text(gitignore_content)
```

### Precedence Examples

**Example 1: User config - OPENAI_API_KEY env var wins**
```bash
# ~/.gitctx/config.yml contains: api_keys.openai: sk-file123
export OPENAI_API_KEY=sk-provider789

gitctx config get api_keys.openai
# Output: api_keys.openai = sk-...789 (from OPENAI_API_KEY)
```

**Example 2: User config - YAML fallback**
```bash
gitctx config set api_keys.openai sk-file123
gitctx config get api_keys.openai
# Output: api_keys.openai = sk-...123 (from user config)
```

**Example 3: Repo config - GITCTX env var overrides YAML**
```bash
# .gitctx/config.yml contains: search.limit: 10
export GITCTX_SEARCH__LIMIT=30

gitctx config get search.limit
# Output: search.limit = 30 (from GITCTX_SEARCH__LIMIT)
```

**Example 4: Repo config - YAML fallback**
```bash
gitctx config init
gitctx config set search.limit 20
gitctx config get search.limit
# Output: search.limit = 20 (from repo config)
```

### CLI Output Format (TUI_GUIDE.md Compliant)

**config init** - Initialize repo structure (NEW):
```bash
# Default (terse)
$ gitctx config init
Initialized .gitctx/

💡 Tip
API keys are stored securely in ~/.gitctx/config.yml with file permissions 0600.
Team settings in .gitctx/config.yml are safe to commit.

# Verbose mode
$ gitctx config init --verbose
Initialized .gitctx/
  Created .gitctx/config.yml
  Created .gitctx/.gitignore

Next steps:
  1. Set your API key: gitctx config set api_keys.openai sk-...
  2. Index your repo: gitctx index
  3. Commit to share: git add .gitctx/ && git commit -m 'chore: Add gitctx embeddings'

# Quiet mode
$ gitctx config init --quiet
(no output)
```

**config get** - Progressive disclosure (quiet/default/verbose):
```bash
# Default (terse) - value only, like git
$ gitctx config get api_keys.openai
sk-...789

# Verbose - show key and source
$ gitctx config get api_keys.openai --verbose
api_keys.openai = sk-...789 (from OPENAI_API_KEY)

# Quiet - value only (same as default, for scripting)
$ gitctx config get api_keys.openai --quiet
sk-...789
```

**config list** - Progressive disclosure:
```bash
# Default - hide sources for defaults (terse)
$ gitctx config list
api_keys.openai=sk-...123 (from user config)
search.limit=20 (from repo config)
search.rerank=true
index.chunk_size=1000
index.chunk_overlap=200
model.embedding=text-embedding-3-large

# Verbose - show ALL sources including defaults
$ gitctx config list --verbose
api_keys.openai=sk-...123 (from user config)
search.limit=20 (from repo config)
search.rerank=true (default)
index.chunk_size=1000 (default)
index.chunk_overlap=200 (default)
model.embedding=text-embedding-3-large (default)

# Quiet - just key=value
$ gitctx config list --quiet
api_keys.openai=sk-...123
search.limit=20
search.rerank=true
index.chunk_size=1000
index.chunk_overlap=200
model.embedding=text-embedding-3-large
```

**config set** - Routes automatically:
```bash
# Default (terse)
$ gitctx config set api_keys.openai sk-test123
set api_keys.openai  # → ~/.gitctx/config.yml

$ gitctx config set search.limit 20
set search.limit  # → .gitctx/config.yml

# Quiet mode
$ gitctx config set search.limit 20 --quiet
(no output)
```

**Platform Symbols** - Auto-fallback on Windows cmd.exe:
```bash
# Modern terminals (macOS, Linux, Windows Terminal)
$ gitctx config init
✓ Initialized .gitctx/

# Legacy Windows cmd.exe
C:\> gitctx config init
[OK] Initialized .gitctx/
```

## Dependencies

Add to `pyproject.toml`:
```toml
dependencies = [
    "typer>=0.12.0",
    "rich>=13.7.0",
    "pyyaml>=6.0.1",  # Already present
    "shellingham>=1.5.0",
    "pydantic>=2.11.0",  # NEW
    "pydantic-settings[yaml]>=2.11.0",  # NEW - [yaml] extra required for YAML support
]
```

## Success Metrics

- **Security**: API keys NEVER in repo config (enforced by Pydantic models)
- **Config Persistence**: Settings survive across sessions
- **UX Win**: Users with `OPENAI_API_KEY` don't need to configure anything
- **Team Sharing**: `.gitctx/` safe to commit, shared across team
- **Type Safety**: Invalid configs caught immediately with helpful errors
- **Test Coverage**: ≥ 85% coverage maintained
- **Interface Compatible**: All 78 tests from STORY-0001.1.1 pass
- **BDD Scenarios**: All persistence, precedence, validation, and security scenarios pass

## Migration from STORY-0001.1.1

Current implementation uses in-memory `_config_store` dict. This story:
- Replaces in-memory dict with `UserConfig` and `RepoConfig` instances
- Adds two-file persistence (user vs repo separation)
- Adds type validation
- Adds environment variable precedence (different per config type)
- Adds `config init` command for repo setup
- **Maintains CLI interface contract** (all existing tests pass)
- **Adds security**: API keys physically cannot be stored in repo

## Estimation Validation

- **Story Points**: 2 SP = 2 hours (per Fibonacci scale)
- **Task Hours**: 0.5 + 1.0 + 0.5 = 2.0 hours ✅
- **Estimates align with story points**

**Complexity Note**: TASK-0001.1.2.2 implements 3 separate modules (~380 lines total) with custom Pydantic sources, routing logic, and comprehensive error handling. If implementation exceeds 2 hours due to debugging/edge cases, consider adjusting to 3 SP retrospectively. The conservative 2 SP estimate assumes efficient implementation following the detailed technical design.

## Performance Targets

- Config load time: <10ms
- Config save time: <50ms
- YAML file size: <1KB for typical configs
- Memory footprint: <100KB for config in memory

## Test Fixtures Reference

**CRITICAL**: This story uses existing comprehensive fixtures. **NO NEW FIXTURES NEEDED.**

### Available Fixtures (tests/conftest.py)

**For Unit Tests** - Use these in `tests/unit/core/test_*_config.py`:

1. **`temp_home`** (Path) - Isolated HOME directory
   - **Already creates `.gitctx/` subdirectory**
   - Use with `monkeypatch.setattr("pathlib.Path.home", lambda: temp_home)`
   - Prevents writing to developer's real home directory

2. **`git_isolation_base`** (dict[str, str]) - Security isolation environment vars
   - Use with `monkeypatch.setenv()` to apply isolation
   - Prevents access to SSH keys, GPG keys, git config

3. **`cli_runner`** (CliRunner) - In-process CLI testing
   - For unit tests of CLI commands
   - Faster than subprocess, good for quick CLI validation

### Available Fixtures (tests/e2e/conftest.py)

**For E2E/BDD Tests** - Use these in step definitions:

1. **`e2e_git_isolation_env`** (dict[str, str]) - Complete subprocess environment
   - **Contains isolated HOME** via `e2e_git_isolation_env["HOME"]`
   - Isolated HOME **already has `.gitctx/` directory created**
   - Use `Path(e2e_git_isolation_env["HOME"])` to access

2. **`e2e_env_factory`** (callable) - Custom environment factory
   - Create environments with custom vars: `e2e_env_factory(OPENAI_API_KEY="sk-test")`
   - Security-checked: prevents overriding isolation vars
   - Returns complete isolated environment dict

3. **`e2e_cli_runner`** (CliRunner) - Subprocess-isolated CLI runner
   - For E2E tests requiring true isolation
   - Automatically uses `e2e_git_isolation_env`

4. **`e2e_git_repo`** (Path) - Real git repository with commits
   - Use for scenarios requiring git operations
   - Fully isolated from developer's git config

### Available Fixtures (tests/e2e/steps/cli_steps.py)

**For BDD Step Definitions** - Already exist, just use them:

1. **`context`** (dict[str, Any]) - **Already exists!**
   - Stores `result`, `output`, `exit_code` between steps
   - Used by existing `@when('I run "{command}")` step
   - Add custom keys as needed (e.g., `context["custom_env"]`)

### Existing Step Definitions

**Already implemented** in [tests/e2e/steps/cli_steps.py](../../../../tests/e2e/steps/cli_steps.py):

- `@when('I run "{command}")` - Executes command via subprocess with isolation
- `@then('the output should contain "{text}")` - Checks stdout
- `@then('the output should not contain "{text}")` - Negative check
- `@then("the exit code should be 0")` - Success check
- `@then("the exit code should be {code:d}")` - Specific code check
- `@then("the exit code should not be 0")` - Failure check

**New step definitions needed** (add to cli_steps.py):

- `@given('user config contains "{content}"')` - Setup user config file
- `@given('repo config contains "{content}"')` - Setup repo config file
- `@given('environment variable "{var}" is "{value}"')` - Set env var for next command
- `@then('the file "{path}" should exist')` - Check file existence
- `@then('the file "{path}" should contain "{content}"')` - Check file content
- `@then('the file "{path}" should NOT contain "{content}"')` - Negative file check

### Fixture Usage Patterns

**Unit Test Pattern** (using temp_home):
```python
def test_user_config_saves(temp_home, monkeypatch):
    """temp_home already has .gitctx/ created."""
    monkeypatch.setattr("pathlib.Path.home", lambda: temp_home)

    config_file = temp_home / ".gitctx" / "config.yml"
    # config_file.parent already exists!
```

**E2E Step Pattern** (using e2e_git_isolation_env):
```python
@given('user config contains "{content}"')
def setup_user_config(e2e_git_isolation_env: dict[str, str], content: str):
    home = Path(e2e_git_isolation_env["HOME"])
    config = home / ".gitctx" / "config.yml"
    # home / ".gitctx" already exists!
    config.write_text(content.replace('\\n', '\n'))
```

**E2E Env Var Pattern** (using e2e_env_factory + context):
```python
@given('environment variable "{var}" is "{value}"')
def setup_env(e2e_env_factory, context: dict[str, Any], var: str, value: str):
    """Store env var for next run_command to use."""
    if "custom_env" not in context:
        context["custom_env"] = {}
    context["custom_env"][var] = value

# Then in run_command step (already exists, no modification needed):
# It can check context["custom_env"] and use e2e_env_factory
```

## Notes

- **Security-First**: User/repo config separation prevents accidental secret commits
- **BDD/TDD Workflow**: Write tests first (RED), implement (GREEN), refactor
- **OpenAI Only**: No Anthropic, Cohere, or other providers (YAGNI principle)
- **Pydantic Choice**: Industry-standard (FastAPI), type-safe, future-proof
- **Smart Routing**: CLI automatically routes by key pattern (transparent to user)
- **No Scope Creep**: Simple YAML + env vars now, cloud secrets available later
- **User Experience**: Respects existing `OPENAI_API_KEY` (don't break their workflow)
- **Comprehensive Fixtures**: 8 existing fixtures provide everything needed - no new fixtures required

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Accidentally committing API keys | **CRITICAL** | Enforced separation via Pydantic models - API keys physically cannot go in repo config |
| Pydantic Settings learning curve | Low | Excellent docs, standard patterns |
| YAML file corruption | Medium | Validate on load, backup on save |
| Breaking CLI interface contract | High | Extensive BDD tests, all 78 existing tests must pass |
| Complex routing logic | Medium | Clear key-based routing, comprehensive tests |

## Related Epics

- **Enables EPIC-0001.2** (Real Indexing): Indexing needs persistent OpenAI API key
- **Completes EPIC-0001.1** (CLI Foundation): 10/10 story points (100%)

---

**Created**: 2025-10-04
**Last Updated**: 2025-10-05
**Completed**: 2025-10-05
