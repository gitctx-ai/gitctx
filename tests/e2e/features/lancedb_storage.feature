Feature: LanceDB Vector Storage
  As the indexing system
  I want to store embeddings with denormalized metadata in LanceDB
  So that semantic search can retrieve precise code locations with full git context in a single query

  Background:
    Given gitctx is installed
    And I am in an isolated test repository

  Scenario: Store embeddings with denormalized metadata
    Given 100 embeddings from 10 blobs
    And each embedding has associated BlobLocation metadata
    When I store embeddings in LanceDB
    Then each vector should be stored with denormalized metadata
    And metadata should include: blob_sha, chunk_index, file_path, line range, commit info
    And I should be able to query and get complete context in one operation

  Scenario: Batch insertion for efficiency
    Given 5000 embeddings to store
    When I insert in batches
    Then all 5000 should be inserted successfully
    And insertion should take less than 10 seconds total
    And batch size should be configurable with default 1000

  Scenario: Automatic IVF-PQ indexing
    Given a table with 300 vectors
    When I call optimize()
    Then an IVF-PQ index should be created automatically
    And index should use cosine similarity metric
    And partitions should be adaptive based on row count divided by 256
    And subvectors should be adaptive based on dimensions divided by 16

  Scenario: Incremental updates
    Given an existing index with 1000 chunks
    And 50 new chunks from 5 new blobs
    When I add the new chunks
    Then index should contain 1050 chunks total
    And old chunks should remain unchanged
    And new chunks should be immediately searchable

  Scenario: Index state tracking
    Given indexing completed at commit abc123
    When I save index metadata
    Then metadata should include last_commit as abc123
    And metadata should include indexed_blobs list
    And metadata should include last_indexed timestamp
    And metadata should include embedding_model name

  Scenario: Schema validation
    Given an existing index with 3072-dimensional vectors
    When I attempt to insert 1024-dimensional vectors
    Then I should get clear error message "Dimension mismatch: expected 3072, got 1024"
    And no data should be written
    And user should be advised to re-index

  Scenario: Statistics reporting
    Given an index with 5000 chunks from 100 files
    When I request statistics
    Then total_chunks should be 5000
    And total_files should be 100
    And index_size_mb should be less than 150
    And total_blobs should be approximately 500

  Scenario: Query with blob location context
    Given embeddings stored with denormalized BlobLocation data
    When I search for similar vectors
    Then results should include chunk content
    And results should include file_path
    And results should include line_range with start_line and end_line
    And results should include blob_sha
    And results should include commit_sha, author, date, message
    And results should include is_head flag

  Scenario: Empty index handling
    Given a newly initialized LanceDB store
    When I query for statistics
    Then total_chunks should be 0
    And total_files should be 0
    And index_size_mb should be approximately 0

  Scenario: Storage location
    Given .gitctx directory in repo root
    When I initialize LanceDB
    Then database should be created at .gitctx/lancedb/
    And .gitctx should be in .gitignore
    And database files should not be committed to git
