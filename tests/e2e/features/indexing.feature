Feature: Repository Indexing
  As a developer
  I want to index my repository with proper cost control and caching
  So that I can search code efficiently without surprise charges

  Background:
    Given gitctx is installed
    And environment variable "OPENAI_API_KEY" is "sk-test-key"

  # STORY-0001.2.6: Indexing Cost & Performance Fixes

  Scenario: History mode requires confirmation in interactive terminal (decline)
    Given a repository with history mode enabled
    When I run "gitctx index" interactively and decline
    Then the exit code should be 0
    And the error should contain "History Mode Enabled"
    And the error should contain "10-50x higher"
    And the error should contain "Cancelled"
    And no indexing should have occurred

  Scenario: History mode requires confirmation in interactive terminal (accept)
    Given a repository with history mode enabled
    When I run "gitctx index" interactively and accept
    Then the exit code should be 0
    And the error should contain "History Mode Enabled"
    And the error should contain "10-50x higher"
    And indexing should complete successfully

  Scenario: History mode bypasses confirmation with --yes flag
    Given a repository with history mode enabled
    When I run "gitctx index --yes"
    Then the exit code should be 0
    And the output should not contain "Continue?"
    And indexing should complete successfully

  Scenario: History mode fails in non-interactive environment without --yes
    Given a repository with history mode enabled
    When I run "gitctx index" non-interactively
    Then the exit code should be 1
    And the error should contain "history mode requires confirmation"
    And the error should contain "--yes"

  Scenario: Snapshot mode does not require confirmation
    Given a repository with snapshot mode enabled
    When I run "gitctx index"
    Then the exit code should be 0
    And the output should not contain "History Mode"
    And the output should not contain "Continue?"
    And indexing should complete successfully
