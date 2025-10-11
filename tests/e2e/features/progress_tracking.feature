Feature: Progress Tracking and Cost Estimation
  As a developer using gitctx
  I want to see progress and cost information during indexing
  So that I can monitor operations and understand the financial impact of indexing my codebase

  # TUI_GUIDE.md compliance: terse by default, verbose with --verbose flag
  # All scenarios use mocked embedders for zero-cost E2E testing

  Scenario: Default terse output (TUI_GUIDE.md:208-209)
    Given a repository with 10 files to index
    When I run "gitctx index" with mocked embedder
    Then I should see single-line output matching "Indexed \d+ commits \(\d+ unique blobs\) in \d+\.\d+s"
    And cost summary should show format "$\d+\.\d{4}"

  Scenario: Verbose mode with phase progress (TUI_GUIDE.md:230-256)
    Given a repository with 10 files to index
    When I run "gitctx index --verbose" with mocked embedder
    Then I should see phase markers "→ Walking commit graph" and "→ Generating embeddings"
    And final summary should show statistics table with fields:
      | Field        | Format          |
      | Commits      | \d+             |
      | Unique blobs | \d+             |
      | Chunks       | \d+             |
      | Tokens       | \d+,\d+         |
      | Cost         | $\d+\.\d{4}     |
      | Time         | \d+:\d+:\d+     |

  Scenario: Pre-indexing cost estimate with --dry-run
    Given a repository with 5 files totaling 2KB
    When I run "gitctx index --dry-run"
    Then I should see estimated tokens
    And estimated cost formatted as "$\d+\.\d{4}"
    And confidence range "Range: $\d+\.\d{4} - $\d+\.\d{4} \(±20%\)"

  Scenario: Graceful cancellation (TUI_GUIDE.md:377-387)
    Given indexing is in progress with 20 files
    When I send SIGINT to the process
    Then I should see "Interrupted" message
    And partial stats with tokens and cost
    And exit code should be 130

  Scenario: Empty repository handling
    Given an empty repository with no indexable files
    When I run "gitctx index"
    Then I should see "No files to index"
    And exit code should be 0
