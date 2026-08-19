"""
One-shot recovery for a companion that exhausted the normal retries.

The normal reflection generation path already gives each companion up to
three attempts. This module deliberately does NOT reuse that retry loop.
A practitioner-triggered recovery is exactly one additional API call for
one companion. If that call fails, the failure is logged as an issue and
there is no further retry path for that session.
"""

import traceback

from rdi.companions import COMPANIONS
from services.error_log import log_error
from services.issue_fingerprint import classify_reflection_failure_root_cause
from services.reflection_service import generate_companion_reflection


def retry_companion_once(companion_key, safe_text, lang):
    """Make exactly one API attempt for one previously failed companion.

    Returns either:
      {"success": True, "result": {"observation": ..., "questions": [...]}}
    or:
      {"success": False, "issue_id": ..., "error_id": ..., "root_cause": ...}

    No retry/backoff/thread-pool is used here. The caller is responsible for
    replacing the failed placeholder or marking the companion permanently
    unavailable for this reflection session.
    """
    companion = next((c for c in COMPANIONS if c["key"] == companion_key), None)
    if companion is None:
        return {"success": False, "issue_id": None, "error_id": None, "root_cause": "Unknown"}

    try:
        result = generate_companion_reflection(companion, safe_text, lang)
    except Exception as exc:
        error_message = "API call failed"
        raw = str(exc)
        tb = traceback.format_exc()
        root_cause = classify_reflection_failure_root_cause(error_message, raw, tb)
        error_id, issue_id = log_error(
            page="reflection_space (companion retry)",
            error_type="ManualCompanionRetryFailed",
            message=(
                f"The one-shot practitioner retry failed for companion "
                f"{companion['label']}. Root cause: {root_cause}."
            ),
            traceback_text=tb,
            traceback_unavailable_reason=None,
            context={
                "companion_key": companion_key,
                "companion_label": companion["label"],
                "root_cause": root_cause,
            },
            severity="error",
            title_override=f"Companion Retry Failed – {root_cause}",
            root_cause_hint=root_cause,
        )
        return {
            "success": False,
            "issue_id": issue_id,
            "error_id": error_id,
            "root_cause": root_cause,
        }

    if result and "error" not in result:
        return {"success": True, "result": result}

    error_message = (result or {}).get("error", "Companion retry returned no usable result")
    raw = (result or {}).get("raw", "")
    root_cause = classify_reflection_failure_root_cause(error_message, raw, None)
    error_id, issue_id = log_error(
        page="reflection_space (companion retry)",
        error_type="ManualCompanionRetryFailed",
        message=(
            f"The one-shot practitioner retry failed for companion "
            f"{companion['label']}. Root cause: {root_cause}."
        ),
        traceback_text=None,
        traceback_unavailable_reason=(
            "The companion call returned without a valid reflection and did not "
            "raise a Python exception. The raw response is intentionally not "
            "stored here because logs must not contain case content."
        ),
        context={
            "companion_key": companion_key,
            "companion_label": companion["label"],
            "root_cause": root_cause,
        },
        severity="error",
        title_override=f"Companion Retry Failed – {root_cause}",
        root_cause_hint=root_cause,
    )
    return {
        "success": False,
        "issue_id": issue_id,
        "error_id": error_id,
        "root_cause": root_cause,
    }
