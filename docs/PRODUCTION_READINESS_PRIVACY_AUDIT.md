# Reflection Space — Production Readiness & Privacy Audit

**Status:** In progress  
**Scope:** Pre-production validation before new product features  
**Base:** `main` branch at the start of this audit

## Purpose

This document is the working gate for deciding whether Reflection Space is ready to move from a controlled pilot toward broader production use. It deliberately separates **technical controls** from **organisational/privacy obligations** that cannot be proved by source code alone.

## Current decision

**Controlled pilot: CONDITIONAL GO**

**Permanent unrestricted production: NOT YET**

The application has strong authentication, access control, database protection, AI timeout/retry handling, anonymisation support, audit logging, deletion handling, connection pooling, and automated security/reliability tests. The remaining work is primarily proof and governance: document the complete data flow, test privacy boundaries adversarially, validate end-to-end user journeys, and strengthen long-term database recovery.

---

## Gate 1 — Privacy and data-flow sign-off

### Data-flow model to validate

`Practitioner → Reflection Space → PostgreSQL → anonymisation boundary → external AI services → Qdrant semantic index`

### What the code currently establishes

1. **PostgreSQL is the system of record.** Accounts, reflections and operational records depend on the PostgreSQL database.
2. **Original case/reflection information is handled inside Reflection Space before AI processing.** The reflection service calls the anonymiser before sending document text to Claude.
3. **Claude receives the anonymised document text and prompts needed to generate the reflective output.**
4. **Gemini is used for embedding/search-vector generation when semantic search is enabled.**
5. **Qdrant is a secondary semantic index, not the authoritative case database.** The design permits rebuilding the index from PostgreSQL.
6. **Practitioner semantic retrieval is case-scoped.** Organisation-wide retrieval is a separate privileged capability.
7. **Audit records deliberately avoid storing case/reflection content.** They retain operational metadata needed to establish who performed an action and when.
8. **Error logging is designed to avoid case content and client names.**
9. **Deleted records can remain in provider/database backups for the applicable backup-retention period.** This must be reflected in the formal retention/erasure policy.

### Privacy questions that still require formal answers

These are not safe to infer from application code and must be confirmed against current provider contracts, settings and organisational policy:

- Exactly what Anthropic receives for each operation.
- Exactly what Google/Gemini receives for each operation.
- Whether provider-side logging or retention applies to those requests.
- Where each provider processes the data geographically.
- Applicable data-processing agreements and contractual safeguards.
- Whether the organisation's legal basis permits this processing.
- Whether the current anonymisation level is sufficient for the intended case material.
- Required retention periods for PostgreSQL, Qdrant, logs, audit records and backups.
- How an erasure request is handled across live data, indexes, logs and backups.
- Whether any uploaded-document path bypasses or weakens the anonymisation boundary.

**Gate result:** TECHNICAL CONTROL PRESENT; FORMAL PRIVACY SIGN-OFF PENDING.

---

## Gate 2 — Backup and recovery

### Current position

The operator runbook documents a Neon Free PostgreSQL setup with a six-hour restore history and no manual snapshots. Qdrant is rebuildable from PostgreSQL because it is not the source of truth.

### Required production decision

Before permanent production, establish a recovery point objective (how much recent data the organisation can afford to lose) and a recovery time objective (how quickly the system must be restored), then choose a backup plan that actually meets them.

### Minimum acceptance evidence

- A known-good PostgreSQL backup/snapshot exists outside the application's normal runtime path.
- A restore has actually been performed in a safe environment.
- The restored database can start the application successfully.
- Qdrant can be rebuilt from PostgreSQL after a simulated loss.
- The team knows who is responsible for recovery.
- Recovery instructions are documented for someone who did not build the application.

**Gate result:** PILOT ACCEPTABLE WITH EXPLICIT RISK; PERMANENT PRODUCTION PENDING.

---

## Gate 3 — Adversarial privacy testing

The goal is **not** to prove perfect anonymity. That is not a realistic guarantee for rich narrative case material. The goal is to identify where the privacy boundary is weak and quantify the remaining risk.

### Test categories

- Names hidden in unusual sentence structures.
- Multiple names in one narrative.
- Addresses and partial addresses.
- Kenyan phone numbers in different formats.
- Kenyan national ID/passport-style identifiers.
- School and institution names.
- Villages, estates, neighbourhoods and other local place references.
- Exact dates and combinations of dates with other facts.
- Rare occupations or unique personal circumstances.
- Combinations of individually harmless facts that together identify a person.
- Spanish names and Spanish-language narratives.
- Kiswahili names and Kiswahili-language narratives.
- Mixed English/Kiswahili/Spanish narratives.
- Identifiers embedded in uploaded documents.
- Identifiers appearing in metadata or filenames where applicable.
- Attempts to cause the AI prompt to repeat the original identifying information.

### Acceptance principle

Every test should answer:

1. What identifying information was present?
2. What did the anonymiser remove?
3. What remained?
4. Could a reasonable person with local knowledge identify the subject from what remained?
5. If yes, is the remaining risk acceptable for the intended use?

**Gate result:** NOT YET EXECUTED AS A FORMAL ADVERSARIAL SUITE.

---

## Gate 4 — End-to-end production tests

### Journey A — Social Worker

`login → create/open case → generate reflection → review companions → save → search own permitted history`

Expected result: the complete journey works and the user sees only information they are authorized to see.

### Journey B — Supervisor/management

`login → enter permitted management workspace → view permitted cases → use Knowledge Assistant → attempt restricted practitioner access`

Expected result: permitted management functions work and restricted data remains inaccessible.

### Journey C — Session isolation

`User A login → view case → logout → User B login in same browser/session`

Expected result: User B cannot inherit User A's case, reflection, draft, assistant, or workspace state.

### Failure journeys

Also test:

- PostgreSQL unavailable.
- Claude unavailable or times out.
- Gemini unavailable.
- Qdrant unavailable.
- Duplicate submission.
- Rate limit reached.
- Partial companion failure.
- Malformed AI response.
- Interrupted session.
- Failed deletion/restore/purge.

**Gate result:** existing unit/reliability coverage is strong; full production journey evidence is still required.

---

## Gate 5 — Feature freeze

No new product feature should be treated as higher priority than closing Gates 1–4.

Once the gates are passed, resume normal feature development with the production-readiness tests included in CI where practical.

---

## Known accepted limitations

1. Streamlit's persistent-login implementation cannot currently provide an `HttpOnly` cookie flag because the cookie is written through browser JavaScript. Compensating controls exist, but this remains an architectural limitation.
2. Rate-limit/lockout state is intentionally designed around service availability; this trade-off should remain documented.
3. The application does not currently expose a dedicated health endpoint.
4. `ADMIN_PASSWORD` remains as unused legacy configuration and should be removed in a later cleanup when doing so is low-risk.
5. The anonymiser reduces direct and contextual identifiers but cannot guarantee that a rich narrative is impossible to re-identify.

---

## Sign-off checklist

- [ ] Complete provider-by-provider data-flow inventory.
- [ ] Confirm Anthropic data-processing/retention terms for the actual account and deployment.
- [ ] Confirm Google/Gemini data-processing/retention terms for the actual account and deployment.
- [ ] Confirm Qdrant hosting, location and retention configuration.
- [ ] Confirm PostgreSQL hosting, backup and retention configuration.
- [ ] Define retention and deletion policy across live data, indexes, logs and backups.
- [ ] Run adversarial anonymisation suite.
- [ ] Review all uploaded-document paths for anonymisation bypasses.
- [ ] Run complete Social Worker journey.
- [ ] Run complete Supervisor journey.
- [ ] Run same-browser session-isolation journey.
- [ ] Run dependency-failure journeys.
- [ ] Perform and document a PostgreSQL restore test.
- [ ] Perform and document Qdrant rebuild-from-PostgreSQL test.
- [ ] Reassess production grade after evidence is collected.
