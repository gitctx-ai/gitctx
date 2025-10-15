# INIT-0001: MVP Foundation

**Timeline**: Q4 2025
**Status**: 🚧 In Progress
**Owner**: Core Team
**Progress**: ████████░░ ~55% (EPIC-0001.1 complete - 10/10 points, EPIC-0001.2 complete - 31/31 points, EPIC-0001.3 in progress - 10/13 points, EPIC-0001.4 not started - 0/21 points, 51/75 total points)

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
| [EPIC-0001.2](EPIC-0001.2/README.md) | Real Indexing Implementation | ✅ Complete | ██████████ 100% | Core Team |
| [EPIC-0001.3](EPIC-0001.3/README.md) | Vector Search Implementation | 🟡 In Progress | ████████░░ 77% | Core Team |
| [EPIC-0001.4](EPIC-0001.4/README.md) | Performance & Observability | 🔵 Not Started | ░░░░░░░░░░ 0% | Core Team |

## Success Metrics

### Functional Requirements

- ✅ CLI responds to all commands
- ✅ Repository indexing completes successfully
- ⬜ Search returns relevant results
- ✅ Configuration management works

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
- ✅ Smart text chunking with overlap (STORY-0001.2.2 complete)
- ✅ OpenAI embedding generation (STORY-0001.2.3 complete)
- ✅ LanceDB storage (STORY-0001.2.4 complete)
- ✅ Progress tracking and cost estimation (STORY-0001.2.5 complete)

**Progress**: 31/31 story points complete (100%) ✅

### Vector Search (EPIC-0001.3)

- ✅ Query embedding generation (STORY-0001.3.1 complete)
- ✅ Vector similarity search (STORY-0001.3.2 complete)
- 🔵 Result formatting & output (STORY-0001.3.3 not started)

**Progress**: 10/13 story points complete (77%)

**Note**: Performance optimization moved to EPIC-0001.4 due to indexing speed dependency.

### Performance & Observability (EPIC-0001.4)

- 🔵 Protocol performance testing infrastructure (STORY-0001.4.1 not started)
- 🔵 Indexing performance optimization (STORY-0001.4.2 not started)
- 🔵 Search performance optimization (STORY-0001.4.3 not started)
- 🔵 LangSmith integration & prompt evals (STORY-0001.4.4 not started)

**Progress**: 0/21 story points complete (0%)

**Note**: Created during EPIC-0001.3 gap analysis. Key insight: "Any protocol deserves performance monitoring."

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

1. **EPIC-0001.3**: Complete vector search implementation
   - 🔵 STORY-0001.3.3: Result Formatting & Output (3 points) - Ready to start
   - Run: `/start-next-task STORY-0001.3.3`
2. **EPIC-0001.4**: Begin performance optimization (after EPIC-0001.3 complete)
   - Implementation order: STORY-0001.4.1 → 0001.4.2 → 0001.4.3 → 0001.4.4
   - Critical: Indexing performance (STORY-0001.4.2) must precede search performance (STORY-0001.4.3)
3. Prepare for alpha testing with optimized index + search

## Notes

- Focus on core functionality first, optimize later
- Use mocked implementations where possible for faster iteration
- Maintain BDD/TDD discipline throughout
- Track costs carefully during development

---

**Created**: 2025-09-28
**Last Updated**: 2025-10-14 (Added EPIC-0001.4 during EPIC-0001.3 gap analysis)
**Review Schedule**: Weekly during active development
