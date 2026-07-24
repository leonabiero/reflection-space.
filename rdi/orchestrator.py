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
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from services.anonymizer import anonymize
from services.reflection_service import generate_companion_reflection
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
    as one attempt succeeds, or the last {"error": ..., "raw": ...}
    seen, only after MAX_ATTEMPTS attempts have all failed.
    """
    last_result = {"error": "Failed to generate reflection", "raw": ""}

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            result = generate_companion_reflection(companion, safe_text, lang)
        except Exception as e:
            result = {"error": "API call failed", "raw": str(e)}

        if result and "error" not in result:
            return result

        last_result = result
        if attempt < MAX_ATTEMPTS:
            time.sleep(RETRY_BACKOFF_SECONDS * attempt)

    return last_result


def run_reflection(text, lang="Español", context_description=""):
    """
    Generate a reflection by running all 8 companions in parallel and
    merging their results.

    Each companion is attempted up to MAX_ATTEMPTS times (see
    _generate_companion_with_retry()) before being counted as failed --
    generation only completes once every companion has been fully
    attempted this way.

    Returns one of:
      - {"error": "...", "raw": "..."} -- only if ALL 8 companions
        failed after every retry; same shape as the old single-call
        error case, so existing error-handling code
        (pages/reflection_space.py) doesn't need to change.
      - {
          "opportunities": [ReflectiveOpportunity, ...],
          "raw": dict,                 -- for log_reflection(), unchanged shape
          "failed_count": int,         -- 0 if everything succeeded
          "failed_labels": [str, ...], -- human-readable labels of any
                                           companions that failed EVERY
                                           attempt, for an honest "N
                                           areas couldn't be generated"
                                           notice
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
            else:
                results[companion["key"]] = result

    if len(failed_labels) == len(COMPANIONS):
        # Total failure -- behave like the old single-call error case so
        # the page's existing error handling catches this unchanged.
        return {
            "error": "Failed to generate reflection",
            "raw": "All reflection companions failed to return a valid response.",
        }

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