# INIT-0001: MVP Foundation

**Timeline**: Q4 2025  
**Status**: 📝 Planning  
**Owner**: Core Team  
**Progress**: ░░░░░░░░░░ 0%

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
| [EPIC-0001.1](epics/EPIC-0001.1.md) | CLI Foundation | 🔵 Not Started | ░░░░░░░░░░ 0% | - |
| [EPIC-0001.2](epics/EPIC-0001.2.md) | Real Indexing | 🔵 Not Started | ░░░░░░░░░░ 0% | - |
| [EPIC-0001.3](epics/EPIC-0001.3.md) | Vector Search | 🔵 Not Started | ░░░░░░░░░░ 0% | - |

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

- ⬜ Main CLI structure with Typer
- ⬜ Config command for API keys
- ⬜ Help system and documentation
- ⬜ Error handling and user feedback
- ⬜ Progress indicators with Rich

### Real Indexing (EPIC-0001.2)

- ⬜ Git-aware file scanner
- ⬜ Smart text chunking with overlap
- ⬜ OpenAI embedding generation
- ⬜ Safetensors storage (5x compression)
- ⬜ Incremental indexing support

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

1. Complete EPIC-0001.1 remaining tasks
2. Start EPIC-0001.2 implementation
3. Set up CI/CD pipeline
4. Prepare for alpha testing

## Notes

- Focus on core functionality first, optimize later
- Use mocked implementations where possible for faster iteration
- Maintain BDD/TDD discipline throughout
- Track costs carefully during development

---

**Created**: 2025-09-28  
**Last Updated**: 2025-09-28  
**Review Schedule**: Weekly during active development
