---
name: 'step-03-quality-evaluation'
description: 'Orchestrate parallel quality dimension checks (4 subprocesses)'
nextStepFile: './step-03f-aggregate-scores.md'
---

# Step 3: Orchestrate Parallel Quality Evaluation

## STEP GOAL

Launch 4 parallel subprocesses to evaluate test quality dimensions:

- Determinism
- Isolation
- Maintainability
- Performance

Coverage is intentionally excluded from this workflow and handled by `trace`.

## MANDATORY EXECUTION RULES

- 📖 Read the entire step file before acting
- ✅ Speak in `{communication_language}`
- ✅ Launch four subprocesses in PARALLEL
- ✅ Wait for all subprocesses to complete
- ❌ Do NOT evaluate quality sequentially (use subprocesses)
- ❌ Do NOT proceed until all subprocesses finish

---

## EXECUTION PROTOCOLS:

- 🎯 Follow the MANDATORY SEQUENCE exactly
- 💾 Wait for subprocess outputs
- 📖 Load the next step only when instructed

## CONTEXT BOUNDARIES:

- Available context: test files from Step 2, knowledge fragments
- Focus: subprocess orchestration only
- Limits: do not evaluate quality directly (delegate to subprocesses)

---

## MANDATORY SEQUENCE

### 1. Prepare Subprocess Inputs

**Generate unique timestamp:**

```javascript
const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
```

**Prepare context for all subprocesses:**

```javascript
const subprocessContext = {
  test_files: /* from Step 2 */,
  knowledge_fragments_loaded: ['test-quality'],
  timestamp: timestamp
};
```

---

### 2. Launch 4 Parallel Quality Subprocesses

**Subprocess A: Determinism**

- File: `./step-03a-subprocess-determinism.md`
- Output: `/tmp/tea-test-review-determinism-${timestamp}.json`
- Status: Running in parallel... ⟳

**Subprocess B: Isolation**

- File: `./step-03b-subprocess-isolation.md`
- Output: `/tmp/tea-test-review-isolation-${timestamp}.json`
- Status: Running in parallel... ⟳

**Subprocess C: Maintainability**

- File: `./step-03c-subprocess-maintainability.md`
- Output: `/tmp/tea-test-review-maintainability-${timestamp}.json`
- Status: Running in parallel... ⟳

**Subprocess D: Performance**

- File: `./step-03e-subprocess-performance.md`
- Output: `/tmp/tea-test-review-performance-${timestamp}.json`
- Status: Running in parallel... ⟳

---

### 3. Wait for All Subprocesses

```
⏳ Waiting for 4 quality subprocesses to complete...
✅ All 4 quality subprocesses completed successfully!
```

---

### 4. Verify All Outputs Exist

```javascript
const outputs = ['determinism', 'isolation', 'maintainability', 'performance'].map(
  (dim) => `/tmp/tea-test-review-${dim}-${timestamp}.json`,
);

outputs.forEach((output) => {
  if (!fs.existsSync(output)) {
    throw new Error(`Subprocess output missing: ${output}`);
  }
});
```

---

### 5. Performance Report

```
🚀 Performance Report:
- Execution Mode: PARALLEL (4 subprocesses)
- Total Elapsed: ~max(all subprocesses) minutes
- Sequential Would Take: ~sum(all subprocesses) minutes
- Performance Gain: ~60-70% faster!
```

---

### 6. Proceed to Aggregation

Pass the same `timestamp` value to Step 3F (do not regenerate it). Step 3F must read the exact temp files written in this step.

Load next step: `{nextStepFile}`

The aggregation step (3F) will:

- Read all 4 subprocess outputs
- Calculate weighted overall score (0-100)
- Aggregate violations by severity
- Generate review report with top suggestions

---

## EXIT CONDITION

Proceed to Step 3F when:

- ✅ All 4 subprocesses completed successfully
- ✅ All output files exist and are valid JSON
- ✅ Performance metrics displayed

**Do NOT proceed if any subprocess failed.**

---

## 🚨 SYSTEM SUCCESS METRICS

### ✅ SUCCESS:

- All 4 subprocesses launched and completed
- Output files generated and valid
- Parallel execution achieved ~60% performance gain

### ❌ FAILURE:

- One or more subprocesses failed
- Output files missing or invalid
- Sequential evaluation instead of parallel

**Master Rule:** Parallel subprocess execution is MANDATORY for performance.
