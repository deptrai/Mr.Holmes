# Brownfield Analysis Integration Guide

## Overview

This guide explains how the Brownfield Analysis workflow integrates with other BMM workflows and how to update existing workflows to check for brownfield documentation.

## Integration Points

### 1. Plan-Project Workflow Integration

The `plan-project` workflow should check if the project is brownfield and verify that brownfield analysis has been completed before proceeding.

#### Recommended Update to `instructions-router.md`

Add this check at the beginning of the router logic:

```markdown
<step n="0.5" goal="Check for brownfield project and required analysis">
<action>Ask the user: Is this a new project (greenfield) or an existing project (brownfield)?</action>

<conditional>
  <if condition="brownfield">
    <action>Check if brownfield analysis document exists in {output_folder}</action>
    <action>Look for files matching pattern: brownfield-analysis-*.md</action>
    
    <conditional>
      <if condition="brownfield_analysis_exists">
        <output>✅ Brownfield analysis found. Loading context for planning...</output>
        <action>Load and summarize key findings from brownfield analysis</action>
        <action>Store constraints and considerations for planning phase</action>
        <template-output>brownfield_context</template-output>
      </if>
      <else>
        <output>⚠️ BROWNFIELD PROJECT DETECTED - ANALYSIS REQUIRED</output>
        <output>
This is a brownfield project (existing codebase), but no brownfield analysis was found.

Before planning new features, you must document the existing system by running:

**workflow brownfield-analysis**

This workflow will:
- Document current architecture
- Identify technical debt
- Assess code quality and security
- Create baseline for planning

Would you like to:
1. Run brownfield-analysis workflow now
2. Continue anyway (not recommended)
3. Exit and run analysis manually

Please select an option.
        </output>
        
        <ask>What would you like to do?</ask>
        
        <conditional>
          <if condition="user_selects_1">
            <action>Execute brownfield-analysis workflow</action>
            <action>After completion, resume plan-project workflow</action>
          </if>
          <if condition="user_selects_2">
            <output>⚠️ Proceeding without brownfield analysis. Planning may miss critical constraints.</output>
            <action>Continue with planning workflow</action>
          </if>
          <if condition="user_selects_3">
            <output>Exiting plan-project. Please run: workflow brownfield-analysis</output>
            <action>Exit workflow</action>
          </if>
        </conditional>
      </else>
    </conditional>
  </if>
  <else>
    <output>✅ Greenfield project detected. Proceeding with standard planning.</output>
    <action>Continue with planning workflow</action>
  </else>
</conditional>
</step>
```

### 2. Solution Architecture Integration

The `solution-architecture` workflow should reference brownfield analysis when designing new features for existing systems.

#### Recommended Addition

Add to the architecture workflow instructions:

```markdown
<step n="1.5" goal="Load brownfield context if applicable">
<action>Check if brownfield analysis exists in {output_folder}</action>

<conditional>
  <if condition="brownfield_analysis_exists">
    <action>Load brownfield analysis document</action>
    <action>Extract key architectural constraints:
      - Current architecture patterns
      - Integration points
      - Technical debt to avoid
      - Performance considerations
      - Security requirements
    </action>
    <output>Brownfield context loaded. New architecture will integrate with existing system.</output>
    <template-output>existing_architecture_constraints</template-output>
  </if>
</conditional>
</step>
```

### 3. Test Architecture Workflows Integration

The `testarch-trace` workflow should reference brownfield analysis for baseline test coverage.

#### Recommended Addition

```markdown
<step n="0.5" goal="Load brownfield testing baseline">
<action>Check if brownfield analysis exists</action>

<conditional>
  <if condition="brownfield_analysis_exists">
    <action>Load testing assessment section from brownfield analysis</action>
    <action>Use as baseline for coverage comparison</action>
    <template-output>baseline_coverage</template-output>
  </if>
</conditional>
</step>
```

## Workflow Sequence for Brownfield Projects

### Recommended Flow

```
1. brownfield-analysis          # REQUIRED FIRST STEP
   ↓
2. plan-project                 # Uses brownfield context
   ↓
3. solution-architecture        # Integrates with existing architecture
   ↓
4. testarch-trace              # Maps existing test coverage
   ↓
5. testarch-framework          # Set up/enhance test infrastructure
   ↓
6. create-story                # Begin implementation
   ↓
7. dev-story                   # Execute with brownfield awareness
```

### Alternative Flow (Quick Start)

```
1. brownfield-analysis (Quick)  # 30-minute overview
   ↓
2. plan-project                 # Minimal PRD
   ↓
3. create-story                 # Start implementation
   ↓
4. brownfield-analysis (Standard) # Deeper analysis as needed
```

## Configuration Updates

### workflow.yaml Updates

Add brownfield_analysis as a recommended input to relevant workflows:

```yaml
recommended_inputs:
  - product_brief: "{output_folder}/product-brief.md"
  - brownfield_analysis: "{output_folder}/brownfield-analysis-*.md"  # NEW
```

### Menu Integration

Add to BMad Master menu or relevant agent menus:

```xml
<item cmd="*brownfield" workflow="{project-root}/bmad/bmm/workflows/1-analysis/brownfield-analysis/workflow.yaml">
  Analyze Brownfield Codebase
</item>
```

## Template Variable Integration

### Variables to Extract from Brownfield Analysis

When loading brownfield analysis in other workflows, extract these key variables:

```yaml
brownfield_variables:
  - architecture_overview: "Current system architecture"
  - tech_stack: "Existing technology stack"
  - technical_debt_critical: "Critical technical debt items"
  - integration_points: "System integration points"
  - performance_baseline: "Current performance metrics"
  - security_concerns: "Security issues to address"
  - testing_gaps: "Test coverage gaps"
  - refactoring_priorities: "Top refactoring priorities"
```

### Usage in Templates

In PRD or architecture templates, add sections:

```markdown
## Brownfield Context (if applicable)

### Existing System Overview
{{brownfield_architecture_overview}}

### Integration Constraints
{{brownfield_integration_points}}

### Technical Debt Considerations
{{brownfield_technical_debt_critical}}

### Migration Strategy
{{brownfield_migration_strategy}}
```

## Validation Integration

### Checklist Updates

Add to planning workflow checklists:

```markdown
## Brownfield Validation (if applicable)

- [ ] Brownfield analysis has been completed
- [ ] Existing architecture is documented
- [ ] Technical debt is identified and prioritized
- [ ] Integration points are mapped
- [ ] Migration strategy is defined
- [ ] New features align with existing patterns
- [ ] Refactoring needs are addressed
```

## Agent Integration

### Analyst Agent

Update analyst agent to recommend brownfield analysis:

```xml
<prompt id="recommend-brownfield">
  If the user mentions working with an existing codebase, recommend:
  
  "I notice you're working with an existing codebase. Before we proceed with 
  planning, I recommend running the brownfield analysis workflow to document 
  the current system:
  
  workflow brownfield-analysis
  
  This will help us make informed decisions about new features and avoid 
  common pitfalls when working with legacy code."
</prompt>
```

### PM Agent

Update PM agent to check for brownfield analysis:

```xml
<prompt id="check-brownfield">
  Before creating PRD for brownfield projects:
  
  1. Check if brownfield analysis exists
  2. If not, halt and request analysis
  3. If yes, load and incorporate findings into PRD
  4. Ensure new features align with existing architecture
</prompt>
```

### Architect Agent

Update architect agent to reference brownfield analysis:

```xml
<prompt id="brownfield-architecture">
  When designing architecture for brownfield projects:
  
  1. Load brownfield analysis document
  2. Review existing architecture patterns
  3. Identify integration points
  4. Design new features to complement existing system
  5. Address technical debt in design
  6. Follow strangler fig pattern if major refactoring needed
</prompt>
```

## MCP Tool Integration

### Recommended MCP Tools for Brownfield Analysis

```yaml
mcp_tools:
  - codebase_retrieval: "Semantic code search"
  - grep_search: "Pattern matching"
  - git_tools: "History analysis"
  - context7: "Framework documentation"
  - perplexity: "Best practices research"
  - chrome_devtools: "Runtime analysis (web apps)"
```

### Tool Usage Patterns

```markdown
# Codebase Retrieval
Use for: Understanding architecture, finding patterns, identifying components

# Grep Search
Use for: Finding TODO/FIXME, detecting anti-patterns, reference counting

# Git Tools
Use for: Hotspot analysis, evolution tracking, ownership patterns

# Context7
Use for: Framework best practices, migration guides

# Perplexity
Use for: Architecture patterns, refactoring strategies
```

## Error Handling

### Missing Brownfield Analysis

```markdown
<error-handler type="missing-brownfield-analysis">
  <message>
    ⚠️ Brownfield project detected but no analysis found.
    
    This workflow requires brownfield analysis to proceed safely.
    
    Please run: workflow brownfield-analysis
    
    Or specify this is a greenfield project.
  </message>
  <action>Halt workflow</action>
  <recovery>Offer to run brownfield-analysis workflow</recovery>
</error-handler>
```

### Outdated Brownfield Analysis

```markdown
<warning type="outdated-brownfield-analysis">
  <condition>brownfield_analysis_date > 90_days_ago</condition>
  <message>
    ⚠️ Brownfield analysis is over 90 days old.
    
    Consider running a fresh analysis to capture recent changes:
    workflow brownfield-analysis
    
    Continue with existing analysis? (y/n)
  </message>
</warning>
```

## Testing Integration

### Test Workflow Updates

```markdown
<step n="0" goal="Load brownfield test baseline">
  <action>Check for brownfield analysis</action>
  <action>Load testing assessment section</action>
  <action>Use as baseline for coverage comparison</action>
  <action>Identify gaps to address in new tests</action>
</step>
```

## Documentation Integration

### README Updates

Add to workflow READMEs:

```markdown
## Brownfield Considerations

If working with an existing codebase, run brownfield analysis first:

workflow brownfield-analysis

This provides essential context for [workflow name] and ensures new 
features integrate properly with existing architecture.
```

## Version Control Integration

### Git Workflow

```bash
# After brownfield analysis
git add docs/brownfield-analysis-*.md
git commit -m "docs: add brownfield analysis baseline"

# Reference in PRs
git commit -m "feat: add feature X

Refs: brownfield-analysis-2025-10-08.md
Integration points: API Gateway, Auth Service
Technical debt addressed: None (new feature)
"
```

## Continuous Integration

### CI/CD Checks

```yaml
# .github/workflows/brownfield-check.yml
name: Brownfield Analysis Check

on:
  pull_request:
    paths:
      - 'src/**'
      - 'lib/**'

jobs:
  check-brownfield:
    runs-on: ubuntu-latest
    steps:
      - name: Check for brownfield analysis
        run: |
          if [ ! -f docs/brownfield-analysis-*.md ]; then
            echo "⚠️ No brownfield analysis found"
            echo "Run: workflow brownfield-analysis"
            exit 1
          fi
```

## Summary

### Key Integration Points

1. ✅ **plan-project** - Check and require brownfield analysis
2. ✅ **solution-architecture** - Load brownfield constraints
3. ✅ **testarch workflows** - Use brownfield test baseline
4. ✅ **Agent prompts** - Recommend brownfield analysis
5. ✅ **Templates** - Include brownfield context sections
6. ✅ **Checklists** - Add brownfield validation items

### Implementation Priority

1. **High Priority** - plan-project integration (blocks planning)
2. **Medium Priority** - solution-architecture integration (improves design)
3. **Low Priority** - CI/CD checks (nice to have)

---

**Last Updated:** 2025-10-08  
**Version:** 1.0.0

