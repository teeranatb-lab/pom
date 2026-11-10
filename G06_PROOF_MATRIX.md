> Historical v0.7.0 G06 evidence only. See TEST_CAPTURE.json and S10_RELEASE_REPORT.json for v0.8.0.

# OLGM v0.7.0 — G-06 Proof Matrix (10 Nov 2026)

Baseline tested: earlier v0.6 local runtime 66 PASS / 2 SKIPPED; v0.7 includes G06 experimental additions. The current local test runs are recorded in `G06_CORE_TEST_OUTPUT.txt` (82 pass, 2 skip), `G06_SOURCE_TEST_OUTPUT.txt` (2 pass), and `G06_LOCAL_PROOF.json` (source hashes at report generation; not independently signed).

| Scope | Mechanism | Local proof | Limitation |
| --- | --- | --- | --- |
| G06-01 Gap detection | AST NotImplementedError scan and exact-allowlist unsupported intent detection | Test for unknown intents and template refusal | Does not discover arbitrary semantic gaps |
| G06-02 Code proposal | Regenerable 2-file method routing patch + original SHA256 and unified diff | Real `compare` proposed and verified | Does not synthesize novel algorithmic Python code |
| G06-03 Sandbox regression | Trusted-source copy; baseline, patched and new-route checks | Baseline/patched pytest results | Copied directory is **not** OS/container isolation |
| G06-04 Approval | CANTI source_apply + Ed25519 per-patch receipt, signed digest and expiry | Missing grant and tampered receipt refused | Local key enrollment is not real-world Origin authentication |
| G06-05 Code apply | Local guarded write, safe path allowlist, optimistic hash, backup, post-apply regression | Real apply on copied repository | Multi-file writes are not atomic as one transaction |
| G06-06 Rollback | Separate signed one-time rollback receipt; backup integrity check | Real rollback tested; original methods restored | Crash recovery and hostile OS not certified |
| G06-07 Genetic programming | Mutation, crossover, tournament, bounded executable primitives | Multi-generation benchmark actual run | Small, human-specified symbolic domain |
| G06-08 Structural growth | Plateau within same intent → primitive composition + semantic equivalence | 6 macros added in 30 cycles | Macros do not create novel expressive power; no added score lift shown |
| G06-09 Curriculum & adversarial | Generate counterexamples against trusted oracle; disjoint train/validation/final test | Counterexample and no-leak tests | Synthetic oracle, not external observations |
| G06-10 Pareto, meta-transfer, memory | Pareto accuracy/cost/complexity, cross-intent starts, pointer memory | Tests of tradeoff, transfer and rehydrate | Transfer must re-validate against recipient domain |
| G06-11 Persistence/audit | Append-only local AuditChain, state commit digest | Tamper and resumption tests | A same-host attacker can tamper with unanchored file and DB |
| G06-12 Release S-10 | Fail-closed gate `S10-17` | Test refuses self-certification | NOT PASSED independently |

## Measured 30-generation synthetic demonstration

- Initial primitive vocabulary: 9; at end: 15; added composites: 6.
- Six human-written reference tasks; 30 training cycles round-robin.
- Holdout mean accuracy baseline identity operator: 0.00000; selected pipelines: 1.00000.
- All six tasks reached 1.00000 before composite growth; **zero extra accuracy gain demonstrated from the six new macros**.
- No model weights changed. No live Ollama, OpenAI model or external source was involved.
- NO GENERALIZATION claim beyond the documented fixed deterministic numeric transformation task family.

## Operational safeguards

- Treat Origin authority, CANTI local grant, and Ed25519 key identity enrollment as separate boundaries. Never fabricate a signature or self-approve a code mutation.
- Do not run code-modification workflow against a production directory, hosted site, master Canonical or Archive.
- Preserve previous version source files and hashes; update only trusted experimental copies.
- Mechanism smoke tests are not scientific validation nor legal/security certification.
