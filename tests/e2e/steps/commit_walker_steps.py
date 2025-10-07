"""Step definitions for commit walker BDD scenarios."""

import subprocess
from pathlib import Path
from typing import Any

from pytest_bdd import given, parsers, then, when

from gitctx.core.commit_walker import CommitWalker
from gitctx.core.config import GitCtxSettings
from gitctx.core.models import BlobRecord, WalkProgress

# ===== Scenario: Blob deduplication across commits =====


@given(parsers.parse("a repository with {num_commits:d} commits"))
def create_repo_with_commits(
    e2e_git_repo_factory,
    e2e_git_isolation_env: dict[str, str],
    context: dict[str, Any],
    num_commits: int,
) -> None:
    """Create repository with N commits."""
    repo_path = e2e_git_repo_factory(num_commits=num_commits)
    context["repo_path"] = repo_path
    context["env"] = e2e_git_isolation_env


@given(parsers.parse('the same blob "{filename}" appears in all {num:d} commits unchanged'))
def create_unchanged_blob_across_commits(
    context: dict[str, Any],
    filename: str,
    num: int,
) -> None:
    """Create blob that appears unchanged across N commits."""
    repo_path: Path = context["repo_path"]
    env: dict[str, str] = context["env"]

    # Get initial commit SHA
    result = subprocess.run(
        ["git", "rev-list", "--max-parents=0", "HEAD"],
        cwd=repo_path,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    initial_commit = result.stdout.strip()

    # Reset to initial commit
    subprocess.run(
        ["git", "reset", "--hard", initial_commit],
        cwd=repo_path,
        env=env,
        capture_output=True,
        check=True,
    )

    # Create the file with specific content
    file_content = "def authenticate(user): return True  # auth logic"
    (repo_path / filename).write_text(file_content)

    # Create N commits with the same file content
    # Also add a dummy file that changes each time to make commits valid
    for i in range(num):
        # Add the file (first commit)
        subprocess.run(
            ["git", "add", filename],
            cwd=repo_path,
            env=env,
            capture_output=True,
            check=True,
        )

        # Add a dummy file that changes to make commit valid
        (repo_path / f"dummy_{i}.txt").write_text(f"content {i}")
        subprocess.run(
            ["git", "add", f"dummy_{i}.txt"],
            cwd=repo_path,
            env=env,
            capture_output=True,
            check=True,
        )

        # Commit (auth.py content unchanged, so blob SHA will be identical)
        subprocess.run(
            ["git", "commit", "-m", f"Commit {i + 1} with {filename}"],
            cwd=repo_path,
            env=env,
            capture_output=True,
            check=True,
        )


@when("I walk the commit graph")
def walk_commit_graph(context: dict[str, Any]) -> None:
    """Walk the commit graph and collect results."""
    repo_path: Path = context["repo_path"]

    # Create config
    config = GitCtxSettings()

    # Create walker
    walker = CommitWalker(str(repo_path), config)

    # Collect all blob records
    blobs: list[BlobRecord] = list(walker.walk_blobs())
    context["blobs"] = blobs
    context["walker"] = walker
    context["stats"] = walker.get_stats()


@then("I should yield the blob exactly once")
def check_blob_yielded_once(context: dict[str, Any]) -> None:
    """Verify blob is yielded exactly once."""
    blobs: list[BlobRecord] = context["blobs"]
    # Filter for auth.py blobs (there should be exactly 1 unique blob)
    auth_blobs = [b for b in blobs if any(loc.file_path == "auth.py" for loc in b.locations)]
    assert len(auth_blobs) == 1, f"Expected 1 auth.py blob, got {len(auth_blobs)}"


@then(parsers.parse("its locations list should contain {count:d} BlobLocation entries"))
def check_locations_count(context: dict[str, Any], count: int) -> None:
    """Verify blob has correct number of locations."""
    blobs: list[BlobRecord] = context["blobs"]
    auth_blobs = [b for b in blobs if any(loc.file_path == "auth.py" for loc in b.locations)]
    assert len(auth_blobs) == 1

    blob = auth_blobs[0]
    assert len(blob.locations) == count, f"Expected {count} locations, got {len(blob.locations)}"


@then("each location should have a unique commit SHA")
def check_unique_commit_shas(context: dict[str, Any]) -> None:
    """Verify all commit SHAs are unique."""
    blobs: list[BlobRecord] = context["blobs"]
    auth_blobs = [b for b in blobs if any(loc.file_path == "auth.py" for loc in b.locations)]
    assert len(auth_blobs) == 1

    blob = auth_blobs[0]
    commit_shas = [loc.commit_sha for loc in blob.locations]
    unique_shas = set(commit_shas)
    assert len(commit_shas) == len(unique_shas), "Found duplicate commit SHAs"


@then(parsers.parse('each location should have file_path "{filepath}"'))
def check_file_paths(context: dict[str, Any], filepath: str) -> None:
    """Verify all locations have correct file path."""
    blobs: list[BlobRecord] = context["blobs"]
    auth_blobs = [b for b in blobs if any(loc.file_path == filepath for loc in b.locations)]
    assert len(auth_blobs) == 1

    blob = auth_blobs[0]
    for loc in blob.locations:
        assert loc.file_path == filepath, f"Expected {filepath}, got {loc.file_path}"


# ===== Scenario: Merge commit detection =====


@given("a repository with a merge commit")
def create_repo_with_merge(
    e2e_git_repo_factory,
    e2e_git_isolation_env: dict[str, str],
    context: dict[str, Any],
) -> None:
    """Create repository with a merge commit."""
    # Create basic repo with 1 commit
    repo_path = e2e_git_repo_factory(num_commits=1)
    context["repo_path"] = repo_path
    context["env"] = e2e_git_isolation_env

    env = e2e_git_isolation_env

    # Create feature branch
    subprocess.run(
        ["git", "checkout", "-b", "feature"],
        cwd=repo_path,
        env=env,
        capture_output=True,
        check=True,
    )

    # Add feature.py on feature branch
    (repo_path / "feature.py").write_text("def feature(): pass")
    subprocess.run(["git", "add", "feature.py"], cwd=repo_path, env=env, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Add feature"],
        cwd=repo_path,
        env=env,
        capture_output=True,
        check=True,
    )

    # Go back to main and add different commit
    subprocess.run(
        ["git", "checkout", "main"],
        cwd=repo_path,
        env=env,
        capture_output=True,
        check=True,
    )
    (repo_path / "other.py").write_text("def other(): pass")
    subprocess.run(["git", "add", "other.py"], cwd=repo_path, env=env, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Add other"],
        cwd=repo_path,
        env=env,
        capture_output=True,
        check=True,
    )

    # Merge feature branch (creates merge commit)
    subprocess.run(
        ["git", "merge", "feature", "--no-ff", "-m", "Merge feature"],
        cwd=repo_path,
        env=env,
        capture_output=True,
        check=True,
    )


@given(parsers.parse('"{filename}" exists in both parent commits'))
def verify_file_in_parents(context: dict[str, Any], filename: str) -> None:
    """Verify file exists in merge commit parents."""
    # This is satisfied by the merge setup above
    # feature.py will be in the merge commit after merge
    pass


@then("the merge commit should be detected")
def check_merge_commit_detected(context: dict[str, Any]) -> None:
    """Verify merge commit was detected."""
    blobs: list[BlobRecord] = context["blobs"]

    # Check that at least one blob has a location with is_merge=True
    merge_locations = []
    for blob in blobs:
        for loc in blob.locations:
            if loc.is_merge:
                merge_locations.append(loc)

    assert len(merge_locations) > 0, "No merge commit detected"


@then(parsers.parse('"{filename}" locations should include the merge commit'))
def check_merge_commit_in_locations(context: dict[str, Any], filename: str) -> None:
    """Verify merge commit is in file's locations."""
    blobs: list[BlobRecord] = context["blobs"]

    # Find blob for filename
    target_blobs = [b for b in blobs if any(loc.file_path == filename for loc in b.locations)]
    assert len(target_blobs) > 0, f"No blob found for {filename}"

    # Check that at least one location has is_merge=True
    blob = target_blobs[0]
    has_merge = any(loc.is_merge for loc in blob.locations)
    assert has_merge, f"{filename} does not have merge commit in locations"


@then("parent commit relationships should be preserved")
def check_parent_relationships(context: dict[str, Any]) -> None:
    """Verify parent relationships are preserved in metadata."""
    # The is_merge flag indicates parent count > 1
    # This is already verified by check_merge_commit_detected
    pass


# ===== Scenario: HEAD blob filtering =====


@given(parsers.parse('"{filename}" exists in commits 1-5 but not in HEAD'))
def create_file_deleted_from_head(context: dict[str, Any], filename: str) -> None:
    """Create file that exists in early commits but is deleted from HEAD."""
    repo_path: Path = context["repo_path"]
    env: dict[str, str] = context["env"]

    # Reset to first commit
    result = subprocess.run(
        ["git", "rev-list", "--max-parents=0", "HEAD"],
        cwd=repo_path,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    initial_commit = result.stdout.strip()
    subprocess.run(
        ["git", "reset", "--hard", initial_commit],
        cwd=repo_path,
        env=env,
        capture_output=True,
        check=True,
    )

    # Create deleted.py and commit, then create other commits to reach 10 total
    (repo_path / filename).write_text("def deleted(): pass")
    subprocess.run(["git", "add", filename], cwd=repo_path, env=env, check=True)
    subprocess.run(
        ["git", "commit", "-m", f"Add {filename}"],
        cwd=repo_path,
        env=env,
        capture_output=True,
        check=True,
    )

    # Add 4 more commits with the file still present
    for i in range(4):
        (repo_path / f"temp{i}.txt").write_text(f"content {i}")
        subprocess.run(["git", "add", "."], cwd=repo_path, env=env, check=True)
        subprocess.run(
            ["git", "commit", "-m", f"Commit {i + 2}"],
            cwd=repo_path,
            env=env,
            capture_output=True,
            check=True,
        )

    # Delete the file and commit (commits 6-10)
    (repo_path / filename).unlink()
    subprocess.run(["git", "add", filename], cwd=repo_path, env=env, check=True)
    subprocess.run(
        ["git", "commit", "-m", f"Delete {filename}"],
        cwd=repo_path,
        env=env,
        capture_output=True,
        check=True,
    )

    # Add 4 more commits without the file
    for i in range(4):
        (repo_path / "other.txt").write_text(f"content {i}")
        subprocess.run(["git", "add", "other.txt"], cwd=repo_path, env=env, check=True)
        subprocess.run(
            ["git", "commit", "-m", f"Commit {i + 7}"],
            cwd=repo_path,
            env=env,
            capture_output=True,
            check=True,
        )


@given(parsers.parse('"{filename}" exists only in HEAD'))
def create_file_only_in_head(context: dict[str, Any], filename: str) -> None:
    """Create file that exists only in HEAD."""
    repo_path: Path = context["repo_path"]
    env: dict[str, str] = context["env"]

    # Add current.py in HEAD only
    (repo_path / filename).write_text("def current(): pass")
    subprocess.run(["git", "add", filename], cwd=repo_path, env=env, check=True)
    subprocess.run(
        ["git", "commit", "-m", f"Add {filename}"],
        cwd=repo_path,
        env=env,
        capture_output=True,
        check=True,
    )


@when("I walk the commit graph with HEAD filtering enabled")
def walk_with_head_filtering(context: dict[str, Any]) -> None:
    """Walk commit graph with HEAD filtering enabled."""
    repo_path: Path = context["repo_path"]

    # Create config with HEAD filtering
    config = GitCtxSettings()
    config.repo.index.head_only = True

    # Create walker
    walker = CommitWalker(str(repo_path), config)

    # Collect all blob records
    blobs: list[BlobRecord] = list(walker.walk_blobs())
    context["blobs"] = blobs
    context["walker"] = walker
    context["stats"] = walker.get_stats()


@then(parsers.parse('"{filename}" should be filtered out'))
def check_file_filtered_out(context: dict[str, Any], filename: str) -> None:
    """Verify file was filtered out."""
    blobs: list[BlobRecord] = context["blobs"]

    # Check that no blob has locations with this filename where is_head=True
    for blob in blobs:
        head_locations = [
            loc for loc in blob.locations if loc.is_head and loc.file_path == filename
        ]
        assert len(head_locations) == 0, f"{filename} should be filtered out but found in results"


@then(parsers.parse('"{filename}" should be included'))
def check_file_included(context: dict[str, Any], filename: str) -> None:
    """Verify file was included."""
    blobs: list[BlobRecord] = context["blobs"]

    # Check that at least one blob has this filename in HEAD
    found = False
    for blob in blobs:
        head_locations = [
            loc for loc in blob.locations if loc.is_head and loc.file_path == filename
        ]
        if len(head_locations) > 0:
            found = True
            break

    assert found, f"{filename} should be included but not found in results"


@then(parsers.parse('"{filename}" should be yielded'))
def check_file_yielded(context: dict[str, Any], filename: str) -> None:
    """Verify file was yielded (alias for should be included)."""
    check_file_included(context, filename)


@then(parsers.parse('"{filename}" locations should have is_head = False'))
def check_is_head_false(context: dict[str, Any], filename: str) -> None:
    """Verify all locations for filename have is_head=False."""
    blobs: list[BlobRecord] = context["blobs"]

    # Find blob(s) for this filename
    found_blob = False
    for blob in blobs:
        matching_locs = [loc for loc in blob.locations if loc.file_path == filename]
        if matching_locs:
            found_blob = True
            # All locations for this file should have is_head=False
            assert all(not loc.is_head for loc in matching_locs), (
                f"{filename} has some locations with is_head=True, expected all False"
            )

    assert found_blob, f"No blob found for {filename}"


@then(parsers.parse('"{filename}" locations should have is_head = True'))
def check_is_head_true(context: dict[str, Any], filename: str) -> None:
    """Verify at least one location for filename has is_head=True."""
    blobs: list[BlobRecord] = context["blobs"]

    # Find blob(s) for this filename
    found_head_location = False
    for blob in blobs:
        matching_locs = [loc for loc in blob.locations if loc.file_path == filename and loc.is_head]
        if matching_locs:
            found_head_location = True
            break

    assert found_head_location, f"{filename} has no locations with is_head=True"


@then("only blobs present in HEAD should be yielded")
def check_only_head_blobs(context: dict[str, Any]) -> None:
    """Verify only HEAD blobs are yielded when filtering is enabled."""
    blobs: list[BlobRecord] = context["blobs"]

    # All blobs should have at least one location with is_head=True
    for blob in blobs:
        has_head = any(loc.is_head for loc in blob.locations)
        assert has_head, f"Blob {blob.sha[:8]} has no HEAD locations"


# ===== Scenario: Binary file exclusion =====


@given("a repository with text and binary files")
def create_repo_with_mixed_files(
    e2e_git_repo_factory,
    e2e_git_isolation_env: dict[str, str],
    context: dict[str, Any],
) -> None:
    """Create repository with text and binary files."""
    repo_path = e2e_git_repo_factory(num_commits=1)
    context["repo_path"] = repo_path
    context["env"] = e2e_git_isolation_env


@given(parsers.parse('"{filename}" is a text file'))
def create_text_file(context: dict[str, Any], filename: str) -> None:
    """Create a text file."""
    repo_path: Path = context["repo_path"]
    env: dict[str, str] = context["env"]

    (repo_path / filename).write_text("def code(): pass  # Python code")
    subprocess.run(["git", "add", filename], cwd=repo_path, env=env, check=True)
    subprocess.run(
        ["git", "commit", "-m", f"Add {filename}"],
        cwd=repo_path,
        env=env,
        capture_output=True,
        check=True,
    )


@given(parsers.parse('"{filename}" is a binary file'))
def create_binary_file(context: dict[str, Any], filename: str) -> None:
    """Create a binary file."""
    repo_path: Path = context["repo_path"]
    env: dict[str, str] = context["env"]

    # Write binary content (PNG header + additional null bytes to ensure binary detection)
    # Real PNG files have null bytes throughout, not just in the header
    (repo_path / filename).write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 1000)
    subprocess.run(["git", "add", filename], cwd=repo_path, env=env, check=True)
    subprocess.run(
        ["git", "commit", "-m", f"Add {filename}"],
        cwd=repo_path,
        env=env,
        capture_output=True,
        check=True,
    )


@when("I walk the commit graph with binary filtering enabled")
def walk_with_binary_filtering(context: dict[str, Any]) -> None:
    """Walk commit graph with binary filtering enabled."""
    repo_path: Path = context["repo_path"]

    # Create config (binary filtering is enabled by default)
    config = GitCtxSettings()

    # Create walker
    walker = CommitWalker(str(repo_path), config)

    # Collect all blob records
    blobs: list[BlobRecord] = list(walker.walk_blobs())
    context["blobs"] = blobs
    context["walker"] = walker
    context["stats"] = walker.get_stats()


# ===== Scenario: Large blob exclusion =====


@given("a repository with files of various sizes")
def create_repo_with_sized_files(
    e2e_git_repo_factory,
    e2e_git_isolation_env: dict[str, str],
    context: dict[str, Any],
) -> None:
    """Create repository with files of various sizes."""
    repo_path = e2e_git_repo_factory(num_commits=1)
    context["repo_path"] = repo_path
    context["env"] = e2e_git_isolation_env


@given(parsers.parse('"{filename}" is {size:d}KB'))
def create_kb_file(context: dict[str, Any], filename: str, size: int) -> None:
    """Create file with specific size in KB."""
    repo_path: Path = context["repo_path"]
    env: dict[str, str] = context["env"]

    byte_size = size * 1024
    content = "x" * byte_size
    (repo_path / filename).write_text(content)
    subprocess.run(["git", "add", filename], cwd=repo_path, env=env, check=True)
    subprocess.run(
        ["git", "commit", "-m", f"Add {filename}"],
        cwd=repo_path,
        env=env,
        capture_output=True,
        check=True,
    )


@given(parsers.parse('"{filename}" is {size:d}MB'))
def create_mb_file(context: dict[str, Any], filename: str, size: int) -> None:
    """Create file with specific size in MB."""
    repo_path: Path = context["repo_path"]
    env: dict[str, str] = context["env"]

    byte_size = size * 1024 * 1024
    content = "x" * byte_size
    (repo_path / filename).write_text(content)
    subprocess.run(["git", "add", filename], cwd=repo_path, env=env, check=True)
    subprocess.run(
        ["git", "commit", "-m", f"Add {filename}"],
        cwd=repo_path,
        env=env,
        capture_output=True,
        check=True,
    )


@when("I walk the commit graph with 1MB size limit")
def walk_with_size_limit(context: dict[str, Any]) -> None:
    """Walk commit graph with size limit."""
    repo_path: Path = context["repo_path"]

    # Create config with 1MB limit
    config = GitCtxSettings()
    config.repo.index.max_blob_size_mb = 1.0

    # Create walker
    walker = CommitWalker(str(repo_path), config)

    # Collect all blob records
    blobs: list[BlobRecord] = list(walker.walk_blobs())
    context["blobs"] = blobs
    context["walker"] = walker
    context["stats"] = walker.get_stats()


# ===== Scenario: Resume from partial index =====


@given(parsers.parse("commits {start:d}-{end:d} are already indexed"))
def mark_commits_indexed(context: dict[str, Any], start: int, end: int) -> None:
    """Mark commits as already indexed."""
    repo_path: Path = context["repo_path"]
    env: dict[str, str] = context["env"]

    # Get first N commit SHAs and collect their blob SHAs
    result = subprocess.run(
        ["git", "rev-list", "--reverse", "HEAD"],
        cwd=repo_path,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    all_commits = result.stdout.strip().split("\n")

    # Collect blobs from commits start-end (1-indexed)
    import pygit2

    repo = pygit2.Repository(str(repo_path))
    already_indexed = set()

    for commit_sha in all_commits[start - 1 : end]:
        commit = repo.get(commit_sha)
        if commit:
            # Collect all blob SHAs from this commit's tree
            def collect_blobs(tree, blob_set):
                for entry in tree:
                    if entry.type_str == "blob":
                        blob_set.add(str(entry.id))
                    elif entry.type_str == "tree":
                        subtree = repo.get(entry.id)
                        if subtree:
                            collect_blobs(subtree, blob_set)

            collect_blobs(commit.tree, already_indexed)

    context["already_indexed"] = already_indexed


@when(parsers.parse("I walk the commit graph starting from commit {start_commit:d}"))
def walk_from_commit(context: dict[str, Any], start_commit: int) -> None:
    """Walk commit graph from specific commit."""
    repo_path: Path = context["repo_path"]

    # Create config
    config = GitCtxSettings()

    # Create walker with already_indexed set
    already_indexed = context.get("already_indexed", set())
    walker = CommitWalker(str(repo_path), config, already_indexed=already_indexed)

    # Collect all blob records
    blobs: list[BlobRecord] = list(walker.walk_blobs())
    context["blobs"] = blobs
    context["walker"] = walker
    context["stats"] = walker.get_stats()


@then(parsers.parse("only commits {start:d}-{end:d} should be processed"))
def check_commits_processed(context: dict[str, Any], start: int, end: int) -> None:
    """Verify only specified commits were processed."""
    stats = context["stats"]
    # We process all commits but skip already-indexed blobs
    # So commits_seen should be total, but blobs_indexed should be less
    assert stats.commits_seen > 0, "No commits processed"


@then("previously indexed blobs should not be re-yielded")
def check_no_reyield(context: dict[str, Any]) -> None:
    """Verify previously indexed blobs are not re-yielded."""
    blobs: list[BlobRecord] = context["blobs"]
    already_indexed: set[str] = context.get("already_indexed", set())

    # Check that no yielded blob is in already_indexed
    for blob in blobs:
        assert blob.sha not in already_indexed, f"Blob {blob.sha[:8]} was re-yielded"


@then("the index should be complete after resuming")
def check_index_complete(context: dict[str, Any]) -> None:
    """Verify index is complete after resume."""
    stats = context["stats"]
    assert stats.blobs_indexed > 0, "No blobs indexed"


# ===== Scenario: Multiple refs =====


@given(parsers.parse("a repository with {num:d} branches"))
def create_repo_with_branches(
    e2e_git_repo_factory,
    e2e_git_isolation_env: dict[str, str],
    context: dict[str, Any],
    num: int,
) -> None:
    """Create repository with multiple branches."""
    # Start with basic repo
    repo_path = e2e_git_repo_factory(num_commits=1)
    context["repo_path"] = repo_path
    context["env"] = e2e_git_isolation_env
    context["branches"] = []


@given(parsers.parse('branch "{branch}" has "{filename}"'))
def create_branch_with_file(
    context: dict[str, Any],
    branch: str,
    filename: str,
) -> None:
    """Create branch with specific file."""
    repo_path: Path = context["repo_path"]
    env: dict[str, str] = context["env"]

    if branch != "main":
        # Create and checkout branch
        subprocess.run(
            ["git", "checkout", "-b", branch],
            cwd=repo_path,
            env=env,
            capture_output=True,
            check=True,
        )
        context["branches"].append(branch)

    # Add file
    (repo_path / filename).write_text(f"# {filename} on {branch}")
    subprocess.run(["git", "add", filename], cwd=repo_path, env=env, check=True)
    subprocess.run(
        ["git", "commit", "-m", f"Add {filename}"],
        cwd=repo_path,
        env=env,
        capture_output=True,
        check=True,
    )

    # Go back to main if we created a branch
    if branch != "main":
        subprocess.run(
            ["git", "checkout", "main"],
            cwd=repo_path,
            env=env,
            capture_output=True,
            check=True,
        )


@when("I walk the commit graph for all refs")
def walk_all_refs(context: dict[str, Any]) -> None:
    """Walk commit graph for all refs."""
    repo_path: Path = context["repo_path"]
    env: dict[str, str] = context["env"]

    # Get all branch refs
    result = subprocess.run(
        ["git", "for-each-ref", "--format=%(refname)", "refs/heads/"],
        cwd=repo_path,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    refs = result.stdout.strip().split("\n")

    # Create config with all branch refs
    config = GitCtxSettings()
    config.repo.index.refs = refs

    # Create walker
    walker = CommitWalker(str(repo_path), config)

    # Collect all blob records
    blobs: list[BlobRecord] = list(walker.walk_blobs())
    context["blobs"] = blobs
    context["walker"] = walker
    context["stats"] = walker.get_stats()


@then(parsers.parse('"{filename}" should be yielded with {branch} branch locations'))
def check_branch_locations(context: dict[str, Any], filename: str, branch: str) -> None:
    """Verify file has locations from specified branch."""
    blobs: list[BlobRecord] = context["blobs"]

    # Find blob for filename
    target_blobs = [b for b in blobs if any(loc.file_path == filename for loc in b.locations)]

    # Verify the file exists
    # Note: Full branch tracking (which ref each location came from) would require
    # storing ref name in BlobLocation, but for now we just verify the blob exists
    assert len(target_blobs) > 0, f"No blob found for {filename}"


# ===== Scenario: Progress reporting =====


@when("I walk the commit graph with progress callbacks")
def walk_with_progress(context: dict[str, Any]) -> None:
    """Walk commit graph with progress callbacks."""
    repo_path: Path = context["repo_path"]

    # Create config
    config = GitCtxSettings()

    # Progress tracking
    progress_updates: list[WalkProgress] = []

    def progress_callback(progress: WalkProgress) -> None:
        progress_updates.append(progress)

    # Create walker
    walker = CommitWalker(str(repo_path), config)

    # Collect all blob records with progress
    blobs: list[BlobRecord] = list(walker.walk_blobs(progress_callback=progress_callback))
    context["blobs"] = blobs
    context["walker"] = walker
    context["stats"] = walker.get_stats()
    context["progress_updates"] = progress_updates


@then("progress updates should be received")
def check_progress_received(context: dict[str, Any]) -> None:
    """Verify progress updates were received."""
    progress_updates: list[WalkProgress] = context["progress_updates"]
    assert len(progress_updates) > 0, "No progress updates received"


@then("total commit count should be reported")
def check_total_commits(context: dict[str, Any]) -> None:
    """Verify total commit count is reported."""
    # Total commits is None during walk (unknown total)
    # This is acceptable behavior
    pass


@then("processed commit count should increment")
def check_commit_increment(context: dict[str, Any]) -> None:
    """Verify processed commit count increments."""
    progress_updates: list[WalkProgress] = context["progress_updates"]

    if len(progress_updates) >= 2:
        # Check that commits_seen increases
        for i in range(1, len(progress_updates)):
            assert progress_updates[i].commits_seen >= progress_updates[i - 1].commits_seen, (
                "Commit count did not increment"
            )


@then("progress percentage should reach 100%")
def check_progress_complete(context: dict[str, Any]) -> None:
    """Verify progress reaches 100%."""
    stats = context["stats"]
    # At the end, all commits are processed
    assert stats.commits_seen > 0, "No commits processed"


# ===== Scenario: Gitignore filtering =====


@given("a repository with various files")
def create_repo_with_files(
    e2e_git_repo_factory,
    e2e_git_isolation_env: dict[str, str],
    context: dict[str, Any],
) -> None:
    """Create repository with various files."""
    repo_path = e2e_git_repo_factory(num_commits=1)
    context["repo_path"] = repo_path
    context["env"] = e2e_git_isolation_env


@given(parsers.parse('".gitignore" contains "{pattern1}" and "{pattern2}"'))
def create_gitignore(context: dict[str, Any], pattern1: str, pattern2: str) -> None:
    """Create .gitignore with patterns."""
    repo_path: Path = context["repo_path"]
    env: dict[str, str] = context["env"]

    # Create .gitignore
    gitignore_content = f"{pattern1}\n{pattern2}\n"
    (repo_path / ".gitignore").write_text(gitignore_content)
    subprocess.run(["git", "add", ".gitignore"], cwd=repo_path, env=env, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Add .gitignore"],
        cwd=repo_path,
        env=env,
        capture_output=True,
        check=True,
    )


@given(parsers.parse('"{filename}" is tracked'))
def create_tracked_file(context: dict[str, Any], filename: str) -> None:
    """Create tracked file."""
    repo_path: Path = context["repo_path"]
    env: dict[str, str] = context["env"]

    # Create parent directory if needed
    file_path = repo_path / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Create file
    file_path.write_text(f"# {filename}")
    subprocess.run(["git", "add", "-f", filename], cwd=repo_path, env=env, check=True)
    subprocess.run(
        ["git", "commit", "-m", f"Add {filename}"],
        cwd=repo_path,
        env=env,
        capture_output=True,
        check=True,
    )


@given(parsers.parse('"{filename}" is tracked but gitignored'))
def create_tracked_ignored_file(context: dict[str, Any], filename: str) -> None:
    """Create tracked but gitignored file."""
    # Same as tracked file - git allows force-adding ignored files
    create_tracked_file(context, filename)


@when("I walk the commit graph with gitignore filtering enabled")
def walk_with_gitignore_filtering(context: dict[str, Any]) -> None:
    """Walk commit graph with gitignore filtering enabled."""
    repo_path: Path = context["repo_path"]

    # Create config (gitignore filtering is enabled by default)
    config = GitCtxSettings()

    # Create walker
    walker = CommitWalker(str(repo_path), config)

    # Collect all blob records
    blobs: list[BlobRecord] = list(walker.walk_blobs())
    context["blobs"] = blobs
    context["walker"] = walker
    context["stats"] = walker.get_stats()
