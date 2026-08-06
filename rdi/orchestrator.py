"""
Reflection Orchestrator
=========================

Sprint 4: now runs the 8 reflection companions (see rdi/companions/) as
independent, parallel API calls instead of one combined call.

Design choices worth knowing about:

- Anonymization happens ONCE here, before fan-out, and the anonymized
  text is reused for all 8 calls -- not re-anonymized 8 times.
- Calls run in parallel (via a thread pool), not sequentially, so total
  latency stays close to a single call rather than 8x slower.
- The merged result is reshaped back into the exact same flat dict shape
  services.reflection_service.generate_reflection() used to return, so
  services.reflection_log.log_reflection() -- and therefore the Learning
  page's theme counts -- needed ZERO changes.
- Partial failure is expected and handled: if some companions fail
  (timeout, parse error, etc.) while others succeed, the ones that
  succeeded are still shown. Only if ALL 8 fail does this behave like the
  old single-call error case.

Sprint 6 addition
------------------
The anonymized `safe_text` produced here is now included in the return
value (key "safe_text"). The Reflection Workspace needs it to continue a
conversation about an opportunity later, without re-anonymizing the
document or ever sending the raw/original text to the API a second time.
This is purely additive -- every existing key in the return dict is
unchanged.

UX pass -- automatic retry for transient failures
-----------------------------------------------------
Previously, a single failed API call (network hiccup, a rate limit, an
empty/unparseable response) for one companion permanently marked that
dimension as failed for the whole reflection, and the practitioner would
see a "1 reflection area(s) couldn't be generated this time" notice --
even though the underlying cause was almost always transient and would
have succeeded on a second try.

Each companion call now goes through _generate_companion_with_retry()
below, which retries the SAME call (same prompt, same model, same
max_tokens -- nothing about what is asked of the model changes) up to
MAX_ATTEMPTS times, with a short backoff between attempts, before that
companion is counted as failed. Generation still only "completes" (i.e.
run_reflection() returns) once every companion has been attempted this
way -- the ThreadPoolExecutor + as_completed() loop already waited for
every future before returning, and that is unchanged; retries just
happen *inside* each future instead of the future giving up after one
try.

This means the practitioner-facing "couldn't be generated" notice should
now be rare -- it only appears if a companion fails MAX_ATTEMPTS times in
a row, which is a much stronger signal of a genuine (not transient)
problem than a single failed call ever was.

Cost note: retries only fire on failures, which are expected to be
uncommon -- a successful first attempt (the normal case) costs exactly
what it always did, with zero extra calls. Only companions that
genuinely fail make one or two extra calls before succeeding or finally
giving up. See the accompanying handoff notes for projected monthly cost
impact at this pilot's volume.

Phase 3 -- Reflection Generation is ONE operation, not 8
-----------------------------------------------------------
Previously, _generate_companion_with_retry() called services.error_log's
log_error() itself, per companion, the moment that ONE companion
exhausted its retries -- while the other 7 companions might still be
running. This meant:
  - A single reflection generation request where, say, 3 companions
    failed for the exact same underlying reason produced 3 separate
    log_error() calls (and, if a run_reflection() call is repeated by
    many practitioners, could scatter across MULTIPLE issue numbers --
    defeating Phase 2's "one issue, many occurrences" design, because
    companion identity was implicitly part of what got logged even
    though it was never part of the fingerprint's intent).
  - A "Complete Failure" (all 8 failed) was ALSO logged a 9th time, as
    a separate "AllCompanionsFailed" summary -- redundant with the 8
    individual logs already written for the exact same event.
  - The practitioner-facing failure screen for a Complete Failure
    (services/reflection_session.py -> pages/reflection_space.py)
    showed a generic "couldn't process the response" message with NO
    issue reference number at all -- not the same calm, numbered
    screen every other unexpected error in the app produces.

Reflection Generation is now treated, end to end, as ONE operation with
exactly three outcomes -- Success, Partial Success, Complete Failure --
and _generate_companion_with_retry() no longer logs anything itself; it
only ever returns a result (success, or a failure detail dict). ALL
logging now happens once, in run_reflection() below, after every
companion has finished, based on the OVERALL outcome:

  - Success (0 failures): nothing is logged at all.
  - Partial Success (1-7 failures): exactly ONE log_error() call,
    severity "warning", title "Partial Reflection Generation". The
    reflection is still shown -- see run_reflection()'s return value
    and pages/reflection_space.py's non-blocking st.warning(). Failed
    companion NAMES are attached as evidence (the `context` dict) on
    this one occurrence -- they are evidence of what happened, never
    issues of their own.
  - Complete Failure (all 8 failed): exactly ONE log_error() call,
    severity "error", title "Reflection Generation Failed -- {root
    cause}". The practitioner sees the same numbered "Something went
    wrong" screen as any other unexpected error (see
    services/error_log.py:render_application_error_screen).

Both the Partial Success and Complete Failure log_error() calls pass a
root_cause_hint (see services/issue_fingerprint.py:
classify_reflection_failure_root_cause and build_fingerprint) -- the
DOMINANT root cause across whichever companions failed this run, out of
a fixed set (Anthropic Authentication / Rate Limit / Network Timeout /
Invalid Model Response / Unknown). This is what makes issue grouping
follow ROOT CAUSE rather than companion identity: two runs that both
fail because of, say, a Claude API rate limit collapse into the SAME
issue regardless of which companions happened to be the ones rate-limited,
while a run that fails for a genuinely different reason (an auth problem,
say) becomes a different issue, exactly as intended.
Concurrency control (September pilot hardening -- "Change 11: Claude
concurrency control")
------------------------------------------------------------------------
Everything above governs ONE reflection's 8 companion calls. Nothing
above bounds how many reflections (each still fanning out to its own 8
parallel calls) can be running at the same moment, org-wide -- at this
pilot's target scale (up to ~1000 social workers, even if only a
fraction are ever concurrently active) that has no ceiling by default,
which risks account-level Claude API overload exactly the way an
unbounded per-user cost guard doesn't (services/rate_limiter.py already
caps cost per person, but says nothing about how many DIFFERENT
people's reflections can be in flight at once).

run_reflection() now acquires one slot from a process-wide
threading.Semaphore (`_reflection_semaphore`, sized by
config.CLAUDE_MAX_CONCURRENT_REFLECTIONS) before doing anything else,
and releases it once the whole operation (all retries, all 8
companions) has finished, success or failure. This deliberately gates
at the RELECTION level, not the companion level -- the 8-way
ThreadPoolExecutor fan-out inside one reflection is completely
unchanged (same parallelism, same latency, same retry behavior, same
quality), so a person generating a reflection while the app is under
load sees the same output as always, just possibly after a short wait
for a free slot.

The acquire is a bounded wait (config.CLAUDE_REFLECTION_QUEUE_TIMEOUT_
SECONDS), which is the "queue" behavior: a request made while every
slot is busy simply waits (Streamlit's existing spinner already covers
this -- see pages/reflection_space.py) for the next slot to free up,
rather than being rejected outright. Only if no slot frees up within
that window does the request give up -- treated as its own Complete-
Failure-shaped outcome (one log_error() call, same numbered "Something
went wrong" screen as any other unexpected failure), with a
friendly_message explaining this was a capacity/timing issue, not a
bug, so the person isn't misled into thinking something is broken.
"""

import random
import threading
import time
import traceback
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import CLAUDE_MAX_CONCURRENT_REFLECTIONS, CLAUDE_REFLECTION_QUEUE_TIMEOUT_SECONDS
from services.anonymizer import anonymize
from services.reflection_service import generate_companion_reflection
from services.error_log import log_error
from services.issue_fingerprint import classify_reflection_failure_root_cause
from rdi.companions import COMPANIONS
from rdi.reflection_objects import ReflectiveOpportunity

# How many total attempts one companion gets before it's counted as a
# genuine (non-transient) failure. 3 means: try once, and if that fails,
# retry up to 2 more times.
MAX_ATTEMPTS = 3

# Backoff between attempts, in seconds, multiplied by the attempt number
# (1st retry waits ~0.75s, 2nd retry waits ~1.5s) -- long enough to ride
# out a brief rate-limit or network hiccup, short enough not to make the
# practitioner wait noticeably longer for the (rare) companion that
# needed a retry.
RETRY_BACKOFF_SECONDS = 0.75

# Small random jitter added on top of the backoff above (September
# pilot hardening, "review retry storms"). Without jitter, every
# companion (and, at higher traffic, every practitioner's companions)
# that fails for the SAME shared root cause -- e.g. a genuine Claude
# API rate-limit window -- retries at the exact same fixed delay,
# recreating the same burst of simultaneous requests a moment later
# instead of spreading it out. This does not change MAX_ATTEMPTS, does
# not change which failures are retried, and does not meaningfully
# lengthen a normal (non-retried) reflection's latency.
RETRY_JITTER_SECONDS = 0.4

# Process-wide cap on how many reflections (NOT individual companion
# calls) may be actively generating at once -- see the module docstring
# ("Concurrency control") above. Sized from config so it can be tuned
# via CLAUDE_MAX_CONCURRENT_REFLECTIONS without a code change.
_reflection_semaphore = threading.Semaphore(CLAUDE_MAX_CONCURRENT_REFLECTIONS)


def _generate_companion_with_retry(companion, safe_text, lang):
    """
    Run generate_companion_reflection() for ONE companion, retrying on
    failure before giving up.

    A "failure" here is either an exception raised by the API call
    itself (network error, timeout, rate limit, etc.) or the same
    {"error": ..., "raw": ...} shape generate_companion_reflection()
    already returns when it can't parse a valid response. Both are
    treated as transient and worth retrying -- neither changes the
    prompt, the model, or max_tokens on the retried call.

    Returns the same shape generate_companion_reflection() always
    returned: either {"observation": ..., "questions": [...]} as soon
    as one attempt succeeds, or {"error": ..., "raw": ...,
    "traceback": ...|None}, only after MAX_ATTEMPTS attempts have all
    failed.

    Phase 3: this function no longer logs anything itself -- see the
    module docstring above. It only reports what happened; deciding
    whether that adds up to a Partial Success or a Complete Failure
    (and logging exactly once for the whole operation) is
    run_reflection()'s job, once every companion has finished.
    """
    last_result = {"error": "Failed to generate reflection", "raw": "", "traceback": None}

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            result = generate_companion_reflection(companion, safe_text, lang)
        except Exception as e:
            # Capture the REAL traceback here, at the moment the
            # exception is caught -- this is the one place it exists.
            result = {"error": "API call failed", "raw": str(e), "traceback": traceback.format_exc()}

        if result and "error" not in result:
            return result

        last_result = result
        if attempt < MAX_ATTEMPTS:
            # September pilot hardening: add a small random jitter on
            # top of the fixed backoff -- see RETRY_JITTER_SECONDS
            # above -- so that companions failing for the same shared
            # root cause (e.g. an account-level rate limit) don't all
            # retry at the exact same moment and recreate the same
            # burst a beat later.
            time.sleep(RETRY_BACKOFF_SECONDS * attempt + random.uniform(0, RETRY_JITTER_SECONDS))

    return last_result


def _dominant_root_cause(failure_details):
    """
    Given every failed companion's classified root cause (see
    classify_reflection_failure_root_cause), returns the single most
    common one -- this becomes the root_cause_hint for the ONE
    log_error() call covering the whole operation. Ties are broken by
    whichever cause was seen first, which is stable and good enough:
    this is a grouping label, not a precise diagnosis.
    """
    if not failure_details:
        return "Unknown"
    counts = Counter(d["root_cause"] for d in failure_details)
    return counts.most_common(1)[0][0]


def _representative_failure(failure_details):
    """
    Picks ONE failed companion's detail to supply the Traceback section
    for the single aggregated log_error() call -- preferring one that
    actually has a real traceback (a genuine Python exception) over one
    that doesn't, since that's strictly more useful evidence. Every
    companion's own detail (including ones NOT picked here) is still
    attached in full as the `context` dict -- this only decides which
    one's traceback gets to be THE traceback for the occurrence.
    """
    with_traceback = next((d for d in failure_details if d.get("traceback")), None)
    return with_traceback or failure_details[0]


def run_reflection(text, lang="Español", context_description=""):
    """
    Generate a reflection by running all 8 companions in parallel and
    merging their results.

    Each companion is attempted up to MAX_ATTEMPTS times (see
    _generate_companion_with_retry()) before being counted as failed --
    generation only completes once every companion has been fully
    attempted this way.

    Phase 3: Reflection Generation is treated as ONE operation with
    exactly three outcomes (see the module docstring for the full
    reasoning) -- Success, Partial Success, and Complete Failure. This
    function is the ONLY place that decides which of the three
    happened and the ONLY place that logs anything about it; individual
    companion failures are evidence attached to that one decision, not
    separate events.

    Returns one of:
      - {"error": "...", "raw": "...", "issue_id": int|None,
         "error_id": int|None, "friendly_message": str|None} --
        Complete Failure: ALL 8 companions failed after every retry,
        OR (September pilot hardening) no concurrency slot freed up
        within CLAUDE_REFLECTION_QUEUE_TIMEOUT_SECONDS (see the module
        docstring's "Concurrency control" section). issue_id/error_id
        let the caller (pages/reflection_space.py) show the same
        numbered "Something went wrong" screen as any other unexpected
        error -- see services/error_log.py:render_application_error_screen.
        friendly_message is only set for the capacity-timeout case, and
        lets that screen explain (truthfully) that this was a timing/
        capacity issue rather than a bug.
      - {
          "opportunities": [ReflectiveOpportunity, ...],
          "raw": dict,                 -- for log_reflection(), unchanged shape
          "failed_count": int,         -- 0 on full Success
          "failed_labels": [str, ...], -- human-readable labels of any
                                           companions that failed EVERY
                                           attempt, for an honest,
                                           non-blocking notice (Partial
                                           Success -- failed_count > 0)
          "safe_text": str,            -- (Sprint 6) the anonymized
                                           document text used for this
                                           run, for reuse by the
                                           Reflection Workspace's
                                           follow-up conversations
        }
    """
    safe_text = anonymize(text)

    results = {}   # key -> companion result dict or None on failure
    failed_labels = []
    failure_details = []  # [{key, label, error_message, raw, traceback, root_cause}, ...]

    # September pilot hardening: acquire one process-wide concurrency
    # slot before making any Claude calls -- see the module docstring's
    # "Concurrency control" section and config.py:
    # CLAUDE_MAX_CONCURRENT_REFLECTIONS. This bounds how many
    # reflections (not companions) can be generating at once, org-wide;
    # the 8-way parallelism below is unchanged either way. A bounded
    # wait here is the "queue" behavior -- only if no slot frees up in
    # time do we give up and report a Complete-Failure-shaped, but
    # distinctly-labeled, outcome.
    slot_acquired = _reflection_semaphore.acquire(timeout=CLAUDE_REFLECTION_QUEUE_TIMEOUT_SECONDS)
    if not slot_acquired:
        error_id, issue_id = log_error(
            page="reflection_space (generate reflection)",
            error_type="ReflectionCapacityTimeout",
            message=(
                f"No reflection-generation slot became free within "
                f"{CLAUDE_REFLECTION_QUEUE_TIMEOUT_SECONDS}s "
                f"(CLAUDE_MAX_CONCURRENT_REFLECTIONS="
                f"{CLAUDE_MAX_CONCURRENT_REFLECTIONS}). The app is at its "
                f"configured concurrent-reflection capacity; no Claude API "
                f"calls were made for this request."
            ),
            traceback_text=None,
            traceback_unavailable_reason=(
                "No exception was raised -- this is an expected capacity "
                "limit, not a failure. See config.py:"
                "CLAUDE_MAX_CONCURRENT_REFLECTIONS / "
                "CLAUDE_REFLECTION_QUEUE_TIMEOUT_SECONDS to tune it."
            ),
            context={
                "lang": lang,
                "max_concurrent_reflections": CLAUDE_MAX_CONCURRENT_REFLECTIONS,
                "queue_timeout_seconds": CLAUDE_REFLECTION_QUEUE_TIMEOUT_SECONDS,
            },
            severity="warning",
            title_override="Reflection Generation Delayed \u2013 App At Capacity",
            root_cause_hint="Capacity",
        )
        return {
            "error": "Failed to generate reflection",
            "raw": "No reflection-generation slot became available in time.",
            "issue_id": issue_id,
            "error_id": error_id,
            "friendly_message": (
                "Reflection Space is handling an unusually high number of "
                "requests right now. Please wait a moment and try again -- "
                "this isn't an error with your document."
            ),
        }

    try:
        with ThreadPoolExecutor(max_workers=len(COMPANIONS)) as executor:
            future_to_companion = {
                executor.submit(_generate_companion_with_retry, companion, safe_text, lang): companion
                for companion in COMPANIONS
            }
            for future in as_completed(future_to_companion):
                companion = future_to_companion[future]
                try:
                    result = future.result()
                except Exception:
                    result = None

                if result is None or "error" in result:
                    results[companion["key"]] = None
                    failed_labels.append(companion["label"])
                    # Companion names are EVIDENCE attached to one
                    # occurrence, never issues of their own -- see the
                    # module docstring. Root cause is classified per
                    # companion here purely so _dominant_root_cause() can
                    # pick the single most common cause across all of
                    # them; no per-companion record is ever written to the
                    # database individually.
                    error_message = (result or {}).get("error", "no result returned")
                    raw = (result or {}).get("raw", "")
                    tb = (result or {}).get("traceback")
                    failure_details.append({
                        "key": companion["key"],
                        "label": companion["label"],
                        "error_message": error_message,
                        "raw": raw,
                        "traceback": tb,
                        "root_cause": classify_reflection_failure_root_cause(error_message, raw, tb),
                    })
                else:
                    results[companion["key"]] = result
    finally:
        # Always release, success or failure -- see the module
        # docstring's "Concurrency control" section. Post-processing
        # below (logging, merging results) deliberately happens AFTER
        # release, so a slot is freed for the next queued request as
        # soon as the actual Claude calls are done, not after this
        # function fully returns.
        _reflection_semaphore.release()

    total = len(COMPANIONS)
    failed = len(failed_labels)

    if failed == total:
        # --- Complete Failure: exactly ONE log_error() call. ---
        root_cause = _dominant_root_cause(failure_details)
        representative = _representative_failure(failure_details)
        error_id, issue_id = log_error(
            page="reflection_space (generate reflection)",
            error_type="ReflectionGenerationFailed",
            message=(
                f"All {total} reflection companions failed to return a valid "
                f"response. Root cause: {root_cause}. Failed companions: "
                f"{', '.join(failed_labels)}."
            ),
            traceback_text=representative.get("traceback"),
            traceback_unavailable_reason=None if representative.get("traceback") else (
                "None of the 8 companions raised a Python exception on their "
                "final attempt -- every one failed because its response could "
                "not be parsed into a valid reflection. Each companion's raw "
                "response is included in 'Relevant Context' below."
            ),
            context={
                "lang": lang,
                "failed_companions": failed_labels,
                "root_cause_by_companion": {d["label"]: d["root_cause"] for d in failure_details},
                "raw_responses_by_companion": {
                    d["label"]: str(d["raw"])[:500] for d in failure_details
                },
            },
            severity="error",
            title_override=f"Reflection Generation Failed \u2013 {root_cause}",
            root_cause_hint=root_cause,
        )
        return {
            "error": "Failed to generate reflection",
            "raw": "All reflection companions failed to return a valid response.",
            "issue_id": issue_id,
            "error_id": error_id,
            "friendly_message": None,
        }

    if failed > 0:
        # --- Partial Success: exactly ONE log_error() call, warning
        # severity, and generation still proceeds -- the practitioner
        # is never interrupted (see pages/reflection_space.py's
        # non-blocking st.warning() for failed_count > 0). ---
        root_cause = _dominant_root_cause(failure_details)
        representative = _representative_failure(failure_details)
        log_error(
            page="reflection_space (generate reflection)",
            error_type="PartialReflectionGeneration",
            message=(
                f"{failed} of {total} reflection companions failed to return a "
                f"valid response; the reflection was still produced with the "
                f"rest. Root cause: {root_cause}. Failed companions: "
                f"{', '.join(failed_labels)}."
            ),
            traceback_text=representative.get("traceback"),
            traceback_unavailable_reason=None if representative.get("traceback") else (
                "None of the failed companions raised a Python exception on "
                "their final attempt -- each failed because its response "
                "could not be parsed into a valid reflection. Each one's raw "
                "response is included in 'Relevant Context' below."
            ),
            context={
                "lang": lang,
                "failed_companions": failed_labels,
                "succeeded_count": total - failed,
                "root_cause_by_companion": {d["label"]: d["root_cause"] for d in failure_details},
                "raw_responses_by_companion": {
                    d["label"]: str(d["raw"])[:500] for d in failure_details
                },
            },
            severity="warning",
            title_override="Partial Reflection Generation",
            root_cause_hint=root_cause,
        )

    # Merge into the same flat shape generate_reflection() used to
    # return, so log_reflection() (and the Learning page) keep working
    # exactly as before. Failed companions are logged as empty/not
    # flagged, same as a dimension the model found nothing notable in.
    raw_result = {}
    opportunities = []
    for companion in COMPANIONS:
        key = companion["key"]
        result = results.get(key)

        if result is None:
            raw_result[key] = {"observation": "", "questions": []}
            continue

        observation = result.get("observation", "")
        questions = result.get("questions", [])
        raw_result[key] = {"observation": observation, "questions": questions}

        opportunity = ReflectiveOpportunity(
            trigger=key,
            context=context_description,
            focus=observation,
            invitation=questions,
        )
        if not opportunity.is_empty():
            opportunities.append(opportunity)

    return {
        "opportunities": opportunities,
        "raw": raw_result,
        "failed_count": len(failed_labels),
        "failed_labels": failed_labels,
        "safe_text": safe_text,
    }