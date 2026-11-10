# OLGM Ultimate v0.8 — Thai/Sovereign traceability

Status: **LOCAL CODE LEVEL ONLY. NOT S-10 RELEASED.**

| Canonical invariant / user requirement | Source component | Test/proof | What is *not* proven |
|---|---|---|---|
| Core 0 conceptual / no agent mutation | `olgm/thai/sovereignty.py`, old Core0 guards | `test_no_origin_impersonation_and_no_outbound` | Actual Origin authentication |
| Protect intellectual sovereignty; Origin's authorship and rights | `OriginPolicy`, `ThaiExampleMemory`, `ThaiLexicon`, signature gate | Signed local test origin, no-approval-before-serving test | Legal title, licensing validity, independent reviewer signoff |
| Append/Inherit/Delta preserves meaning and relationships | `ThaiLexicon`: new approved alias → existing CID | `test_thai_lexicon_links_existing_cid_without_rewriting` | Cross-linguistic identity across large external corpora |
| Thai comprehension | 72 intent categories / 263 surface triggers + normalization | 42 curated developer examples (`THAI_PATTERN_BENCHMARK.json`) | Open-domain Thai comprehension or blind generalization |
| Thai reply with evidence/unknown | `ThaiResponder`, `ThaiMath`, approved examples + `IntegratedRuntime.process(intent_tag='thai')` | Full 16-stage gated trace, denied without CANTI reason grant, local tests and demo | Independent truth verification; dialogue quality outside rules |
| Thai learning | Candidate / approval ledger; exact/Fuzzy high-threshold retrieval | Approval & replay, hash tampering, no-approval tests | LLM weight training, continual unsupervised generalization |
| Write Python | 37 reviewed algorithms, 21 typed composition contracts | Every generated blueprint executed on sample, six typed composition tests | Novel architectural coding or deployment-ready safety |
| Derive code from behavior | `ThaiProgramSynthesizer`, bounded integer grammar | Affine function synthesized from train I/O; disjoint supplied validation | New primitive operators, truly unseen blind benchmarks |
| CANTI execution policy | Explicit `sandbox_write` or `sandbox_train`; source write not automatic | Access-denied, no overwrite, code injection test | Hardened production identity, system isolation |
| Provenance/Audit | SHA256, signed receipts, audit chain | `AuditChain.verify` in demo and unit tests | Independently anchored audit ledger |
| S-10 | S10-18 Thai evaluation; S10-19 coding; S10-20 sovereignty | `test_s10_thai_requirements_do_not_self_pass` | Independent signoff; see `S10_RELEASE_REPORT.json` |

### Key security decisions

1. No normal user message or AI output is allowed to assert that it *is* the Origin. Enrolling a key as local `Origin` is a trust-bootstrap step, not independent confirmation of identity.
2. No default outbound network operation in the Thai subsystems. HTTP endpoint can only bind on loopback and Thai answer route demands a local development token.
3. Both Thai example and alias tables use SQLite append-only triggers and separate signed approval-bound content hashes. Direct in-DB tampering is detected in local tests, but the database owner can remove SQLite triggers; independent external anchors are needed for stronger adversary resistance.
4. Unapproved training examples are never used to answer; they are candidates only. Approved examples remain claims from sources, not independently proven facts.
5. Canonical / Archive are referenced only. Neither the Thai learner nor the code generator writes to their source files or directly changes the production application source.
6. Generated Python comes from reviewed, bounded grammars and is stored under `generated/` after explicit CANTI local-dev permission. Tests are not OS-container isolation or a malware scanner.
7. The demo signer is ephemeral and synthetic. It is not a real Origin signing ceremony, accreditation or ownership proof.

### Release blockers

S10-01 through S10-20 remain blocked until their independent evidence requirements are satisfied, including live language benchmarks, actual human Origin identity verification, adversarial code generation review, policy/security audit, and production environment tests. The result from the developer-curated test set cannot be substituted for those proofs.
