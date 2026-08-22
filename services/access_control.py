"""Server-side authorization helpers for case-scoped access.

UI visibility is not an authorization boundary. This module provides the small
set of role/case checks needed by retrieval and deletion call paths so direct
page access or a manipulated identifier cannot silently bypass the UI.
"""

from services.db_pool import get_conn as _acquire_pooled_conn
from services.db_time import get_logger

logger = get_logger(__name__)

MANAGEMENT_ROLES = {
    "Supervisor",
    "Programme Manager",
    "System Administrator",
}


def can_access_case_history(actor_name: str, actor_role: str, case_ref: str) -> bool:
    """Return whether an authenticated actor may retrieve completed history.

    Management roles may access completed case history organisation-wide, which
    matches the existing Case History permission model. A Social Worker may
    retrieve history only for a case for which they themselves have completed
    documentation. This prevents a guessed/manipulated case reference from
    becoming a cross-worker retrieval oracle.

    The check is performed against PostgreSQL, not Streamlit UI state.
    Fail-closed on database errors.
    """
    if not actor_name or not actor_role or not case_ref or not case_ref.strip():
        return False

    if actor_role in MANAGEMENT_ROLES:
        return True

    if actor_role != "Social Worker":
        return False

    conn = None
    try:
        conn = _acquire_pooled_conn()
        with conn.cursor() as c:
            c.execute(
                """
                SELECT 1
                FROM drafts
                WHERE case_ref = %s
                  AND status = 'completed'
                  AND created_by = %s
                LIMIT 1
                """,
                (case_ref, actor_name),
            )
            return c.fetchone() is not None
    except Exception:
        logger.exception("Case access check failed; denying access")
        return False
    finally:
        if conn is not None:
            conn.close()


def require_management_role(actor_role: str) -> bool:
    """Small pure helper used by organisation-wide retrieval/deletion paths."""
    return actor_role in MANAGEMENT_ROLES
