"""Core business logic for gitctx."""

from gitctx.core.protocols import CommitWalkerProtocol, create_walker

__all__ = [
    "CommitWalkerProtocol",
    "create_walker",
]
