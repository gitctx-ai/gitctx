# INIT-0001: MVP Foundation

**Timeline**: Q4 2025
**Status**: 🚧 In Progress
**Owner**: Core Team
**Progress**: ████░░░░░░ ~38% (EPIC-0001.1 complete - 10/10 points, EPIC-0001.2 in progress - 9/25 points, 19/60 total points)

## Objective

Build the core functionality users need to search their codebase intelligently. Establish the foundation for a git-like CLI tool that provides semantic search capabilities with OpenAI embeddings and LanceDB vector storage.

## Key Results

- [ ] Complete CLI interface with all basic commands working
- [ ] Real indexing with OpenAI embeddings functional
- [ ] Vector search returning relevant results in <2 seconds
- [ ] Installation via pipx working smoothly

## Epics

| ID | Title | Status | Progress | Owner |
|----|-------|--------|----------|-------|
| [EPIC-0001.1](EPIC-0001.1/README.md) | CLI Foundation | ✅ Complete | ██████████ 100% | Core Team |
| [EPIC-0001.2](EPIC-0001.2/README.md) | Real Indexing | 🟡 In Progress | ███░░░░░░░ 36% | Core Team |
| [EPIC-0001.3](EPIC-0001.3/README.md) | Vector Search | 🔵 Not Started | ░░░░░░░░░░ 0% | - |

## Success Metrics

### Functional Requirements

- ⬜ CLI responds to all commands
- ⬜ Repository indexing completes successfully
- ⬜ Search returns relevant results
- ⬜ Configuration management works

### Performance Targets

- Search latency: <2 seconds for 10K files
- Index speed: >100 files/minute
- Memory usage: <500MB during operation
- Startup time: <100ms

### Quality Gates

- BDD scenarios: 100% coverage for user features
- Unit tests: >90% code coverage
- Integration tests: All components tested
- Documentation: User guide complete

## Dependencies

### External Services

- OpenAI API for embeddings
- PyPI for package distribution

### Technology Stack

- Python 3.11+ (async support, type hints)
- Typer + Rich (CLI framework)
- OpenAI text-embedding-3-large
- LanceDB (vector storage)
- Safetensors (embedding storage)

## Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| API costs exceed budget | High | Medium | Implement caching, cost tracking |
| Search latency too high | High | Low | Use indices, optimize queries |
| Complex installation | Medium | Low | pipx-only distribution |
| Poor search relevance | High | Medium | Iterate on embeddings, add reranking |

## Deliverables Checklist

### CLI Foundation (EPIC-0001.1)

- ✅ Main CLI structure with Typer
- ✅ Config command with persistent storage (STORY-0001.1.2 complete)
- ✅ Help system and documentation
- ✅ Error handling and user feedback
- ✅ Progress indicators with Rich

**Progress**: 10/10 story points complete (100%) ✅

### Real Indexing (EPIC-0001.2)

- ✅ Commit graph walker with blob deduplication (STORY-0001.2.1 complete)
- ⬜ Smart text chunking with overlap (STORY-0001.2.2 - planned)
- ⬜ OpenAI embedding generation (STORY-0001.2.3 - planned)
- ⬜ LanceDB storage (STORY-0001.2.4 - planned)
- ⬜ Progress tracking and cost estimation (STORY-0001.2.5 - planned)

**Progress**: 9/25 story points complete (36%)

### Vector Search (EPIC-0001.3)

- ⬜ LanceDB integration
- ⬜ Query embedding generation
- ⬜ Similarity search implementation
- ⬜ Result ranking and formatting
- ⬜ Search performance optimization

## Acceptance Criteria

The MVP is complete when:

1. **Installation Works**

   ```bash
   pipx install gitctx
   gitctx --version  # Shows version
   ```

2. **Configuration Works**

   ```bash
   gitctx config set api_keys.openai "sk-..."
   gitctx config get api_keys.openai  # Shows masked key
   ```

3. **Indexing Works**

   ```bash
   gitctx index
   # Shows progress bar
   # Completes without errors
   # Creates .gitctx/ directory
   # Creates safetensored code chunks
   # Creates vector store in lancedb
   ```

4. **Search Works**

   ```bash
   gitctx search "authentication"
   # Returns results in <2 seconds
   # Shows file:line references
   # Results are relevant
   ```

## Timeline

### Oct Week 1-2: CLI Foundation (EPIC-0001.1)

- Set up project structure
- Implement basic commands
- Add configuration management

### Oct Week 3-4: Real Indexing (EPIC-0001.2)

- Build file scanner
- Implement chunking
- Integrate OpenAI embeddings

### Nov Week 1-2: Vector Search (EPIC-0001.3)

- Set up LanceDB
- Implement search
- Optimize performance

### Nov Week 3-4: Integration & Testing

- End-to-end testing
- Performance optimization
- Documentation

## Next Steps

1. **EPIC-0001.2**: Complete real indexing implementation
   - ✅ STORY-0001.2.1: Commit Graph Walker (9 points) - Complete
   - 🔵 STORY-0001.2.2: Blob Chunking (5 points) - Need to write
   - 🔵 STORY-0001.2.3: OpenAI Embeddings (5 points) - Need to write
   - 🔵 STORY-0001.2.4: LanceDB Storage (3 points) - Need to write
   - 🔵 STORY-0001.2.5: Progress/Cost (3 points) - Need to write
2. **EPIC-0001.3**: Start vector search implementation
3. Prepare for alpha testing with working index + search

## Notes

- Focus on core functionality first, optimize later
- Use mocked implementations where possible for faster iteration
- Maintain BDD/TDD discipline throughout
- Track costs carefully during development

---

**Created**: 2025-09-28
**Last Updated**: 2025-10-05
**Review Schedule**: Weekly during active development
