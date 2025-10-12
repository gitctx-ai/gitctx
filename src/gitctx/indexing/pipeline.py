"""Indexing pipeline with progress tracking and cost estimation.

This module provides the main index_repository function that orchestrates
the full indexing pipeline with TUI_GUIDE-compliant progress reporting.
"""

import sys
from pathlib import Path

from gitctx.core.config import GitCtxSettings
from gitctx.indexing.progress import CostEstimator, ProgressReporter


async def index_repository(
    repo_path: Path,
    settings: GitCtxSettings,
    dry_run: bool = False,
    verbose: bool = False,
) -> None:
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

        print(f"Files:        {estimate['total_files']:,}")
        print(f"Lines:        {estimate['total_lines']:,}")
        print(f"Est. tokens:  {estimate['estimated_tokens']:,}")
        print(f"Est. cost:    ${estimate['estimated_cost']:.4f}")
        print(f"Range:        ${estimate['min_cost']:.4f} - ${estimate['max_cost']:.4f} (±10%)")
        return

    # Import pipeline components (lazy import to avoid circular dependencies)
    from gitctx.core.chunker import LanguageAwareChunker
    from gitctx.core.commit_walker import CommitWalker
    from gitctx.embeddings.openai_embedder import OpenAIEmbedder
    from gitctx.storage.lancedb_store import LanceDBStore

    # Initialize components
    reporter = ProgressReporter(verbose=verbose)
    walker = CommitWalker(str(repo_path), settings)
    chunker = LanguageAwareChunker(
        chunk_overlap_ratio=settings.repo.index.chunk_overlap_ratio,
    )
    embedder = OpenAIEmbedder(api_key=settings.get("api_keys.openai"))
    store = LanceDBStore(repo_path / ".gitctx" / "lancedb")

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
            print("No files to index")
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
                # Decode blob content
                content = blob_record.content.decode("utf-8")

                # Detect language for language-aware chunking (use first location's path)
                from gitctx.core.language_detection import detect_language_from_extension

                file_path = blob_record.locations[0].file_path
                language = detect_language_from_extension(file_path)

                # Chunk the file
                chunks = chunker.chunk_file(
                    content=content,
                    language=language,
                    max_tokens=settings.repo.index.max_chunk_tokens,
                )
                reporter.update(chunks=len(chunks))

                # Embed chunks - returns protocol.Embedding with vectors
                protocol_embeddings = await embedder.embed_chunks(chunks, blob_record.sha)

                # Track tokens and cost from protocol embeddings
                total_tokens = sum(e.token_count for e in protocol_embeddings)
                total_cost = sum(e.cost_usd for e in protocol_embeddings)
                reporter.update(tokens=total_tokens, cost=total_cost)

                # Convert to models.Embedding for storage
                from gitctx.core.models import Embedding as StorageEmbedding

                storage_embeddings = []

                for chunk, proto_emb in zip(chunks, protocol_embeddings, strict=True):
                    storage_embeddings.append(
                        StorageEmbedding(
                            vector=proto_emb.vector,
                            chunk_content=chunk.content,
                            token_count=chunk.token_count,
                            blob_sha=blob_record.sha,
                            chunk_index=proto_emb.chunk_index,
                            start_line=chunk.start_line,
                            end_line=chunk.end_line,
                            total_chunks=len(chunks),
                            language=language,
                            model=proto_emb.model,
                        )
                    )

                # Store embeddings with blob metadata
                blob_locations = {blob_record.sha: blob_record.locations}
                store.add_chunks_batch(
                    embeddings=storage_embeddings,
                    blob_locations=blob_locations,
                )

            except UnicodeDecodeError:
                # Skip binary files
                reporter.record_error()
                continue
            except Exception as e:
                # Log error and continue
                file_path = (
                    blob_record.locations[0].file_path if blob_record.locations else blob_record.sha
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
