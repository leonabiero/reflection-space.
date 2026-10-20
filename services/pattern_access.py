"""
Pattern Explorer access rules
===============================

Who may open the pattern explorer. The decision (October 2026) is that it
is for EDE's management team: Supervisors and Programme Managers. The
System Administrator role is deliberately NOT included -- administering
the system does not require reading practitioners' shared reflections.
To widen access later, change PATTERN_REVIEW_ROLES here; every check in
the app reads this one set.

The check is enforced in the DATA layer (services/pattern_store.py calls
require_pattern_role() at the top of every function), not just by hiding
the page link, so a direct URL or a manipulated request cannot bypass it.
"""

PATTERN_REVIEW_ROLES = frozenset({"Supervisor", "Programme Manager"})


def can_review_patterns(role):
    """True if this authenticated role may use the pattern explorer."""
    return role in PATTERN_REVIEW_ROLES


def require_pattern_role(role):
    """Raise PermissionError unless `role` may use the pattern explorer."""
    if not can_review_patterns(role):
        raise PermissionError("Not permitted to use the pattern explorer")
