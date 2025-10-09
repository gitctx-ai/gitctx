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
    Given I embed 3 chunks totaling 600 tokens
    When I review the cost tracking
    Then total cost should be $0.000078 (600 tokens * $0.13/1M)
    And cost should be tracked per chunk
    And aggregate cost should be logged

  Scenario: Validate API key on initialization
    Given GitCtxSettings has no OpenAI API key configured
    When I attempt to initialize the OpenAIEmbedder
    Then a ConfigurationError should be raised
    And the error message should indicate missing API key
    And suggest how to configure the key
