# OLGM Ultimate Control Plane v0.10.0 — Acceptance / Evidence Matrix

| ID | Scope | Code/test evidence | Current verdict | To reach LIVE / PRODUCTION |
|---|---|---|---|---|
| CP-01 | Sovereign Catalog: no implicit authority | `registry.py` and append-only/resource-tamper tests | LOCAL PASS | Owner-approved inventory / independently reviewed access classes |
| CP-02 | Origin-bound signed approvals | `plane.py`, Ed25519 binding/role/replay tests | LOCAL PASS | Independent Origin identity proof, key custody and key-revocation procedures |
| CP-03 | CANTI exact-resource access and latest Intent | `plane.py` / stale-intent/revoked grant tests | LOCAL PASS | Production policy gateway, RBAC/IdP and machine deployment |
| CP-04 | Computer screen observation | `executor.py`, disabled-by-default test | MECHANISM ONLY | On-device GUI, consent, screenshot evidence, PDPA safeguards |
| CP-05 | Computer remote interaction | `executor.py` bounded click/type | MECHANISM ONLY | Real X-admin connector, screen dimension checks, human-in-loop verification |
| CP-06 | Plugin tool allowlist | exact target allowlist tests | LOCAL PASS | Connected provider tool registry and independently authorized execution bridge |
| CP-07 | Space / Page allowlist | Page binding/version tests | LOCAL PASS | Connected Space instance, actual Page IDs and revision-safe verified writes |
| CP-08 | 8 deterministic Skills | `skills.py`, local workflow demo and tests | LOCAL PASS | Deployment, higher-level skill policy and coverage benchmarking |
| CP-09 | Manual scheduled queue | at-most-once/cancel/priority/revocation tests | LOCAL PASS | Durable operator review, incident recovery and monitored worker |
| CP-10 | Retry / reconciliation | `UNKNOWN_OUTCOME` no-auto-retry test | LOCAL PASS | Independent remote effect verification, manual reconciliation policy |
| CP-11 | Entire OLGM regression | `docs/FULL_TEST_V10.txt` | LOCAL PASS (see latest log) | X-admin staging run and signed source manifest |
| CP-12 | S-10 final Production gate | Existing S-10 evaluator | NOT PASSED | Independent per-gate evidence, Origin and reviewer authorization |

## External connectivity observed from ChatGPT account at time of inspection

- Desktop Commander account lists **X-admin: OFFLINE** (not live-controlled in this development run).
- ChatGPT Space connector `list_spaces`: **no visible Spaces returned** (`items: []`, `next_cursor: null`). This does not mean the user has no resources elsewhere.
- Management and Space connector tools are available in ChatGPT but they are not Python APIs automatically invokable in the local OLGM runtime.

## Limitations and non-claims

Code-level unit and integration tests, synthetic results and an ephemeral locally generated key do not establish a real screen capture, remote computer control, live Space read/write, authorized plugin invocation, independently authenticated Origin, or S-10 Production PASS.

Production CLI keeps mutation, external execution and device operation disabled. Device control requires explicit per-plan approval; user-level signed approval and actual provider/session access must both be present.
