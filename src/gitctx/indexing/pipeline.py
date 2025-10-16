"""Indexing pipeline with progress tracking and cost estimation.

This module provides the main index_repository function that orchestrates
the full indexing pipeline with TUI_GUIDE-compliant progress reporting.
"""
# ruff: noqa: PLC0415 # Lazy load heavy dependencies (LanceDB, pyarrow) to reduce import time

import logging
import sys
from pathlib import Path

from gitctx.config.settings import GitCtxSettings
from gitctx.indexing.formatting import format_cost, format_number
from gitctx.indexing.progress import CostEstimator, ProgressReporter

logger = logging.getLogger(__name__)


async def index_repository(
    repo_path: Path, settings: GitCtxSettings, dry_run: bool = False, verbose: bool = False
) -> None:  # Complex pipeline orchestration requires many statements
    """Index a repository with progress tracking (TUI_GUIDE compliant).

    Args:
        repo_path: Path to git repository
        settings: Configuration settings
        dry_run: If True, only show cost estimate without indexing
        verbose: If True, show detailed phase-by-phase progress

    Raises:
        ValueError: If repo_path is not a valid git repository
        KeyboardInterrupt: Handled gracefully with partial stats and exit 130
    """
    # Cost estimation mode (dry-run)
    if dry_run:
        estimator = CostEstimator()
        estimate = estimator.estimate_repo_cost(repo_path)

        print(f"Files:        {format_number(estimate['total_files'])}")
        print(f"Lines:        {format_number(estimate['total_lines'])}")
        print(f"Est. tokens:  {format_number(estimate['estimated_tokens'])}")
        print(f"Est. cost:    {format_cost(estimate['estimated_cost'])}")
        print(
            f"Range:        {format_cost(estimate['min_cost'])} - "
            f"{format_cost(estimate['max_cost'])} (±10%)"
        )
        return

    # Import pipeline components (lazy import to avoid circular dependencies)
    from gitctx.git.walker import CommitWalker
    from gitctx.indexing.chunker import LanguageAwareChunker
    from gitctx.indexing.embeddings import embed_with_cache
    from gitctx.models.providers.openai import OpenAIEmbedder
    from gitctx.storage.embedding_cache import EmbeddingCache
    from gitctx.storage.lancedb_store import LanceDBStore

    # Initialize components
    reporter = ProgressReporter(verbose=verbose)
    walker = CommitWalker(str(repo_path), settings)
    chunker = LanguageAwareChunker(
        chunk_overlap_ratio=settings.repo.index.chunk_overlap_ratio,
    )
    embedder = OpenAIEmbedder(api_key=settings.get("api_keys.openai"))
    cache = EmbeddingCache(repo_path / ".gitctx", model=settings.repo.model.embedding)
    store = LanceDBStore(repo_path / ".gitctx" / "db" / "lancedb")

    reporter.start()

    try:
        # Phase 1: Walk commits and count blobs
        reporter.phase("Walking commit graph")

        # First pass: just count blobs to detect empty repo
        blob_count = 0
        blob_records = []

        for blob_record in walker.walk_blobs():
            blob_count += 1
            blob_records.append(blob_record)

            # Update progress periodically in verbose mode
            stats = walker.get_stats()
            if blob_count % 100 == 0:
                reporter.update(
                    commits=stats.commits_seen,
                    blobs=stats.blobs_indexed,
                )

        # Handle empty repository
        if blob_count == 0:
            print("No files to index", file=sys.stderr)
            return

        # Final walk phase update
        stats = walker.get_stats()
        reporter.update(
            commits=stats.commits_seen,
            blobs=stats.blobs_indexed,
        )

        # Phase 2: Chunk and embed
        reporter.phase("Generating embeddings")

        for blob_record in blob_records:
            try:
                # Single orchestrated call: check cache → chunk → embed → save cache
                embeddings = await embed_with_cache(
                    chunker=chunker,
                    embedder=embedder,
                    cache=cache,
                    blob_record=blob_record,
                )

                # Track stats (embeddings already have all metadata)
                total_tokens = sum(e.token_count for e in embeddings)
                total_cost = sum(e.cost_usd for e in embeddings)
                reporter.update(tokens=total_tokens, cost=total_cost, chunks=len(embeddings))

                # Store (embeddings have all fields: chunk_content, vectors, metadata)
                blob_locations = {blob_record.sha: blob_record.locations}
                store.add_chunks_batch(embeddings=embeddings, blob_locations=blob_locations)

            except Exception as e:
                # embed_with_cache handles UTF-8 errors internally, log other errors
                file_path = (
                    blob_record.locations[0].file_path if blob_record.locations else blob_record.sha
                )
                logger.debug(
                    "Error processing blob %s (sha: %s)",
                    file_path,
                    blob_record.sha,
                    exc_info=True,
                )
                print(f"Error processing {file_path}: {e}", file=sys.stderr)
                reporter.record_error()
                continue

    except KeyboardInterrupt:
        # Handle graceful cancellation (SIGINT)
        # Print message and let exception propagate to CLI layer for exit code 130
        print("\nInterrupted", file=sys.stderr)
        raise

    finally:
        # Always show final summary (called on success or cancellation)
        reporter.finish()
