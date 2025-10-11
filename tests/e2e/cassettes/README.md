# VCR.py Cassettes

This directory contains VCR.py cassettes - recorded HTTP interactions with the OpenAI API for E2E testing.

## What are cassettes?

Cassettes are YAML files containing:
- HTTP requests (method, URL, headers, body)
- HTTP responses (status, headers, body, embeddings)
- Sanitized data (API keys removed)

## Benefits

- **Zero CI costs**: Replay recorded responses, no real API calls
- **Fast tests**: Instant replay vs multi-second API calls
- **Deterministic**: Same responses every run
- **Real data**: Actual API response structures, not mocks

## Recording Workflow

### Initial Recording (One-Time)

```bash
# Set real OpenAI API key
export OPENAI_API_KEY="sk-your-real-key-here"

# Record all E2E cassettes using poe task
uv run poe record-cassettes

# Or record manually with pytest
uv run pytest tests/e2e/test_progress_tracking_features.py --vcr-record=once

# Verify cassettes created
ls tests/e2e/cassettes/
```

Expected cassettes:
- `test_default_terse_output.yaml`
- `test_verbose_mode_with_phase_progress.yaml`
- `test_preindexing_cost_estimate_with_dryrun.yaml`
- `test_graceful_cancellation.yaml`
- `test_empty_repository_handling.yaml`

### Re-Recording (When API Changes)

```bash
# Force re-record all cassettes
export OPENAI_API_KEY="sk-your-real-key-here"
uv run pytest tests/e2e/ --vcr-record=all

# Or re-record specific test
uv run pytest tests/e2e/test_progress_tracking_features.py::test_verbose_mode_with_phase_progress --vcr-record=all
```

### Using Cassettes (Normal Development)

```bash
# No API key needed - uses cassettes
uv run pytest tests/e2e/

# Cassettes automatically loaded by VCR.py
```

## CI/CD Usage

In CI/CD, cassettes are used automatically:

1. Cassettes committed to git (API keys stripped)
2. CI clones repo with cassettes
3. Tests replay cassettes (no OPENAI_API_KEY needed)
4. Fast, deterministic, zero-cost tests

## Cassette Format

Example structure:

```yaml
version: 1
interactions:
- request:
    method: POST
    uri: https://api.openai.com/v1/embeddings
    body:
      encoding: utf-8
      string: '{"input":["def function_1():..."],"model":"text-embedding-3-large"}'
    headers:
      # authorization header filtered out
  response:
    status: {code: 200, message: OK}
    headers:
      content-type: [application/json]
    body:
      encoding: utf-8
      string: '{"data":[{"embedding":[0.123, 0.456, ...]}],"usage":{"total_tokens":42}}'
```

## Troubleshooting

### Test fails with "cassette not found"

**Cause**: Cassette not recorded yet

**Fix**:
```bash
export OPENAI_API_KEY="sk-..."
uv run pytest tests/e2e/test_progress_tracking_features.py::test_name --vcr-record=once
```

### Test fails with "cassette doesn't match request"

**Cause**: API request changed (new parameter, different body)

**Fix**: Re-record cassette
```bash
export OPENAI_API_KEY="sk-..."
uv run pytest tests/e2e/test_progress_tracking_features.py::test_name --vcr-record=all
```

### Want to verify test uses real API

**Cause**: Testing without cassette

**Fix**: Delete cassette and run without --vcr-record
```bash
rm tests/e2e/cassettes/test_name.yaml
export OPENAI_API_KEY="sk-..."
uv run pytest tests/e2e/test_progress_tracking_features.py::test_name
```

## Security

- **API keys filtered**: VCR automatically strips authorization headers
- **No secrets in cassettes**: All sensitive data removed
- **Safe to commit**: Cassettes contain only response data

## Size Considerations

Cassettes contain full embedding vectors (3072 dimensions × 8 bytes = ~24KB per embedding).

Typical sizes:
- Small test (1-2 embeddings): ~50KB
- Medium test (10 embeddings): ~250KB
- Large test (100 embeddings): ~2.5MB

Keep E2E tests small (5-20 files) to maintain reasonable cassette sizes.

## References

- [VCR.py Documentation](https://vcrpy.readthedocs.io/)
- [pytest-vcr Documentation](https://pytest-vcr.readthedocs.io/)
