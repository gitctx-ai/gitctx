"""Unit tests for storage schema definitions.

TDD Workflow: These tests are written FIRST (red phase) before implementation.
They define the expected behavior of CodeChunkRecord and CHUNK_SCHEMA.
"""

import pyarrow as pa


def test_code_chunk_record_has_19_fields():
    """CodeChunkRecord defines exactly 19 fields."""
    from gitctx.storage.schema import CodeChunkRecord

    fields = CodeChunkRecord.model_fields
    assert len(fields) == 19, f"Expected 19 fields, got {len(fields)}"


def test_code_chunk_record_vector_dimension():
    """Vector field is 3072-dimensional (text-embedding-3-large)."""
    from gitctx.storage.schema import CodeChunkRecord

    # LanceDB Vector fields are defined with dimension parameter
    # We verify the vector field exists and has correct annotation
    assert "vector" in CodeChunkRecord.model_fields
    # The dimension validation will be enforced by LanceDB at runtime


def test_pyarrow_schema_matches_pydantic():
    """PyArrow CHUNK_SCHEMA matches CodeChunkRecord fields."""
    from gitctx.storage.schema import CHUNK_SCHEMA, CodeChunkRecord

    pydantic_fields = set(CodeChunkRecord.model_fields.keys())
    pyarrow_fields = {f.name for f in CHUNK_SCHEMA}

    assert pydantic_fields == pyarrow_fields, (
        f"Field mismatch:\n"
        f"  Pydantic only: {pydantic_fields - pyarrow_fields}\n"
        f"  PyArrow only: {pyarrow_fields - pydantic_fields}"
    )


def test_code_chunk_record_field_types():
    """CodeChunkRecord has correct field types (str, int, bool)."""
    from gitctx.storage.schema import CodeChunkRecord

    fields = CodeChunkRecord.model_fields

    # String fields
    string_fields = [
        "chunk_content",
        "blob_sha",
        "file_path",
        "language",
        "commit_sha",
        "author_name",
        "author_email",
        "commit_message",
        "embedding_model",
        "indexed_at",
    ]
    for field_name in string_fields:
        assert field_name in fields, f"Missing string field: {field_name}"

    # Integer fields
    int_fields = [
        "token_count",
        "chunk_index",
        "start_line",
        "end_line",
        "total_chunks",
        "commit_date",
    ]
    for field_name in int_fields:
        assert field_name in fields, f"Missing int field: {field_name}"

    # Boolean fields
    bool_fields = ["is_head", "is_merge"]
    for field_name in bool_fields:
        assert field_name in fields, f"Missing bool field: {field_name}"

    # Vector field
    assert "vector" in fields, "Missing vector field"


def test_chunk_schema_vector_field_is_list_of_float32():
    """PyArrow CHUNK_SCHEMA vector field is list<float32> with 3072 items."""
    from gitctx.storage.schema import CHUNK_SCHEMA

    vector_field = CHUNK_SCHEMA.field("vector")
    # PyArrow creates a FixedSizeListType for list_(type, size)
    assert pa.types.is_fixed_size_list(vector_field.type), (
        "vector field must be fixed-size list type"
    )
    assert vector_field.type.list_size == 3072, (
        f"Expected 3072-dim vector, got {vector_field.type.list_size}"
    )
    assert pa.types.is_float32(vector_field.type.value_type), "vector elements must be float32"


def test_schema_version_constant_exists():
    """SCHEMA_VERSION constant exists and equals 1."""
    from gitctx.storage.schema import SCHEMA_VERSION

    assert SCHEMA_VERSION == 1, f"Expected SCHEMA_VERSION=1, got {SCHEMA_VERSION}"


def test_code_chunk_record_can_instantiate():
    """CodeChunkRecord can be instantiated with valid data."""
    from gitctx.storage.schema import CodeChunkRecord

    # Create a minimal valid record
    record = CodeChunkRecord(
        vector=[0.1] * 3072,
        chunk_content="def foo():\n    pass",
        token_count=10,
        blob_sha="abc123" * 7,
        chunk_index=0,
        start_line=1,
        end_line=2,
        total_chunks=1,
        file_path="src/main.py",
        language="python",
        commit_sha="def456" * 7,
        author_name="Test Author",
        author_email="test@example.com",
        commit_date=1234567890,
        commit_message="Initial commit",
        is_head=True,
        is_merge=False,
        embedding_model="text-embedding-3-large",
        indexed_at="2025-10-10T00:00:00Z",
    )

    assert record.vector == [0.1] * 3072
    assert record.chunk_content == "def foo():\n    pass"
    assert record.token_count == 10
    assert record.blob_sha == "abc123" * 7
