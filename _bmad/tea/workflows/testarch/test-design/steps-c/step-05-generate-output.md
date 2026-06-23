---
name: 'step-05-generate-output'
description: 'Generate output documents and validate against checklist'
outputFile: '{test_artifacts}/test-design-epic-{epic_num}.md'
progressFile: '{test_artifacts}/test-design-progress.md'
---

# Step 5: Generate Outputs & Validate

## STEP GOAL

Write the final test-design document(s) using the correct template(s), then validate against the checklist.

## MANDATORY EXECUTION RULES

- 📖 Read the entire step file before acting
- ✅ Speak in `{communication_language}`
- ✅ Use the provided templates and output paths

---

## EXECUTION PROTOCOLS:

- 🎯 Follow the MANDATORY SEQUENCE exactly
- 💾 Record outputs before proceeding
- 📖 Load the next step only when instructed

## CONTEXT BOUNDARIES:

- Available context: config, loaded artifacts, and knowledge fragments
- Focus: this step's goal only
- Limits: do not execute future steps
- Dependencies: prior steps' outputs (if any)

## MANDATORY SEQUENCE

**CRITICAL:** Follow this sequence exactly. Do not skip, reorder, or improvise.

## 1. Select Output Template(s)

### System-Level Mode (Phase 3)

Generate **two** documents:

- `{test_artifacts}/test-design-architecture.md` using `test-design-architecture-template.md`
- `{test_artifacts}/test-design-qa.md` using `test-design-qa-template.md`

### Epic-Level Mode (Phase 4)

Generate **one** document:

- `{outputFile}` using `test-design-template.md`
- If `epic_num` is unclear, ask the user

---

## 2. Populate Templates

Ensure the outputs include:

- Risk assessment matrix
- Coverage matrix and priorities
- Execution strategy
- Resource estimates (ranges)
- Quality gate criteria
- Any mode-specific sections required by the template

---

## 3. Validation

Validate the output(s) against:

- `checklist.md` in this workflow folder
- [ ] CLI sessions cleaned up (no orphaned browsers)
- [ ] Temp artifacts stored in `{test_artifacts}/` not random locations

If any checklist criteria are missing, fix before completion.

---

## 4. Generate BMAD Handoff Document (System-Level Mode Only)

**If this is a system-level test design** (not component/feature level):

1. Copy `test-design-handoff-template.md` to `{test_artifacts}/test-design/{project_name}-handoff.md`
2. Populate all sections from the test design output:
   - Fill TEA Artifacts Inventory with actual paths
   - Extract P0/P1 risks into Epic-Level guidance
   - Map critical test scenarios to Story-Level guidance
   - Build risk-to-story mapping table from risk register
3. Save alongside the test design document

> **Note**: The handoff document is designed for consumption by BMAD's `create-epics-and-stories` workflow. It is only generated for system-level test designs where epic/story decomposition is relevant.

---

## 5. Polish Output

Before finalizing, review the complete output document for quality:

1. **Remove duplication**: Progressive-append workflow may have created repeated sections — consolidate
2. **Verify consistency**: Ensure terminology, risk scores, and references are consistent throughout
3. **Check completeness**: All template sections should be populated or explicitly marked N/A
4. **Format cleanup**: Ensure markdown formatting is clean (tables aligned, headers consistent, no orphaned references)

---

## 6. Completion Report

Summarize:

- Mode used
- Output file paths
- Key risks and gate thresholds
- Any open assumptions

---

### 7. Save Progress

**Save this step's accumulated work to `{progressFile}`.**

- **If `{progressFile}` does not exist** (first save), create it with YAML frontmatter:

  ```yaml
  ---
  stepsCompleted: ['step-05-generate-output']
  lastStep: 'step-05-generate-output'
  lastSaved: '{date}'
  ---
  ```

  Then write this step's output below the frontmatter.

- **If `{progressFile}` already exists**, update:
  - Add `'step-05-generate-output'` to `stepsCompleted` array (only if not already present)
  - Set `lastStep: 'step-05-generate-output'`
  - Set `lastSaved: '{date}'`
  - Append this step's output to the appropriate section of the document.

## 🚨 SYSTEM SUCCESS/FAILURE METRICS:

### ✅ SUCCESS:

- Step completed in full with required outputs

### ❌ SYSTEM FAILURE:

- Skipped sequence steps or missing outputs
  **Master Rule:** Skipping steps is FORBIDDEN.
