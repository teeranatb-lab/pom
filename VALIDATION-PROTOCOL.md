# OLGM 512 + CANTI — Scientific Validation Protocol v1.0

**Origin / Author:** Teeranat Butda  
**Version:** 1.0  
**Date:** 17 September 2026

## Principle

The framework must have a genuine opportunity to fail.

The protocol therefore defines **failure before execution**, not after observing the result.

> **Define the failure boundary, not the path.**

## Minimal protocol

### 1. Intent Lock
State the target clearly enough that success and failure can be evaluated.

### 2. Pre-declared win / loss conditions
Before running the test, define:
- what counts as success,
- what counts as failure,
- what counts as inconclusive.

### 3. No post-hoc rescue
After the result is known:
- do not move the goalposts,
- do not reinterpret failure as success,
- do not silently exclude inconvenient cases.

### 4. Preserve provenance
Record:
- prompt / task / context,
- model or system configuration,
- relevant multimodal inputs,
- declared intent,
- declared criteria,
- output / action,
- observed result,
- failure or success status,
- corrections or interventions.

### 5. Baseline comparison
Where possible, compare with a suitable baseline workflow or model under materially equivalent conditions.

### 6. Stress conditions
Increase difficulty using:
- ambiguity,
- incomplete information,
- conflicting evidence,
- adversarial inputs,
- multimodal inputs,
- time pressure,
- long-context intent retention,
- dynamic information appearing during execution.

### 7. Honest conclusion
Repeated success supports only the tested scope.

Preferred wording:

> **No failure was observed under the tested conditions.**

Do not convert this into a universal claim that failure is impossible.

## Candidate metrics

Metrics may be used where useful, but they are not mandatory constraints on internal reasoning.

Possible measures:
- Intent Fidelity
- Successful Closure Rate
- Time to Closure
- Unnecessary Branching / Search
- Provenance Completeness
- Recovery after new information
- Human intervention required
- Failure transparency

## CANTI execution rule

When an action is already necessary and preserves future choices, execution may begin before the final answer is complete.

> **Do not wait for the final answer when a necessary action is already known.**

## Accountability

The system may recommend or execute within delegated authority. Final accountability follows actual decision authority and delegation provenance.
