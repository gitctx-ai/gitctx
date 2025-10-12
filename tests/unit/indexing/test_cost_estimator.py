"""Unit tests for cost estimation (TDD approach)."""


class TestCostEstimatorConstants:
    """Test CostEstimator constants."""

    def test_cost_per_1k_tokens_constant(self):
        """Test COST_PER_1K_TOKENS matches text-embedding-3-large pricing."""
        from gitctx.indexing.progress import CostEstimator

        # text-embedding-3-large pricing: $0.00013 per 1K tokens
        assert CostEstimator.COST_PER_1K_TOKENS == 0.00013

    def test_sampling_parameters(self):
        """Test sampling configuration constants."""
        from gitctx.indexing.progress import CostEstimator

        # Sample 10KB per file for token estimation
        assert CostEstimator.SAMPLE_SIZE_BYTES == 10_000

        # Sample 10% of files
        assert CostEstimator.SAMPLE_PERCENTAGE == 0.1


class TestCostEstimatorBasic:
    """Test basic cost estimation functionality."""

    def test_estimate_repo_cost_with_tiktoken(self, tmp_path):
        """Test estimate_repo_cost uses tiktoken for accurate estimation."""
        from gitctx.indexing.progress import CostEstimator

        # Create small test repo with realistic code content
        repo = tmp_path / "test_repo"
        repo.mkdir()

        # Create Python files with typical code structure
        # ~4 chars per token for code (cl100k_base)
        (repo / "main.py").write_text('def main():\n    print("Hello, world!")\n    return 0\n')
        (repo / "utils.py").write_text("def helper(x):\n    return x * 2\n")
        (repo / "config.py").write_text('SETTINGS = {"key": "value"}\n')

        estimator = CostEstimator()
        result = estimator.estimate_repo_cost(repo)

        # Should have basic counts
        assert result["total_files"] == 3
        assert result["total_lines"] > 0

        # Tokens should be estimated via tiktoken
        # Expected ~20-40 tokens for this content
        assert 10 < result["estimated_tokens"] < 100

        # Cost should be > 0
        assert result["estimated_cost"] > 0

    def test_confidence_range_calculation(self, tmp_path):
        """Test confidence range is ±10% with tiktoken sampling."""
        from gitctx.indexing.progress import CostEstimator

        # Create repo with some content
        repo = tmp_path / "test_repo"
        repo.mkdir()
        (repo / "file.py").write_text("\n".join([f"def function_{i}(): pass" for i in range(20)]))

        estimator = CostEstimator()
        result = estimator.estimate_repo_cost(repo)

        estimated_cost = result["estimated_cost"]

        # Verify ±10% range (improved from ±20% with line-based)
        assert result["min_cost"] == estimated_cost * 0.9
        assert result["max_cost"] == estimated_cost * 1.1

    def test_empty_repo_returns_zeros(self, tmp_path):
        """Test empty repository returns zero estimates."""
        from gitctx.indexing.progress import CostEstimator

        # Create empty repo
        repo = tmp_path / "empty_repo"
        repo.mkdir()

        estimator = CostEstimator()
        result = estimator.estimate_repo_cost(repo)

        assert result["total_files"] == 0
        assert result["total_lines"] == 0
        assert result["estimated_tokens"] == 0
        assert result["estimated_cost"] == 0.0
        assert result["min_cost"] == 0.0
        assert result["max_cost"] == 0.0


class TestCostEstimatorFileWalking:
    """Test file walking and indexable file detection."""

    def test_get_indexable_files_excludes_git_dir(self, tmp_path):
        """Test _get_indexable_files excludes .git directory."""
        from gitctx.indexing.progress import CostEstimator

        # Create repo with .git directory
        repo = tmp_path / "test_repo"
        repo.mkdir()
        (repo / "file.py").write_text("print('hello')")

        git_dir = repo / ".git"
        git_dir.mkdir()
        (git_dir / "config").write_text("should not count\n" * 100)
        (git_dir / "hooks").mkdir()
        (git_dir / "hooks" / "pre-commit").write_text("#!/bin/bash\n")

        estimator = CostEstimator()
        indexable_files = estimator._get_indexable_files(repo)

        # Should only find file.py, not .git/*
        assert len(indexable_files) == 1
        assert indexable_files[0].name == "file.py"

    def test_get_indexable_files_multiple_languages(self, tmp_path):
        """Test _get_indexable_files finds all supported language files."""
        from gitctx.indexing.progress import CostEstimator

        # Create repo with multiple language files
        repo = tmp_path / "test_repo"
        repo.mkdir()

        # Create files with various extensions
        test_files = [
            "script.py",  # Python
            "app.java",  # Java
            "service.rb",  # Ruby
            "api.php",  # PHP
            "main.go",  # Go
            "index.js",  # JavaScript
            "app.ts",  # TypeScript
            "README.md",  # Markdown
            "Makefile",  # Extensionless (supported)
        ]

        for filename in test_files:
            (repo / filename).write_text(f"content of {filename}")

        estimator = CostEstimator()
        indexable_files = estimator._get_indexable_files(repo)

        # Should find all test files
        found_names = {f.name for f in indexable_files}
        assert found_names == set(test_files)

    def test_get_indexable_files_excludes_binary(self, tmp_path):
        """Test _get_indexable_files excludes binary extensions."""
        from gitctx.indexing.progress import CostEstimator

        repo = tmp_path / "test_repo"
        repo.mkdir()

        # Create text file
        (repo / "text.py").write_text("print('hello')")

        # Create binary file (.bin is not in supported extensions)
        (repo / "binary.bin").write_bytes(b"\x00\x01\x02\xff")

        estimator = CostEstimator()
        indexable_files = estimator._get_indexable_files(repo)

        # Should only find text.py (binary.bin excluded by extension)
        assert len(indexable_files) == 1
        assert indexable_files[0].name == "text.py"


class TestCostEstimatorTiktokenAccuracy:
    """Test tiktoken-based token estimation accuracy."""

    def test_token_estimation_accuracy_python(self, tmp_path):
        """Test token estimation is accurate for Python code."""
        import tiktoken

        from gitctx.indexing.progress import CostEstimator

        # Create repo with substantial Python code
        repo = tmp_path / "test_repo"
        repo.mkdir()

        # Real Python code sample (~200 tokens)
        python_code = '''
def authenticate_user(username: str, password: str) -> bool:
    """Authenticate user with username and password.

    Args:
        username: User's username
        password: User's password

    Returns:
        True if authentication successful, False otherwise
    """
    # Hash password
    password_hash = hash_password(password)

    # Query database
    user = db.query(User).filter_by(username=username).first()

    if user is None:
        return False

    # Verify password
    return verify_password(password_hash, user.password_hash)
'''
        (repo / "auth.py").write_text(python_code)
        (repo / "utils.py").write_text(python_code)  # Duplicate for more content
        (repo / "main.py").write_text(python_code)

        # Calculate actual token count with tiktoken
        encoding = tiktoken.get_encoding("cl100k_base")
        total_content = python_code * 3
        actual_tokens = len(encoding.encode(total_content))

        # Get estimate
        estimator = CostEstimator()
        result = estimator.estimate_repo_cost(repo)

        # Should be within ±10% accuracy
        estimated_tokens = result["estimated_tokens"]
        accuracy = abs(estimated_tokens - actual_tokens) / actual_tokens

        assert accuracy < 0.1, (
            f"Token estimation accuracy {accuracy:.1%} exceeds ±10% tolerance. "
            f"Expected ~{actual_tokens}, got {estimated_tokens}"
        )

    def test_sampling_provides_consistent_estimates(self, tmp_path):
        """Test that sampling provides consistent estimates across runs."""
        from gitctx.indexing.progress import CostEstimator

        # Create repo with multiple files
        repo = tmp_path / "test_repo"
        repo.mkdir()

        for i in range(20):
            content = "\n".join([f"def function_{i}_{j}(): pass" for j in range(10)])
            (repo / f"file_{i}.py").write_text(content)

        estimator = CostEstimator()

        # Run estimation multiple times
        results = [estimator.estimate_repo_cost(repo) for _ in range(5)]

        # All estimates should be reasonably close (within 20% of each other)
        # Note: Some variance expected due to random sampling
        token_estimates = [r["estimated_tokens"] for r in results]
        mean_estimate = sum(token_estimates) / len(token_estimates)

        for estimate in token_estimates:
            variance = abs(estimate - mean_estimate) / mean_estimate
            assert variance < 0.2, (
                f"Sampling variance {variance:.1%} too high. Estimates: {token_estimates}"
            )

    def test_handles_unicode_content(self, tmp_path):
        """Test estimation handles Unicode content correctly."""
        from gitctx.indexing.progress import CostEstimator

        repo = tmp_path / "test_repo"
        repo.mkdir()

        # Create files with Unicode content
        (repo / "chinese.py").write_text('greeting = "你好世界"  # Hello World')
        (repo / "emoji.py").write_text('status = "✅ Complete 🎉"')
        (repo / "mixed.py").write_text('text = "Hello мир 世界 🌍"')

        estimator = CostEstimator()
        result = estimator.estimate_repo_cost(repo)

        # Should handle Unicode without errors
        assert result["estimated_tokens"] > 0
        assert result["estimated_cost"] > 0
        assert result["total_files"] == 3
