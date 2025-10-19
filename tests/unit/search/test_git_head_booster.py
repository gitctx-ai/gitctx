"""Unit tests for GitHeadBooster class.

Following TDD (Test-Driven Development):
1. Write tests first (RED - all fail)
2. Implement minimal code to pass (GREEN)
3. Refactor while keeping tests green

These tests verify the HEAD boosting algorithm that applies a configurable
multiplier to search result scores for chunks from the HEAD commit.
"""

# ruff: noqa: PLC0415 # Inline imports in test methods are acceptable

import pytest

from gitctx.indexing.types import SearchResult


def create_search_result(
    file_path: str = "test.py",
    hybrid_score: float | None = 0.8,
    is_head: bool = True,
) -> SearchResult:
    """Helper to create SearchResult for testing."""
    return SearchResult(
        chunk_content="test content",
        file_path=file_path,
        distance=0.2,
        commit_sha="a" * 40,
        token_count=10,
        blob_sha="b" * 40,
        chunk_index=0,
        start_line=1,
        end_line=5,
        total_chunks=1,
        language="python",
        author_name="Test Author",
        author_email="test@example.com",
        commit_date="2025-01-15T10:00:00Z",
        commit_message="test commit",
        is_head=is_head,
        is_merge=False,
        bm25_score=0.7,
        vector_score=0.85,
        hybrid_score=hybrid_score,
    )


class TestGitHeadBoosterInitialization:
    """Test GitHeadBooster initialization and validation."""

    def test_init_with_default_multiplier(self) -> None:
        """Test booster initializes with default 1.5x multiplier."""
        from gitctx.search.git_head_booster import GitHeadBooster

        booster = GitHeadBooster()
        assert booster.head_multiplier == 1.5

    def test_init_with_custom_multiplier(self) -> None:
        """Test booster initializes with custom multiplier."""
        from gitctx.search.git_head_booster import GitHeadBooster

        booster = GitHeadBooster(head_multiplier=2.0)
        assert booster.head_multiplier == 2.0

    def test_init_rejects_multiplier_below_one(self) -> None:
        """Test booster rejects multipliers < 1.0 (would penalize HEAD)."""
        from gitctx.search.git_head_booster import GitHeadBooster

        with pytest.raises(ValueError, match=r"Multiplier must be between 1\.0 and 3\.0"):
            GitHeadBooster(head_multiplier=0.9)

    def test_init_rejects_multiplier_above_three(self) -> None:
        """Test booster rejects multipliers > 3.0 (too aggressive)."""
        from gitctx.search.git_head_booster import GitHeadBooster

        with pytest.raises(ValueError, match=r"Multiplier must be between 1\.0 and 3\.0"):
            GitHeadBooster(head_multiplier=3.1)

    def test_init_accepts_boundary_values(self) -> None:
        """Test booster accepts boundary values 1.0 and 3.0."""
        from gitctx.search.git_head_booster import GitHeadBooster

        booster_min = GitHeadBooster(head_multiplier=1.0)
        assert booster_min.head_multiplier == 1.0

        booster_max = GitHeadBooster(head_multiplier=3.0)
        assert booster_max.head_multiplier == 3.0


class TestGitHeadBoosterBoostMethod:
    """Test GitHeadBooster.boost() method behavior."""

    def test_boost_single_head_result(self) -> None:
        """Test boosting a single HEAD result multiplies hybrid_score by 1.5."""
        from gitctx.search.git_head_booster import GitHeadBooster

        booster = GitHeadBooster(head_multiplier=1.5)
        result = create_search_result(file_path="head.py", hybrid_score=0.8, is_head=True)

        boosted = booster.boost([result])

        assert len(boosted) == 1
        assert boosted[0].hybrid_score == pytest.approx(0.8 * 1.5)  # 1.2
        assert boosted[0].file_path == "head.py"

    def test_boost_single_historical_result_unchanged(self) -> None:
        """Test historical results (is_head=False) are not boosted."""
        from gitctx.search.git_head_booster import GitHeadBooster

        booster = GitHeadBooster(head_multiplier=1.5)
        result = create_search_result(file_path="old.py", hybrid_score=0.8, is_head=False)

        boosted = booster.boost([result])

        assert len(boosted) == 1
        assert boosted[0].hybrid_score == 0.8  # Unchanged
        assert boosted[0].file_path == "old.py"

    def test_boost_mixed_head_and_historical_results(self) -> None:
        """Test boosting mixed HEAD and historical results."""
        from gitctx.search.git_head_booster import GitHeadBooster

        booster = GitHeadBooster(head_multiplier=1.5)
        results = [
            create_search_result(file_path="head1.py", hybrid_score=0.8, is_head=True),
            create_search_result(file_path="old1.py", hybrid_score=0.9, is_head=False),
            create_search_result(file_path="head2.py", hybrid_score=0.6, is_head=True),
        ]

        boosted = booster.boost(results)

        assert len(boosted) == 3
        # HEAD results boosted
        assert boosted[0].hybrid_score == pytest.approx(0.8 * 1.5)  # 1.2
        assert boosted[2].hybrid_score == pytest.approx(0.6 * 1.5)  # 0.9
        # Historical result unchanged
        assert boosted[1].hybrid_score == 0.9

    def test_boost_handles_empty_list(self) -> None:
        """Test boosting empty list returns empty list."""
        from gitctx.search.git_head_booster import GitHeadBooster

        booster = GitHeadBooster()
        boosted = booster.boost([])

        assert boosted == []

    def test_boost_handles_none_hybrid_score(self) -> None:
        """Test boosting handles results with None hybrid_score (skip boosting)."""
        from gitctx.search.git_head_booster import GitHeadBooster

        booster = GitHeadBooster(head_multiplier=1.5)
        result = create_search_result(file_path="head.py", hybrid_score=None, is_head=True)

        boosted = booster.boost([result])

        assert len(boosted) == 1
        assert boosted[0].hybrid_score is None  # Unchanged (can't boost None)

    def test_boost_handles_zero_score(self) -> None:
        """Test boosting handles zero scores (edge case)."""
        from gitctx.search.git_head_booster import GitHeadBooster

        booster = GitHeadBooster(head_multiplier=1.5)
        result = create_search_result(file_path="head.py", hybrid_score=0.0, is_head=True)

        boosted = booster.boost([result])

        assert len(boosted) == 1
        assert boosted[0].hybrid_score == 0.0  # 0.0 * 1.5 = 0.0

    def test_boost_handles_max_score(self) -> None:
        """Test boosting handles maximum score (1.0)."""
        from gitctx.search.git_head_booster import GitHeadBooster

        booster = GitHeadBooster(head_multiplier=1.5)
        result = create_search_result(file_path="head.py", hybrid_score=1.0, is_head=True)

        boosted = booster.boost([result])

        assert len(boosted) == 1
        assert boosted[0].hybrid_score == pytest.approx(1.5)  # Can exceed 1.0 after boosting


class TestGitHeadBoosterImmutability:
    """Test GitHeadBooster immutability (functional programming pattern)."""

    def test_boost_does_not_modify_input_list(self) -> None:
        """Test boost() does not modify the input results list."""
        from gitctx.search.git_head_booster import GitHeadBooster

        booster = GitHeadBooster(head_multiplier=1.5)
        original = create_search_result(file_path="head.py", hybrid_score=0.8, is_head=True)
        results = [original]

        boosted = booster.boost(results)

        # Original result unchanged
        assert results[0].hybrid_score == 0.8
        assert results[0] is original  # Same object reference

        # Boosted is a new result
        assert boosted[0].hybrid_score == pytest.approx(1.2)
        assert boosted[0] is not original  # Different object

    def test_boost_preserves_all_other_fields(self) -> None:
        """Test boost() only modifies hybrid_score, preserves all other fields."""
        from gitctx.search.git_head_booster import GitHeadBooster

        booster = GitHeadBooster(head_multiplier=1.5)
        original = create_search_result(
            file_path="head.py",
            hybrid_score=0.8,
            is_head=True,
        )

        boosted = booster.boost([original])

        # All fields except hybrid_score should be identical
        assert boosted[0].chunk_content == original.chunk_content
        assert boosted[0].file_path == original.file_path
        assert boosted[0].distance == original.distance
        assert boosted[0].commit_sha == original.commit_sha
        assert boosted[0].is_head == original.is_head
        assert boosted[0].bm25_score == original.bm25_score
        assert boosted[0].vector_score == original.vector_score
        # Only hybrid_score changed
        assert boosted[0].hybrid_score != original.hybrid_score


class TestGitHeadBoosterCustomMultipliers:
    """Test GitHeadBooster with various custom multipliers."""

    def test_boost_with_neutral_multiplier(self) -> None:
        """Test multiplier=1.0 results in no change (neutral boost)."""
        from gitctx.search.git_head_booster import GitHeadBooster

        booster = GitHeadBooster(head_multiplier=1.0)
        result = create_search_result(file_path="head.py", hybrid_score=0.8, is_head=True)

        boosted = booster.boost([result])

        assert boosted[0].hybrid_score == 0.8  # No change

    def test_boost_with_aggressive_multiplier(self) -> None:
        """Test multiplier=2.0 doubles the score (aggressive boost)."""
        from gitctx.search.git_head_booster import GitHeadBooster

        booster = GitHeadBooster(head_multiplier=2.0)
        result = create_search_result(file_path="head.py", hybrid_score=0.8, is_head=True)

        boosted = booster.boost([result])

        assert boosted[0].hybrid_score == pytest.approx(1.6)  # 0.8 * 2.0

    def test_boost_with_maximum_multiplier(self) -> None:
        """Test multiplier=3.0 (maximum allowed)."""
        from gitctx.search.git_head_booster import GitHeadBooster

        booster = GitHeadBooster(head_multiplier=3.0)
        result = create_search_result(file_path="head.py", hybrid_score=0.8, is_head=True)

        boosted = booster.boost([result])

        assert boosted[0].hybrid_score == pytest.approx(2.4)  # 0.8 * 3.0
