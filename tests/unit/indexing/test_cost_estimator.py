"""Unit tests for cost estimation (TDD approach)."""



class TestCostEstimatorConstants:
    """Test CostEstimator constants."""

    def test_tokens_per_line_constant(self):
        """Test TOKENS_PER_LINE is conservative estimate from 16x Prompt study."""
        from gitctx.indexing.progress import CostEstimator

        # Conservative estimate: 5.0 tokens/line
        # Empirical: Python ~10, JS ~7, SQL ~11.5 tokens/line
        # Source: https://prompt.16x.engineer/blog/code-to-tokens-conversion
        assert CostEstimator.TOKENS_PER_LINE == 5.0

    def test_cost_per_1k_tokens_constant(self):
        """Test COST_PER_1K_TOKENS matches text-embedding-3-large pricing."""
        from gitctx.indexing.progress import CostEstimator

        # text-embedding-3-large pricing: $0.00013 per 1K tokens
        assert CostEstimator.COST_PER_1K_TOKENS == 0.00013


class TestCostEstimatorBasic:
    """Test basic cost estimation functionality."""

    def test_estimate_repo_cost_basic(self, tmp_path):
        """Test estimate_repo_cost calculates tokens and cost correctly."""
        from gitctx.indexing.progress import CostEstimator

        # Create small test repo with known line count
        repo = tmp_path / "test_repo"
        repo.mkdir()

        # Create 3 files with 10 lines each = 30 total lines
        for i in range(3):
            file = repo / f"file{i}.py"
            file.write_text("\n".join([f"line {j}" for j in range(10)]))

        estimator = CostEstimator()
        result = estimator.estimate_repo_cost(repo)

        # Expected: 30 lines * 5.0 tokens/line = 150 tokens
        assert result["total_lines"] == 30
        assert result["total_files"] == 3
        assert result["estimated_tokens"] == 150

        # Expected: (150 / 1000) * 0.00013 = 0.0000195
        expected_cost = (150 / 1000) * 0.00013
        assert result["estimated_cost"] == expected_cost

    def test_confidence_range_calculation(self, tmp_path):
        """Test confidence range is ±20% of estimated cost."""
        from gitctx.indexing.progress import CostEstimator

        # Create repo with 100 lines
        repo = tmp_path / "test_repo"
        repo.mkdir()
        (repo / "file.py").write_text("\n".join([f"line {i}" for i in range(100)]))

        estimator = CostEstimator()
        result = estimator.estimate_repo_cost(repo)

        estimated_cost = result["estimated_cost"]

        # Verify ±20% range
        assert result["min_cost"] == estimated_cost * 0.8
        assert result["max_cost"] == estimated_cost * 1.2


class TestCostEstimatorFileWalking:
    """Test file walking and counting logic."""

    def test_count_lines_excludes_git_dir(self, tmp_path):
        """Test _count_lines excludes .git directory."""
        from gitctx.indexing.progress import CostEstimator

        # Create repo with .git directory
        repo = tmp_path / "test_repo"
        repo.mkdir()
        (repo / "file.py").write_text("line1\nline2\nline3")

        git_dir = repo / ".git"
        git_dir.mkdir()
        (git_dir / "config").write_text("should not count\n" * 100)

        estimator = CostEstimator()
        line_count = estimator._count_lines(repo)

        # Should only count file.py (3 lines), not .git/config
        assert line_count == 3

    def test_count_lines_multiple_languages(self, tmp_path):
        """Test _count_lines counts all supported language files."""
        from gitctx.indexing.progress import CostEstimator

        # Create repo with multiple language files
        repo = tmp_path / "test_repo"
        repo.mkdir()

        # Create files with various extensions (sampling of supported languages)
        files_and_lines = {
            "script.py": 10,  # Python
            "app.java": 15,  # Java
            "service.rb": 12,  # Ruby
            "api.php": 8,  # PHP
            "main.go": 20,  # Go
            "index.js": 5,  # JavaScript
            "app.ts": 9,  # TypeScript
            "README.md": 6,  # Markdown
        }

        for filename, line_count in files_and_lines.items():
            content = "\n".join([f"line {i}" for i in range(line_count)])
            (repo / filename).write_text(content)

        estimator = CostEstimator()
        total_lines = estimator._count_lines(repo)

        # Expected: sum of all lines
        expected = sum(files_and_lines.values())
        assert total_lines == expected

    def test_count_lines_handles_binary_files(self, tmp_path):
        """Test _count_lines gracefully skips binary files."""
        from gitctx.indexing.progress import CostEstimator

        repo = tmp_path / "test_repo"
        repo.mkdir()

        # Create text file
        (repo / "text.py").write_text("line1\nline2")

        # Create binary file
        (repo / "binary.bin").write_bytes(b"\x00\x01\x02\xff")

        estimator = CostEstimator()
        line_count = estimator._count_lines(repo)

        # Should count text file only (2 lines)
        assert line_count == 2

    def test_count_files_matches_count_lines_filtering(self, tmp_path):
        """Test _count_files uses same filtering as _count_lines."""
        from gitctx.indexing.progress import CostEstimator

        repo = tmp_path / "test_repo"
        repo.mkdir()

        # Create various files
        (repo / "code.py").write_text("code")
        (repo / "docs.md").write_text("docs")

        # Create .git directory (should be excluded)
        git_dir = repo / ".git"
        git_dir.mkdir()
        (git_dir / "config").write_text("git config")

        estimator = CostEstimator()
        file_count = estimator._count_files(repo)

        # Should count 2 files (code.py, docs.md), not .git/config
        assert file_count == 2
