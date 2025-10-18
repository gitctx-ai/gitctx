#!/usr/bin/env python3
"""Benchmark compression performance for safetensors embedding cache.

This script measures:
1. Compression ratio (target: 8-10% reduction, 90-92% of original)
2. Compression time (target: <10ms per 100KB file)
3. Decompression time (target: <5ms per file)
4. Throughput (MB/s for compression and decompression)

Usage:
    uv run python scripts/benchmark_compression.py [--json]

Options:
    --json  Output results as JSON instead of human-readable format

Performance targets from STORY-0001.4.4:
- Compression time: <10ms overhead per file
- Decompression time: <5ms overhead per file
- Size reduction: 8-10% (90-92% of original safetensors)
- Throughput: ~500 MB/s compression, ~1500 MB/s decompression
"""

import argparse
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import zstandard as zstd
from safetensors.numpy import load, save

from gitctx.indexing.types import Embedding


def generate_synthetic_embeddings(
    count: int = 1000, dimensions: int = 3072
) -> list[Embedding]:
    """Generate synthetic embeddings with realistic entropy.

    Args:
        count: Number of embeddings to generate
        dimensions: Embedding vector dimensions (3072 for text-embedding-3-large)

    Returns:
        List of Embedding objects with random vectors
    """
    embeddings = []

    for i in range(count):
        # Generate random float32 vectors (realistic entropy)
        # Use numpy for fast generation
        vector = np.random.randn(dimensions).astype(np.float32).tolist()

        embeddings.append(
            Embedding(
                vector=vector,
                token_count=100 + (i % 400),  # Vary between 100-500 tokens
                model="text-embedding-3-large",
                cost_usd=0.000013 + (i % 400) * 0.00000013,  # Proportional to tokens
                blob_sha=f"benchmark_{i:04d}",
                chunk_index=0,
            )
        )

    return embeddings


def serialize_to_safetensors(embeddings: list[Embedding]) -> bytes:
    """Serialize embeddings to safetensors bytes (uncompressed).

    Args:
        embeddings: List of Embedding objects

    Returns:
        Safetensors bytes (uncompressed)
    """
    tensors = {}
    metadata = {}

    for i, emb in enumerate(embeddings):
        tensors[f"chunk_{i}"] = np.array(emb.vector, dtype=np.float32)
        metadata[f"chunk_{i}_tokens"] = str(emb.token_count)
        metadata[f"chunk_{i}_cost"] = str(emb.cost_usd)

    metadata["model"] = "text-embedding-3-large"
    metadata["chunks"] = str(len(embeddings))

    return save(tensors, metadata=metadata)


def benchmark_compression(
    safetensors_bytes: bytes, level: int = 3, runs: int = 10
) -> dict[str, Any]:
    """Benchmark compression performance.

    Args:
        safetensors_bytes: Uncompressed safetensors data
        level: zstd compression level (3 = default)
        runs: Number of benchmark runs

    Returns:
        Dict with compression statistics
    """
    cctx = zstd.ZstdCompressor(level=level)
    times_ms = []
    compressed_bytes = None

    for _ in range(runs):
        start = time.perf_counter()
        compressed_bytes = cctx.compress(safetensors_bytes)
        end = time.perf_counter()
        times_ms.append((end - start) * 1000)

    uncompressed_size = len(safetensors_bytes)
    compressed_size = len(compressed_bytes) if compressed_bytes else 0
    compression_ratio = compressed_size / uncompressed_size

    return {
        "uncompressed_size_bytes": uncompressed_size,
        "compressed_size_bytes": compressed_size,
        "compression_ratio": compression_ratio,
        "size_reduction_percent": (1 - compression_ratio) * 100,
        "compression_level": level,
        "time_ms_min": min(times_ms),
        "time_ms_max": max(times_ms),
        "time_ms_mean": statistics.mean(times_ms),
        "time_ms_median": statistics.median(times_ms),
        "time_ms_stdev": statistics.stdev(times_ms) if len(times_ms) > 1 else 0.0,
        "throughput_mb_s": (uncompressed_size / (1024 * 1024))
        / (statistics.median(times_ms) / 1000),
    }


def benchmark_decompression(
    compressed_bytes: bytes, runs: int = 10
) -> dict[str, Any]:
    """Benchmark decompression performance.

    Args:
        compressed_bytes: Compressed data
        runs: Number of benchmark runs

    Returns:
        Dict with decompression statistics
    """
    dctx = zstd.ZstdDecompressor()
    times_ms = []
    decompressed_bytes = None

    for _ in range(runs):
        start = time.perf_counter()
        decompressed_bytes = dctx.decompress(compressed_bytes)
        end = time.perf_counter()
        times_ms.append((end - start) * 1000)

    decompressed_size = len(decompressed_bytes) if decompressed_bytes else 0

    return {
        "decompressed_size_bytes": decompressed_size,
        "time_ms_min": min(times_ms),
        "time_ms_max": max(times_ms),
        "time_ms_mean": statistics.mean(times_ms),
        "time_ms_median": statistics.median(times_ms),
        "time_ms_stdev": statistics.stdev(times_ms) if len(times_ms) > 1 else 0.0,
        "throughput_mb_s": (decompressed_size / (1024 * 1024))
        / (statistics.median(times_ms) / 1000),
    }


def verify_roundtrip(embeddings: list[Embedding]) -> bool:
    """Verify compression/decompression roundtrip preserves data.

    Args:
        embeddings: Original embeddings

    Returns:
        True if roundtrip successful
    """
    # Serialize
    original_bytes = serialize_to_safetensors(embeddings)

    # Compress
    cctx = zstd.ZstdCompressor(level=3)
    compressed = cctx.compress(original_bytes)

    # Decompress
    dctx = zstd.ZstdDecompressor()
    decompressed = dctx.decompress(compressed)

    # Verify bytes match
    if original_bytes != decompressed:
        return False

    # Verify we can load tensors
    tensors = load(decompressed)

    # Verify vector count matches
    if len(tensors) != len(embeddings):
        return False

    # Verify first vector matches
    original_vector = embeddings[0].vector
    loaded_vector = tensors["chunk_0"].tolist()

    return np.allclose(original_vector, loaded_vector, rtol=1e-6)


def main() -> int:
    """Run compression benchmarks."""
    parser = argparse.ArgumentParser(description="Benchmark compression performance")
    parser.add_argument(
        "--json", action="store_true", help="Output results as JSON"
    )
    args = parser.parse_args()

    # Test configurations
    configs = [
        {"count": 1, "label": "Single embedding (~12KB)"},
        {"count": 10, "label": "10 embeddings (~120KB)"},
        {"count": 100, "label": "100 embeddings (~1.2MB)"},
    ]

    results = []

    for config in configs:
        if not args.json:
            print(f"\n{'=' * 60}")
            print(f"Benchmarking: {config['label']}")
            print(f"{'=' * 60}")

        # Generate embeddings
        embeddings = generate_synthetic_embeddings(count=config["count"])
        safetensors_bytes = serialize_to_safetensors(embeddings)

        # Benchmark compression
        comp_stats = benchmark_compression(safetensors_bytes)

        # Compress for decompression benchmark
        cctx = zstd.ZstdCompressor(level=3)
        compressed = cctx.compress(safetensors_bytes)

        # Benchmark decompression
        decomp_stats = benchmark_decompression(compressed)

        # Verify roundtrip
        roundtrip_ok = verify_roundtrip(embeddings)

        result = {
            "config": config,
            "compression": comp_stats,
            "decompression": decomp_stats,
            "roundtrip_verified": roundtrip_ok,
        }
        results.append(result)

        if not args.json:
            print(f"\nCompression:")
            print(
                f"  Size: {comp_stats['uncompressed_size_bytes']:,} → "
                f"{comp_stats['compressed_size_bytes']:,} bytes"
            )
            print(
                f"  Ratio: {comp_stats['compression_ratio']:.2%} "
                f"(reduction: {comp_stats['size_reduction_percent']:.1f}%)"
            )
            print(
                f"  Time: {comp_stats['time_ms_median']:.2f}ms "
                f"(min: {comp_stats['time_ms_min']:.2f}ms, "
                f"max: {comp_stats['time_ms_max']:.2f}ms)"
            )
            print(f"  Throughput: {comp_stats['throughput_mb_s']:.1f} MB/s")

            print(f"\nDecompression:")
            print(
                f"  Time: {decomp_stats['time_ms_median']:.2f}ms "
                f"(min: {decomp_stats['time_ms_min']:.2f}ms, "
                f"max: {decomp_stats['time_ms_max']:.2f}ms)"
            )
            print(f"  Throughput: {decomp_stats['throughput_mb_s']:.1f} MB/s")

            print(f"\nRoundtrip: {'✅ PASS' if roundtrip_ok else '❌ FAIL'}")

    # Verify targets
    if not args.json:
        print(f"\n{'=' * 60}")
        print("Performance Target Verification")
        print(f"{'=' * 60}")

        # Check 100-embedding case (closest to real-world)
        typical = results[2]["compression"]  # 100 embeddings
        typical_decomp = results[2]["decompression"]

        checks = [
            (
                "Compression ratio 8-10% reduction",
                8.0 <= typical["size_reduction_percent"] <= 10.0,
                f"{typical['size_reduction_percent']:.1f}%",
            ),
            (
                "Compression time <10ms",
                typical["time_ms_median"] < 10.0,
                f"{typical['time_ms_median']:.2f}ms",
            ),
            (
                "Decompression time <5ms",
                typical_decomp["time_ms_median"] < 5.0,
                f"{typical_decomp['time_ms_median']:.2f}ms",
            ),
            (
                "Compression throughput >400 MB/s",
                typical["throughput_mb_s"] > 400,
                f"{typical['throughput_mb_s']:.1f} MB/s",
            ),
            (
                "Decompression throughput >1000 MB/s",
                typical_decomp["throughput_mb_s"] > 1000,
                f"{typical_decomp['throughput_mb_s']:.1f} MB/s",
            ),
        ]

        all_pass = True
        for name, passed, value in checks:
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {status}  {name}: {value}")
            all_pass = all_pass and passed

        print()
        if all_pass:
            print("🎉 All performance targets met!")
            return 0
        else:
            print("⚠️  Some targets not met (may be acceptable)")
            return 1

    else:
        # JSON output
        print(json.dumps(results, indent=2))
        return 0


if __name__ == "__main__":
    sys.exit(main())
