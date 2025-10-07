Feature: Commit Graph Walker with Blob Deduplication
  As a gitctx indexing system
  I want to walk git commit graphs and extract unique blobs with location metadata
  So that downstream components can chunk, embed, and store with complete git context

  Background:
    Given gitctx is installed

  Scenario: Blob deduplication across commits
    Given a repository with 50 commits
    And the same blob "auth.py" appears in all 50 commits unchanged
    When I walk the commit graph
    Then I should yield the blob exactly once
    And its locations list should contain 50 BlobLocation entries
    And each location should have a unique commit SHA
    And each location should have file_path "auth.py"

  Scenario: Merge commit detection
    Given a repository with a merge commit
    And "feature.py" exists in both parent commits
    When I walk the commit graph
    Then the merge commit should be detected
    And "feature.py" locations should include the merge commit
    And parent commit relationships should be preserved

  Scenario: HEAD blob filtering
    Given a repository with 10 commits
    And "deleted.py" exists in commits 1-5 but not in HEAD
    And "current.py" exists only in HEAD
    When I walk the commit graph
    Then "deleted.py" locations should have is_head = False
    And "current.py" locations should have is_head = True

  Scenario: Binary file exclusion
    Given a repository with text and binary files
    And "code.py" is a text file
    And "image.png" is a binary file
    And "data.db" is a binary file
    When I walk the commit graph with binary filtering enabled
    Then "code.py" should be yielded
    And "image.png" should be filtered out
    And "data.db" should be filtered out

  Scenario: Large blob exclusion
    Given a repository with files of various sizes
    And "small.py" is 1KB
    And "medium.py" is 500KB
    And "large.py" is 2MB
    When I walk the commit graph with 1MB size limit
    Then "small.py" should be yielded
    And "medium.py" should be yielded
    And "large.py" should be filtered out

  Scenario: Resume from partial index
    Given a repository with 100 commits
    And commits 1-50 are already indexed
    When I walk the commit graph starting from commit 51
    Then only commits 51-100 should be processed
    And previously indexed blobs should not be re-yielded
    And the index should be complete after resuming

  Scenario: Multiple refs
    Given a repository with 3 branches
    And branch "main" has "main.py"
    And branch "feature1" has "feature1.py"
    And branch "feature2" has "feature2.py"
    When I walk the commit graph for all refs
    Then "main.py" should be yielded with main branch locations
    And "feature1.py" should be yielded with feature1 branch locations
    And "feature2.py" should be yielded with feature2 branch locations

  Scenario: Progress reporting
    Given a repository with 100 commits
    When I walk the commit graph with progress callbacks
    Then progress updates should be received
    And total commit count should be reported
    And processed commit count should increment
    And progress percentage should reach 100%

  Scenario: Gitignore filtering
    Given a repository with various files
    And ".gitignore" contains "*.pyc" and "__pycache__/"
    And "code.py" is tracked
    And "cache.pyc" is tracked but gitignored
    And "__pycache__/module.cpython-311.pyc" is tracked but gitignored
    When I walk the commit graph with gitignore filtering enabled
    Then "code.py" should be yielded
    And "cache.pyc" should be filtered out
    And "__pycache__/module.cpython-311.pyc" should be filtered out
