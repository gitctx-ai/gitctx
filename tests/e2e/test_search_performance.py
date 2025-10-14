"""Performance tests for search command.

These tests validate that search meets performance requirements:
- p95 latency <2.0 seconds for 10K vector index
- Max latency <5.0 seconds for any single query

Performance tests run in separate CI workflow (daily schedule + main branch pushes).
Regular CI excludes these tests with: pytest -m "not performance"
"""

import os
import time
from pathlib import Path

import numpy as np
import pytest

from gitctx.cli.main import app
from gitctx.storage.lancedb_store import LanceDBStore


@pytest.mark.performance
@pytest.mark.vcr()
def test_search_p95_latency_under_2_seconds(e2e_git_repo_factory, e2e_cli_runner):
    """Test p95 latency <2.0s for 10K chunks with 100 queries.

    Uses VCR cassette to record embedding API call once, then replay 100×.
    This makes the test deterministic and zero-cost for CI.
    """
    # Arrange: Create repo with 10K chunks
    repo = e2e_git_repo_factory(
        num_files=1000,  # 1000 files × ~10 chunks/file = ~10K chunks
        avg_size=500,  # tokens per file
    )
    os.chdir(repo)

    # Index the repository
    result = e2e_cli_runner.invoke(app, ["index"])
    assert result.exit_code == 0, f"Index failed: {result.output}"

    # Verify index size
    store = LanceDBStore(Path(".gitctx/db/lancedb"))
    chunk_count = store.count()
    assert chunk_count >= 10000, f"Expected ≥10K chunks, got {chunk_count}"

    # Act: Run search 100 times
    latencies = []
    for i in range(100):
        start = time.time()
        result = e2e_cli_runner.invoke(app, ["search", "authentication"])
        latencies.append(time.time() - start)
        assert result.exit_code == 0, f"Search {i} failed: {result.output}"

    # Assert: Check p95 and max latency
    p95 = np.percentile(latencies, 95)
    max_latency = max(latencies)
    mean_latency = np.mean(latencies)

    print("\nPerformance Results:")
    print(f"  Mean: {mean_latency:.3f}s")
    print(f"  p95:  {p95:.3f}s")
    print(f"  Max:  {max_latency:.3f}s")

    assert p95 < 2.0, f"p95 latency {p95:.3f}s exceeds 2.0s threshold"
    assert max_latency < 5.0, f"Max latency {max_latency:.3f}s exceeds 5.0s threshold"
