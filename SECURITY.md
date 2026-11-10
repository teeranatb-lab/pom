# Security and sovereignty constraints

**Threat model:** local developer with trusted CLI shell and a private SQLite store. This is *not* a production service or a multi-tenant security boundary.

1. **Core 0 and Origin** — no API into Core 0 and no autonomous agent permission to read/modify it. `origin_ref` is an attribution pointer, not authenticated identity. Canonical baseline stores a file reference/hash only; the referenced document is not edited.
2. **External models** — disabled by default. The Observer never sends internal graph snapshots to an untrusted/non-loopback ModelBackend. User question text can still be shared if an external provider is explicitly selected; do not send protected inputs without authorization. Local Ollama is recognized only for `localhost`, `127.0.0.1`, `::1` URL hostnames.
3. **Default deny** — CANTI scopes are narrow; `reason agent.ask` and `sandbox_write <resource>` must be explicitly granted for the developer environment. **`grant-dev` and `key-enroll-dev` are not authenticated identity enrollment.** Restrict shell, database permissions and service account. Do not run on shared hosts as a privileged process.
4. **Approval vs independent verification** — the Ed25519 signature gate proves possession of a locally enrolled key. It does NOT establish source truth, policy compliance, or Origin identity without a separate trust authority. `decision_ref` is trace metadata, not independent decision certification.
5. **Force signed approval** — set `OLGM_REQUIRE_SIGNED_APPROVAL=1` before CANTI sandbox approvals; enroll a public Ed25519 key using `key-enroll-dev`, then sign the canonical JSON digest of a full receipt containing `principal`, `plan_id`, `intent_id`, `intent_hash`, `resource`, `scope`, `nonce`, `expires_at`, `approval_ref`, `decision_ref`. CLI supports `approve ... --receipt-file receipt.json --signature-file signature.txt`. **No private key is stored in SQLite or bundled.**
6. **No external side effects** — only `sandbox.note` and `sandbox.counter` are executable. Any arbitrary tool action or network operation must be designed, reviewed and accepted separately.
7. **Append-only provenance** — hash-chains and receipts detect many in-place modifications, but are not resistant to wholesale rollback of an unanchored local DB. HMAC local anchor file is also not a trusted external timestamp service. Store independently signed copies outside the host for stronger integrity.
8. **HTTP** — serves loopback only, optionally protected with `OLGM_HTTP_TOKEN`; always set a token for tests involving nontrivial/private content. No LAN/Internet binding, secure session login, TLS, rate limiting or tenant isolation; do not proxy publicly.
9. **PII and media** — metadata ingest stores filenames, small previews and hashes; content may be sensitive. Protect database and audit logs. Do not upload real personal records to arbitrary models.
10. **Model/training supply chain** — training downloads external model dependencies and weights only when user explicitly invokes it. Set `trust_remote_code=False`, pin/review dependencies, benchmark on held-out data. No implied automatic training.

## Signature code sketch (run with your own private key; not supplied here)

```python
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from olgm.intent import digest

private_key = Ed25519PrivateKey.generate()  # Demo only. Do not discard keys used for real authorization.
public_key_hex = private_key.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw).hex()
# Register public_key_hex by explicitly trusted local key enrollment.
# receipt = {... required receipt fields with a short expiry ...}
# signature_hex = private_key.sign(digest(receipt).encode()).hex()
```

Never put real private keys into a ChatGPT message, database, code repository or log. For production use protected key storage and verified enrollment.

## G-06 developer source mutation (v0.7.0)

- Code patches are limited to deterministic, trusted intent-routing templates and two allowlisted files. A regression workspace copied to a temporary directory is **not a container**; never run arbitrary downloaded or LLM-generated Python in it.
- No unattended production self-modification. The apply path requires CANTI `source_apply/repo.olgm.methods`, an enrolled Origin-class public key, and an Ed25519 signature binding action, fingerprint, test digest, nonce and expiry to the individual proposal. Local key enrollment is not independent identity verification.
- A one-use signed receipt is required separately for rollback; replays are denied. Target source byte hashes and backup hashes are checked; source drift fails closed.
- Per-file `os.replace` is atomic, but multiple source files cannot be replaced atomically as a group. A sudden power loss can require manual restoration using `.g06_backups`. Never run this developer proof against a production website or Canonical/Archive directory.
- Structural primitives in the symbolic learner are closed-over trusted Python functions and bounded integer values; no source eval/exec/import from persisted learner state. State files are audit-hash-bound but local audit files do not replace independent immutable anchoring.


## v0.8 Sovereign Thai extension

The Thai language subsystem does not transmit queries or learned source texts
to remote model APIs; the governed Thai `IntegratedRuntime.process` refuses
`enable_model=True` pending a separate Origin-approved transfer policy.
`/api/thai/answer` requires a loopback-only development token.

Examples and lexical aliases are *candidate* records until a locally enrolled
Origin-authority key approves their exact content digest, with CANTI grants
for approval. Such enrollment is not proof of the real person's identity.
Both tables use append-only SQL triggers plus separate approval-bound digests.
A database owner can defeat local SQL controls; external immutable anchors are
still required.

Reviewed source proposals are not automatically executed and files can only
be written in the `generated/` area with a specific development CANTI grant.
No general-purpose model-generated code, OS sandbox isolation or production
application source rewriting is claimed by the Thai extension.
