---
name: 'step-02-generate-pipeline'
description: 'Generate CI pipeline configuration'
nextStepFile: './step-03-configure-quality-gates.md'
outputFile: '{test_artifacts}/ci-pipeline-progress.md'
---

# Step 2: Generate CI Pipeline

## STEP GOAL

Create platform-specific CI configuration with test execution, sharding, burn-in, and artifacts.

## MANDATORY EXECUTION RULES

- 📖 Read the entire step file before acting
- ✅ Speak in `{communication_language}`

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

## 1. Resolve Output Path and Select Template

Determine the pipeline output file path based on the detected `ci_platform`:

| CI Platform      | Output Path                                 | Template File                                       |
| ---------------- | ------------------------------------------- | --------------------------------------------------- |
| `github-actions` | `{project-root}/.github/workflows/test.yml` | `{installed_path}/github-actions-template.yaml`     |
| `gitlab-ci`      | `{project-root}/.gitlab-ci.yml`             | `{installed_path}/gitlab-ci-template.yaml`          |
| `jenkins`        | `{project-root}/Jenkinsfile`                | `{installed_path}/jenkins-pipeline-template.groovy` |
| `azure-devops`   | `{project-root}/azure-pipelines.yml`        | `{installed_path}/azure-pipelines-template.yaml`    |
| `harness`        | `{project-root}/.harness/pipeline.yaml`     | `{installed_path}/harness-pipeline-template.yaml`   |
| `circle-ci`      | `{project-root}/.circleci/config.yml`       | _(no template; generate from first principles)_     |

Use templates from `{installed_path}` when available. Adapt the template to the project's `test_stack_type` and `test_framework`.

---

## 2. Pipeline Stages

Include stages:

- lint
- test (parallel shards)
- burn-in (flaky detection)
- report (aggregate + publish)

---

## 3. Test Execution

- Parallel sharding enabled
- CI retries configured
- Capture artifacts (HTML report, JUnit XML, traces/videos on failure)
- Cache dependencies (language-appropriate: node_modules, .venv, .m2, go module cache, NuGet, bundler)

Write the selected pipeline configuration to the resolved output path from step 1. Adjust test commands based on `test_stack_type` and `test_framework`:

- **Frontend/Fullstack**: Include browser install, E2E/component test commands, Playwright/Cypress artifacts
- **Backend (Node.js)**: Use `npm test` or framework-specific commands (`vitest`, `jest`), skip browser install
- **Backend (Python)**: Use `pytest` with coverage (`pytest --cov`), install via `pip install -r requirements.txt` or `poetry install`
- **Backend (Java/Kotlin)**: Use `mvn test` or `gradle test`, cache `.m2/repository` or `.gradle/caches`
- **Backend (Go)**: Use `go test ./...` with coverage (`-coverprofile`), cache Go modules
- **Backend (C#/.NET)**: Use `dotnet test` with coverage, restore NuGet packages
- **Backend (Ruby)**: Use `bundle exec rspec` with coverage, cache `vendor/bundle`

---

### 4. Save Progress

**Save this step's accumulated work to `{outputFile}`.**

- **If `{outputFile}` does not exist** (first save), create it with YAML frontmatter:

  ```yaml
  ---
  stepsCompleted: ['step-02-generate-pipeline']
  lastStep: 'step-02-generate-pipeline'
  lastSaved: '{date}'
  ---
  ```

  Then write this step's output below the frontmatter.

- **If `{outputFile}` already exists**, update:
  - Add `'step-02-generate-pipeline'` to `stepsCompleted` array (only if not already present)
  - Set `lastStep: 'step-02-generate-pipeline'`
  - Set `lastSaved: '{date}'`
  - Append this step's output to the appropriate section of the document.

Load next step: `{nextStepFile}`

## 🚨 SYSTEM SUCCESS/FAILURE METRICS:

### ✅ SUCCESS:

- Step completed in full with required outputs

### ❌ SYSTEM FAILURE:

- Skipped sequence steps or missing outputs
  **Master Rule:** Skipping steps is FORBIDDEN.
