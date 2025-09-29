# CLAUDE.md - Vision & Strategy Guidelines for docs/vision/

This document defines how to maintain product vision, strategic planning, and success metrics for gitctx.

## 🚨 Vision Philosophy

**Clear vision drives successful execution.**

Vision documents should:

1. Define the problem being solved
2. Articulate the solution approach
3. Set measurable success criteria
4. Guide strategic decision-making

## Directory Structure

```
docs/vision/
├── CLAUDE.md           # This file - vision guidelines
├── ROADMAP.md         # Product vision & strategic initiatives
└── success-metrics.md # KPIs, metrics, and canonical tests
```

## Writing Strategic Initiatives

### Initiative Structure

Initiatives are multi-quarter strategic goals that contain multiple epics.

```markdown
# Initiative Title

**Timeline**: Q1-Q2 2025
**Status**: 🟡 In Progress
**Owner**: Team/Person

## Objective
[One paragraph describing the business goal]

## Key Results
- [ ] Measurable outcome 1
- [ ] Measurable outcome 2
- [ ] Measurable outcome 3

## Child Epics
- [EPIC-0001.1](../tickets/initiatives/INIT-0001/epics/EPIC-0001.1.md): Epic Title
- [EPIC-0001.2](../tickets/initiatives/INIT-0001/epics/EPIC-0001.2.md): Epic Title

## Success Metrics
- Metric 1: Target value
- Metric 2: Target value
```

### Initiative States

| State | Symbol | Description |
|-------|--------|-------------|
| Planning | 📝 | Being defined |
| Not Started | 🔵 | Planned but not begun |
| In Progress | 🟡 | Active development |
| Complete | 🟢 | All epics done |
| Blocked | 🔴 | Waiting on dependencies |
| Archived | 📦 | Moved to archive |

## Maintaining the ROADMAP

### ROADMAP.md Structure

```markdown
# Product Roadmap

## Executive Vision
[Problem statement]
[Solution approach]
[Product vision]

## Strategic Initiatives

### Q1 2025
- [INIT-0001](../tickets/initiatives/INIT-0001/): MVP Foundation

### Q2 2025
- [INIT-0002](../tickets/initiatives/INIT-0002/): Intelligence Layer

## Version Planning

### v0.1.0 - MVP (Q4 2025)
- Basic functionality
- Key features

### v1.0.0 -  (Q2 2026)
- Full feature set
- Production ready
```

### Roadmap Updates

Update the roadmap:

- **Quarterly**: Review and adjust initiatives
- **Monthly**: Update progress indicators
- **Weekly**: Sync with initiative README files

## Success Metrics Management

### Metric Categories

#### Coverage Metrics

Track test coverage across the codebase:

- BDD Coverage: % of features with scenarios
- Unit Test Coverage: % of code covered
- Integration Coverage: % of components tested together

#### Performance Metrics

Track system performance:

- Search Latency: Response time for queries
- Index Speed: Files processed per minute
- Memory Usage: RAM consumption during operations
- CLI Response: Command parsing time

#### Quality Metrics

Track output quality:

- Semantic Density: Relevant content ratio
- Source Diversity: Multi-source result percentage
- Result Relevance: Average relevance score

#### Efficiency Metrics

Track resource usage:

- Cost per Query: API costs
- Storage Efficiency: Compression ratio
- Token Utilization: % of budget used effectively

### Canonical Test Suites

#### Purpose

Canonical tests ensure consistent quality measurement across all changes.

#### Canonical Test Queries

Standard queries for benchmarking:

```yaml
code_patterns:
  - "authentication logic"
  - "error handling"
  - "database connection"
  
architecture_queries:
  - "API endpoints"
  - "React components"
  - "state management"
  
cross_file_queries:
  - "user registration flow"
  - "payment processing pipeline"
```

#### Canonical Test Repositories

Reference repositories for benchmarks:

```yaml
small_projects:
  - python_flask_app
  - node_express_api
  - react_frontend
  
mixed_projects:
  - fullstack_webapp
  - microservices_demo
  
open_source:
  - popular_library_v1
  - framework_core
```

### Tracking Metrics

#### Dashboard Format

```markdown
## Success Metrics Dashboard

### Coverage
- 📊 BDD: 100% ██████████
- 📊 Unit: 92%  █████████░
- 📊 Integration: 85% ████████░░

### Performance
- ⚡ Search: 1.8s (target: <2s) ✅
- ⚡ Index: 120 files/min (target: >100) ✅
- ⚡ Memory: 450MB (target: <500MB) ✅

### Quality
- 🎯 Semantic Density: 0.65 (target: >0.6) ✅
- 🎯 Source Diversity: 58% (target: >60%) ⚠️
- 🎯 Relevance: 0.72 (target: >0.7) ✅
```

#### Metric Tracking Process

1. **Measure**: Run canonical tests weekly
2. **Record**: Update success-metrics.md
3. **Analyze**: Identify trends and regressions
4. **Act**: Create tickets for improvements

## Strategic Planning

### Quarterly Planning

1. **Review**: Assess previous quarter
2. **Define**: Set new initiatives
3. **Prioritize**: Stack rank epics
4. **Resource**: Assign teams/owners
5. **Commit**: Update ROADMAP.md

### Initiative Planning

1. **Objective**: Define clear business goal
2. **Scope**: Identify required epics
3. **Timeline**: Set realistic timeline
4. **Metrics**: Define success criteria
5. **Dependencies**: Identify blockers

### Risk Management

Track risks in initiative README files:

```markdown
## Risks
| Risk | Impact | Mitigation |
|------|--------|------------|
| API costs | High | Implement caching |
| Complexity | Medium | Incremental delivery |
```

## Version Planning

### Semantic Versioning

- **Major (X.0.0)**: Breaking changes
- **Minor (0.X.0)**: New features
- **Patch (0.0.X)**: Bug fixes

### Release Criteria

Each version should define:

1. Feature list
2. Quality gates
3. Performance targets
4. Documentation requirements

### Version Milestones

```markdown
## v0.1.0 - MVP
**Target**: Q1 2025
**Theme**: Basic Functionality

### Features
- [ ] CLI commands
- [ ] Basic search
- [ ] Configuration

### Quality Gates
- [ ] 90% test coverage
- [ ] All BDD scenarios pass
- [ ] Documentation complete
```

## Communication

### Stakeholder Updates

Weekly updates should include:

- Initiative progress (% complete)
- Blockers and risks
- Metric trends
- Upcoming milestones

### Progress Reporting

Use visual indicators:

```
Progress: ████████░░ 80%
Status: 🟡 In Progress
Confidence: High ✅
```

## Best Practices

### DO

- ✅ Keep vision documents high-level
- ✅ Link to detailed tickets
- ✅ Update metrics regularly
- ✅ Review quarterly
- ✅ Maintain canonical tests

### DON'T

- ❌ Include implementation details
- ❌ Duplicate ticket content
- ❌ Set unrealistic targets
- ❌ Ignore metric trends
- ❌ Skip quarterly reviews

## Resources

- [OKR Guide](https://www.whatmatters.com/resources/okr-meaning-definition-example)
- [Product Roadmap Best Practices](https://www.productplan.com/learn/product-roadmap/)
- [Metrics-Driven Development](https://www.atlassian.com/agile/project-management/metrics)
