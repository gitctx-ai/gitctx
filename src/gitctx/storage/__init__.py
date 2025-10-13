"""Vector storage module for gitctx.

This module provides LanceDB-based vector storage with denormalized schema
for optimal read performance in semantic code search.
"""

from gitctx.models.errors import DimensionMismatchError
from gitctx.storage.lancedb_store import LanceDBStore
from gitctx.storage.protocols import VectorStoreProtocol
from gitctx.storage.schema import CHUNK_SCHEMA, CodeChunkRecord

__all__ = [
    "CHUNK_SCHEMA",
    "CodeChunkRecord",
    "DimensionMismatchError",
    "LanceDBStore",
    "VectorStoreProtocol",
]
