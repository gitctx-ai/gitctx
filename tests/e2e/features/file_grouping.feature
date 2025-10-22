Feature: File-Grouped Result Presentation
  As a developer reviewing search results
  I want results grouped by file showing HEAD chunks by default
  So that I understand the current file context and can see matching chunks organized naturally for my use case

  Background:
    Given gitctx is installed

  # Scenario 1: File grouping works across all formats (Smoke Test)
  # Tests that results are properly grouped by file path in all output formats
  Scenario: File grouping works across all formats
    Given an indexed repository with files containing "auth" keyword
    When I search for "auth"
    Then results should be grouped by file path
    And each file should appear exactly once as a header
    And all chunks should appear under their respective file headers
    And this behavior should be consistent across terse, verbose, and MCP formats

  # Scenario 2: Format selection produces different outputs (Smoke Test)
  # Tests that the three format options (terse, verbose, MCP) produce visibly different output styles
  Scenario: Format selection produces different outputs
    Given an indexed repository with files containing "login" keyword
    When I search for "login" with default format (terse)
    Then I see compact output with one line per chunk
    When I search for "login" with --format=verbose
    Then I see full code blocks with ANSI color codes
    And output contains escape sequences for syntax highlighting
    When I search for "login" with --format=mcp
    Then I get valid JSON with chunks array

  # Scenario 3: Score filtering removes low-scoring chunks (Smoke Test)
  # Tests that the --min-similarity threshold correctly filters out low-scoring chunks
  Scenario: Score filtering removes low-scoring chunks
    Given an indexed repository with multiple files
    When I search with --min-similarity=0.8
    Then only high-scoring chunks appear in results
    And low-scoring chunks are filtered out
    And files with no chunks passing threshold are omitted entirely
