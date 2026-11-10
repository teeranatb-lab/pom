# OLGM Ultimate — S-10 Production Hardening v0.9.0

**RELEASE STATUS: NOT PASSED / NOT DEPLOYED.** This release does not and cannot self-certify the 20 external S-10 requirements. X-admin was **offline** when checked; no production deployment, independently authenticated Origin approval, live T06, T17 or independent security review has occurred.

## New in v0.9.0

- `OLGM_ENV=production` blocks all developer privilege grants, dev public-key enrollment, privileged source/data mutations, canonical init and developer CLI approval/execution. An externally authenticated production identity-and-write gateway is **not** yet implemented; preflight therefore blocks release. Informational operations may still create audit/intent records and must not be exposed to untrusted callers.
- Loopback HTTP server in production **requires** a varied 32+-character token; production HTTP denies direct observation/experience writes and refuses `enable_model` (Origin data leakage control). This is **not** sufficient for public/LAN deployment: configure and independently test reverse-proxy TLS, IdP/RBAC and rate-limiting before access.
- `python runtime.py production-preflight --output s10_preflight.json` validates SQLite integrity, audit chain, checkpoint ledger, canonical ledger, local dev grants, listener restrictions and SQLite backup/restore on a *temporary isolated copy*, alongside explicit external proof blockers.
- S-10 evaluation returns `FAIL` rather than throwing on corrupted/unreadable databases.
- G-06 source patch assessment runs a bounded governance/route regression subset in copied repository; a separate full suite remains mandatory for any release acceptance.
- 20-gate matrix in `docs/S10_V09_ACCEPTANCE_MATRIX.json` and step-by-step Thai runbook in `docs/S10_PRODUCTION_RUNBOOK_TH.md`.

**Code-level test evidence:** `docs/S10_V09_TEST_CAPTURE.json` — **175 PASSED, 2 SKIPPED, 0 FAILED**, captured using the exact source hash and real subprocess `pytest` output. `docs/S10_V09_LOCAL_GATE_REPORT.json` confirms `NOT_PASSED` with 20/20 external gates blocked. Local synthetic DB preflight is in `docs/S10_V09_LOCAL_PREFLIGHT.json`; it is not an X-admin run.

### How to check (isolated STAGING first)

Windows PowerShell (run from project root):
```powershell
python -m pip install -r requirements-dev.txt
$env:OLGM_DB = '.\staging_olgm.db'
$env:OLGM_ENV = 'production'
# Provide a random secret from a separate trusted secret manager, not this README.
# Obtain a high-entropy token from a trusted secret manager outside this script.
# For a local non-production test, enter without echo:
$secure = Read-Host 'Enter staging secret' -AsSecureString
$env:OLGM_HTTP_TOKEN = [System.Net.NetworkCredential]::new('', $secure).Password
python runtime.py production-preflight --output staging_preflight.json
python runtime.py s10-capture --output staging_tests.json
python runtime.py s10-evaluate --test-capture staging_tests.json --output staging_gate.json
```

`production-preflight` and `s10-evaluate` intentionally exit nonzero while S-10 is blocked. Do not disable gates to obtain exit code zero. Re-check all evidence on real X-admin after it reconnects. No provided command modifies a master Canonical or Archive.

---

# OLGM Ultimate — Sovereign Thai Learning & Code Synthesis v0.8.0

**สถานะ:** Working code-level research prototype; **NOT PRODUCTION CERTIFIED**, **S-10 NOT PASSED**.  
**ต้นทางการจัดขอบเขต:** OLGM Ultimate Sovereign Semantic & Factual Master Canonical (9 Nov 2026), retained as an **external reference** only. This repository neither embeds nor mutates Core 0, the original Master Canonical document, or the Archive.


## v0.8.0: Thai language, Code Generation, Sovereign Meaning Space

This release adds a **local-only, deterministic Thai layer** to the previous OLGM/G-06 runtime.
It does not replace a large language model; it does not claim open-domain Thai
fluency, autonomous source rewriting, or legal certification.

| New capability | Implemented mechanism | Limit |
|---|---|---|
| Thai intent routing | 72 inspectable intent patterns / 263 Thai–English triggers | Lexical detection, not general comprehension |
| Thai replies | Rule-based replies, bounded arithmetic, cited local learning retrieval | Unknown/ambiguous questions abstain |
| Thai memory | Append-only *application* proposals; origin/source/license; Ed25519 Origin-authority-key approval + CANTI; content hash | Human/signed local approval required; key ownership is not independently authenticated |
| Thai Meaning Space lexicon | Human-approved Thai aliases map to **existing stable CIDs** | Does not update Core/Edge or prove external facts |
| Code generation | 37 audited Python algorithm blueprints | No open-ended new architecture or unreviewed code execution |
| Structural code composition | 21 type-contracted patterns can form 2–6 step pipelines | Static contracts, limited input types; does not certify general code safety |
| I/O-driven program synthesis | Bounded search over integer primitive expression grammar | Fixed operators and depth ≤5, no general programming-language synthesis |
| Sovereignty controls | Core0/Origin/Canonical protected resources; no outgoing network in Thai modules; signed authorizations for promotion | Local policy model, not a substitute for external trust or security audit |
| S-10 | Three additional blocking gates S10-18/19/20 (20 total) | `NOT_PASSED` pending independent evidence |

### Quick start: Thai answer, intent recognition, program writing

```bash
python -m pip install -r requirements-dev.txt
python runtime.py init
python runtime.py thai-patterns
python runtime.py thai-detect "ตรวจรับพัสดุภาครัฐ"
python runtime.py thai-answer "หนึ่ง บวก สอง"  # lightweight local-only, no full checkpoint trace
python runtime.py grant-dev reason agent.ask --ttl 300
python runtime.py thai-run "หนึ่ง บวก สอง" --origin-ref local-origin-declaration
python runtime.py thai-run "อธิปไตยทางปัญญา" --origin-ref local-origin-declaration
python runtime.py thai-code-list
python runtime.py thai-code-request "เขียนโค้ดหาผลรวมตัวเลข" --origin-ref local-origin-declaration
python runtime.py thai-code-pipeline unique sort --origin-ref local-origin-declaration
```

To save the reviewed source to `generated/example.py` (not to the original
project, canonical, or system Python environment), explicitly authorize the
local-development sandbox write:

```bash
python runtime.py grant-dev sandbox_write thai.generated --ttl 300
python runtime.py thai-code sum --origin-ref local-origin-declaration --save example_sum.py
```

For example-driven bounded synthesis, provide local examples as JSON:

```json
{"train":[[0,1],[1,3],[2,5],[3,7]],"validation":[[6,13],[8,17]]}
```

```bash
python runtime.py thai-synthesize examples/affine_examples.json --origin-ref local-origin-declaration
```

This attempts to discover an integer transformation program such as
`double → plus_one` using a bounded symbolic search. Validation is user
supplied and is not an independent blind test. When no exact program is found
it returns `NO_EXACT_PROGRAM` without a fabricated solution.

### Thai learning with lineage and Origin governance

```bash
python runtime.py thai-learn-propose "ศัพท์ตัวอย่างหมายถึงอะไร" "คำตอบต้นทาง" \
  --origin-ref local-origin-declaration --source-ref owned-document-001 \
  --license owned-content --submitted-by local-curator
python runtime.py thai-learn-status
```

An example remains a **Candidate** and cannot be served as a learned answer
until an authorized local Origin key signs a receipt bound to its content
hash. For a real workflow, locally enroll an independently verified Origin
public key, use `thai-learn-receipt <id> --principal <enrolled-principal>
--expires-at <ISO-8601>`, sign the JSON receipt digest with an offline Ed25519
key, grant CANTI `sandbox_train thai.examples`, then call
`thai-learn-approve <id> --receipt-file <path> --signature-file <path>`.
No training source is sent to an external provider. The code never silently
enrolls the user or pretends to have authenticated the actual Origin.

For vocabulary linked to Meaning Space:

```bash
python runtime.py grant-dev sandbox_write meaning_space
python runtime.py core-add WATER th "น้ำ" --definition "ของเหลว" --origin-ref local-origin-declaration
python runtime.py grant-dev sandbox_write thai.lexicon
python runtime.py thai-alias-propose "ธารา" WATER --origin-ref local-origin-declaration \
  --source-ref owned-document-001 --license owned-content
```

A second approval receipt must be signed with a locally enrolled **Origin**
authority key, after CANTI `sandbox_train thai.lexicon`, before `thai-alias-resolve`
and `thai-answer "ธาราแปลว่าอะไร"` will use the new alias. The original CID,
revision, and graph edges remain unchanged. Proposals never mutate the Canonical.

**Demo / evidence:**

```bash
PYTHONPATH=. python examples/demo_thai_sovereign.py --output docs/THAI_DEMO_REPORT.json
PYTHONPATH=. python examples/benchmark_thai_patterns.py --output docs/THAI_PATTERN_BENCHMARK.json
python -m pytest -q
```

The demo uses a **throwaway synthetic Origin key**. Its approval is not a
production sign-off. The 42-phrase benchmark is a manually curated developer
regression set, NOT a blind third-party assessment of Thai fluency. The
`/api/thai/answer` endpoint remains localhost-only and **requires**
`OLGM_HTTP_TOKEN` even on loopback to avoid accidental exposure of local examples.

**Governance distinction:** `thai-run` invokes `IntegratedRuntime.process(..., intent_tag='thai')`
and records the full 16-stage Origin/Intent/Meaning/OTFA/Quality/CANTI/Audit chain.
It refuses model transfers requested with `enable_model=True` unless a separate,
future Origin authorization policy is implemented. `thai-answer` is a light,
read-only helper without that full checkpoint trace; use `thai-run` for governed
OLGM operation. An Answer from an approved example is still **not a verified
fact**. See `docs/THAI_SOVEREIGN_TRACEABILITY.md`.

The learning/lexicon SQLite tables include application-level append-only
triggers and approval-bound content hashes. Privileged database administrators
can change SQLite schemas or remove triggers; full resilience therefore needs
independent anchoring, OS permissions and tested backup/recovery.

This extension requires origin and licensing references for new knowledge and
source, keeps Origin authority distinct from user prompts, prevents normal
AI actions from mutating Core 0 or Canonical master, and makes no assertion
that generated source is owned by the model or OpenAI. The original content
and copyright/license rights remain with their respective rights holders.

## What is really implemented

A **single integrated Python/SQLite runtime**, not a collection of independent response examples:

`Core0 boundary reference → User/Origin Intent Lock → Immutable Canonical Reference → Shared Meaning Space & 3D graph → Graph Resonance → 1+18 structural operators → Optional model observation → Evidence V1–V7 mechanical checks & three-plane OTFA → Logical Gravity → Five Axes / Quality Gate → Latest Intent Proof → CANTI sandbox-only action → Checkpoint receipts & Hash Chain → Return-to-Intent`.

It includes bounded curiosity, a persistent step-worker, alternative graph paths, conflict records, historical revisions, Ed25519 signed authorizations, independent HMAC-style checkpoint receipts, epistemic classes, text/image/audio/video/PDF **hash/metadata** ingestion, optional `pyproj` GIS conversion and on-CPU retrieval benchmarking. These capabilities are **not** equivalent to verified causal inference, certified facts or autonomous multimodal understanding.

## Start locally

Requirements: Python 3.10+; SQLite (Python stdlib). For code-level tests, `pytest`, `requests`. Optional `pyproj` (GIS), `Pillow` (image metadata), `cryptography` (Ed25519), and `torch`/`transformers`/`peft` for optional training.

```bash
cd OLGM_Ultimate_integrated_v0_7
python -m pip install -r requirements-dev.txt
export OLGM_DB=./olgm.db
python runtime.py init
python runtime.py grant-dev reason agent.ask --ttl 3600
python runtime.py run "1+2" --intent numeric
python runtime.py audit-verify
python runtime.py checkpoint-verify
python -m pytest -q
```

Windows PowerShell:

```powershell
$env:OLGM_DB = ".\olgm.db"
python runtime.py init
python runtime.py grant-dev reason agent.ask --ttl 3600
python runtime.py run "1+2" --intent numeric
python -m pytest -q
```

No permission is auto-granted. **`grant-dev` is ONLY for a trusted local test machine** and is not a production identity scheme. Do not expose this CLI or its SQLite database to untrusted users.

## Meaning Space example (no model needed)

```bash
python runtime.py grant-dev sandbox_write meaning_space
python runtime.py core-add water th "น้ำ" --definition "water meaning" --origin-ref pilot-origin
python runtime.py core-add river th "แม่น้ำ" --definition "river meaning" --origin-ref pilot-origin
python runtime.py edge-add link1 water river flows_to --origin-ref pilot-origin
python runtime.py graph-path water river
python runtime.py run "น้ำไหลลงแม่น้ำ" --intent why --seed water --goal river
```

These graph links are **registered assertions**, not independent facts. `run` can return a transparent `CANDIDATE` path explanation even without a model; it returns `INSUFFICIENT` when no usable relation is found. Such graph output is **not** a verified real-world fact. It preserves alternate paths and issues checkpoint/audit receipts.

## Optional Ollama live observation

```bash
# Pull a supported model separately, using your own Ollama installation.
export OLGM_MODEL_PROVIDER=ollama
export OLLAMA_HOST=http://127.0.0.1:11434
export OLGM_MODEL=deepseek-r1:7b
python runtime.py run "สังเกตความสัมพันธ์ระหว่างน้ำกับแม่น้ำ" --intent why --enable-model
```

The model is disabled by default; **no model was present/queried for the code-level acceptance results**. Responses generated by a model remain `CANDIDATE_OBSERVATION`, subject to evidence/verification. An external OpenAI-compatible endpoint is optional via `OLGM_MODEL_PROVIDER=openai`, `OLGM_BASE_URL`, `OLGM_API_KEY`, `OLGM_MODEL`; the Observer does **not** include live internal Meaning Space snapshots for non-local endpoints. Never put sensitive source content in prompts to remote endpoints without explicit authorization.

## Queued AI observer

```bash
python runtime.py intent-lock "หาความสัมพันธ์ของมิติความหมาย" --actor local_user --origin-ref external-policy-ref
# Use returned intent_id and intent_hash:
python runtime.py queue-intent <intent_id> <intent_hash> --intent why
python runtime.py worker-step --limit 3
```

Jobs are **not** auto-started; `worker-step` executes a bounded batch. If the model is disabled the job becomes `BLOCKED_MODEL`. To run periodically, schedule the command yourself via a trusted service; there is no automatic always-on service in this ZIP.

## Local loopback API

```bash
export OLGM_HTTP_TOKEN=use-your-own-local-dev-token
python runtime.py serve --host 127.0.0.1 --port 8765
```

```bash
curl -X POST http://127.0.0.1:8765/api/process \
  -H 'Content-Type: application/json' -H 'X-OLGM-Token: use-your-own-local-dev-token' \
  -d '{"q":"1+2","intent":"numeric"}'
```

`GET /health`, `POST /api/process`, `POST /api/ask`, `POST /api/observe`, `POST /api/experience`. The server refuses non-loopback binding. Token verification is optional only for **loopback development**; **do not** expose over LAN or Internet without TLS, identity provider, hardened RBAC, rate limits and a full security review.

## CANTI action example: development sandbox ONLY

```bash
python runtime.py grant-dev sandbox_write sandbox.counter
python runtime.py intent-lock "Increment my development-only counter" --actor local_user --task-type WORK
# Capture intent_id, intent_hash from output.
python runtime.py plan <intent_id> <intent_hash> sandbox.counter '{"name":"trial"}' --requested-by local_user --idempotency-key trial-001
python runtime.py approve <plan_id> --by authorized_dev_operator --approval-ref local-approval-001
python runtime.py execute <plan_id>
```

CANTI records `TARGET_LOCK → PATH_ANALYSIS → EXECUTE_NO_EXPAND → OBSERVE → EMPIRICAL_EVAL → REFINE_ONLY_DEVIATIONS → TERMINATE`. It supports **only** `sandbox.note` and `sandbox.counter`; OS commands, web writes, live GIS editing, procurement approvals and real financial operations are forbidden. `OLGM_REQUIRE_SIGNED_APPROVAL=1` requires signed authorization receipts and explicit local public-key enrollment (see `docs/SECURITY.md`). Signature verification proves possession of an enrolled key; it **does not** replace the factual and policy decision gate.

## BigMap and multimodal adapters

```bash
python -m pip install pyproj Pillow
python runtime.py gis-point 16.199682 103.197839
python runtime.py gis-csv input_wgs84.csv output_indian1975_zone48.csv
python runtime.py media-ingest example.png --origin-ref external-policy-ref
```

GIS transforms EPSG:4326 to EPSG:24048 (Indian 1975 / UTM Zone 48N). **Datum transform / field accuracy NOT VERIFIED** and height remains unknown unless provided. DWG/DXF editing, remote BigMap automation, image understanding, audio transcription and video semantics are **NOT IMPLEMENTED**. Metadata and file hashes are implemented only.

## Training and benchmarks

- `olgm.training.TrainingPipeline.train()` has an **optional PEFT/transformers Trainer** path for JSONL `{"text": "..."}`. It refuses overwrite, records input/output hashes and checks trainable-parameter fingerprint changes. This path **was NOT RUN** without the compatible model and dependencies. A weight change alone is not proof of learning quality.
- `olgm.training.evaluate_jsonl()` performs exact-match benchmarks on held-out JSONL `{"input":"...", "expected":"..."}`.
- `olgm.benchmarks.evaluate_retrieval()` computes Recall@5/20 and nDCG@10; `rank_bm25()` is a transparent character-bigram baseline. Independent blinded evaluation is **NOT TESTED**.

## Actual acceptance evidence

v0.8.0 local result: **156 PASS, 2 SKIPPED, 0 FAIL**; the original v0.7.0 subset had 84 PASS. See `docs/TEST_CAPTURE.json` for source-bound test results and `docs/FULL_TEST_OUTPUT.txt`; rerun `python -m pytest -q`. **S-10 remains NOT PASSED.** (`T06` live and `T17` live). Reproduce with `python -m pytest -q`. These are **unit/integration and loopback API tests**, NOT scientific verification, GPU/LLM validation, external trust proof, certified security, government compliance, a professional survey, or S-10 sign-off.

Refer to `docs/TRACEABILITY.md`, `docs/SECURITY.md`, `docs/THAI_DEMO_REPORT.json`, `docs/S10_RELEASE_REPORT.json` for detailed coverage. There is no automatic code change to your original v0.3.1 package, canonical PDF, external repository, web server, or installed models.


## G-06 v0.7.0: governed self-improvement (actual implementation)

Two separate mechanisms are implemented. **Do not conflate them**:

**1. Bounded symbolic self-learning without a model/GPU:**

- `PrimitiveRegistry`, `Pipeline`, `Evolver`: typed unary integer primitives, actual program mutations, crossover and tournament selection. Multi-objective Pareto front is calculated for accuracy/cost/complexity.
- `Curriculum`, `CoEvolution`: independent reference-oracle training samples, validation samples, and final held-out samples, with adversarial counterexamples added to **training only**. No label from validation or final holdout enters the evolution routine.
- `MetaRouter`, `Reflector`, `PipelineMemory`: validated cross-intent warm starts, concrete failure examples, SQLite episode pointer rehydration.
- `StructuralGrower`: after at least three consecutive near-identical performances for the **same task**, it composes adjacent operators from the winner. It checks deterministic equivalence before registration and **does not invent a cost discount**. This **adds a search macro**, not novel computational expressivity; no claimed improvement until a separately scored task shows it.
- `HeavyDutyLearnerV2`: replayable state with an audit-bound SHA-256 digest, file-safe state replacement, no Canonical or source mutation, explicit status `EXPERIMENTAL_NOT_S10_CERTIFIED`.

**Run real demonstration** (CPU only, no model):

```bash
python examples/demo_selflearn.py --cycles 30 --output docs/G06_DEMO_REPORT.json
python runtime.py selflearn-v2-cycle --gens 12 --batch 10 --pop 48 --state selflearn_v2_state.json
python runtime.py selflearn-v2-report --state selflearn_v2_state.json
```

The demonstration uses **six synthetic, human-specified integer transformation tasks**. In a local 30-cycle run, baseline final-test mean accuracy was **0.00** and selected programs scored **1.00**; composite primitive count grew by **6**. Importantly, the selected programs **already scored 1.00 before composite growth**, so the 6 new macros did not establish further accuracy gains. These results do **not** establish general intelligence, semantic understanding, independent external evaluation, or continuous improvement on every future task. Repeated examination of a final holdout before future tuning also invalidates a claim of a single untouched final benchmark.

**2. Governed developer source improvement, trusted templates only:**

```bash
# Must be operated in a trusted, isolated local developer COPY first.
python runtime.py g06-propose compare
python runtime.py g06-status
# Review the exact diff and test results; record the proposal ID.
# An enrolled Origin-class public key and an explicit LOCAL CANTI grant are both required:
python runtime.py grant-dev source_apply repo.olgm.methods --ttl 900
python runtime.py g06-receipt PROPOSAL_ID --principal YOUR_ENROLLED_KEY_NAME > receipt.json
# Sign receipt OFFLINE with an operator-held private Ed25519 key:
python examples/dev_g06_signing.py sign --private /secure/path/private.pem --receipt receipt.json --signature-out receipt.sig
python runtime.py g06-apply PROPOSAL_ID --receipt-file receipt.json --signature-file receipt.sig
# If rollback needed: create a NEW receipt with --action rollback and sign it again.
python runtime.py g06-receipt PROPOSAL_ID --principal YOUR_ENROLLED_KEY_NAME --action rollback > rollback.json
python examples/dev_g06_signing.py sign --private /secure/path/private.pem --receipt rollback.json --signature-out rollback.sig
python runtime.py g06-rollback PROPOSAL_ID --receipt-file rollback.json --signature-file rollback.sig
```

Local developer key bootstrap (not authenticating the real Origin):

```bash
python -m pip install cryptography
python examples/dev_g06_signing.py keygen --private-out /secure/path/private.pem
# Copy only public_key_hex from stdout and enroll it in local dev database:
python runtime.py key-enroll-dev YOUR_ENROLLED_KEY_NAME PUBLIC_KEY_HEX --authority Origin --enrolled-by trusted_local_operator
```

**Security and correctness constraints:** proposer only edits `olgm/methods.py` and `olgm/g06_capabilities.json`; novel source synthesis, executable arbitrary user/LLM patches, silent auto-apply, edit-to-Core0, and edit-to-Canonical are not supported. A copied regression workspace is **not a security-isolated container** and must never execute untrusted code. It performs independent baseline/patched tests and post-apply tests, uses optimistic source hashes, signed single-use approvals, retained backups and explicit signed rollback. Individual-file `os.replace` is atomic but **multiple file replacements are not a filesystem transaction**; a machine crash may require manual recovery. The locally enrolled public key does not independently prove real-world identity.

**Release status:** `S10-17` is an additional fail-closed release gate for G06. The entire S-10 remains `NOT_PASSED` pending independent evidence, live-model experiments, validated source truth, production threat-model, and actual owner signoff. See `docs/G06_PROOF_MATRIX.md` and `docs/G06_DEMO_REPORT.json` for what was and was not observed. This package is a new local experimental copy, not a modification of your hosted website, Canonical PDF or Archive.

---

## OLGM Control Plane v0.10.0 — Computer / Plugin / Space / Skills / Queue (2026-11-10)

**สถานะ:** LOCAL CODE TESTED เท่านั้น · NOT CONNECTED to the user's physical desktop and ChatGPT Spaces · S-10 PRODUCTION NOT PASSED.

โมดูลใหม่อยู่ใน `olgm/control/`. แยกสิทธิ์การ *มองเห็นว่ามีเครื่องมืออะไร* ออกจากสิทธิ์ *ลงมือใช้เครื่องมือ* ตามหลัก Origin/Intellectual Sovereignty. การมี Connector บน ChatGPT ไม่ทำให้ Runtime Python เรียก Connector นั้นเองได้: ต้องมีบริการเชื่อมต่อที่รองรับการตรวจอัตลักษณ์และสิทธิ์ซึ่งยังไม่ได้ติดตั้ง.

### ความสามารถใหม่

| Subsystem | Implemented and locally testable | Limitations |
|---|---|---|
| Resource Registry | Catalog of computers/plugins/spaces/skills, per-resource allowlists and integrity hash, append-only versioned identifiers | เป็นการลงทะเบียน metadata ไม่ใช่หลักฐานว่าเชื่อมต่อแล้ว |
| Computer View | Local `pyautogui` screenshot adapter, local file hash; separate `computer_view` grant and signed plan required | ต้องมี GUI, module dependency, local consent, explicit opt-in; X-admin not connected |
| Computer Control | Bounded click and type operations, screen bounds, fail-safe, human-signed plan | ไม่ใช่ remote desktop streaming; no arbitrary shell, downloads or clipboard. Thai Unicode typing not independently validated |
| Plugin Bridge | Resource/tool exact allowlist; `ConnectorDispatcher` interface for injected authorized tool handler | ยังไม่มี ChatGPT Connector API transport ผูกกับ Python Runtime; returns `NOT_CONNECTED` |
| Space Bridge | Space/Page allowlist, version required for write, exact signed plan | Real page access requires an authorized connector bridge; none deployed |
| Skills | 8 deterministic internal skills (inventory, connection gaps, queue, audit, intent, local permission count, Space and Plugin inventory) | Third-party skills cannot be executed by merely registering their names |
| Queue | Manual worker, scheduled `not_before`, priority, cancellation, at-most-once claim, idempotency | No autonomous background daemon; interrupted dispatch requires manual reconciliation |
| Authorization | Origin-class Ed25519 signature over action+resource+args hash+intent hash+expiry+nonce; exact-scope CANTI, re-check at dispatch | Local key enrollment ≠ independently verified Origin; production command execution remains OFF |

**ขอบเขตที่ห้าม:** ไม่มีการเข้าถึง Core 0, เปลี่ยน Canonical, Archive, ยกสิทธิ์ตัวเอง, ส่งภาพหน้าจอออก API, เปิด shell จากข้อความ หรือเขียน Space ทั้งหมดโดยอาศัยสิทธิ์กว้าง ๆ.

### Quick start: inspect inventory / skills offline

```bash
python runtime.py init
python runtime.py control-skills
python runtime.py control-resources
python runtime.py control-status
python examples/demo_control_access.py
python -m pytest -q tests/test_control_plane_v10.py
```

### Local development flow (explicit operator approval)

```bash
# 1. Declare a resource. Does not connect or grant control.
python runtime.py control-register computer.xadmin-v1 computer X-admin \
  --provider local-desktop --actions computer.status,computer.screenshot \
  --classification RESTRICTED --ownership-ref origin-policy-REF \
  --source-ref operator-inventory --connection-state OFFLINE

# 2. Register a built-in skill. Again this does not grant execution.
python runtime.py control-install-skill connection_gaps --origin-ref origin-policy-REF

# 3. Lock an operational intent; note returned intent_id and intent_hash.
python runtime.py intent-lock 'ตรวจสอบช่องว่างการเชื่อมต่อ' \
  --actor local_operator --origin-ref origin-policy-REF --task-type WORK

# 4. Plan the exact skill (replace ID/HASH from step 3).
python runtime.py control-propose INTENT_ID INTENT_HASH skill.connection_gaps-v1 \
  skill.run '{}' --requested-by local_operator --idempotency-key audit-001

# 5. In the DEV environment only, grant the exact skill resource.
python runtime.py grant-dev skill_run skill.connection_gaps-v1 --ttl 180

# 6. The approver must have a separate *trusted*, enrolled public key.
#    Never treat the --principal name itself as identity evidence.
python runtime.py control-receipt PLAN_ID --principal APPROVER_KEY_ID \
  --expires-at 2027-01-01T00:00:00+07:00 --approval-ref signed-change-REF
# Sign the returned exact 'receipt' object with an independently-held
# Ed25519 private key: signature over SHA256(canonical_json(receipt)).
# Provide receipt.json and signature.txt files, never private keys.
python runtime.py control-approve PLAN_ID --receipt-file receipt.json \
  --signature-file signature.txt
python runtime.py control-enqueue PLAN_ID --priority 1
python runtime.py control-worker-step --limit 1
```

The date in the example is illustrative: choose a short expiry later than the current time. Do not use a development key or development CANTI grant in production. `OLGM_ENV=production` blocks all write/control commands until an independently validated Identity/Policy gateway exists.

### Opt-in desktop adapter

The worker has a **local-only** optional desktop adapter. On the authorized machine, in a foreground interactive session, an operator must set **both** `OLGM_ENABLE_DESKTOP=1` and `OLGM_INTERACTIVE_CONSENT=1` (or equivalent environment variables on Windows). Every screenshot/click/type operation additionally requires an Origin-class signed receipt, CANTI exact-scope grant, fresh Intent proof and a queued plan. Screenshots are stored locally under `OLGM_CAPTURE_DIR` or `control_captures`, never uploaded by the runtime. `pyautogui` must be installed and an active graphical desktop available. No feature in this package can wake or reconnect an offline device.

### Connector embedding contract

`ConnectorDispatcher(handlers={"space.example-v1": handler})` accepts only **pre-authorized and trusted handlers injected by a hosting application**. Handler signature: `handler(action, args, idempotency_key=...) -> {"status":"EXECUTED"|"NOT_CONNECTED"|"DENIED"|"FAILED",...}`. `EXECUTED` means the bridge reports a call; not an independently verified external outcome. Bind provider-side identity and Page ownership, protect credentials in the hosting application, and report source revisions and remote audit IDs. **Do not wire arbitrary Python `exec`, shell, raw browser URLs, or generic remote command handlers to this interface.**

### Acceptance

- `docs/CONTROL_PLANE_DEMO_V10.json`: deterministic self-contained test/demo with ephemeral keys and no real connector calls.
- `docs/CONTROL_PLANE_MATRIX_V10.md`: capabilities, evidence and remaining integration dependencies.
- `docs/TEST_RUN_NON_G06_V10.txt` and `docs/TEST_RUN_G06_V10.txt`: split full regression (G-06 uses nested subprocess tests).
- The original S-10 release gate remains unchanged and **NOT PASSED**. `production-preflight` now explicitly reports control-queue reconciliation and independent live connector/desktop verification as still needed.

---

## v0.11.0 • ValueGuard owner-first alert (OLGM-VG-01)

A policy extension now supports **high-value answer estimates for external users**, with corrected Origin email **`teeranat.b@gmail.com`**. A strictly **greater-than 1,000,000 THB** forecast (using structured incremental net benefit and registered supporting evidence) stages an email to the Origin first; a user notice only becomes available after an OWNER send succeeds. Origin/family exemptions require a locally trusted Origin Ed25519-signed attestation; self-reported family status never qualifies. Sensitive names/locations are excluded from Origin email unless sharing is explicitly consented. Unknown identity/location remains undisclosed.

This is an **estimated-value notification mechanism**, not a new legal restriction or proof of realized value. There is **no automatic appraisal of arbitrary free-text answers**, no live SMTP transmission in tests, and **S-10 is still NOT PASSED**. The existing answer pathway includes `value_assessment: NOT_ESTIMATED` until sufficient financial evidence exists. The CLI `value-dispatch` is manual/permission-gated in development and is **blocked in production** until a properly authenticated service is installed. See [ValueGuard policy (Thai)](docs/VALUE_GUARD_POLICY_TH.md) and `examples/value_forecast_example.json`.
