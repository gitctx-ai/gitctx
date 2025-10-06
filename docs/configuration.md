# gitctx Configuration Guide

**Complete reference for configuring gitctx, including all options, environment variables, security best practices, and troubleshooting.**

---

## Overview

gitctx uses a **two-file configuration system** that separates secrets from team settings:

- **User Config** (`~/.gitctx/config.yml`) - API keys only, never committed to git
- **Repo Config** (`.gitctx/config.yml`) - Team settings, safe to commit and share

This design ensures API keys stay secure while allowing teams to share search parameters, indexing settings, and model preferences.

---

## Quick Start

```bash
# 1. Initialize repo configuration (creates .gitctx/)
gitctx config init

# 2. Set your API key (stored in ~/.gitctx/config.yml)
gitctx config set api_keys.openai sk-abc123...

# 3. Optional: Customize team settings (stored in .gitctx/config.yml)
gitctx config set search.limit 20
gitctx config set index.chunk_size 1500

# 4. Verify configuration
gitctx config list
```

---

## Configuration Files

### User Config (~/.gitctx/config.yml)

**Purpose**: Stores API keys and user-specific preferences

**Location**:
- **macOS/Linux**: `~/.gitctx/config.yml`
- **Windows**: `%USERPROFILE%\.gitctx\config.yml`

**Security**:
- File permissions: `0600` (owner read/write only)
- Never committed to git (excluded by design)
- API keys auto-masked in all output (shows `sk-...123`)

**Example**:
```yaml
api_keys:
  openai: sk-abc123def456ghi789jkl...
```

**Precedence** (highest to lowest):
1. `OPENAI_API_KEY` environment variable
2. User YAML file (`~/.gitctx/config.yml`)
3. Default (none)

### Repo Config (.gitctx/config.yml)

**Purpose**: Stores team settings for search, indexing, and models

**Location**: `.gitctx/config.yml` (in repo root)

**Security**:
- File permissions: `0644` (readable by all, writable by owner)
- **Safe to commit** - contains no secrets
- Shared across team via git

**Example**:
```yaml
search:
  limit: 10
  rerank: true

index:
  chunk_size: 1000
  chunk_overlap: 200

model:
  embedding: text-embedding-3-large
```

**Precedence** (highest to lowest):
1. `GITCTX_*` environment variables (e.g., `GITCTX_SEARCH__LIMIT`)
2. Repo YAML file (`.gitctx/config.yml`)
3. Defaults

---

## Configuration Options

### API Keys

#### `api_keys.openai`
- **Type**: String (SecretStr - auto-masked)
- **Required**: Yes (for indexing)
- **Storage**: User config only (~/.gitctx/config.yml)
- **Default**: None
- **Description**: OpenAI API key for generating embeddings
- **Example**: `sk-abc123def456...`

**How to set**:
```bash
# Via config command (recommended)
gitctx config set api_keys.openai sk-abc123...

# Via environment variable
export OPENAI_API_KEY=sk-abc123...

# Verify (shows masked value)
gitctx config get api_keys.openai
# Output: sk-...123
```

**Security Notes**:
- Never commit API keys to git
- Keys are automatically masked in all output
- File permissions enforced to 0600
- Rotate keys if exposed

### Search Settings

#### `search.limit`
- **Type**: Integer
- **Range**: 1-100
- **Default**: 10
- **Description**: Maximum number of search results to return
- **Example**: `20`

```bash
gitctx config set search.limit 20
```

#### `search.rerank`
- **Type**: Boolean
- **Default**: `true`
- **Description**: Enable reranking of search results for better relevance
- **Example**: `false`

```bash
gitctx config set search.rerank false
```

### Index Settings

#### `index.chunk_size`
- **Type**: Integer
- **Range**: >0
- **Default**: 1000
- **Description**: Token chunk size for splitting code into embeddings
- **Example**: `1500`

```bash
gitctx config set index.chunk_size 1500
```

**Guidance**:
- Smaller chunks (500-1000): Better precision, more API calls
- Larger chunks (1000-2000): Better context, fewer API calls
- Recommended: 1000 for balanced performance

#### `index.chunk_overlap`
- **Type**: Integer
- **Range**: ≥0
- **Default**: 200
- **Description**: Token overlap between consecutive chunks to preserve context
- **Example**: `100`

```bash
gitctx config set index.chunk_overlap 100
```

**Guidance**:
- Overlap prevents context loss at chunk boundaries
- Typical range: 10-20% of chunk_size
- Zero overlap risks missing cross-boundary context

### Model Settings

#### `model.embedding`
- **Type**: String
- **Default**: `text-embedding-3-large`
- **Description**: OpenAI embedding model to use for code embeddings
- **Example**: `text-embedding-3-small`

```bash
gitctx config set model.embedding text-embedding-3-small
```

**Available models**:
- `text-embedding-3-large` (default) - Best quality, higher cost
- `text-embedding-3-small` - Good quality, lower cost

---

## Environment Variables

Environment variables override config file values, useful for CI/CD and temporary overrides.

### User Config Variables

| Variable | Config Key | Description | Example |
|----------|-----------|-------------|---------|
| `OPENAI_API_KEY` | `api_keys.openai` | OpenAI API key | `sk-abc123...` |

**Precedence**: `OPENAI_API_KEY` > User YAML file

**Usage**:
```bash
# Set for current session
export OPENAI_API_KEY=sk-abc123...

# Or prefix command
OPENAI_API_KEY=sk-abc123... gitctx index
```

### Repo Config Variables

| Variable | Config Key | Description | Example |
|----------|-----------|-------------|---------|
| `GITCTX_SEARCH__LIMIT` | `search.limit` | Max search results | `20` |
| `GITCTX_SEARCH__RERANK` | `search.rerank` | Enable reranking | `false` |
| `GITCTX_INDEX__CHUNK_SIZE` | `index.chunk_size` | Token chunk size | `1500` |
| `GITCTX_INDEX__CHUNK_OVERLAP` | `index.chunk_overlap` | Chunk overlap | `100` |
| `GITCTX_MODEL__EMBEDDING` | `model.embedding` | Embedding model | `text-embedding-3-small` |

**Naming Convention**:
- Prefix: `GITCTX_`
- Section separator: `__` (double underscore)
- Format: `GITCTX_<SECTION>__<FIELD>`

**Precedence**: `GITCTX_*` env vars > Repo YAML file

**Usage**:
```bash
# Override search limit for CI
export GITCTX_SEARCH__LIMIT=50

# Use smaller embedding model to save costs
export GITCTX_MODEL__EMBEDDING=text-embedding-3-small
```

---

## Command Reference

### `gitctx config init`

Initialize `.gitctx/` directory structure in the current repository.

**Creates**:
- `.gitctx/config.yml` - Repo config with default settings
- `.gitctx/.gitignore` - Excludes `db/`, `logs/`, `*.log`

**Example**:
```bash
$ gitctx config init
Initialized .gitctx/
```

**Idempotent**: Safe to run multiple times (won't overwrite existing config)

### `gitctx config set <key> <value>`

Set a configuration value (routes to user or repo config automatically).

**Routing**:
- `api_keys.*` → User config (~/.gitctx/config.yml)
- `search.*`, `index.*`, `model.*` → Repo config (.gitctx/config.yml)

**Examples**:
```bash
# Set API key (user config)
gitctx config set api_keys.openai sk-abc123...

# Set search limit (repo config)
gitctx config set search.limit 20

# Set chunk size (repo config)
gitctx config set index.chunk_size 1500
```

**Type Validation**: Values are validated against expected types (int, bool, string)

### `gitctx config get <key>`

Get a configuration value (shows masked secrets).

**Default Mode** (terse):
```bash
$ gitctx config get api_keys.openai
sk-...123
```

**Verbose Mode** (shows source):
```bash
$ gitctx config get api_keys.openai --verbose
api_keys.openai = sk-...123 (from OPENAI_API_KEY)
```

**Source Indicators**:
- `(from OPENAI_API_KEY)` - Environment variable
- `(from user config)` - ~/.gitctx/config.yml
- `(from GITCTX_SEARCH__LIMIT)` - Environment variable
- `(from repo config)` - .gitctx/config.yml
- `(default)` - Built-in default value

### `gitctx config list`

List all configuration values.

**Default Mode** (terse, hides default sources):
```bash
$ gitctx config list
api_keys.openai=sk-...123 (from user config)
search.limit=20 (from repo config)
search.rerank=true
index.chunk_size=1000
index.chunk_overlap=200
model.embedding=text-embedding-3-large
```

**Verbose Mode** (shows all sources including defaults):
```bash
$ gitctx config list --verbose
api_keys.openai=sk-...123 (from user config)
search.limit=20 (from repo config)
search.rerank=true (default)
index.chunk_size=1000 (default)
index.chunk_overlap=200 (default)
model.embedding=text-embedding-3-large (default)
```

**Quiet Mode** (machine-parseable):
```bash
$ gitctx config list --quiet
api_keys.openai=sk-...123
search.limit=20
search.rerank=true
index.chunk_size=1000
index.chunk_overlap=200
model.embedding=text-embedding-3-large
```

---

## Security Best Practices

### API Key Safety

#### 1. Never Commit API Keys
- User config (~/.gitctx/config.yml) is never committed by design
- Repo config (.gitctx/config.yml) cannot store API keys (enforced by Pydantic models)
- If you accidentally commit a key, **rotate it immediately** at https://platform.openai.com/api-keys

#### 2. Use Environment Variables in CI/CD
```bash
# GitHub Actions
- name: Index repository
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
  run: gitctx index
```

#### 3. Check File Permissions
```bash
# Verify user config has secure permissions
ls -la ~/.gitctx/config.yml
# Should show: -rw------- (0600)

# Fix if needed
chmod 600 ~/.gitctx/config.yml
```

#### 4. Rotate Keys Regularly
- Rotate keys every 90 days as a best practice
- Rotate immediately if:
  - Key appears in logs or error messages
  - Key was committed to git (even if reverted)
  - Team member with access leaves

### File Permissions

**User Config** (`~/.gitctx/config.yml`):
- **Permissions**: `0600` (owner read/write only)
- **Enforced**: gitctx automatically sets 0600 on save
- **Warning**: gitctx warns if permissions are too open (e.g., 0644)

**Repo Config** (`.gitctx/config.yml`):
- **Permissions**: `0644` (readable by all, writable by owner)
- **Safe to commit**: Contains no secrets
- **Shareable**: Team members can read and apply settings

### Secret Masking

All API keys are automatically masked in output:

```bash
$ gitctx config get api_keys.openai
sk-...123  # Shows first 3 and last 3 chars

$ gitctx config list
api_keys.openai=sk-...123 (from user config)
```

**Masking Format**:
- Keys >6 chars: Shows first 3 and last 3 (e.g., `sk-...123`)
- Keys ≤6 chars: Shows `***`

---

## Cross-Platform Notes

### Windows

**User Config Location**:
```
%USERPROFILE%\.gitctx\config.yml
```

**File Permissions**:
- Windows uses ACLs (Access Control Lists), not Unix permissions
- gitctx verifies file is readable/writable by owner
- No direct equivalent to Unix `0600` permissions

**Path Handling**:
- Backslashes (`\`) used for paths
- `%USERPROFILE%` expands to `C:\Users\YourName`

**Terminal Support**:
- **Windows Terminal**: Full Unicode support (✓ ✗ ⚠️ symbols)
- **PowerShell 7+**: Full Unicode support
- **cmd.exe (legacy)**: ASCII fallback ([OK] [X] [!] symbols)

**Example Setup**:
```powershell
# PowerShell
gitctx config init
gitctx config set api_keys.openai sk-abc123...
```

### macOS / Linux

**User Config Location**:
```
~/.gitctx/config.yml
```

**File Permissions**:
- Standard Unix permissions (0600/0644)
- gitctx enforces 0600 for user config
- Warns if permissions are too open

**Path Handling**:
- Forward slashes (`/`) for paths
- `~` expands to user home directory
- HOME environment variable respected

**Terminal Support**:
- Full Unicode support in modern terminals
- Symbols: ✓ ✗ ⚠️ 💡 →

**Example Setup**:
```bash
# Bash/Zsh
gitctx config init
gitctx config set api_keys.openai sk-abc123...
```

---

## Troubleshooting

### "Permission denied" when saving config

**Problem**: Cannot write to config file due to insufficient permissions.

**Symptoms**:
```bash
$ gitctx config set api_keys.openai sk-abc123...
✗ Error: permission denied: ~/.gitctx/config.yml
```

**Solutions**:

1. **Check file permissions**:
```bash
ls -la ~/.gitctx/config.yml
# Should show: -rw------- (owner read/write)
```

2. **Fix permissions**:
```bash
chmod 600 ~/.gitctx/config.yml
```

3. **Check directory permissions**:
```bash
ls -ld ~/.gitctx
# Should be readable/writable by owner
chmod 700 ~/.gitctx
```

4. **On Windows**: Verify file is not read-only
```powershell
attrib ~/.gitctx/config.yml
# Remove read-only if set
attrib -r ~/.gitctx/config.yml
```

### "Invalid value" validation error

**Problem**: Config value doesn't match expected type or range.

**Symptoms**:
```bash
$ gitctx config set search.limit abc
✗ Error: invalid value for search.limit

Expected: integer (1-100)
Got:      "abc"
```

**Solutions**:

1. **Check type constraints**:
   - `search.limit`: Integer (1-100)
   - `search.rerank`: Boolean (true/false)
   - `index.chunk_size`: Integer (>0)
   - `index.chunk_overlap`: Integer (≥0)

2. **Use correct format**:
```bash
# Good
gitctx config set search.limit 20
gitctx config set search.rerank true

# Bad
gitctx config set search.limit "twenty"  # Not an integer
gitctx config set search.limit 200       # Exceeds max (100)
```

3. **Check range constraints**:
```bash
# search.limit must be 1-100
gitctx config set search.limit 50  # ✓ Valid

# index.chunk_size must be >0
gitctx config set index.chunk_size 1000  # ✓ Valid
gitctx config set index.chunk_size 0     # ✗ Invalid
```

### "Config file not found"

**Problem**: Config file doesn't exist yet.

**Symptoms**:
```bash
$ gitctx config get search.limit
✗ Error: no index found
```

**Solution**:
```bash
# Initialize .gitctx/ directory
gitctx config init
```

### API key not recognized

**Problem**: API key is set but not being loaded correctly.

**Symptoms**:
```bash
$ gitctx index
✗ Error: OPENAI_API_KEY not set
```

**Diagnostic Steps**:

1. **Verify file exists**:
```bash
ls ~/.gitctx/config.yml
# Should exist
```

2. **Check file contents**:
```bash
cat ~/.gitctx/config.yml
# Should contain:
# api_keys:
#   openai: sk-...
```

3. **Verify permissions** (Unix only):
```bash
ls -la ~/.gitctx/config.yml
# Should show: -rw------- (0600)
```

4. **Test with environment variable**:
```bash
export OPENAI_API_KEY=sk-abc123...
gitctx config get api_keys.openai
# Should show: sk-...123
```

5. **Check config loading**:
```bash
gitctx config list --verbose
# Should show: api_keys.openai=sk-...123 (from user config)
```

### "Insecure permissions" warning

**Problem**: User config file has permissions that are too open.

**Symptoms**:
```
Warning: User config has insecure permissions (current: 644, should be 0600)
```

**Solution**:
```bash
chmod 600 ~/.gitctx/config.yml
```

**Explanation**: User config should only be readable by owner (you) since it contains API keys.

### YAML parsing errors

**Problem**: Config file contains invalid YAML syntax.

**Symptoms**:
```bash
✗ Error: Failed to parse config file
```

**Solutions**:

1. **Check YAML syntax**:
```bash
# Valid YAML
search:
  limit: 20

# Invalid YAML (wrong indentation)
search:
limit: 20
```

2. **Validate YAML online**: Use https://www.yamllint.com/

3. **Recreate config**:
```bash
# Backup old config
mv ~/.gitctx/config.yml ~/.gitctx/config.yml.bak

# Create fresh config
gitctx config set api_keys.openai sk-abc123...
```

---

## Examples

### Basic Setup

```bash
# 1. Initialize repo config
cd /path/to/your/repo
gitctx config init

# 2. Set API key (stored in ~/.gitctx/config.yml)
gitctx config set api_keys.openai sk-abc123def456...

# 3. Verify configuration
gitctx config list

# 4. Index repository
gitctx index

# 5. Search
gitctx search "authentication logic"
```

### Team Configuration

**Scenario**: Share search and indexing preferences across team.

**Steps**:

1. **One team member sets up**:
```bash
gitctx config init

# Customize settings
gitctx config set search.limit 25
gitctx config set index.chunk_size 1500
gitctx config set index.chunk_overlap 150

# Commit .gitctx/ to git
git add .gitctx/
git commit -m "chore: Add gitctx team configuration"
git push
```

2. **Other team members clone**:
```bash
git pull

# Settings automatically loaded from .gitctx/config.yml
gitctx config list
# Shows team settings:
# search.limit=25 (from repo config)
# index.chunk_size=1500 (from repo config)

# Each member sets their own API key
gitctx config set api_keys.openai sk-their-key...
```

### Environment Variable Overrides

**Scenario**: Use different settings for CI/CD vs local development.

**Local Development** (uses repo config):
```bash
# .gitctx/config.yml has:
# search:
#   limit: 10

gitctx search "query"
# Returns 10 results
```

**CI/CD** (overrides with env var):
```bash
# GitHub Actions workflow
- name: Search codebase
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
    GITCTX_SEARCH__LIMIT: 50  # Override for CI
  run: |
    gitctx index
    gitctx search "TODO FIXME" --limit 50
```

### Temporary Setting Override

```bash
# Override for single command
GITCTX_SEARCH__LIMIT=100 gitctx search "authentication"

# Override for session
export GITCTX_SEARCH__LIMIT=100
gitctx search "auth"      # Uses 100
gitctx search "database"  # Uses 100

# Restore default
unset GITCTX_SEARCH__LIMIT
```

### Cost Optimization

**Scenario**: Reduce OpenAI API costs by using smaller embedding model.

```bash
# Use smaller, cheaper embedding model
gitctx config set model.embedding text-embedding-3-small

# Use larger chunk size (fewer API calls)
gitctx config set index.chunk_size 2000

# Reindex with new settings
gitctx index --force
```

**Cost Comparison**:
- `text-embedding-3-large`: Higher quality, ~2x cost
- `text-embedding-3-small`: Good quality, ~50% cost savings

---

## Related Documentation

- [Main README](../README.md) - Getting started guide
- [TUI Guide](../TUI_GUIDE.md) - CLI output formats and symbols
- [Architecture Docs](architecture/) - Technical design details

---

**Last Updated**: 2025-10-05
