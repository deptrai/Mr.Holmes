# Brownfield Analysis Workflow

**Type:** Interactive Analysis Workflow  
**Module:** BMad Method Module (bmm)  
**Phase:** 1 - Analysis

## Purpose

The Brownfield Analysis workflow provides comprehensive documentation and assessment of existing codebases before planning new features or enhancements. This workflow is **mandatory** for brownfield projects to establish a baseline understanding of the current system, identify technical debt, assess risks, and create a foundation for informed planning decisions.

## When to Use

### Required For:
- **Brownfield Projects** - Any project with existing codebase before adding new features
- **Legacy System Modernization** - Before planning major refactoring or migration
- **Technical Debt Assessment** - When you need to understand and prioritize technical debt
- **Pre-Planning Phase** - Before running `plan-project` workflow on existing systems
- **Team Onboarding** - To document system for new team members

### Not Needed For:
- **Greenfield Projects** - New projects starting from scratch
- **Well-Documented Systems** - If comprehensive, up-to-date documentation already exists
- **Minor Bug Fixes** - Small changes that don't require full system understanding

## Key Features

- **Comprehensive Analysis** - Covers architecture, technical debt, code quality, security, performance, testing, and documentation
- **Adaptive Depth** - Choose between Quick (30 min), Standard (1-2 hours), or Comprehensive (3-4 hours) analysis
- **Tool-Powered** - Leverages codebase-retrieval, grep-search, git tools, and MCP integrations
- **Visual Documentation** - Generates Mermaid architecture diagrams
- **Actionable Roadmap** - Provides prioritized refactoring roadmap with effort estimates
- **Migration Strategy** - Includes guidelines for integrating new features into existing codebase
- **Baseline Metrics** - Establishes measurable baseline for future comparison

## Prerequisites

### Required Access:
- Full codebase access (read permissions)
- Git repository access for history analysis
- Configuration files (package.json, requirements.txt, etc.)

### Recommended Tools:
- **codebase-retrieval** - Semantic code search and understanding
- **grep-search** - Pattern matching and reference finding
- **git tools** - Commit history and evolution analysis
- **Context7 MCP** - Framework/library documentation (optional)
- **Perplexity MCP** - Best practices research (optional)

### Before Running:
- Ensure codebase is accessible in workspace
- Have recent git history available
- Gather any existing documentation
- Identify known pain points or concerns

## Workflow Structure

```
brownfield-analysis/
├── workflow.yaml          # Configuration and metadata
├── instructions.md        # 15-step workflow logic
├── template.md           # Comprehensive report template
├── checklist.md          # Validation criteria
└── README.md            # This file
```

## Analysis Components

### 1. System Overview
- Technology stack identification
- Project structure mapping
- Key statistics and metrics

### 2. Architecture Analysis
- Current architecture documentation
- Design patterns identification
- Component relationships
- Architecture diagram (Mermaid)
- Anti-patterns detection

### 3. Technical Debt Assessment
- Debt item cataloging
- Severity categorization (Critical/High/Medium/Low)
- Effort estimation (S/M/L/XL)
- Prioritization matrix

### 4. Code Quality Evaluation
- Code organization assessment
- Coding standards compliance
- Code smells identification
- Complexity analysis
- Error handling review

### 5. Dependency Analysis
- Dependency inventory
- Outdated package detection
- Security vulnerability check
- License compliance review

### 6. Security Assessment
- Vulnerability identification
- Best practices compliance
- Authentication/authorization review
- Data protection evaluation

### 7. Performance Baseline
- Performance metrics documentation
- Bottleneck identification
- Anti-pattern detection
- Optimization opportunities

### 8. Testing Assessment
- Test coverage estimation
- Testing framework identification
- Coverage gap analysis
- Test quality evaluation

### 9. Documentation Review
- Existing documentation inventory
- Gap identification
- Quality assessment
- Accuracy verification

### 10. Evolution Analysis
- Git history review
- Code hotspot identification
- Change frequency analysis
- Code ownership patterns

## Outputs

### Primary Deliverable
**Brownfield Analysis Report** - Comprehensive markdown document saved to:
```
{output_folder}/brownfield-analysis-{project_name}-{date}.md
```

### Report Sections
1. Executive Summary with key findings
2. System Overview and statistics
3. Current Architecture Analysis with diagram
4. Technical Debt Register with prioritization
5. Code Quality Assessment
6. Dependency Analysis
7. Security Assessment
8. Performance Baseline
9. Testing Assessment
10. Documentation Review
11. Evolution Analysis
12. Refactoring Recommendations (4-phase roadmap)
13. Migration Strategy
14. Next Steps for Planning

### Additional Artifacts
- **Architecture Diagram** - Mermaid diagram of current architecture
- **Technical Debt Register** - Prioritized list of debt items
- **Refactoring Roadmap** - Phased improvement plan
- **Migration Checklist** - Pre-planning validation

## Usage

### Basic Invocation
```
workflow brownfield-analysis
```

### Workflow Steps

1. **Initialize** - Provide project name and system description
2. **Set Scope** - Choose analysis depth (Quick/Standard/Comprehensive)
3. **Select Focus** - Identify priority areas for analysis
4. **Analyze Structure** - Map codebase structure and tech stack
5. **Review Architecture** - Document current architecture
6. **Assess Debt** - Identify and prioritize technical debt
7. **Evaluate Quality** - Assess code quality and standards
8. **Check Dependencies** - Analyze dependencies and security
9. **Review Testing** - Assess test coverage and quality
10. **Baseline Performance** - Document performance metrics
11. **Audit Documentation** - Review existing documentation
12. **Analyze Evolution** - Review git history and hotspots
13. **Generate Recommendations** - Create refactoring roadmap
14. **Define Migration** - Establish integration strategy
15. **Validate Report** - Review and finalize analysis

### Analysis Depth Options

#### Quick Analysis (~30 minutes)
- Surface-level overview
- Basic architecture mapping
- Critical issues only
- Minimal documentation
- **Use when:** Time-constrained, need quick assessment

#### Standard Analysis (~1-2 hours)
- Balanced coverage of all areas
- Moderate detail level
- Key issues and recommendations
- Standard documentation
- **Use when:** Most brownfield projects (recommended default)

#### Comprehensive Analysis (~3-4 hours)
- Deep dive into all aspects
- Detailed findings and metrics
- Extensive recommendations
- Complete documentation
- **Use when:** Large systems, major refactoring, compliance needs

## Integration with Other Workflows

### Prerequisite For:
- `plan-project` - Brownfield projects must run this first
- `prd` - Informs PRD creation with existing constraints
- `solution-architecture` - Provides context for new architecture
- `testarch-trace` - Baseline for test coverage mapping

### Complementary Workflows:
- `testarch-framework` - Set up test infrastructure after analysis
- `testarch-test-design` - Risk-based test planning
- `research` - Deep dive into specific technical areas

### Workflow Sequence (Brownfield Project):
```
1. brownfield-analysis     # Document existing system
2. plan-project           # Create PRD with brownfield context
3. solution-architecture  # Design new features
4. testarch-trace        # Map existing test coverage
5. create-story          # Begin implementation
```

## Best Practices

### Before Analysis:
- ✅ Ensure codebase is up-to-date
- ✅ Have git history available
- ✅ Gather existing documentation
- ✅ Identify known issues or concerns
- ✅ Allocate sufficient time based on depth

### During Analysis:
- ✅ Be thorough but focused on selected depth
- ✅ Document specific examples with file paths
- ✅ Use codebase-retrieval for semantic understanding
- ✅ Verify findings with actual code inspection
- ✅ Prioritize findings by business impact

### After Analysis:
- ✅ Share report with team for validation
- ✅ Discuss and prioritize recommendations
- ✅ Address critical issues before new development
- ✅ Use findings to inform planning workflows
- ✅ Update analysis periodically (quarterly/bi-annually)

## Common Use Cases

### Use Case 1: New Team Onboarding
**Scenario:** New team taking over existing project  
**Approach:** Comprehensive analysis to document everything  
**Focus:** Architecture, code quality, documentation gaps

### Use Case 2: Feature Planning
**Scenario:** Adding new features to existing system  
**Approach:** Standard analysis focusing on integration points  
**Focus:** Architecture, technical debt, testing coverage

### Use Case 3: Technical Debt Sprint
**Scenario:** Dedicated sprint to reduce technical debt  
**Approach:** Standard analysis with debt focus  
**Focus:** Technical debt, code quality, quick wins

### Use Case 4: Security Audit
**Scenario:** Security compliance or audit preparation  
**Approach:** Comprehensive analysis with security focus  
**Focus:** Security, dependencies, best practices compliance

### Use Case 5: Performance Optimization
**Scenario:** System performance issues  
**Approach:** Standard analysis with performance focus  
**Focus:** Performance baseline, bottlenecks, optimization opportunities

## Tips and Tricks

### Maximizing Analysis Quality:
- Use **codebase-retrieval** for understanding patterns and relationships
- Use **grep-search** for finding specific issues (TODO, FIXME, etc.)
- Review **git-log** to identify frequently changed files (hotspots)
- Check **dependency lock files** for exact versions
- Look for **configuration files** to understand build/deploy setup

### Time-Saving Strategies:
- Start with Quick analysis, upgrade to Standard if needed
- Focus on selected areas rather than comprehensive coverage
- Leverage existing documentation where accurate
- Use automated tools (linters, coverage reports) if available
- Prioritize high-impact areas first

### Common Pitfalls to Avoid:
- ❌ Skipping brownfield analysis for "small" changes
- ❌ Analysis paralysis - don't over-analyze
- ❌ Ignoring critical security issues
- ❌ Not validating findings with team
- ❌ Creating analysis but not acting on it

## Example Output

### Executive Summary Example:
```markdown
## Executive Summary

The Mr.Holmes codebase is a TypeScript-based blockchain analytics platform
with 45,000 lines of code across 230 files. The system demonstrates solid
architecture with clear separation of concerns, but faces moderate technical
debt primarily in the data processing layer.

**Key Findings:**
- Architecture Health: 7/10 (Good)
- Technical Debt: Medium (23 items, ~3 weeks effort)
- Code Quality: 8/10 (Very Good)
- Security Risk: Low (2 minor issues)
- Test Coverage: 65% (Needs improvement)

**Critical Actions:**
1. Update 8 outdated dependencies with security vulnerabilities
2. Add integration tests for blockchain data ingestion
3. Refactor data processing layer to reduce complexity
```

## Troubleshooting

### Issue: Analysis taking too long
**Solution:** Switch to Quick or Standard depth, focus on specific areas

### Issue: Can't access certain files
**Solution:** Document access limitations in report, analyze available code

### Issue: No git history available
**Solution:** Skip evolution analysis, focus on current state

### Issue: Large codebase (>100k LOC)
**Solution:** Use Comprehensive depth, consider analyzing modules separately

### Issue: Multiple programming languages
**Solution:** Analyze each language ecosystem separately, then synthesize

## Version History

- **v6.0.0** - Initial brownfield analysis workflow
  - Comprehensive 15-step analysis process
  - Adaptive depth options (Quick/Standard/Comprehensive)
  - Integration with BMM planning workflows
  - Mermaid architecture diagrams
  - 4-phase refactoring roadmap

## Related Documentation

- [BMM Workflows Overview](../README.md)
- [Planning Workflow](../../2-plan/workflow.yaml)
- [Solution Architecture](../../3-solutioning/workflow.yaml)
- [Test Architecture Workflows](../../testarch/README.md)

---

**Maintained by:** BMad Core Team  
**Last Updated:** 2025-10-08  
**Workflow Version:** 6.0.0

