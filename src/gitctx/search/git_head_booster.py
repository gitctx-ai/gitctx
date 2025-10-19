"""Search result boosting for HEAD code over historical versions.

This module provides GitHeadBooster, which applies a configurable multiplier to
hybrid search scores for chunks from the HEAD commit, making current code rank
higher than historical versions.

Design rationale:
- Simple 1.5x multiplier (conservative, won't override strong semantic matches)
- Post-RRF application (hybrid scores normalized before boosting)
- Immutable pattern (returns new SearchResult objects)
- Easy to understand, test, and reason about

Future improvements (EPIC-0001.5):
- Sophisticated bucketing with recency decay
- LLM reranking based on query intent (recommended approach)
"""

from __future__ import annotations

from dataclasses import replace

from gitctx.indexing.types import SearchResult

# Multiplier validation constants
MIN_MULTIPLIER = 1.0  # No penalization of HEAD code
MAX_MULTIPLIER = 3.0  # Prevent override of semantic relevance


class GitHeadBooster:
    """Boost HEAD code over historical versions in search results.

    Simple MVP approach: Apply configurable multiplier to HEAD chunks post-RRF.
    Defers sophisticated ranking (recency decay, LLM reranking) to EPIC-0001.5.

    The 1.5x default multiplier is conservative:
    - Mid-range of typical BM25 boost factors (1.2-2.0, per Robertson & Zaragoza 2009)
    - Sufficient to break ties without overriding strong semantic matches
    - Can be increased to 2.0x based on EPIC-0001.5 evaluation data

    Example:
        >>> booster = GitHeadBooster(head_multiplier=1.5)
        >>> results = [
        ...     SearchResult(..., is_head=True, hybrid_score=0.8),
        ...     SearchResult(..., is_head=False, hybrid_score=0.9),
        ... ]
        >>> boosted = booster.boost(results)
        >>> boosted[0].hybrid_score  # HEAD: 0.8 * 1.5 = 1.2
        1.2
        >>> boosted[1].hybrid_score  # Historical: unchanged
        0.9
    """

    def __init__(self, head_multiplier: float = 1.5) -> None:
        """Initialize booster with HEAD multiplier.

        Args:
            head_multiplier: Boost multiplier for HEAD chunks (default: 1.5x).
                Valid range: 1.0 (no boost) to 3.0 (aggressive).
                - < 1.0: Would penalize HEAD (nonsensical)
                - 1.0: No boost (neutral)
                - 1.2-2.0: Typical range from BM25 literature
                - 1.5: Conservative choice (story default)
                - 2.0: Aggressive boost (EPIC acceptance criteria)
                - > 3.0: Likely to override semantic relevance (too aggressive)

        Raises:
            ValueError: If multiplier is outside valid range [1.0, 3.0].
        """
        if head_multiplier < MIN_MULTIPLIER or head_multiplier > MAX_MULTIPLIER:
            raise ValueError(
                f"Multiplier must be between {MIN_MULTIPLIER} and {MAX_MULTIPLIER}, "
                f"got {head_multiplier}. "
                "Values < 1.0 would penalize HEAD, values > 3.0 override semantic relevance."
            )

        self.head_multiplier = head_multiplier

    def boost(self, results: list[SearchResult]) -> list[SearchResult]:
        """Apply HEAD boost to search results and return new list.

        This method boosts hybrid_score for results with is_head=True by the
        configured multiplier, then returns a new list of SearchResult objects.

        The boost is applied as a simple multiplication:
            boosted_score = hybrid_score * head_multiplier (if is_head=True)

        Immutability: This method does NOT modify the input list or its results.
        Instead, it returns a new list with new SearchResult objects for boosted
        items and the original objects for non-boosted items.

        Args:
            results: Search results from hybrid search (post-RRF).
                Each result should have hybrid_score and is_head fields.

        Returns:
            New list of SearchResult objects with boosted scores for HEAD chunks.
            Historical chunks (is_head=False) are unchanged.
            Results with hybrid_score=None are skipped (cannot boost None).

        Example:
            >>> booster = GitHeadBooster(head_multiplier=2.0)
            >>> original = [
            ...     SearchResult(..., is_head=True, hybrid_score=0.8),
            ...     SearchResult(..., is_head=False, hybrid_score=0.9),
            ... ]
            >>> boosted = booster.boost(original)
            >>> original[0].hybrid_score  # Original unchanged
            0.8
            >>> boosted[0].hybrid_score  # New object, boosted
            1.6
            >>> boosted[1] is original[1]  # Historical: same object
            True
        """
        boosted = []

        for result in results:
            # Skip boosting if hybrid_score is None (can't boost None)
            if result.hybrid_score is None:
                boosted.append(result)
                continue

            # Boost HEAD chunks by multiplier
            if result.is_head:
                boosted_score = result.hybrid_score * self.head_multiplier
                # Create new SearchResult with boosted score (immutable pattern)
                boosted_result = replace(result, hybrid_score=boosted_score)
                boosted.append(boosted_result)
            else:
                # Historical chunks: no boost, keep original object
                boosted.append(result)

        return boosted
