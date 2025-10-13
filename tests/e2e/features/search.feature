Feature: Query Embedding for Semantic Search
  As a developer
  I want to convert my search queries into embeddings
  So that I can perform semantic code search based on meaning rather than exact text matching

  Background:
    Given gitctx is installed

  # This scenario verifies query embedding generation via OpenAI API
  # VCR cassette records API response for deterministic replay
  # Uses quoted query to test that quotes work
  Scenario: Query embedding generated successfully
    Given an indexed repository
    And environment variable "OPENAI_API_KEY" is "$ENV"
    When I run "gitctx search 'authentication middleware'"
    Then the exit code should be 0
    And results should be displayed

  # This scenario verifies cache reuse to avoid duplicate API calls
  # Uses unquoted variadic query
  Scenario: Cached query embedding reused (no API call)
    Given an indexed repository
    And environment variable "OPENAI_API_KEY" is "$ENV"
    And query "database setup" was previously searched
    When I run "gitctx search database setup"
    Then the exit code should be 0
    And results should be displayed

  # This scenario verifies API key configuration detection (exit code 4)
  # Uses unquoted variadic query
  Scenario: Missing API key (exit code 4)
    Given an indexed repository
    And environment variable "OPENAI_API_KEY" is ""
    When I run "gitctx search test query"
    Then the exit code should be 4
    And the error should contain "Error: OpenAI API key not configured"
    And the error should contain "Set with: export OPENAI_API_KEY=sk-..."
    And the error should contain "Or run: gitctx config set api_keys.openai sk-..."

  # This scenario verifies empty query validation (exit code 2)
  Scenario: Empty query validation (exit code 2)
    Given an indexed repository
    When I run "gitctx search ''"
    Then the exit code should be 2
    And the error should contain "Error: Query cannot be empty"

  # This scenario verifies token limit validation (exit code 2)
  Scenario: Query exceeds token limit (exit code 2)
    Given an indexed repository
    And environment variable "OPENAI_API_KEY" is "$ENV"
    And a file "tests/fixtures/long_query_9000_tokens.txt" with 9000 tokens
    When I run gitctx with query from file "tests/fixtures/long_query_9000_tokens.txt"
    Then the exit code should be 2
    And the error should contain "Error: Query exceeds 8191 tokens (got 9000)"
    And the error should contain "Try a shorter"

  # STORY-0001.3.2: Vector Similarity Search scenarios below

  Scenario: Search with unquoted multi-word query
    Given an indexed repository
    And environment variable "OPENAI_API_KEY" is "$ENV"
    When I run "gitctx search authentication middleware"
    Then the exit code should be 0
    And results should match query "authentication middleware"

  Scenario: Search with flags before query terms
    Given an indexed repository
    And environment variable "OPENAI_API_KEY" is "$ENV"
    When I run "gitctx search --limit 5 find all api references"
    Then the exit code should be 0
    And exactly 5 results should be shown

  Scenario: Search from stdin (pipeline)
    Given an indexed repository
    And environment variable "OPENAI_API_KEY" is "$ENV"
    When I pipe "authentication middleware" to "gitctx search"
    Then the exit code should be 0
    And results should match query "authentication middleware"

  Scenario: Search returns results sorted by similarity score
    Given an indexed repository
    And environment variable "OPENAI_API_KEY" is "$ENV"
    When I run "gitctx search authentication middleware"
    Then the exit code should be 0
    And results should be sorted by _distance ascending (0.0 = best match first)
    And each result should show cosine similarity score between 0.0 and 1.0

  Scenario: Search with result limit
    Given an indexed repository with 20+ chunks containing "database" keyword
    And environment variable "OPENAI_API_KEY" is "$ENV"
    When I run "gitctx search database --limit 5"
    Then the exit code should be 0
    And exactly 5 results should be shown

  Scenario: Search with no results
    Given an indexed repository
    And environment variable "OPENAI_API_KEY" is "$ENV"
    When I run "gitctx search nonexistent_function_xyz"
    Then the exit code should be 0
    And the output should contain "0 results in"

  Scenario: Search before indexing (exit code 8)
    Given no index exists at .gitctx/db/lancedb/
    And environment variable "OPENAI_API_KEY" is "$ENV"
    When I run "gitctx search test"
    Then the exit code should be 8
    And the output should contain "Error: No index found"
    And the output should contain "Run: gitctx index"

  Scenario: Empty stdin with no args (exit code 2)
    Given an indexed repository
    When I run "gitctx search" with empty stdin in non-interactive terminal
    Then the exit code should be 2
    And the output should contain "Error: Query required (from args or stdin)"

  Scenario: Invalid result limit too low (exit code 2)
    Given an indexed repository
    When I run "gitctx search test --limit 0"
    Then the exit code should be 2
    And the output should contain "Error: --limit must be between 1 and 100 (got 0)"

  Scenario: Invalid result limit too high (exit code 2)
    Given an indexed repository
    When I run "gitctx search test --limit 150"
    Then the exit code should be 2
    And the output should contain "Error: --limit must be between 1 and 100 (got 150)"

  @performance
  Scenario: Search performance meets p95 latency target
    Given an indexed repository with 10000 chunks
    And environment variable "OPENAI_API_KEY" is "$ENV"
    When I run search 100 times with query "authentication"
    Then p95 response time should be under 2.0 seconds
    And all requests should complete within 5.0 seconds
