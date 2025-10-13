Feature: Query Embedding for Semantic Search
  As a developer
  I want to convert my search queries into embeddings
  So that I can perform semantic code search based on meaning rather than exact text matching

  Background:
    Given gitctx is installed

  # This scenario verifies query embedding generation via OpenAI API
  # VCR cassette records API response for deterministic replay
  Scenario: Query embedding generated successfully
    Given an indexed repository
    And environment variable "OPENAI_API_KEY" is "$ENV"
    When I run "gitctx search 'authentication middleware'"
    Then the exit code should be 0
    And results should be displayed

  # This scenario verifies cache reuse to avoid duplicate API calls
  Scenario: Cached query embedding reused (no API call)
    Given an indexed repository
    And environment variable "OPENAI_API_KEY" is "$ENV"
    And query "database setup" was previously searched
    When I run "gitctx search 'database setup'"
    Then the exit code should be 0
    And results should be displayed

  # This scenario verifies API key configuration detection (exit code 4)
  Scenario: Missing API key (exit code 4)
    Given an indexed repository
    And environment variable "OPENAI_API_KEY" is ""
    When I run "gitctx search 'test query'"
    Then the exit code should be 4
    And the output should contain "Error: OpenAI API key not configured"
    And the output should contain "Set with: export OPENAI_API_KEY=sk-..."
    And the output should contain "Or run: gitctx config set api_keys.openai sk-..."

  # This scenario verifies empty query validation (exit code 2)
  Scenario: Empty query validation (exit code 2)
    Given an indexed repository
    When I run "gitctx search ''"
    Then the exit code should be 2
    And the output should contain "Error: Query cannot be empty"

  # This scenario verifies token limit validation (exit code 2)
  Scenario: Query exceeds token limit (exit code 2)
    Given an indexed repository
    And environment variable "OPENAI_API_KEY" is "$ENV"
    And a file "tests/fixtures/long_query_9000_tokens.txt" with 9000 tokens
    When I run gitctx with query from file "tests/fixtures/long_query_9000_tokens.txt"
    Then the exit code should be 2
    And the output should contain "Error: Query exceeds 8191 tokens (got 9000)"
    And the output should contain "Try a shorter, more specific query"
