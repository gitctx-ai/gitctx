Feature: Progress Tracking and Cost Estimation
  As a developer using gitctx
  I want clear real-time progress for all long-running operations
  So that I understand what gitctx is doing, how long it will take, and when work is complete

  # STORY-0001.4.5: Default mode shows full progress, --quiet for minimal output
  # All scenarios use VCR.py cassettes (recorded from real API, replayed in CI)

  Scenario: Default mode shows multi-phase progress
    Given a repository with 100 files to index
    And environment variable "OPENAI_API_KEY" is "$ENV"
    When I run "gitctx index"
    Then I should see phase markers "→ Walking commit graph" and "→ Generating embeddings"
    And I should see "→ Saving index" marker
    And I should see progress bars with counts and percentages
    And final summary should show statistics table with fields:
      | Field        | Format            |
      | Commits      | \d+               |
      | Unique blobs | \d+               |
      | Chunks       | \d+               |
      | Tokens       | \d+(?:,\d+)?      |
      | Cost         | \$\d+\.\d{4}      |
      | Time         | \d+:\d+:\d+       |

  Scenario: Quiet mode shows minimal output
    Given a repository with 100 files to index
    And environment variable "OPENAI_API_KEY" is "$ENV"
    When I run "gitctx index --quiet"
    Then I should see single-line output matching "Indexed \d+ commits \(\d+ unique blobs, \d+ cached\) in \d+\.\d+s"
    And I should NOT see progress bars or phase markers

  Scenario: Pre-indexing cost estimate with --dry-run
    Given a repository with 5 files totaling 2KB
    When I run "gitctx index --dry-run"
    Then I should see estimated tokens
    And estimated cost formatted as "\$\d+\.\d{4}"
    And confidence range "Range:\\s+\$\d+\\.\\d{4} - \$\d+\\.\\d{4} \\(±10%\\)"

  Scenario: Empty repository handling
    Given an empty repository with no indexable files
    And environment variable "OPENAI_API_KEY" is "$ENV"
    When I run "gitctx index"
    Then I should see "No files to index"
    And exit code should be 0

  Scenario: Cache savings displayed during embedding
    Given I have previously indexed a repository
    And environment variable "OPENAI_API_KEY" is "$ENV"
    When I run "gitctx index" again with 50% cached blobs
    Then embedding phase should show "Total Costs: $X (N blobs) | Saved using repo cache: $Y (M blobs)"
    And saved cost should equal sum of cached embedding costs

  Scenario: ETA updates based on throughput
    Given I am indexing a large repository
    And environment variable "OPENAI_API_KEY" is "$ENV"
    When embedding phase starts
    Then ETA should update every second based on current throughput
    And throughput should be calculated from last 100 blobs processed

  Scenario: Throughput calculation handles small repositories
    Given a repository with 50 files to index
    And environment variable "OPENAI_API_KEY" is "$ENV"
    When I run "gitctx index"
    Then embedding phase should calculate throughput over min(100, 50) blobs
    And throughput should show "blobs/sec" metric
    And progress bar should complete without division-by-zero errors

  Scenario: Progress bar updates smoothly without flicker
    Given a repository with 50 files to index
    And environment variable "OPENAI_API_KEY" is "$ENV"
    When I run "gitctx index"
    Then I should see progress bars for walking, embedding, and saving phases
    And each progress bar should overwrite the previous line (no scrolling)
    And the final statistics should display after completion

  Scenario: Progress error handling with stderr redirected
    Given a repository with 100 files to index
    And environment variable "OPENAI_API_KEY" is "$ENV"
    When I run "gitctx index 2>/tmp/output.txt"
    Then indexing should complete successfully
    And output file should contain phase markers without ANSI codes
    And no progress bars should be written
