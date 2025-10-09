Feature: OpenAI Embedding Generation
  As the indexing system (serving developers and AI agents)
  I want to generate embeddings for code chunks using OpenAI's text-embedding-3-large model
  So that chunks can be semantically searched with high-quality vector representations while tracking costs accurately

  Background:
    Given gitctx is installed

  Scenario: Generate embedding for single chunk
    Given a code chunk with 200 tokens
    And OpenAI API key is configured in GitCtxSettings
    When I generate an embedding for the chunk
    Then I should receive a 3072-dimensional vector
    And the API should report 200 tokens used
    And the cost should be $0.000026 (200 tokens * $0.13/1M)

  Scenario: Batch process multiple chunks efficiently
    Given 500 code chunks from a repository
    And max batch size is 2048 chunks
    When I generate embeddings with batching enabled
    Then chunks should be batched into 1 API call
    And all 500 embeddings should be 3072 dimensions
    And total API calls should be 1 (not 500)
    And processing time should be <5 seconds

  Scenario: Handle rate limit errors with exponential backoff
    Given the OpenAI API is returning 429 rate limit errors
    And exponential backoff is configured (base delay: 1s, max retries: 5)
    When I attempt to generate embeddings
    Then the system should retry with delays: 1s, 2s, 4s, 8s, 16s
    And eventually succeed when rate limit clears
    And log each retry attempt with timestamp

  Scenario: Handle network errors gracefully
    Given the OpenAI API is unreachable (network error)
    When I attempt to generate embeddings
    Then the system should retry up to 5 times with exponential backoff
    And if all retries fail, raise a clear NetworkError
    And log the error with context (chunk count, blob SHA)

  Scenario: Cache embeddings by blob SHA
    Given a blob with SHA "abc123" was previously embedded
    And the embedding is cached in EmbeddingCache
    When I request an embedding for SHA "abc123"
    Then the cached embedding should be returned
    And no API call should be made
    And the cache hit should be logged

  Scenario: Generate new embeddings for uncached blobs
    Given a blob with SHA "def456" is not in the cache
    When I request an embedding for SHA "def456"
    Then an API call should be made to OpenAI
    And the embedding should be stored in the cache with key "def456"
    And the cache miss should be logged

  Scenario: Validate embedding dimensions
    Given an embedding is generated from the API
    When I validate the embedding
    Then it should have exactly 3072 dimensions
    And if dimensions don't match, raise DimensionMismatchError
    And log the error with expected vs actual dimensions

  Scenario: Track API costs accurately
    Given I embed 10,000 chunks totaling 2,000,000 tokens
    When I review the cost tracking
    Then total cost should be $0.26 (2M tokens * $0.13/1M)
    And cost should be tracked per chunk
    And aggregate cost should be logged

  Scenario: Log progress during batch processing
    Given 1000 chunks to embed
    When I generate embeddings with progress logging enabled
    Then progress should be logged every 100 chunks
    And logs should include: chunks processed, tokens used, estimated cost
    And final log should show totals

  Scenario: Validate API key on initialization
    Given GitCtxSettings has no OpenAI API key configured
    When I attempt to initialize the OpenAIEmbedder
    Then a ConfigurationError should be raised
    And the error message should indicate missing API key
    And suggest how to configure the key
