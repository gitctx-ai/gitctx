"""Unit tests for language detection module.

Following TDD workflow:
1. Write these tests FIRST (they will fail - RED)
2. Then implement language_detection.py (GREEN)
3. Refactor if needed
"""

import pytest

from gitctx.core.language_detection import (
    EXTENSION_TO_LANGUAGE,
    detect_language_from_extension,
)


class TestLanguageDetection:
    """Test suite for extension-based language detection."""

    @pytest.mark.parametrize(
        "file_path,expected_language",
        [
            # Common languages
            ("src/main.py", "python"),
            ("app.js", "js"),
            ("index.jsx", "js"),
            ("types.ts", "ts"),
            ("Component.tsx", "ts"),
            ("main.go", "go"),
            ("lib.rs", "rust"),
            ("Main.java", "java"),
            ("util.c", "c"),
            ("header.h", "cpp"),  # .h defaults to C++
            ("class.cpp", "cpp"),
            ("README.md", "markdown"),
            # Case insensitivity
            ("SCRIPT.PY", "python"),
            ("App.JS", "js"),
            # Paths with directories
            ("src/core/engine.py", "python"),
            ("/absolute/path/to/file.go", "go"),
            # Edge cases
            ("no_extension", "markdown"),  # fallback
            (".hidden.py", "python"),  # hidden file
            ("file.tar.gz", "markdown"),  # multiple dots, unknown extension
            ("", "markdown"),  # empty string
        ],
    )
    def test_detect_language_from_extension(self, file_path: str, expected_language: str):
        """Test language detection for various file extensions."""
        # ACT
        result = detect_language_from_extension(file_path)

        # ASSERT
        assert result == expected_language

    def test_extension_map_contains_common_languages(self):
        """Verify EXTENSION_TO_LANGUAGE contains key languages."""
        # ARRANGE - Expected languages for 90%+ coverage
        expected_extensions = {
            ".py",
            ".js",
            ".jsx",
            ".ts",
            ".tsx",
            ".go",
            ".rs",
            ".java",
            ".c",
            ".cpp",
            ".md",
        }

        # ACT
        actual_extensions = set(EXTENSION_TO_LANGUAGE.keys())

        # ASSERT
        assert expected_extensions.issubset(actual_extensions)

    def test_fallback_to_markdown_for_unknown(self):
        """Unknown extensions should fall back to markdown."""
        # ARRANGE
        unknown_files = ["file.xyz", "data.bin", "document.docx"]

        for file_path in unknown_files:
            # ACT
            result = detect_language_from_extension(file_path)

            # ASSERT
            assert result == "markdown", f"Expected fallback for {file_path}"
