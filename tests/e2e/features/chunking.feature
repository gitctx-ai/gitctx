Feature: Blob Content Chunking
  As the indexing system
  I want to split blob content into semantically coherent chunks
  So that large files can be indexed within token limits while preserving context

  Background:
    Given gitctx is installed

  Scenario: Chunk large Python file with overlap
    Given a Python blob with 5000 tokens
    And max_tokens configured as 800
    And chunk_overlap_ratio configured as 0.2
    When I chunk the blob
    Then I should get 7-8 chunks
    And each chunk should have at most 800 tokens
    And consecutive chunks should have approximately 20 percent content overlap
    And each chunk should have start_line and end_line metadata

  Scenario: Small blob returns single chunk
    Given a Python blob with 500 tokens
    And max_tokens configured as 800
    When I chunk the blob
    Then I should get exactly 1 chunk
    And the chunk should contain the entire blob content
    And chunk start_line should be 1

  Scenario: Language-aware splitting preserves function boundaries
    Given a Python blob with 3 small functions totaling 1200 tokens
    And max_tokens configured as 800
    When I chunk the blob
    Then functions should not be split mid-body
    And chunk boundaries should align with function boundaries when possible

  Scenario: Long single line handling
    Given a blob with one 2000-token line
    And max_tokens configured as 800
    When I chunk the blob
    Then the line should split into 3 chunks at character boundaries
    And each chunk should have at most 800 tokens
    And no content should be lost

  Scenario: Unicode and emoji support
    Given a blob containing Unicode and emoji characters
    When I count tokens in the blob
    Then tiktoken should handle non-ASCII correctly
    And chunking should not corrupt multibyte characters

  Scenario: Multiple language support
    Given blobs in Python, JavaScript, TypeScript, Go, Rust, Java, and Markdown
    When I chunk each blob
    Then each should use language-specific splitting rules
    And metadata should indicate the detected language

  Scenario: Chunk metadata completeness
    Given a blob chunked into 5 pieces
    When I examine chunk metadata
    Then each chunk should have a content field
    And each chunk should have a start_line field
    And each chunk should have an end_line field
    And each chunk should have a token_count field
    And each chunk should have a metadata dictionary

  Scenario: Empty content handling
    Given an empty blob
    When I chunk the blob
    Then I should get an empty list
    And no errors should be raised

  Scenario: Token limit compliance verification
    Given 100 random blobs of varying sizes
    And max_tokens configured as 800
    When I chunk all blobs
    Then 100 percent of chunks should have token_count at most 880
