"""EDE individual-document reflection pipeline.

One entry point -- run_ede_analysis() -- takes ONE selected text and
returns validated, evidence-checked findings across EDE's eight reflection
dimensions. The stages, in order:

  1. validate the input                      (validate_input)
  2. confirm the actor may use the workflow  (authorise)
  3. apply the existing privacy filter       (services.anonymizer.anonymize)
  4. detect the document language            (services.ede_language_detection)
  5. prepare programme / document-type context from configuration
  6. ask the CONFIGURED model to analyse all eight dimensions
     (the same Anthropic client, model, timeout and usage ledger as the
     rest of the app -- see services/reflection_service.py)
  7. require strict JSON that follows the schema, validated server-side
  8. check that every quoted excerpt really appears in the text that was
     sent to the model (the anonymised text) and record where
  9. discard malformed findings and unsupported quotations
 10. return only validated findings; failures raise EdeAnalysisError with
     a SAFE code -- never document text, credentials or provider messages.

Privacy notes (verified against this code):
- The text sent to the model is the output of anonymize(); the original
  text is used only locally (length check) and is never stored, logged or
  returned by this module.
- Nothing here writes to PostgreSQL or Qdrant, and the text is never
  embedded. The only database writes are the existing, content-free
  usage-ledger row and (on failure) an error-log row that carries only
  the exception CLASS NAME, never its message.
- Anonymization reduces risk; it is not a guarantee of anonymity.
"""

import json
import re
import time
import unicodedata

import anthropic

import config
from navigation.permissions import can_access_workspace
from services import reflection_service
from services.anonymizer import anonymize
from rdi import orchestrator as _orchestrator
from services.ede_framework import (
    DIMENSIONS, EVIDENCE_ABSENCE, EVIDENCE_DIRECT_QUOTE, EVIDENCE_TYPES,
    build_system_prompt, build_user_message, document_type_name, programme_name,
)
from services.ede_language_detection import detect_language
from services.error_log import log_error

OUTPUT_LANGUAGES = ("es", "eu", "en")
EXPLANATION_LANGUAGE_AUTO = "auto"

# Limits for model-produced fields (server-side, independent of the prompt).
_MAX_TEXT_FIELD = 1500
_MAX_LIST_ITEM = 500
_MAX_QUOTE = 400
_MIN_QUOTE = 3
_MAX_QUESTIONS = 3
_MAX_LIMITATIONS = 5

_FINDING_KEYS = {
    "dimension", "source_evidence", "observation", "why_it_matters",
    "alternative_perspective", "reflection_questions", "limitations",
}
_EVIDENCE_KEYS = {"type", "quote", "not_documented"}


class EdeAnalysisError(Exception):
    """A failure the interface can explain safely.

    `code` is one of the fixed strings below -- the page maps each to a
    translated message. The exception message deliberately contains
    nothing but the code, so it can never leak document content.
    `retryable` tells the page whether a 'try again' button makes sense.
    `issue_id` is the existing error-log reference, when one was written.
    """

    def __init__(self, code, retryable=False, issue_id=None):
        super().__init__(code)
        self.code = code
        self.retryable = retryable
        self.issue_id = issue_id


# ---------------------------------------------------------------- stage 1
def validate_input(text):
    """Return the cleaned text or raise EdeAnalysisError."""
    if not isinstance(text, str):
        raise EdeAnalysisError("input_invalid")
    if "\x00" in text:
        raise EdeAnalysisError("input_invalid")
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not cleaned:
        raise EdeAnalysisError("input_empty")
    if len(cleaned) < config.EDE_MIN_DOCUMENT_CHARS:
        raise EdeAnalysisError("input_too_short")
    if len(cleaned) > config.EDE_MAX_DOCUMENT_CHARS:
        raise EdeAnalysisError("input_too_long")
    return cleaned


# ---------------------------------------------------------------- stage 2
def authorise(actor_name, actor_role):
    """Fail closed. The same rule the page uses (practitioner work mode),
    re-checked here so calling this service directly cannot bypass it."""
    if not actor_name or not actor_role or not can_access_workspace(actor_role, "Practitioner"):
        raise EdeAnalysisError("not_authorised")


# ------------------------------------------------------- evidence checking
def _collapse(text):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", text)).strip()


def split_paragraphs(safe_text):
    """Non-empty lines of the analysed text, collapsed. Paragraph numbers
    in the interface and in exports refer to this list (1-based)."""
    return [_collapse(line) for line in safe_text.split("\n") if line.strip()]


def locate_quote(quote, safe_text):
    """Return {"paragraph": n} if `quote` appears VERBATIM in `safe_text`
    (whitespace differences ignored, nothing else: no case folding, no
    punctuation changes), else None. A quote that crosses paragraph
    boundaries is accepted and located at the paragraph where it starts."""
    needle = _collapse(quote)
    if len(needle) < _MIN_QUOTE:
        return None
    paragraphs = split_paragraphs(safe_text)
    joined = " ".join(paragraphs)
    position = joined.find(needle)
    if position < 0:
        return None
    running = 0
    for number, paragraph in enumerate(paragraphs, start=1):
        end = running + len(paragraph)
        if position <= end:
            return {"paragraph": number}
        running = end + 1
    return {"paragraph": len(paragraphs)}


# ------------------------------------------------------ schema validation
def _clean_text(value, max_len=_MAX_TEXT_FIELD):
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value or len(value) > max_len:
        return None
    return value


def _clean_string_list(value, min_items, max_items):
    if not isinstance(value, list) or not (min_items <= len(value) <= max_items):
        return None
    cleaned = [_clean_text(item, _MAX_LIST_ITEM) for item in value]
    if any(item is None for item in cleaned):
        return None
    return cleaned


def validate_finding(raw, safe_text):
    """Return a validated finding dict, or None if it must be discarded.

    Strict by design: unknown fields, wrong types, unknown dimensions,
    quotations not found in the text, or an 'absence' finding that carries
    a quotation all cause the whole finding to be dropped. Nothing is
    repaired or filled in on the model's behalf."""
    if not isinstance(raw, dict) or set(raw) - _FINDING_KEYS:
        return None
    if _FINDING_KEYS - set(raw):
        return None

    dimension = raw["dimension"]
    if not isinstance(dimension, str) or dimension not in DIMENSIONS:
        return None

    evidence = raw["source_evidence"]
    if not isinstance(evidence, dict) or set(evidence) - _EVIDENCE_KEYS:
        return None
    evidence_type = evidence.get("type")
    if evidence_type not in EVIDENCE_TYPES:
        return None

    if evidence_type == EVIDENCE_DIRECT_QUOTE:
        if evidence.get("not_documented") not in (None, ""):
            return None
        quote = evidence.get("quote")
        if not isinstance(quote, str) or not (_MIN_QUOTE <= len(_collapse(quote)) <= _MAX_QUOTE):
            return None
        location = locate_quote(quote, safe_text)
        if location is None:
            return None  # unsupported quotation -> discard, never repair
        clean_evidence = {"type": EVIDENCE_DIRECT_QUOTE, "quote": _collapse(quote),
                          "not_documented": None, "location": location}
    else:  # absence_in_document
        # A document cannot be quoted for something it does not say, and a
        # single document cannot show an absence over time.
        if evidence.get("quote") is not None or dimension == "contradictions_and_change":
            return None
        not_documented = _clean_text(evidence.get("not_documented"))
        if not_documented is None:
            return None
        clean_evidence = {"type": EVIDENCE_ABSENCE, "quote": None,
                          "not_documented": not_documented, "location": None}

    observation = _clean_text(raw["observation"])
    why = _clean_text(raw["why_it_matters"])
    alternative = _clean_text(raw["alternative_perspective"])
    questions = _clean_string_list(raw["reflection_questions"], 1, _MAX_QUESTIONS)
    limitations = _clean_string_list(raw["limitations"], 1, _MAX_LIMITATIONS)
    if None in (observation, why, alternative, questions, limitations):
        return None

    return {
        "dimension": dimension,
        "source_evidence": clean_evidence,
        "observation": observation,
        "why_it_matters": why,
        "alternative_perspective": alternative,
        "reflection_questions": questions,
        "limitations": limitations,
    }


def parse_model_output(raw_text):
    """Parse the model's reply into the top-level findings list.
    Raises EdeAnalysisError('output_invalid') for anything that is not
    exactly {"findings": [...]}."""
    cleaned = (raw_text or "").strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    try:
        payload = json.loads(cleaned)
    except (ValueError, TypeError):
        raise EdeAnalysisError("output_invalid", retryable=True)
    if not isinstance(payload, dict) or set(payload) != {"findings"} or not isinstance(payload["findings"], list):
        raise EdeAnalysisError("output_invalid", retryable=True)
    return payload["findings"]


def validate_findings(raw_findings, safe_text):
    """Return (dimensions, accepted, discarded). `dimensions` always holds
    all eight keys, each a (possibly empty) list, so a dimension the model
    said nothing about is represented clearly instead of being missing."""
    dimensions = {key: [] for key in DIMENSIONS}
    accepted = discarded = 0
    cap = config.EDE_MAX_FINDINGS_PER_DIMENSION
    for raw in raw_findings:
        finding = validate_finding(raw, safe_text)
        if finding is None or len(dimensions[finding["dimension"]]) >= cap:
            discarded += 1
            continue
        finding["id"] = f"{finding['dimension']}-{len(dimensions[finding['dimension']]) + 1}"
        dimensions[finding["dimension"]].append(finding)
        accepted += 1
    return dimensions, accepted, discarded


# --------------------------------------------------------- provider call
def _is_transient(exc):
    if isinstance(exc, (anthropic.APIConnectionError, anthropic.RateLimitError,
                        anthropic.InternalServerError)):
        return True
    status = getattr(exc, "status_code", None)
    return isinstance(status, int) and (status >= 500 or status == 429)


def _safe_log(error_type, message, *, user_name, user_role, context, severity="error"):
    """Write to the existing error log WITHOUT document content. Never
    raises: a logging failure must not hide the original problem."""
    try:
        _error_id, issue_id = log_error(
            page="ede_reflection", error_type=error_type, message=message,
            traceback_text=None,
            traceback_unavailable_reason=(
                "Traceback intentionally omitted: provider exception text can echo "
                "request content, which may include case material."),
            user_name=user_name, user_role=user_role, context=context, severity=severity,
        )
        return issue_id
    except Exception:
        return None


def _call_provider(system_prompt, user_message, *, user_name, user_role):
    """Call the configured Anthropic model, retrying transient failures.
    Returns the response message; raises EdeAnalysisError otherwise."""
    if not config.ANTHROPIC_API_KEY:
        raise EdeAnalysisError("provider_not_configured")

    attempts = max(1, config.EDE_MAX_PROVIDER_ATTEMPTS)
    for attempt in range(1, attempts + 1):
        started = time.monotonic()
        try:
            message = reflection_service.client.messages.create(
                model=reflection_service.CLAUDE_MODEL,
                max_tokens=config.EDE_ANALYSIS_MAX_TOKENS,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
        except Exception as exc:
            reflection_service._record_claude_usage(
                "ede_analysis", started, success=False, error_type=type(exc).__name__)
            if isinstance(exc, anthropic.AuthenticationError):
                issue = _safe_log("EdeProviderAuthentication", "EDE analysis rejected by provider credentials",
                                  user_name=user_name, user_role=user_role,
                                  context={"error_class": type(exc).__name__})
                raise EdeAnalysisError("provider_not_configured", issue_id=issue)
            if _is_transient(exc) and attempt < attempts:
                time.sleep(1.5 * attempt)
                continue
            issue = _safe_log("EdeProviderCallFailed", "EDE analysis provider call failed",
                              user_name=user_name, user_role=user_role,
                              context={"error_class": type(exc).__name__, "attempts": attempt})
            raise EdeAnalysisError("provider_unavailable", retryable=True, issue_id=issue)
        reflection_service._record_claude_usage("ede_analysis", started, message=message)
        return message
    raise EdeAnalysisError("provider_unavailable", retryable=True)  # pragma: no cover


def _extract_text(message):
    return next((b.text for b in getattr(message, "content", []) or []
                 if getattr(b, "type", None) == "text"), "")


# ------------------------------------------------------------ entry point
def run_ede_analysis(text, *, programme, document_type, actor_name, actor_role,
                     explanation_language=EXPLANATION_LANGUAGE_AUTO, ui_language="es"):
    """Analyse ONE selected text. See the module docstring for the stages.

    `programme` and `document_type` must be keys from config (they are
    never taken from free text). `explanation_language` is "auto"
    (follow the document's language) or "es"/"eu"/"en"; `ui_language` is
    the fallback code used when the document's language cannot be
    determined. Raises EdeAnalysisError; never returns placeholder data."""
    cleaned = validate_input(text)                                      # 1
    authorise(actor_name, actor_role)                                   # 2
    if programme not in config.EDE_PROGRAMME_KEYS or document_type not in config.EDE_DOCUMENT_TYPE_KEYS:
        raise EdeAnalysisError("input_invalid")
    if explanation_language != EXPLANATION_LANGUAGE_AUTO and explanation_language not in OUTPUT_LANGUAGES:
        raise EdeAnalysisError("input_invalid")

    safe_text = anonymize(cleaned)                                      # 3
    detected = detect_language(safe_text)                               # 4
    if explanation_language == EXPLANATION_LANGUAGE_AUTO:
        output_language = detected["dominant"] if detected["code"] in OUTPUT_LANGUAGES else (
            detected["dominant"] or (ui_language if ui_language in OUTPUT_LANGUAGES else "es"))
    else:
        output_language = explanation_language

    system_prompt = build_system_prompt(                                # 5
        organisation=config.EDE_ORGANISATION_NAME,
        programme_label=programme_name(programme),
        document_type_label=document_type_name(document_type),
        document_language=detected["code"],
        output_language=output_language,
        max_per_dimension=config.EDE_MAX_FINDINGS_PER_DIMENSION,
    )
    user_message = build_user_message(safe_text)

    # Same organisation-wide cap on simultaneous Claude work that the
    # existing reflection flow uses (rdi/orchestrator.py), so this
    # workflow cannot add unbounded load on the shared provider account.
    slot = _orchestrator._reflection_semaphore.acquire(
        timeout=_orchestrator.CLAUDE_REFLECTION_QUEUE_TIMEOUT_SECONDS)
    if not slot:
        raise EdeAnalysisError("busy", retryable=True)
    try:
        message = _call_provider(system_prompt, user_message,           # 6
                                 user_name=actor_name, user_role=actor_role)
    finally:
        _orchestrator._reflection_semaphore.release()
    if getattr(message, "stop_reason", None) == "max_tokens":
        issue = _safe_log("EdeOutputTruncated", "EDE analysis response was cut off at the token limit",
                          user_name=actor_name, user_role=actor_role,
                          context={"stop_reason": "max_tokens"}, severity="warning")
        raise EdeAnalysisError("output_truncated", retryable=True, issue_id=issue)

    try:
        raw_findings = parse_model_output(_extract_text(message))       # 7
    except EdeAnalysisError as exc:
        exc.issue_id = _safe_log("EdeOutputInvalid", "EDE analysis response did not follow the schema",
                                 user_name=actor_name, user_role=actor_role,
                                 context={"reason": "not_valid_json_object"}, severity="warning")
        raise

    dimensions, accepted, discarded = validate_findings(raw_findings, safe_text)  # 8-9

    return {                                                            # 10
        "programme": programme,
        "document_type": document_type,
        "detected_language": detected["code"],
        "output_language": output_language,
        "dimensions": dimensions,
        "accepted_count": accepted,
        "discarded_count": discarded,
        "paragraph_count": len(split_paragraphs(safe_text)),
        "document_chars": len(cleaned),
    }
