"""Unit tests for git protocols."""

from gitctx.config.settings import GitCtxSettings
from gitctx.git.protocols import CommitWalkerProtocol
from gitctx.git.walker import CommitWalker


class TestCommitWalkerProtocol:
    """Test CommitWalkerProtocol structure and contract compliance."""

    def test_protocol_has_required_methods(self):
        """CommitWalkerProtocol defines required methods."""
        assert hasattr(CommitWalkerProtocol, "walk_blobs")
        assert hasattr(CommitWalkerProtocol, "get_stats")

    def test_protocol_is_runtime_checkable(self, git_repo_factory, isolated_env):
        """CommitWalkerProtocol can be checked at runtime with isinstance()."""
        # Arrange
        repo_path = git_repo_factory(num_commits=1)
        config = GitCtxSettings()
        walker = CommitWalker(str(repo_path), config)

        # Act & Assert - isinstance() should work with @runtime_checkable
        assert isinstance(walker, CommitWalkerProtocol)

    def test_walk_blobs_signature(self):
        """walk_blobs method has correct signature."""
        import inspect

        # Get the method from protocol
        walk_blobs = CommitWalkerProtocol.walk_blobs

        # Check signature exists and has expected parameters
        sig = inspect.signature(walk_blobs)
        params = list(sig.parameters.keys())

        assert "self" in params
        assert "progress_callback" in params

    def test_get_stats_signature(self):
        """get_stats method has correct signature."""
        import inspect

        # Get the method from protocol
        get_stats = CommitWalkerProtocol.get_stats

        # Check signature exists and has expected parameters
        sig = inspect.signature(get_stats)
        params = list(sig.parameters.keys())

        assert "self" in params
        assert len(params) == 1  # Only self, no other parameters

    def test_implementation_satisfies_protocol(self, git_repo_factory, isolated_env):
        """CommitWalker implementation satisfies CommitWalkerProtocol."""
        # Arrange
        repo_path = git_repo_factory(num_commits=1)
        config = GitCtxSettings()

        # Act
        walker = CommitWalker(str(repo_path), config)

        # Assert - walker has all required methods
        assert hasattr(walker, "walk_blobs")
        assert hasattr(walker, "get_stats")
        assert callable(walker.walk_blobs)
        assert callable(walker.get_stats)

    def test_protocol_method_return_types(self, git_repo_factory, isolated_env):
        """Protocol methods return expected types."""
        # Arrange
        repo_path = git_repo_factory(num_commits=1)
        config = GitCtxSettings()
        walker = CommitWalker(str(repo_path), config)

        # Act - call methods through protocol interface
        blobs_iter = walker.walk_blobs()
        stats = walker.get_stats()

        # Assert - return types match protocol specification
        from collections.abc import Iterator

        from gitctx.git.types import WalkStats

        assert isinstance(blobs_iter, Iterator)
        assert isinstance(stats, WalkStats)
