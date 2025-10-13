"""Unit tests for language detection module.

Following TDD workflow:
1. Write these tests FIRST (they will fail - RED)
2. Then implement language_detection.py (GREEN)
3. Refactor if needed
"""

import pytest

from gitctx.indexing.language_detection import (
    EXTENSION_TO_LANGUAGE,
    LANGUAGE_TO_LANGCHAIN,
    detect_language_from_extension,
    get_langchain_language,
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

    def test_extension_map_contains_all_27_langchain_languages(self):
        """Verify EXTENSION_TO_LANGUAGE supports all 27 LangChain languages."""
        # ARRANGE - All 27 LangChain-supported languages
        # Source: https://github.com/langchain-ai/langchain/blob/master/libs/text-splitters/langchain_text_splitters/base.py
        expected_languages = {
            "cpp",
            "go",
            "java",
            "kotlin",
            "js",
            "ts",
            "php",
            "proto",
            "python",
            "rst",
            "ruby",
            "rust",
            "scala",
            "swift",
            "markdown",
            "latex",
            "html",
            "sol",
            "csharp",
            "cobol",
            "c",
            "lua",
            "perl",
            "haskell",
            "elixir",
            "powershell",
            "visualbasic6",
        }

        # ACT
        actual_languages = set(EXTENSION_TO_LANGUAGE.values())

        # ASSERT
        assert expected_languages.issubset(actual_languages), (
            f"Missing languages: {expected_languages - actual_languages}"
        )

    def test_fallback_to_markdown_for_unknown(self):
        """Unknown extensions should fall back to markdown."""
        # ARRANGE
        unknown_files = ["file.xyz", "data.bin", "document.docx"]

        for file_path in unknown_files:
            # ACT
            result = detect_language_from_extension(file_path)

            # ASSERT
            assert result == "markdown", f"Expected fallback for {file_path}"

    @pytest.mark.parametrize(
        "file_path,expected_language",
        [
            # Test all 27 LangChain-supported languages
            ("main.cpp", "cpp"),
            ("main.cc", "cpp"),
            ("main.h", "cpp"),
            ("main.go", "go"),
            ("Main.java", "java"),
            ("Main.kt", "kotlin"),
            ("app.js", "js"),
            ("app.mjs", "js"),
            ("app.ts", "ts"),
            ("index.php", "php"),
            ("message.proto", "proto"),
            ("script.py", "python"),
            ("doc.rst", "rst"),
            ("app.rb", "ruby"),
            ("lib.rs", "rust"),
            ("App.scala", "scala"),
            ("View.swift", "swift"),
            ("README.md", "markdown"),
            ("doc.tex", "latex"),
            ("page.html", "html"),
            ("Token.sol", "sol"),
            ("Program.cs", "csharp"),
            ("legacy.cob", "cobol"),
            ("util.c", "c"),
            ("script.lua", "lua"),
            ("script.pl", "perl"),
            ("Main.hs", "haskell"),
            ("app.ex", "elixir"),
            ("script.ps1", "powershell"),
            ("legacy.vb", "visualbasic6"),
        ],
    )
    def test_all_27_langchain_languages_detected(self, file_path: str, expected_language: str):
        """Test detection for all 27 LangChain-supported languages."""
        # ACT
        result = detect_language_from_extension(file_path)

        # ASSERT
        assert result == expected_language


class TestLangChainMapping:
    """Test suite for LangChain language code mapping."""

    @pytest.mark.parametrize(
        "gitctx_language,expected_langchain_code",
        [
            # Test all 27 LangChain-supported languages
            ("cpp", "cpp"),
            ("go", "go"),
            ("java", "java"),
            ("kotlin", "kotlin"),
            ("js", "js"),
            ("ts", "ts"),
            ("php", "php"),
            ("proto", "proto"),
            ("python", "python"),
            ("rst", "rst"),
            ("ruby", "ruby"),
            ("rust", "rust"),
            ("scala", "scala"),
            ("swift", "swift"),
            ("markdown", "markdown"),
            ("latex", "latex"),
            ("html", "html"),
            ("sol", "sol"),
            ("csharp", "csharp"),
            ("cobol", "cobol"),
            ("c", "c"),
            ("lua", "lua"),
            ("perl", "perl"),
            ("haskell", "haskell"),
            ("elixir", "elixir"),
            ("powershell", "powershell"),
            ("visualbasic6", "visualbasic6"),
        ],
    )
    def test_get_langchain_language_all_supported(
        self, gitctx_language: str, expected_langchain_code: str
    ):
        """Test LangChain mapping for all 27 supported languages."""
        # ACT
        result = get_langchain_language(gitctx_language)

        # ASSERT
        assert result == expected_langchain_code

    def test_get_langchain_language_case_insensitive(self):
        """Test that language mapping is case-insensitive."""
        # ARRANGE
        test_cases = [("PYTHON", "python"), ("Python", "python"), ("pYtHoN", "python")]

        for input_lang, expected in test_cases:
            # ACT
            result = get_langchain_language(input_lang)

            # ASSERT
            assert result == expected

    def test_get_langchain_language_unknown_returns_none(self):
        """Test that unknown languages return None for generic fallback."""
        # ARRANGE
        unknown_languages = ["unknown", "fake", "notreal"]

        for lang in unknown_languages:
            # ACT
            result = get_langchain_language(lang)

            # ASSERT
            assert result is None, f"Expected None for unknown language: {lang}"

    def test_language_to_langchain_contains_all_27_languages(self):
        """Verify LANGUAGE_TO_LANGCHAIN contains exactly 27 languages."""
        # ACT
        actual_count = len(LANGUAGE_TO_LANGCHAIN)

        # ASSERT
        assert actual_count == 27, f"Expected 27 languages, got {actual_count}"

    def test_all_extension_languages_have_langchain_mapping(self):
        """Verify every language in EXTENSION_TO_LANGUAGE has LangChain mapping."""
        # ARRANGE
        extension_languages = set(EXTENSION_TO_LANGUAGE.values())

        # ACT & ASSERT
        for lang in extension_languages:
            langchain_code = get_langchain_language(lang)
            assert langchain_code is not None, (
                f"Language '{lang}' from EXTENSION_TO_LANGUAGE has no LangChain mapping"
            )
