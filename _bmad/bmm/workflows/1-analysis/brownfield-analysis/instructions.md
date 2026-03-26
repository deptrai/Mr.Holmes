# Brownfield Analysis - Workflow Instructions

<critical>The workflow execution engine is governed by: {project-root}/bmad/core/tasks/workflow.xml</critical>
<critical>You MUST have already loaded and processed: {installed_path}/workflow.yaml</critical>

<workflow>

<step n="0" goal="Initialize brownfield analysis session">
<action>Welcome the user to the Brownfield Analysis workflow</action>
<action>Explain this workflow will comprehensively analyze their existing codebase</action>
<action>Emphasize this is a prerequisite for brownfield projects before planning new features</action>

<ask>What is the project name for this brownfield analysis?</ask>
<template-output>project_name</template-output>

<ask>Please provide a brief description of the existing system (what it does, its purpose):</ask>
<template-output>system_description</template-output>
</step>

<step n="1" goal="Determine analysis scope and depth">
<ask>What level of analysis depth do you need?

**1. Quick Analysis** (~30 min) - Surface-level overview, basic architecture, critical issues only
**2. Standard Analysis** (~1-2 hours) - Balanced analysis covering all major areas
**3. Comprehensive Analysis** (~3-4 hours) - Deep dive into all aspects, detailed recommendations

Which level works best for your needs?</ask>

<action>Store the analysis depth preference</action>
<template-output>analysis_depth</template-output>

<ask>What are your primary concerns or focus areas? (Select all that apply)
1. Architecture and design patterns
2. Technical debt and code quality
3. Security vulnerabilities
4. Performance issues
5. Testing coverage
6. Documentation gaps
7. Dependency management
8. All of the above

Please list the numbers or select option 8.</ask>

<action>Store focus areas for prioritized analysis</action>
<template-output>focus_areas</template-output>
</step>

<step n="2" goal="Gather codebase context and structure">
<action>Use codebase-retrieval to understand overall project structure</action>
<action>Identify primary programming languages and frameworks</action>
<action>Map directory structure and key components</action>
<action>Identify entry points and main modules</action>

<ask>What is the root directory of the codebase to analyze? (relative to workspace root)</ask>
<template-output>codebase_root</template-output>

<action>Use view tool to examine root directory structure</action>
<action>Identify configuration files (package.json, requirements.txt, Cargo.toml, etc.)</action>
<action>Detect build systems and tooling</action>

<template-output>project_structure</template-output>
<template-output>tech_stack</template-output>
</step>

<step n="3" goal="Analyze current architecture">
<action>Use codebase-retrieval to identify architectural patterns</action>
<action>Map component relationships and dependencies</action>
<action>Identify design patterns in use</action>
<action>Detect architectural anti-patterns</action>

<ask>Are there any existing architecture documents or diagrams? If yes, please share them.</ask>

<action>Compare existing docs (if any) with actual codebase</action>
<action>Identify architecture drift or documentation gaps</action>
<action>Create current-state architecture diagram using Mermaid</action>

<template-output>architecture_overview</template-output>
<template-output>architecture_diagram</template-output>
<template-output>design_patterns</template-output>
</step>

<step n="4" goal="Assess technical debt">
<action>Use grep-search to find TODO, FIXME, HACK, XXX comments</action>
<action>Identify code duplication patterns</action>
<action>Detect outdated dependencies and deprecated APIs</action>
<action>Find complex functions (high cyclomatic complexity indicators)</action>
<action>Identify inconsistent coding styles</action>

<action>Categorize technical debt by severity:
- Critical: Security issues, major bugs, blocking issues
- High: Performance problems, maintainability issues
- Medium: Code quality, minor refactoring needs
- Low: Style inconsistencies, minor improvements</action>

<action>Estimate effort for each debt item (T-shirt sizing: S/M/L/XL)</action>

<template-output>technical_debt_items</template-output>
<template-output>debt_prioritization</template-output>
</step>

<step n="5" goal="Evaluate code quality">
<action>Analyze code organization and modularity</action>
<action>Check for separation of concerns</action>
<action>Identify god objects or god functions</action>
<action>Assess naming conventions consistency</action>
<action>Review error handling patterns</action>
<action>Check for proper logging and monitoring</action>

<ask>Do you have any code quality tools or linters configured? (ESLint, Pylint, Clippy, etc.)</ask>

<action>If tools exist, review their configuration and recent reports</action>
<action>Identify code quality standards violations</action>

<template-output>code_quality_assessment</template-output>
<template-output>quality_metrics</template-output>
</step>

<step n="6" goal="Analyze dependencies and security">
<action>Identify all dependency files (package.json, requirements.txt, Cargo.toml, go.mod, etc.)</action>
<action>List direct and transitive dependencies</action>
<action>Check for outdated packages</action>
<action>Identify deprecated dependencies</action>
<action>Look for security vulnerabilities (if lock files exist)</action>

<ask>When was the last time dependencies were updated?</ask>

<action>Assess dependency health and maintenance status</action>
<action>Identify potential supply chain risks</action>
<action>Check for license compatibility issues</action>

<template-output>dependency_analysis</template-output>
<template-output>security_concerns</template-output>
</step>

<step n="7" goal="Review testing strategy and coverage">
<action>Identify test directories and test files</action>
<action>Determine testing frameworks in use</action>
<action>Assess test types (unit, integration, e2e)</action>
<action>Estimate test coverage (if coverage reports exist)</action>
<action>Identify untested critical paths</action>

<ask>Do you have test coverage reports available? If yes, please share the latest report.</ask>

<action>Analyze test quality and maintainability</action>
<action>Identify testing gaps and risks</action>

<template-output>testing_assessment</template-output>
<template-output>coverage_gaps</template-output>
</step>

<step n="8" goal="Assess performance baseline">
<action>Identify performance-critical code paths</action>
<action>Look for common performance anti-patterns:
- N+1 queries
- Inefficient loops
- Memory leaks
- Blocking operations
- Missing caching</action>

<ask>Do you have any performance metrics or monitoring data? (response times, throughput, resource usage)</ask>

<action>Document current performance baseline</action>
<action>Identify performance bottlenecks</action>
<action>Suggest performance improvement opportunities</action>

<template-output>performance_baseline</template-output>
<template-output>performance_issues</template-output>
</step>

<step n="9" goal="Review documentation">
<action>Identify existing documentation (README, docs/, wiki, comments)</action>
<action>Assess documentation completeness</action>
<action>Check documentation accuracy vs actual code</action>
<action>Identify documentation gaps</action>

<action>Evaluate:
- Setup/installation instructions
- Architecture documentation
- API documentation
- Code comments quality
- Deployment documentation
- Troubleshooting guides</action>

<template-output>documentation_assessment</template-output>
<template-output>documentation_gaps</template-output>
</step>

<step n="10" goal="Analyze git history and evolution">
<action>Use git-log to review recent commit history</action>
<action>Identify active development areas</action>
<action>Find frequently changed files (hotspots)</action>
<action>Assess commit message quality</action>
<action>Identify code ownership patterns</action>

<ask>Are there any known pain points or problematic areas in the codebase?</ask>

<action>Correlate user feedback with code analysis</action>

<template-output>evolution_analysis</template-output>
<template-output>hotspots</template-output>
</step>

<step n="11" goal="Generate refactoring recommendations">
<action>Synthesize all analysis findings</action>
<action>Prioritize refactoring opportunities by:
- Business impact
- Technical risk
- Implementation effort
- Dependencies</action>

<action>Create refactoring roadmap with phases:
- Phase 1: Critical fixes (security, major bugs)
- Phase 2: High-impact improvements (performance, maintainability)
- Phase 3: Quality enhancements (code quality, testing)
- Phase 4: Nice-to-haves (style, minor improvements)</action>

<template-output>refactoring_recommendations</template-output>
<template-output>refactoring_roadmap</template-output>
</step>

<step n="12" goal="Create migration strategy">
<action>Define strategy for introducing new features to brownfield codebase</action>
<action>Recommend patterns for gradual modernization</action>
<action>Suggest strangler fig pattern if major refactoring needed</action>
<action>Provide guidelines for maintaining consistency</action>

<template-output>migration_strategy</template-output>
<template-output>implementation_guidelines</template-output>
</step>

<step n="13" goal="Generate comprehensive report">
<action>Load template from {installed_path}/template.md</action>
<action>Populate all template sections with analysis findings</action>
<action>Include architecture diagram (Mermaid format)</action>
<action>Add executive summary highlighting key findings</action>
<action>Include actionable recommendations</action>

<action>Save report to {output_folder}/brownfield-analysis-{project_name}-{date}.md</action>

<output>Brownfield analysis report saved successfully!</output>
</step>

<step n="14" goal="Validate and review">
<action>Load validation checklist from {installed_path}/checklist.md</action>
<action>Run through all validation criteria</action>
<action>Identify any gaps or missing information</action>

<ask>Would you like to review the analysis report together and make any adjustments?</ask>

<action>If yes, present report sections for review and refinement</action>
<action>If no, proceed to completion</action>
</step>

<step n="15" goal="Provide next steps guidance">
<output>
## Brownfield Analysis Complete! 🎉

Your comprehensive brownfield analysis has been saved to:
`{output_folder}/brownfield-analysis-{project_name}-{date}.md`

### Next Steps:

1. **Review the Analysis Report**
   - Share with your team
   - Discuss key findings and priorities
   - Validate technical debt assessment

2. **Address Critical Issues First**
   - Review Phase 1 items in the refactoring roadmap
   - Fix security vulnerabilities immediately
   - Resolve blocking technical debt

3. **Ready for Planning?**
   - You can now run `workflow plan-project` or `workflow prd`
   - The brownfield analysis will inform your planning
   - New features can be designed with existing architecture in mind

4. **Consider Running:**
   - `workflow testarch-trace` - Map requirements to existing tests
   - `workflow testarch-framework` - Set up test infrastructure if missing
   - `workflow solution-architecture` - Design new features with brownfield context

### Key Findings Summary:
{executive_summary}

Would you like guidance on any specific next steps?
</output>
</step>

</workflow>

