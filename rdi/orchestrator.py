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
"""

from concurrent.futures import ThreadPoolExecutor, as_completed

from services.anonymizer import anonymize
from services.reflection_service import generate_companion_reflection
from rdi.companions import COMPANIONS
from rdi.reflection_objects import ReflectiveOpportunity


def run_reflection(text, lang="Español", context_description=""):
    """
    Generate a reflection by running all 8 companions in parallel and
    merging their results.

    Returns one of:
      - {"error": "...", "raw": "..."} -- only if ALL 8 companions
        failed; same shape as the old single-call error case, so
        existing error-handling code (pages/reflection_space.py) doesn't
        need to change.
      - {
          "opportunities": [ReflectiveOpportunity, ...],
          "raw": dict,                 -- for log_reflection(), unchanged shape
          "failed_count": int,         -- 0 if everything succeeded
          "failed_labels": [str, ...], -- human-readable labels of any
                                           companions that failed, for an
                                           honest "N areas couldn't be
                                           generated" notice
        }
    """
    safe_text = anonymize(text)

    results = {}   # key -> companion result dict or None on failure
    failed_labels = []

    with ThreadPoolExecutor(max_workers=len(COMPANIONS)) as executor:
        future_to_companion = {
            executor.submit(generate_companion_reflection, companion, safe_text, lang): companion
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
    }