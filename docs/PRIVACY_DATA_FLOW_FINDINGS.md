# Privacy & Data-Flow Audit — Concrete Findings

**Audit branch:** `production-readiness-privacy-audit`
**Status:** Phase 1 evidence collection

## Executive finding

The intended privacy boundary is real in the main reflection and semantic-indexing paths: original case text is processed inside Reflection Space, anonymized before external AI processing, and Qdrant is treated as a secondary index rather than the system of record.

However, the audit found one important privacy issue that must be resolved before permanent production: the organisational Knowledge Assistant currently includes the retrieved `case_ref` value in the Claude prompt even though the retrieved excerpt itself is anonymized.

A case reference is metadata, but it can still be identifying or linkable. The external AI does not need it to answer the organisational question. The safe design is to keep the real case reference for the authorised UI/evidence panel while replacing it with an opaque local evidence identifier (for example, `EVIDENCE-1`) before the evidence is sent to Claude.

## Evidence confirmed from code

### 1. Claude reflection path

`services/reflection_service.py` calls `anonymize(text)` before the main reflection request is sent to Anthropic. The companion path receives already-anonymized text from the orchestrator and documents that the raw document is not seen by that function/API path.

**Assessment: PROVEN BY CODE — PASS.**

### 2. Gemini embedding path

`services/embedding_service.py` is a thin wrapper around the Google Gemini Embedding API. Its documented contract is that callers pass already-anonymized text. It does not log or store the embedded text itself, and provider failures return `None` rather than blocking document submission/reflection.

**Assessment: PROVEN BY CODE — PASS, subject to provider-retention confirmation.**

### 3. Qdrant storage

`services/qdrant_service.py` explicitly treats PostgreSQL as the system of record and Qdrant as a semantic index. Its design states that Qdrant stores vectors plus small metadata, not document content, and that the index can be rebuilt from PostgreSQL.

Practitioner-facing semantic search requires `case_ref`; the global search is deliberately separate for authorised management/administrative functions.

**Assessment: PROVEN BY CODE — PASS for practitioner case isolation.**

### 4. Qdrant operational logging

`services/rag_logging.py` centrally redacts `case_ref` values before sending RAG diagnostic messages to stdout/log handlers. Retrieval diagnostics are intended to contain opaque document IDs, document types and scores rather than case content.

**Assessment: PROVEN BY CODE — PASS, with continued regression testing required.**

### 5. Audit/error logging

The reviewed storage and audit design records operational metadata rather than case/reflection content. This reduces the chance that application logs become a second sensitive-data database.

**Assessment: PROVEN BY CODE — PASS, but future logging changes must preserve this rule.**

## Finding P-001 — Knowledge Assistant sends case references to Claude

### Location

`services/knowledge_assistant.py`, `_build_evidence_block()`.

### What happens

For each globally retrieved document, the application:

1. anonymizes the document excerpt;
2. obtains the document's `case_ref` separately;
3. constructs the evidence prompt containing `case_ref=<real case reference>`;
4. sends that evidence block to Claude.

The same real `case_ref` is also returned to the authorised UI evidence panel, which is reasonable for an internal management user. The problem is specifically the copy placed in the external AI prompt.

### Why it matters

The case reference may be pseudonymous rather than a person's name, but it can still be linkable information. It provides no necessary value to the model for answering an organisation-wide learning question.

This weakens the otherwise strong privacy boundary: the narrative is anonymized, but identifying metadata is reintroduced into the external AI request.

### Required disposition

**FIX BEFORE PERMANENT PRODUCTION.**

The external prompt should contain an opaque evidence label only, while the real `case_ref` remains available to the authorised application UI if needed. For example:

`EVIDENCE-1` instead of the real case reference.

The model should never receive the real case reference unless a future, explicitly reviewed product requirement proves that it is necessary.

### Severity

**HIGH privacy priority, low implementation complexity.**

This is the first concrete privacy issue discovered during the formal audit.

## Finding P-002 — Anonymisation is risk reduction, not anonymity

`services/anonymizer.py` explicitly states that indirect identification cannot be reliably solved by pattern matching. The implementation removes common emails, dates, phones, identifiers, addresses, contextual identifiers and conservative proper-name phrases.

This is a good privacy layer, but a unique combination of harmless-looking facts can still identify a person.

**Disposition:** retain the current approach, but formally describe it as privacy-risk reduction rather than guaranteed anonymisation. Close the remaining risk through adversarial testing and organisational privacy controls, not by claiming that regex-based anonymisation can provide perfect anonymity.

## Finding P-003 — Uploaded-document bypass not yet proven

Repository searches for common Streamlit file-upload markers did not identify a clearly separate uploaded-document ingestion path in the files inspected during this phase. This is **not** evidence that no upload path exists.

**Disposition:** trace all UI inputs and document ingestion paths explicitly before privacy sign-off. Any path that extracts text from an uploaded PDF/DOCX/image must be shown to pass through the same privacy boundary before external AI use.

**Assessment: REQUIRES FURTHER CODE TRACE — OPEN.**

## Finding P-004 — Provider governance cannot be proven from source code

The code proves that Anthropic and Google/Gemini are called and that API keys are supplied through environment configuration rather than embedded in the application source. It cannot prove the provider account's actual retention, regional processing, contractual terms, or data-processing agreement.

**Assessment: REQUIRES LIVE CONFIGURATION/CONTRACT VERIFICATION — OPEN.**

## Phase 1 conclusion

The application's intended privacy architecture is fundamentally sound, but it is not yet safe to mark the privacy gate complete.

The immediate engineering item is **P-001: remove the real case reference from the Knowledge Assistant's Claude prompt**.

The remaining Phase 1 work is to complete the input/upload trace and verify provider-side data-processing and retention arrangements.
