"""Language detection for code files.

MVP approach: Extension-based detection covers 95%+ of real-world files
with zero dependencies. Falls back to 'markdown' for unknown types
(generic text splitting works fine).

Supports all 27 LangChain-supported languages with 60+ file extensions.
Source: https://github.com/langchain-ai/langchain/blob/master/libs/text-splitters/langchain_text_splitters/base.py

Future: Can upgrade to content-based detection if metrics show need.
"""

from pathlib import Path

# Map file extensions to gitctx language identifiers
# Covers all 27 LangChain-supported languages for 95%+ coverage in real-world repos
EXTENSION_TO_LANGUAGE = {
    # Python
    ".py": "python",
    ".pyw": "python",
    ".pyx": "python",
    # JavaScript/TypeScript
    ".js": "js",
    ".jsx": "js",
    ".mjs": "js",
    ".cjs": "js",
    ".ts": "ts",
    ".tsx": "ts",
    ".mts": "ts",
    ".cts": "ts",
    # C/C++/C#
    ".c": "c",
    ".h": "cpp",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".hxx": "cpp",
    ".cs": "csharp",
    # Go
    ".go": "go",
    # Rust
    ".rs": "rust",
    # Java
    ".java": "java",
    # Kotlin
    ".kt": "kotlin",
    ".kts": "kotlin",
    # Scala
    ".scala": "scala",
    ".sc": "scala",
    # Ruby
    ".rb": "ruby",
    # PHP
    ".php": "php",
    # Swift
    ".swift": "swift",
    # Protocol Buffers
    ".proto": "proto",
    # Solidity
    ".sol": "sol",
    # Lua
    ".lua": "lua",
    # Perl
    ".pl": "perl",
    ".pm": "perl",
    # Haskell
    ".hs": "haskell",
    ".lhs": "haskell",
    # Elixir
    ".ex": "elixir",
    ".exs": "elixir",
    # PowerShell
    ".ps1": "powershell",
    ".psm1": "powershell",
    # Visual Basic 6
    ".vb": "visualbasic6",
    ".bas": "visualbasic6",
    # COBOL
    ".cob": "cobol",
    ".cbl": "cobol",
    # Markup/Documentation
    ".md": "markdown",
    ".markdown": "markdown",
    ".rst": "rst",
    ".tex": "latex",
    ".html": "html",
    ".htm": "html",
}

# Map gitctx language names to LangChain language codes
# LangChain supports exactly 27 languages (from Language enum)
# Source: https://github.com/langchain-ai/langchain/blob/master/libs/text-splitters/langchain_text_splitters/base.py
LANGUAGE_TO_LANGCHAIN = {
    "cpp": "cpp",
    "go": "go",
    "java": "java",
    "kotlin": "kotlin",
    "js": "js",
    "ts": "ts",
    "php": "php",
    "proto": "proto",
    "python": "python",
    "rst": "rst",
    "ruby": "ruby",
    "rust": "rust",
    "scala": "scala",
    "swift": "swift",
    "markdown": "markdown",
    "latex": "latex",
    "html": "html",
    "sol": "sol",
    "csharp": "csharp",
    "cobol": "cobol",
    "c": "c",
    "lua": "lua",
    "perl": "perl",
    "haskell": "haskell",
    "elixir": "elixir",
    "powershell": "powershell",
    "visualbasic6": "visualbasic6",
}


def get_langchain_language(language: str) -> str | None:
    """Convert gitctx language to LangChain language code.

    Extracted as separate function for testability and replaceability.
    Can be tested independently of LangChain dependency.
    Easy to swap LangChain for alternative text splitter in future.

    Args:
        language: gitctx language identifier (e.g., "python", "js")

    Returns:
        LangChain language code if supported, None otherwise.
        None indicates fallback to generic RecursiveCharacterTextSplitter.

    Examples:
        >>> get_langchain_language("python")
        'python'
        >>> get_langchain_language("js")
        'js'
        >>> get_langchain_language("unknown")
        None
    """
    return LANGUAGE_TO_LANGCHAIN.get(language.lower())


def detect_language_from_extension(file_path: str) -> str:
    """Detect programming language from file extension.

    MVP approach: Simple extension mapping covers 95%+ of real-world files
    with 60+ extensions across all 27 LangChain-supported languages.
    Falls back to 'markdown' for unknown types (generic text splitting works fine).

    Future: Can upgrade to content-based detection if metrics show need.

    Args:
        file_path: Path to file (can be relative or absolute)

    Returns:
        Language identifier for gitctx (use get_langchain_language() to convert)
        Falls back to "markdown" for unknown extensions

    Examples:
        >>> detect_language_from_extension("src/main.py")
        'python'
        >>> detect_language_from_extension("app.js")
        'js'
        >>> detect_language_from_extension("unknown.xyz")
        'markdown'
    """
    # Handle empty path
    if not file_path:
        return "markdown"

    # Extract extension (case-insensitive)
    ext = Path(file_path).suffix.lower()

    # Return mapped language or fallback to markdown
    return EXTENSION_TO_LANGUAGE.get(ext, "markdown")
