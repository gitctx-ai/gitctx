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
    And the output should contain "Set"

  Scenario: Config get command
    When I run "gitctx config get nonexistent.key"
    Then the exit code should be 0
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

  # Scenario: Clear command help
  #   When I run "gitctx clear --help"
  #   Then the output should contain "Clear cache and embeddings"
  #   And the output should contain "--force"
  #   And the output should contain "--database"
  #   And the output should contain "--embeddings"
  #   And the output should contain "--all"

  # Scenario: Invalid command
  #   When I run "gitctx invalid"
  #   Then the exit code should not be 0
  #   And the output should contain "error: unknown command 'invalid'"
  #   And the output should suggest valid commands

  Scenario: Missing required arguments
    When I run "gitctx search"
    Then the exit code should not be 0
