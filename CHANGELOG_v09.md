# v0.9 — Production Hardening (NOT CERTIFIED)

- Added production mode command-deny policy for local developer grants, arbitrary legacy approvals and code mutation.
- Prevented production loopback API without a sufficiently long varied token; forbade direct LAN bind and model opt-in via production HTTP requests; denied direct observe/experience mutation endpoints in production.
- Added read-only local preflight SQLite checks, source-safe backup/restore drill, active dev grant detection and explicit blockers for external TLS, identity, threat/PDPA and Origin signoff.
- Hardened S10 evaluator to FAIL closed when the database or chain becomes unreadable.
- Removed nested whole-suite G06 regression runs; patch workspace runs impact-specific regression suite, while S-10 requires a separate top-level complete suite.
- Added 20-gate acceptance inventory, Windows/Linux preflight helpers and Thai deployment/owner-review runbook.
- No changes made to Canonical/Archive; no deployment to X-admin; no production authorization or third-party attestation is claimed.
