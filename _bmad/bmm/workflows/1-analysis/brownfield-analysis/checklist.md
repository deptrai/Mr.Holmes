# Brownfield Analysis Validation Checklist

## Document Completeness

- [ ] All required sections are present and populated
- [ ] No placeholder text remains (e.g., [TODO], {{variable}})
- [ ] Document follows the brownfield analysis template format
- [ ] Executive summary accurately reflects findings
- [ ] All analysis areas from workflow.yaml are covered

## System Overview Quality

- [ ] System description is clear and accurate
- [ ] Technology stack is completely identified
- [ ] Project structure is documented with directory tree
- [ ] Key statistics are measured and reported
- [ ] Primary languages and frameworks are identified

## Architecture Analysis

- [ ] Current architecture is comprehensively documented
- [ ] Architecture diagram is created (Mermaid format)
- [ ] Design patterns are identified and explained
- [ ] Component relationships are mapped
- [ ] Integration points are documented
- [ ] Architecture strengths are highlighted
- [ ] Architecture weaknesses are identified
- [ ] Anti-patterns are detected and explained

## Technical Debt Assessment

- [ ] Technical debt items are catalogued in register
- [ ] Each debt item has priority, impact, and effort estimate
- [ ] Debt is categorized by severity (Critical/High/Medium/Low)
- [ ] Critical debt items are clearly flagged
- [ ] Debt metrics are calculated (total items, ratio, effort)
- [ ] Root causes of debt are identified
- [ ] Debt prioritization is justified

## Code Quality Evaluation

- [ ] Code organization is assessed
- [ ] Coding standards compliance is checked
- [ ] Code smells are identified with examples
- [ ] Complexity analysis is performed
- [ ] Error handling patterns are reviewed
- [ ] Logging and monitoring are evaluated
- [ ] Quality metrics are measured and reported
- [ ] Specific quality issues are documented with locations

## Dependency Analysis

- [ ] All dependency files are identified
- [ ] Direct dependencies are listed
- [ ] Outdated dependencies are identified with versions
- [ ] Deprecated dependencies are flagged
- [ ] Security vulnerabilities are checked
- [ ] License compliance is assessed
- [ ] Dependency health is evaluated
- [ ] Update recommendations are provided

## Security Assessment

- [ ] Security vulnerabilities are identified
- [ ] Security best practices compliance is checked
- [ ] Authentication/authorization patterns are reviewed
- [ ] Data protection measures are assessed
- [ ] Common security issues are checked (XSS, SQL injection, etc.)
- [ ] Security recommendations are specific and actionable
- [ ] Critical security issues are clearly flagged

## Performance Baseline

- [ ] Performance metrics are documented (if available)
- [ ] Performance issues are identified with locations
- [ ] Performance anti-patterns are detected
- [ ] Optimization opportunities are listed
- [ ] Performance-critical paths are identified
- [ ] Baseline measurements are recorded
- [ ] Performance recommendations are provided

## Testing Assessment

- [ ] Test coverage is estimated or measured
- [ ] Testing frameworks are identified
- [ ] Test types are categorized (unit/integration/e2e)
- [ ] Coverage gaps are identified
- [ ] Test quality is assessed
- [ ] Untested critical paths are flagged
- [ ] Testing recommendations are specific

## Documentation Review

- [ ] Existing documentation is inventoried
- [ ] Documentation gaps are identified
- [ ] Documentation quality is assessed
- [ ] Documentation accuracy is verified against code
- [ ] Setup/installation docs are reviewed
- [ ] API documentation is checked
- [ ] Documentation recommendations are provided

## Evolution Analysis

- [ ] Git history is analyzed
- [ ] Code hotspots are identified
- [ ] Change frequency is documented
- [ ] Code ownership patterns are noted
- [ ] Commit quality is assessed
- [ ] Development trends are identified

## Refactoring Recommendations

- [ ] Refactoring strategy is clearly defined
- [ ] Recommendations are prioritized by impact and effort
- [ ] Roadmap is divided into phases with timelines
- [ ] Phase 1 (Critical) items are clearly identified
- [ ] Each recommendation includes rationale
- [ ] Quick wins are identified
- [ ] Dependencies between refactoring items are noted

## Migration Strategy

- [ ] Modernization approach is defined
- [ ] Strangler fig pattern is considered if applicable
- [ ] Gradual migration guidelines are provided
- [ ] New feature integration strategy is documented
- [ ] Implementation guidelines are specific
- [ ] Risk mitigation strategies are included
- [ ] Backward compatibility is addressed

## Actionability

- [ ] Immediate actions are specific and achievable
- [ ] Short-term goals are realistic and measurable
- [ ] Long-term vision is aligned with business goals
- [ ] Recommendations include effort estimates
- [ ] Priorities are clearly justified
- [ ] Next steps are clearly defined

## Overall Quality

- [ ] Language is clear and professional
- [ ] Technical terms are used accurately
- [ ] Findings are supported by evidence
- [ ] Code examples are provided where relevant
- [ ] File paths and locations are specific
- [ ] Metrics and numbers are accurate
- [ ] Report is ready for team review

## Completeness for Planning

- [ ] Analysis provides sufficient context for PRD creation
- [ ] Constraints and limitations are documented
- [ ] Existing architecture informs new feature planning
- [ ] Technical debt impact on new features is assessed
- [ ] Integration points for new features are identified
- [ ] Risk areas for new development are flagged

## Tool Usage Validation

- [ ] codebase-retrieval was used for semantic understanding
- [ ] grep-search was used for pattern matching
- [ ] git tools were used for history analysis
- [ ] File system was explored for structure
- [ ] All required tools from workflow.yaml were utilized

## Diagram and Visual Quality

- [ ] Architecture diagram is valid Mermaid syntax
- [ ] Diagram accurately represents current architecture
- [ ] Component relationships are clear
- [ ] Diagram is readable and well-organized
- [ ] Additional diagrams are included if helpful

## Metrics Validation

- [ ] All metrics are measured (not estimated) where possible
- [ ] Metrics are consistent throughout document
- [ ] Metrics are relevant and meaningful
- [ ] Baseline metrics are established for future comparison
- [ ] Metrics support recommendations

## Risk Assessment

- [ ] Technical risks are identified
- [ ] Business risks are considered
- [ ] Security risks are highlighted
- [ ] Performance risks are noted
- [ ] Mitigation strategies are provided

## Stakeholder Readiness

- [ ] Report is suitable for technical team review
- [ ] Executive summary is suitable for management
- [ ] Recommendations are business-aligned
- [ ] ROI considerations are included where relevant
- [ ] Report supports decision-making

## Final Validation

### Critical Issues Found:

- [ ] None identified
- [ ] List critical issues here if any

### Analysis Gaps:

- [ ] None identified
- [ ] List any areas that need deeper analysis

### Ready for Planning Phase:

- [ ] Yes, brownfield analysis is complete and validated
- [ ] No, requires additional analysis (specify above)

### Recommended Next Workflows:

- [ ] `workflow plan-project` - Create PRD with brownfield context
- [ ] `workflow solution-architecture` - Design new features
- [ ] `workflow testarch-trace` - Map existing test coverage
- [ ] `workflow testarch-framework` - Set up test infrastructure
- [ ] Other: _______________

---

## Validation Notes

**Validator:** {{user_name}}
**Validation Date:** {{date}}
**Analysis Quality Score:** {{quality_score}}/10

**Additional Comments:**

{{validation_comments}}

