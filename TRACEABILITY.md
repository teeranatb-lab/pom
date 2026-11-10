# OLGM Ultimate integrated runtime — traceability (v0.4.0)

## Truthfulness convention

- `TESTED`: runnable code paths observed in isolated code-level / HTTP integration tests.
- `PARTIAL`: implemented a bounded mechanism but the full canonical contract is **not** met.
- `NOT TESTED`: actual model, GPU, outside identity/signing service, third-party evidence, or production target not exercised.
- `NOT IMPLEMENTED`: requested features have no working adapter.
- **NOT CERTIFIED**: no stage or code-level PASS authorizes S-10 production acceptance.

## Contract checkpoints

| Checkpoint | What actually runs | Independent evidence / remaining gap | Status |
|---|---|---|---|
| F-00 Core 0 | Prevents runtime access; audit of refused attempt | External Origin declaration/authority identity cannot be inferred from DB | TESTED mechanism, unverified external policy |
| F-01 Origin Identity | Public-key enrollment and Ed25519 signed ticket checking | Real-world Origin identity proof, trusted enrollment governance | PARTIAL |
| F-02 Origin Intent | Immutable reference/fingerprint; no Core0 content | Sign and independently authenticate external declaration | PARTIAL |
| F-03 Five Axes | Ethics/morality/justice/compassion/truthfulness individual statuses; FAIL cannot average out | Actual policy evaluators and validation are not present | PARTIAL |
| F-04 User Intent | Append-only initial intent and authorized, version-checked changes | Live identity authentication | TESTED mechanism |
| X-00 Meaning Space | SQLite CID registry, unique 3D coords, incremental placement, typed relation graph, path expansion | Semantic accuracy of locations and truth of stored edges | PARTIAL |
| OP-01 Intent Lock | Stable hash, revision, current-intent lock | Distributed identity | TESTED |
| OP-02 Inherit | Canonical source reference, append/inherit/delta ledger, tamper check | Original reference hash authenticity, sign-off | TESTED mechanism, partial trust |
| OP-03 Evidence | Epistemic classes, claim/substring source links, V1–V7 mechanical checks and OTFA three-plane | Independent credibility, entailment, temporal validity and theory proof | PARTIAL |
| OP-04 Resonance/reason | Graph methods 1+18 structural handlers, alternate paths, conflict detection, bounded curiosity | Real model observation and independent reasoning accuracy | PARTIAL |
| OP-05 Latest Proof | Rejects stale hash and records root reentry | Policy-authority attestation | TESTED |
| OP-06 Verified Decision | Ten-dimensional quality gate and Logical Gravity; unknowns preserved | Production verified-decision proof, ethical validators, independent review | PARTIAL / action blocked |
| OP-07 CANTI | Sandbox-only 7-stage controller, explicit grants, approval, nonce receipt, exact scope | General tools, actual side effects, hardened authenticated authority | TESTED sandbox, NOT IMPLEMENTED production |
| OP-08 Observe effects | Reads durable note/counter effects and records receipt | Real-world device/tool/contract effect inspection | TESTED sandbox only |
| OP-09 Audit | Concurrent SQLite SHA256 hash-chain, signed local anchors, receipts | Externally independent immutable timestamps/anchor service | PARTIAL |
| OP-10 Return-compare | Compares latest hash against lock and logs closure | Measured real-world outcome quality | TESTED mechanism, incomplete proof |

## Canonical major modules

| Module | Implemented evidence | Unimplemented or unverified part |
|---|---|---|
| Origin sovereignty | Core0 conceptual boundary; immutable external refs; signed ticket validator | Verified identity of real Origin; no Core0 programmatic entry by design |
| Shared Semantic State / OLTM | Typed graph, aliases via core surface forms, revision histories, category-independent CIDs, neighbor resonance | Full OLTM Lite/Full adaptive indexing, learned semantics, self-improving embedding space |
| MRRE/field lock | Graph 3D positions, graph hops, context/time filters, path candidates | Physical field theory, learned resonance calibration |
| Observation F-01/T06 | Pluggable Ollama/API backends, schema and provenance validation, candidate proposal, queue | LIVE model not tested; original anti-pattern semantic equivalence benchmark not completed |
| Logical Gravity | Hard-failure rejection, alternatives and rejected-route reasons preserved | Calibrated utility model, independently validated path scoring |
| OTFA-100 | Conservative three-plane (empirical, theoretical, relational) plus V1–V7 mechanical checks | Empirical independent source validation, V5 independence, V7 temporal policies, V1–V7 certification |
| Quality/5 values | Transparent gate statuses; no false PASS from missing checks | Automated five-axis validation and final production gate |
| CANTI | sandbox write scopes, human approval reference, optional Ed25519 signature, expiry/nonces, persistent idempotency | Real-world action targets and verified decision voucher issuance |
| Episodic Memory | Pointer-only episode and rehydrate (v0.3.1 retained) | Long-term retention policy, privacy/consent lifecycle |
| Continual observer | SQLite queue and bounded manual worker-step | Always-on OS service, unattended live model loop not tested |
| Curiosity | Generates a small capped number of gap/conflict/evidence questions | Autonomous research without authorization prohibited |
| Methods | All 1+18 names have bounded graph operators; selection by intent | This is not general human-level reasoning; scientific calibration pending |
| Audit / Provenance | SHA256 chain, optional HMAC anchors, Ed25519 approval receipts, timestamps | Trusted external WORM anchor, hardware-backed private-key custody |
| Model training | Optional PEFT Trainer with actual tensors & artifact manifest | T17 real GPU/model training and independent before/after holdout NOT TESTED |
| Evaluation | Exact match, BM25 retrieval, Recall@5/20, nDCG@10, adversarial integrity tests | Blind large-scale set, calibration, ablations and cost/latency production benchmark |
| GIS BigMap | pyproj WGS84→Indian1975 zone48 point/CSV conversion | Survey validation, DWG/DXF, BigMap direct tool automation |
| Multimodal | Fingerprint and basic image/WAV/plain-text metadata ingest | Image/audio/video meaning extraction and corpus understanding |
| Dictionary | TSV license/source-gated import as candidates | Full licensed dictionary providers, lexical sense disambiguation |
| External web research | Explicit opt-in injectable provider; source registry under CANTI | Actual live provider connector and external fact validation |
| HTTP API | Loopback JSON process/ask/observe/experience; token check | Hardened auth, TLS, multi-user, throttling, LAN/Internet deployment |
| Procurement application integration | Architecture can be reused as governed AI officer | Procurement-specific end-to-end workflows are separate and NOT IMPLEMENTED in this OLGM runtime |

## Acceptance matrix and nonclaims

- `T06`: synthetic model contract tested; **LIVE / independent semantic generalization NOT TESTED**.
- `T15`: episodic pointer round trip **code-level TESTED**.
- `T17`: optional training mechanism implemented; **weight training and blind benchmark NOT RUN**.
- `T19`: no-evidence OTFA fail-closed **code-level TESTED**; real independent claim verification NOT TESTED.
- `T20`: detects mutation/chain breaks in code-level tests; rollback to earlier unanchored complete DB copy is still not independently detectable.
- `T22`: deterministic arithmetic 1+2=3 tested.
- `S-10`: **NOT PASSED** (missing independent identity, evidence, external model/training, source audit, production integrations).
- `API`: real local HTTP test verifies 401 without token and processing response after valid token.

No tests touched a remote service, model API, the canonical PDF, athena-30.com or an external machine.

## Delta v0.7.0 — G-06 source improvement + bounded symbolic learner

Implementation additions: `olgm/improve.py`, `olgm/gaps.py`, `olgm/proposals.py`, `olgm/sandbox.py`, and `olgm/self_learn/*.py`; CLI `g06-*` and `selflearn-v2-*`; demo and tests. See `docs/G06_PROOF_MATRIX.md` for code-level evidence and limitations. S-10 now includes `S10-17`, which is `BLOCKED` in local-only evaluation and **cannot be passed by these unit tests or claims alone**. Original v0.4 history is retained for compatibility; current authoritative local results are `docs/G06_ALL_TEST_OUTPUT.txt` and `docs/G06_DEMO_REPORT.json`.
