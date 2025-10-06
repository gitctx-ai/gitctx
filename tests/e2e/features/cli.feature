Feature: CLI Foundation
  As a developer
  I want to use gitctx from the command line
  So that I can search my codebase effectively

  Background:
    Given gitctx is installed

  # TASK-0001.1.0.3: Framework Setup - Only basic scenarios
  Scenario: Display version
    When I run "gitctx --version"
    Then the output should contain "gitctx version"
    And the exit code should be 0

  # TODO: Enable when commands are implemented in future tasks

  Scenario: Display help
    When I run "gitctx --help"
    Then the exit code should be 0
    And the output should contain "Usage:"
    And the output should contain "gitctx"
    And the output should contain "Context optimization engine"

  Scenario: Config set command
    When I run "gitctx config set api_keys.openai sk-test123"
    Then the exit code should be 0
    And the output should contain "set"

  Scenario: Config get command
    When I run "gitctx config get nonexistent.key"
    Then the exit code should not be 0
    And the output should contain "not set"

  Scenario: Config list command
    When I run "gitctx config list"
    Then the exit code should be 0

  Scenario: Index command help
    When I run "gitctx index --help"
    Then the output should contain "Index the repository"
    And the output should contain "--verbose"
    And the exit code should be 0

  Scenario: Search command help
    When I run "gitctx search --help"
    Then the output should contain "Search the indexed repository"
    And the exit code should be 0

  Scenario: Search with conflicting output modes
    When I run "gitctx search test --mcp --verbose"
    Then the exit code should not be 0

  Scenario: Clear command help
    When I run "gitctx clear --help"
    Then the output should contain "Clear cached data"
    And the output should contain "--force"
    And the output should contain "--database"
    And the output should contain "--embeddings"
    And the output should contain "--all"
    And the exit code should be 0

  Scenario: Clear database only preserves embeddings
    When I run "gitctx clear --database --force"
    Then the exit code should be 0
    And the output should contain "database"
    And the output should not contain "embeddings"

  Scenario: Clear embeddings clears database too
    When I run "gitctx clear --embeddings --force"
    Then the exit code should be 0
    And the output should contain "database"
    And the output should contain "embeddings"

  # Scenario: Invalid command
  #   When I run "gitctx invalid"
  #   Then the exit code should not be 0
  #   And the output should contain "error: unknown command 'invalid'"
  #   And the output should suggest valid commands

  Scenario: Missing required arguments
    When I run "gitctx search"
    Then the exit code should not be 0

  Scenario: Empty command shows quick start
    When I run "gitctx"
    Then the exit code should be 0
    And the output should contain "Quick start"
    And the output should contain "gitctx index"

  # TASK-0001.1.2.1: Real Configuration Management with User/Repo Separation

  Scenario: config init creates repo structure (default terse output)
    When I run "gitctx config init"
    Then the exit code should be 0
    And the output should contain "Initialized .gitctx/"
    And the output should not contain "Created"
    And the output should not contain "Next steps"
    And the file ".gitctx/config.yml" should exist
    And the file ".gitctx/.gitignore" should exist
    And ".gitctx/.gitignore" should contain "# LanceDB vector database - never commit"
    And ".gitctx/.gitignore" should contain "db/"
    And ".gitctx/.gitignore" should contain "# Application logs - never commit"
    And ".gitctx/.gitignore" should contain "logs/"
    And ".gitctx/.gitignore" should contain "*.log"

  Scenario: config init quiet mode suppresses all output
    When I run "gitctx config init --quiet"
    Then the exit code should be 0
    And the output should be empty

  Scenario: config init verbose mode shows detailed output
    When I run "gitctx config init --verbose"
    Then the exit code should be 0
    And the output should contain "Initialized .gitctx/"
    And the output should contain "Created .gitctx/config.yml"
    And the output should contain "Created .gitctx/.gitignore"
    And the output should contain "Next steps:"
    And the output should contain "1. Set your API key: gitctx config set api_keys.openai sk-..."
    And the output should contain "2. Index your repo: gitctx index"
    And the output should contain "3. Commit to share: git add .gitctx/"

  Scenario: API keys stored in user config only
    When I run "gitctx config set api_keys.openai sk-test123"
    Then the exit code should be 0
    And the output should contain "set api_keys.openai"
    And the user config file should exist at "~/.gitctx/config.yml"
    And the file "~/.gitctx/config.yml" should contain "api_keys:"
    And the file "~/.gitctx/config.yml" should contain "openai:"
    And the file "~/.gitctx/config.yml" should contain "sk-test123"
    And the file ".gitctx/config.yml" should not contain "api_keys"
    And the file ".gitctx/config.yml" should not contain "sk-test123"

  Scenario: Repo settings stored in repo config only
    Given I run "gitctx config init"
    When I run "gitctx config set search.limit 20"
    Then the exit code should be 0
    And the output should contain "set search.limit"
    And the file ".gitctx/config.yml" should contain "search:"
    And the file ".gitctx/config.yml" should contain "limit: 20"
    And the file "~/.gitctx/config.yml" should not contain "search"
    And the file "~/.gitctx/config.yml" should not contain "limit"

  Scenario: config get default mode shows value only (terse)
    Given user config contains "api_keys:\n  openai: sk-test123"
    When I run "gitctx config get api_keys.openai"
    Then the exit code should be 0
    And the output should contain "sk-...123"
    And the output should not contain "api_keys.openai ="
    And the output should not contain "(from"

  Scenario: config get verbose mode shows key and source
    Given user config contains "api_keys:\n  openai: sk-test123"
    When I run "gitctx config get api_keys.openai --verbose"
    Then the exit code should be 0
    And the output should contain "api_keys.openai"
    And the output should contain "sk-...123"
    And the output should contain "(from user config)"

  Scenario: config get quiet mode outputs value only with no formatting
    Given user config contains "api_keys:\n  openai: sk-test123"
    When I run "gitctx config get api_keys.openai --quiet"
    Then the exit code should be 0
    And the output should contain "sk-...123"

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

  Scenario: config list default mode hides sources for defaults (terse)
    Given user config contains "api_keys:\n  openai: sk-test123"
    And repo config contains "search:\n  limit: 20"
    When I run "gitctx config list"
    Then the output should contain "api_keys.openai=sk-...123"
    And the output should contain "(from user config)"
    And the output should contain "search.limit=20"
    And the output should contain "(from repo config)"
    And the output should contain "model.embedding=text-embedding-3-large"
    And the output should not contain "(default)"

  Scenario: config list verbose mode shows all sources
    Given user config contains "api_keys:\n  openai: sk-test123"
    When I run "gitctx config list --verbose"
    Then the output should contain "api_keys.openai=sk-...123"
    And the output should contain "(from user config)"
    And the output should contain "model.embedding=text-embedding-3-large"
    And the output should contain "(default)"

  Scenario: config set default mode shows terse confirmation
    Given I run "gitctx config init"
    When I run "gitctx config set search.limit 20"
    Then the exit code should be 0
    And the output should contain "set search.limit"
    And the file ".gitctx/config.yml" should contain "search:"
    And the file ".gitctx/config.yml" should contain "limit: 20"
    And the file "~/.gitctx/config.yml" should not contain "search"

  Scenario: config set quiet mode suppresses output
    Given I run "gitctx config init"
    When I run "gitctx config set search.limit 20 --quiet"
    Then the exit code should be 0
    And the output should be empty
    And the file ".gitctx/config.yml" should contain "search:"
    And the file ".gitctx/config.yml" should contain "limit: 20"

  Scenario: config set api key persists to user config
    When I run "gitctx config set api_keys.openai sk-test456"
    Then the exit code should be 0
    And the file "~/.gitctx/config.yml" should exist
    And the file "~/.gitctx/config.yml" should contain "api_keys:"
    And the file "~/.gitctx/config.yml" should contain "openai:"
    And the file "~/.gitctx/config.yml" should contain "sk-test456"
    And the file ".gitctx/config.yml" should not contain "sk-test456"
    And the file ".gitctx/config.yml" should not contain "api_keys"

  Scenario: Config validation catches invalid values
    Given I run "gitctx config init"
    When I run "gitctx config set search.limit invalid"
    Then the exit code should be 2
    And the error should contain "expected a number"
    And the error should not contain "ValidationError"
    And the error should not contain "Traceback"

  Scenario: Repo config is safe to commit (no secrets)
    Given I run "gitctx config init"
    When I run "gitctx config set search.limit 20"
    And I run "gitctx config set api_keys.openai sk-secret123"
    Then the file ".gitctx/config.yml" should contain "search:"
    And the file ".gitctx/config.yml" should contain "limit: 20"
    And the file ".gitctx/config.yml" should not contain "sk-"
    And the file ".gitctx/config.yml" should not contain "api_keys"
    And the file "~/.gitctx/config.yml" should contain "api_keys:"
    And the file "~/.gitctx/config.yml" should contain "sk-secret123"

  Scenario: Malformed YAML file shows clear error
    Given repo config contains invalid YAML "search:\n  limit: [unclosed"
    When I run "gitctx config get search.limit"
    Then the exit code should be 1
    And the error should contain "Failed to parse config file"

  Scenario: User config with insecure permissions shows warning
    Given user config exists with permissions 0644
    When I run "gitctx config get api_keys.openai"
    Then the error should contain "insecure permissions"
    And the error should contain "644"
    And the error should contain "600"

  Scenario: Permission denied on config save shows clear error
    Given repo config file exists with read-only permissions
    When I run "gitctx config set search.limit 30"
    Then the exit code should be 6
    And the error should contain "Permission denied"
