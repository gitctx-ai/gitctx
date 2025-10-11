Feature: Progress Tracking and Cost Estimation
  As a developer using gitctx
  I want to see progress and cost information during indexing
  So that I can monitor operations and understand the financial impact of indexing my codebase

  # TUI_GUIDE.md compliance: terse by default, verbose with --verbose flag
  # All scenarios use VCR.py cassettes (recorded from real API, replayed in CI)

  Scenario: Default terse output
    Given a repository with 10 files to index
    And environment variable "OPENAI_API_KEY" is "$ENV"
    When I run "gitctx index"
    Then I should see single-line output matching "Indexed \d+ commits \(\d+ unique blobs\) in \d+\.\d+s"
    And cost summary should show format "\$\d+\.\d{4}"

  Scenario: Verbose mode with phase progress
    Given a repository with 10 files to index
    And environment variable "OPENAI_API_KEY" is "$ENV"
    When I run "gitctx index --verbose"
    Then I should see phase markers "→ Walking commit graph" and "→ Generating embeddings"
    And final summary should show statistics table with fields:
      | Field        | Format            |
      | Commits      | \d+               |
      | Unique blobs | \d+               |
      | Chunks       | \d+               |
      | Tokens       | \d+(?:,\d+)?      |
      | Cost         | \$\d+\.\d{4}      |
      | Time         | \d+:\d+:\d+       |

  Scenario: Pre-indexing cost estimate with --dry-run
    Given a repository with 5 files totaling 2KB
    When I run "gitctx index --dry-run"
    Then I should see estimated tokens
    And estimated cost formatted as "\$\d+\.\d{4}"
    And confidence range "Range:\\s+\$\d+\\.\\d{4} - \$\d+\\.\\d{4} \\(±20%\\)"

  Scenario: Empty repository handling
    Given an empty repository with no indexable files
    And environment variable "OPENAI_API_KEY" is "$ENV"
    When I run "gitctx index"
    Then I should see "No files to index"
    And exit code should be 0
