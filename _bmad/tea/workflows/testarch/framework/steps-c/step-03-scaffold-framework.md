---
name: 'step-03-scaffold-framework'
description: 'Create directory structure, config, fixtures, factories, and sample tests'
nextStepFile: './step-04-docs-and-scripts.md'
knowledgeIndex: '{project-root}/_bmad/tea/testarch/tea-index.csv'
outputFile: '{test_artifacts}/framework-setup-progress.md'
---

# Step 3: Scaffold Framework

## STEP GOAL

Generate the test directory structure, configuration files, fixtures, factories, helpers, and sample tests.

## MANDATORY EXECUTION RULES

- 📖 Read the entire step file before acting
- ✅ Speak in `{communication_language}`
- ✅ Apply knowledge base patterns where required

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

## 1. Create Directory Structure

Use `{detected_stack}` from Step 1 to determine directory layout.

**If {detected_stack} is `frontend` or `fullstack`:**

- `{test_dir}/e2e/`
- `{test_dir}/support/fixtures/`
- `{test_dir}/support/helpers/`
- `{test_dir}/support/page-objects/` (optional)

**If {detected_stack} is `backend` or `fullstack`:**

Create the idiomatic test directory for the detected language:

- **Python (pytest)**: `tests/` with `conftest.py`, `tests/unit/`, `tests/integration/`, `tests/api/`
- **Java/Kotlin (JUnit)**: `src/test/java/` mirroring `src/main/java/` package structure, with `unit/`, `integration/`, `api/` sub-packages
- **Go**: `*_test.go` files alongside source files (Go convention), plus `testdata/` for fixtures
- **C#/.NET (xUnit)**: `tests/` project with `Unit/`, `Integration/`, `Api/` directories
- **Ruby (RSpec)**: `spec/` with `spec/unit/`, `spec/integration/`, `spec/api/`, `spec/support/`
- **Rust**: `tests/` for integration tests, inline `#[cfg(test)]` modules for unit tests

---

## 2. Generate Framework Config

**If {detected_stack} is `frontend` or `fullstack`:**

Create `playwright.config.ts` or `cypress.config.ts` with:

- **Timeouts**: action 15s, navigation 30s, test 60s
- **Base URL**: env fallback (`BASE_URL`)
- **Artifacts**: retain-on-failure (trace/screenshot/video)
- **Reporters**: HTML + JUnit + console
- **Parallelism**: enabled (CI tuned)

Use TypeScript if `use_typescript: true`.

**If {detected_stack} is `backend` or `fullstack`:**

Create the idiomatic test config for the detected framework:

- **pytest**: `pyproject.toml` `[tool.pytest.ini_options]` or `pytest.ini` with markers, test paths, coverage settings
- **JUnit**: `build.gradle`/`pom.xml` test configuration with JUnit 5 dependencies, Surefire/Failsafe plugins
- **Go test**: no config file needed (Go convention); optionally create `Makefile` test targets
- **xUnit**: `.csproj` test project with xUnit and coverlet dependencies
- **RSpec**: `.rspec` config file with `spec_helper.rb` and `rails_helper.rb` (if Rails)

---

## 3. Environment Setup

Create `.env.example` with `TEST_ENV`, `BASE_URL`, `API_URL`.

**Stack-conditional environment files:**

**If {detected_stack} is `frontend` or `fullstack` (Node.js):**

- `.nvmrc` using current LTS Node (prefer Node 24+)

**If {detected_stack} is `backend`:**

Create the idiomatic version file for the detected language:

- **Python**: `.python-version` with current stable Python (prefer 3.12+)
- **Java**: `.java-version` or `JAVA_HOME` documentation in `.env.example`
- **Go**: Go version is already in `go.mod` (no additional file needed)
- **C#/.NET**: `global.json` with SDK version if not already present
- **Ruby**: `.ruby-version` with current stable Ruby

---

## 4. Fixtures & Factories

Read `{config_source}` and use `{knowledgeIndex}` to load fragments based on `config.tea_use_playwright_utils`:

**If Playwright Utils enabled:**

- `overview.md`, `fixtures-composition.md`, `auth-session.md`, `api-request.md`, `burn-in.md`, `network-error-monitor.md`, `data-factories.md`
- Recommend installing `@seontechnologies/playwright-utils`

**If disabled:**

- `fixture-architecture.md`, `data-factories.md`, `network-first.md`, `playwright-config.md`, `test-quality.md`

Implement:

- Fixture index with `mergeTests`
- Auto-cleanup hooks
- Faker-based data factories with overrides

---

## 5. Sample Tests & Helpers

**If {detected_stack} is `frontend` or `fullstack`:**

Create example tests in `{test_dir}/e2e/` demonstrating:

- Given/When/Then format
- data-testid selector strategy
- Factory usage
- Network interception pattern (if applicable)

**If {detected_stack} is `backend` or `fullstack`:**

Create example tests in the idiomatic location for the detected language:

- **Python**: `tests/test_example.py` with pytest fixtures, parametrize, and factory usage
- **Java**: `src/test/java/.../ExampleTest.java` with JUnit 5 annotations, `@BeforeEach` setup
- **Go**: `example_test.go` alongside source with table-driven tests and `testify` assertions
- **C#/.NET**: `tests/ExampleTests.cs` with xUnit `[Fact]`/`[Theory]` and fixture injection
- **Ruby**: `spec/example_spec.rb` with RSpec `describe`/`context`/`it` and factory_bot

Create helpers for:

- API clients (if needed)
- Network utilities (frontend/fullstack only)
- Auth helpers
- Test data factories (language-idiomatic patterns)

---

### 6. Save Progress

**Save this step's accumulated work to `{outputFile}`.**

- **If `{outputFile}` does not exist** (first save), create it with YAML frontmatter:

  ```yaml
  ---
  stepsCompleted: ['step-03-scaffold-framework']
  lastStep: 'step-03-scaffold-framework'
  lastSaved: '{date}'
  ---
  ```

  Then write this step's output below the frontmatter.

- **If `{outputFile}` already exists**, update:
  - Add `'step-03-scaffold-framework'` to `stepsCompleted` array (only if not already present)
  - Set `lastStep: 'step-03-scaffold-framework'`
  - Set `lastSaved: '{date}'`
  - Append this step's output to the appropriate section of the document.

Load next step: `{nextStepFile}`

## 🚨 SYSTEM SUCCESS/FAILURE METRICS:

### ✅ SUCCESS:

- Step completed in full with required outputs

### ❌ SYSTEM FAILURE:

- Skipped sequence steps or missing outputs
  **Master Rule:** Skipping steps is FORBIDDEN.
