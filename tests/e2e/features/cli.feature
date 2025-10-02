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

  # Scenario: Display help
  #   When I run "gitctx --help"
  #   Then the exit code should be 0
  #   And the output should contain "Usage: gitctx"
  #   And the output should contain "Commands:"

  # Scenario: Configure API key
  #   When I run "gitctx config set api_keys.openai sk-test123"
  #   Then the configuration should be saved
  #   When I run "gitctx config get api_keys.openai"
  #   Then the output should contain "sk-...123"

  # Scenario: Display configuration
  #   Given the configuration contains API keys
  #   When I run "gitctx config list"
  #   Then the output should show all settings
  #   And sensitive values should be masked

  # Scenario: Environment variable override
  #   Given the environment variable "OPENAI_API_KEY" is set to "sk-env123"
  #   When I run "gitctx config get api_keys.openai"
  #   Then the output should contain "sk-...123"
  #   And the environment value should take precedence

  # Scenario: Index command help
  #   When I run "gitctx index --help"
  #   Then the output should contain "Index the repository"
  #   And the output should contain "--verbose"

  # Scenario: Search command help
  #   When I run "gitctx search --help"
  #   Then the output should contain "Search the indexed repository"

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

  # Scenario: Missing required arguments
  #   When I run "gitctx search"
  #   Then the exit code should not be 0
  #   And the output should contain "error: missing argument"
  #   And the output should contain "Usage: gitctx"
