"""Unit tests for storage protocol definitions.

Tests validate that SearchStrategy protocol has correct signature
and can be used in type hints for storage-agnostic implementations.
"""

import inspect

from gitctx.storage.protocols import SearchStrategy


def test_search_strategy_protocol_can_be_imported() -> None:
    """Test SearchStrategy protocol can be imported."""
    assert SearchStrategy is not None


def test_search_strategy_has_search_method() -> None:
    """Test SearchStrategy protocol has search method."""
    assert hasattr(SearchStrategy, "search")


def test_search_strategy_search_signature() -> None:
    """Test SearchStrategy.search() has correct 5-parameter signature."""
    # Get the search method signature
    search_method = SearchStrategy.search
    sig = inspect.signature(search_method)

    # Should have 5 parameters: query_vector, query_text, limit, filter_head_only, max_distance
    params = list(sig.parameters.keys())
    assert "query_vector" in params
    assert "query_text" in params
    assert "limit" in params
    assert "filter_head_only" in params
    assert "max_distance" in params
    assert len(params) == 6  # self + 5 params


def test_search_strategy_query_vector_type() -> None:
    """Test query_vector parameter is np.ndarray."""
    sig = inspect.signature(SearchStrategy.search)
    # Check query_vector parameter exists (type annotation checked at runtime by mypy)
    assert "query_vector" in sig.parameters
    # Type hint is in __annotations__ but may be string due to TYPE_CHECKING
    assert SearchStrategy.search.__annotations__.get("query_vector") is not None


def test_search_strategy_query_text_type() -> None:
    """Test query_text parameter is str (NEW for BM25)."""
    sig = inspect.signature(SearchStrategy.search)
    assert "query_text" in sig.parameters
    # Verify type annotation exists (may be string 'str' or actual str type)
    annotation = SearchStrategy.search.__annotations__.get("query_text")
    assert annotation is not None
    assert annotation is str or str(annotation) == "str"


def test_search_strategy_return_type() -> None:
    """Test search() returns list[SearchResult]."""
    # Check return type annotation exists
    return_annotation = SearchStrategy.search.__annotations__.get("return")
    assert return_annotation is not None
    # Should be list[SearchResult]
    assert "list" in str(return_annotation).lower()
    assert "SearchResult" in str(return_annotation)


def test_search_strategy_can_be_used_in_type_hints() -> None:
    """Test SearchStrategy protocol can be used in type annotations."""

    # Should not raise TypeError
    def takes_search_strategy(searcher: SearchStrategy) -> None:
        pass

    # Type hint should work
    assert takes_search_strategy.__annotations__["searcher"] is SearchStrategy
