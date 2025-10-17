# Brownfield Context Template

This template is used when planning new features for brownfield (existing) projects.
It should be populated from the brownfield analysis report.

## Brownfield Context Section

**Note:** This project is adding features to an existing codebase. The following context from brownfield analysis informs our planning decisions.

### Existing System Overview

**Current Architecture:**
{{brownfield_architecture_overview}}

**Technology Stack:**
{{brownfield_tech_stack}}

**System Health:**
- Architecture Health: {{architecture_health_score}}
- Code Quality: {{code_quality_score}}
- Test Coverage: {{test_coverage}}
- Security Risk: {{security_risk_level}}

### Integration Constraints

**Integration Points:**
{{brownfield_integration_points}}

**Existing Patterns:**
{{brownfield_design_patterns}}

**Data Flow:**
{{brownfield_data_flow}}

### Technical Debt Considerations

**Critical Technical Debt:**
{{brownfield_technical_debt_critical}}

**Debt Impact on New Features:**
{{brownfield_debt_impact}}

**Recommended Mitigations:**
{{brownfield_debt_mitigations}}

### Security & Performance Baseline

**Security Concerns:**
{{brownfield_security_concerns}}

**Performance Baseline:**
{{brownfield_performance_baseline}}

**Known Bottlenecks:**
{{brownfield_performance_issues}}

### Testing & Quality Context

**Current Test Coverage:**
{{brownfield_test_coverage}}

**Testing Gaps:**
{{brownfield_testing_gaps}}

**Quality Requirements for New Code:**
- Maintain or improve existing quality metrics
- Add tests for all new functionality
- Follow established coding standards
- Address related technical debt where feasible

### Migration & Refactoring Strategy

**Approach:**
{{brownfield_migration_strategy}}

**Refactoring Priorities:**
{{brownfield_refactoring_priorities}}

**Integration Guidelines:**
{{brownfield_implementation_guidelines}}

### Constraints & Risks

**Architectural Constraints:**
- Must integrate with existing {{existing_components}}
- Cannot break existing {{critical_features}}
- Must maintain backward compatibility with {{compatibility_requirements}}

**Known Risks:**
{{brownfield_risks}}

**Mitigation Strategies:**
{{brownfield_risk_mitigations}}

### References

**Brownfield Analysis Report:** {{brownfield_analysis_file}}
**Last Analysis Date:** {{brownfield_analysis_date}}
**Next Review Date:** {{brownfield_next_review}}

---

## Usage Instructions

When populating this template:

1. **Load Brownfield Analysis:** Read the brownfield-analysis-*.md file
2. **Extract Key Sections:** Pull relevant information from analysis
3. **Summarize:** Keep summaries concise (2-3 paragraphs max per section)
4. **Focus on Impact:** Emphasize how existing code affects new features
5. **Be Specific:** Include file paths, component names, specific constraints
6. **Update PRD:** Insert populated template into PRD brownfield_context section

## Example Populated Section

```markdown
### Brownfield Context

**Note:** This project is adding features to an existing codebase. The following context from brownfield analysis informs our planning decisions.

#### Existing System Overview

**Current Architecture:**
Mr.Holmes uses a hybrid CLI + Web GUI architecture with Python core modules and PHP-based web interface. The system follows a modular design with specialized Searcher modules for different data types (username, phone, website, person).

**Technology Stack:**
- Python 3 (Core logic, 16,482 LOC)
- PHP (Web GUI backend)
- JavaScript (Frontend interactivity)
- JSON (Configuration and data storage)

**System Health:**
- Architecture Health: 6.5/10 (Good with concerns)
- Code Quality: 6/10 (Functional but needs improvement)
- Test Coverage: 0% (Critical issue)
- Security Risk: Medium (outdated dependencies)

#### Integration Constraints

**Integration Points:**
- Core/Searcher.py - Main search orchestration (700+ lines, needs refactoring)
- GUI/Actions/ - PHP controllers for web interface
- Site_lists/ - JSON configurations for 200+ platforms
- Reports/ - File-based output system

**Existing Patterns:**
- Static method pattern extensively used
- File-based communication between CLI and GUI
- Sequential HTTP request processing
- Configuration via INI files

#### Technical Debt Considerations

**Critical Technical Debt:**
1. beautifulsoup4 outdated (4.9.3 → 4.12.3) - Security risk
2. Zero test coverage - High regression risk
3. Monolithic Searcher.py - Maintainability issue
4. No async operations - Performance bottleneck

**Debt Impact on New Features:**
- New search features must follow sequential pattern (performance impact)
- Cannot safely refactor without tests
- Integration testing manual only
- Security vulnerabilities in dependencies

**Recommended Mitigations:**
- Update dependencies before adding features
- Add tests for new code (minimum 70% coverage)
- Extract common search logic to base class
- Consider async implementation for new features

#### Migration & Refactoring Strategy

**Approach:**
Use Strangler Fig pattern - implement new features with modern patterns alongside existing code, gradually migrate old code.

**Integration Guidelines:**
- New code should use async/await where possible
- Add comprehensive tests for all new functionality
- Follow PEP 8 and add type hints
- Document all public APIs
- Use dependency injection for testability

**Constraints:**
- Must maintain CLI and GUI compatibility
- Cannot break existing site configurations
- Must support existing report formats
- Backward compatibility with Python 3.7+
```

## Validation Checklist

When using this template, ensure:

- [ ] Brownfield analysis report has been completed
- [ ] All critical technical debt is documented
- [ ] Integration points are clearly identified
- [ ] Security and performance constraints are noted
- [ ] Migration strategy is defined
- [ ] Team has reviewed and validated context
- [ ] Constraints are reflected in epic planning
- [ ] Risks are documented with mitigations

---

**Template Version:** 1.0.0
**Last Updated:** 2025-10-08
**Part of:** BMad Brownfield Analysis Workflow v6.0

