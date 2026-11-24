"""
Demo data (17 November 2026 -- product owner's decision, see DEMO.md)
=======================================================================

To show Pattern Review to EDE's staff and management, the app needs about
70 texts written over many months. Real texts must never be used for that,
and fictional texts must never reach the real pilot's database (they would
appear in real Pattern Review reports and stay for 15 months).

So demonstrations use a SEPARATE app connected to a SEPARATE, empty
database (DEMO.md explains how to set it up). This module loads the
fictional texts (services/demo_texts.py) into that database, and removes
them again.

Locks -- all checked HERE, in the service layer, not only on screen
---------------------------------------------------------------------
1. config.DEMO_MODE must be on. Only the demo app's secrets set it.
2. Each database is LABELLED the first time an app connects to it
   (app_settings key "database_purpose"):
     - the real app (DEMO_MODE off) labels an unlabelled database "live";
     - the demo app (DEMO_MODE on) labels an unlabelled database "demo",
       but ONLY if it holds no reflections and no ratings at all.
   A label is never changed by the app afterwards, and "Erase all data"
   keeps it (it keeps app_settings).
3. Demo texts are only ever loaded into a database labelled "demo". The
   demo app pointed at the real database therefore refuses to load
   anything, and says so on every page; the real app pointed at the demo
   database shows a warning on every page.
4. Only the System Administrator can load or remove demo data.
5. Every demo row is marked: its author starts with DEMO_AUTHOR_PREFIX
   ("demo:"), so removing demo data removes exactly those rows.

Nothing here calls an AI: loading the texts costs nothing. Texts are never
written to logs -- only counts.
"""

import json
import time
from datetime import timedelta

from services.db_pool import get_conn as _acquire_pooled_conn
from services.db_time import now_utc, get_logger
from services.audit_log import log_action
from services.reflection_records import generate_code
from services.text_fingerprint import text_fingerprint

logger = get_logger(__name__)

ADMIN_ROLE = "System Administrator"
PURPOSE_KEY = "database_purpose"
PURPOSE_LIVE = "live"
PURPOSE_DEMO = "demo"
DEMO_AUTHOR_PREFIX = "demo:"
DEMO_PROMPT_VERSION = "demo-data-2026-11"
DEMO_AUTHOR_ROLE = "Social Worker"

_STATUS_CACHE_SECONDS = 300
_status_cache = {"at": 0.0, "value": None}


def _get_conn():
    return _acquire_pooled_conn()


def demo_mode_on():
    from config import DEMO_MODE
    return bool(DEMO_MODE)


# ---------------------------------------------------------------------
# Database label
# ---------------------------------------------------------------------
def _read_label(cursor):
    cursor.execute("SELECT value FROM app_settings WHERE key = %s", (PURPOSE_KEY,))
    row = cursor.fetchone()
    return row[0] if row else None


def _holds_any_data(cursor):
    """True if the database holds any reflection or rating at all."""
    cursor.execute("SELECT EXISTS (SELECT 1 FROM reflection_runs) OR EXISTS (SELECT 1 FROM feedback)")
    return bool(cursor.fetchone()[0])


def label_database():
    """Label an unlabelled database (see lock 2 in the module docstring).
    Called once at startup (app.py). Returns the label afterwards: "live",
    "demo", or None (the demo app found a database that already holds
    data and is not labelled -- it is then NOT labelled "demo")."""
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            label = _read_label(c)
            if label is None:
                if not demo_mode_on():
                    label = PURPOSE_LIVE
                elif not _holds_any_data(c):
                    label = PURPOSE_DEMO
                if label is not None:
                    c.execute(
                        "INSERT INTO app_settings (key, value) VALUES (%s, %s) "
                        "ON CONFLICT (key) DO NOTHING",
                        (PURPOSE_KEY, label),
                    )
                    label = _read_label(c)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    _status_cache["at"] = 0.0
    return label


def database_label():
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            return _read_label(c)
    finally:
        conn.close()


def check_status():
    """What the banner and the System Administration section show:

    {"demo_mode": bool, "label": "live" | "demo" | None,
     "problem": None | "demo_app_on_real_database" | "real_app_on_demo_database"}

    Cached for a few minutes (it is read on every page)."""
    now = time.monotonic()
    cached = _status_cache["value"]
    if cached is not None and now - _status_cache["at"] < _STATUS_CACHE_SECONDS:
        return dict(cached)
    demo = demo_mode_on()
    label = database_label()
    problem = None
    if demo and label != PURPOSE_DEMO:
        problem = "demo_app_on_real_database"
    elif not demo and label == PURPOSE_DEMO:
        problem = "real_app_on_demo_database"
    value = {"demo_mode": demo, "label": label, "problem": problem}
    _status_cache.update(at=now, value=value)
    return dict(value)


def may_use_demo_data(actor_role):
    """True only in the demo app, on a database labelled "demo", for the
    System Administrator (locks 1, 3 and 4)."""
    if actor_role != ADMIN_ROLE or not demo_mode_on():
        return False
    try:
        return database_label() == PURPOSE_DEMO
    except Exception:
        return False


# ---------------------------------------------------------------------
# Counting, loading, removing
# ---------------------------------------------------------------------
def demo_counts():
    """How many demo texts and demo ratings are in the database."""
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            c.execute("SELECT COUNT(*) FROM reflection_runs WHERE created_by LIKE %s",
                      (DEMO_AUTHOR_PREFIX + "%",))
            texts = c.fetchone()[0] or 0
            c.execute("SELECT COUNT(*) FROM feedback WHERE submitted_by LIKE %s",
                      (DEMO_AUTHOR_PREFIX + "%",))
            ratings = c.fetchone()[0] or 0
    finally:
        conn.close()
    return {"texts": texts, "ratings": ratings}


def planned_rows(now=None):
    """The rows load_demo_data() writes, without touching the database:
    ([text rows], [rating rows]). Each text row: author, language, text,
    created_at. Each rating row: author, rating, submitted_at."""
    from services.demo_texts import DEMO_TEXTS, DEMO_RATINGS
    now = now or now_utc()
    texts = []
    for item in DEMO_TEXTS:
        texts.append({
            "author": DEMO_AUTHOR_PREFIX + item["author"],
            "language": item["language"],
            "text": item["text"].strip(),
            "created_at": now - timedelta(days=item["days_ago"], hours=item.get("hour_offset", 0)),
        })
    ratings = []
    for days_ago, rating, author in DEMO_RATINGS:
        ratings.append({
            "author": DEMO_AUTHOR_PREFIX + author,
            "rating": int(rating),
            "submitted_at": now - timedelta(days=days_ago, hours=2),
        })
    return texts, ratings


def load_demo_data(actor_name, actor_role):
    """Load the fictional texts and ratings. Returns
    {"status": "ok", "texts": n, "ratings": n}, or {"status": reason} with
    reason "refused" (locks), "already_loaded". Raises on a database
    failure (single transaction: then nothing was loaded)."""
    if not actor_name or not may_use_demo_data(actor_role):
        return {"status": "refused"}
    if demo_counts()["texts"]:
        return {"status": "already_loaded"}

    texts, ratings = planned_rows()
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            # Check the label again inside the transaction.
            if _read_label(c) != PURPOSE_DEMO:
                conn.rollback()
                return {"status": "refused"}
            used = set()
            for row in texts:
                code = generate_code()
                while code in used:
                    code = generate_code()
                used.add(code)
                c.execute(
                    """
                    INSERT INTO reflection_runs
                        (case_ref, language, prompt_version, model, module_status,
                         created_by, created_by_role, created_at,
                         reflection_code, original_text, text_fingerprint)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (code, row["language"], DEMO_PROMPT_VERSION, None, json.dumps({}),
                     row["author"], DEMO_AUTHOR_ROLE, row["created_at"], code, row["text"],
                     # Same coded fingerprint as a real reflection (24 Nov 2026).
                     text_fingerprint(row["text"])),
                )
            for row in ratings:
                c.execute(
                    """
                    INSERT INTO feedback (draft_ids, rating, comment, submitted_by,
                                          submitted_by_role, submitted_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    ("", row["rating"], "", row["author"], DEMO_AUTHOR_ROLE, row["submitted_at"]),
                )
        conn.commit()
    except Exception:
        conn.rollback()
        logger.exception("load_demo_data FAILED (rolled back, nothing loaded)")
        raise
    finally:
        conn.close()

    logger.info("Demo data loaded: %d texts, %d ratings", len(texts), len(ratings))
    _audit(actor_name, actor_role, f"demo data loaded: {len(texts)} texts, {len(ratings)} ratings")
    return {"status": "ok", "texts": len(texts), "ratings": len(ratings)}


def remove_demo_data(actor_name, actor_role):
    """Remove every demo text and rating, and the Pattern Review reports
    made in this demo database. Returns {"status": "ok", "texts": n,
    "ratings": n, "reports": n} or {"status": "refused"}. Raises on a
    database failure (single transaction: then nothing was removed)."""
    if not actor_name or not may_use_demo_data(actor_role):
        return {"status": "refused"}
    conn = _get_conn()
    try:
        with conn.cursor() as c:
            if _read_label(c) != PURPOSE_DEMO:
                conn.rollback()
                return {"status": "refused"}
            like = DEMO_AUTHOR_PREFIX + "%"
            c.execute(
                "DELETE FROM reflection_findings WHERE run_id IN "
                "(SELECT id FROM reflection_runs WHERE created_by LIKE %s)", (like,),
            )
            c.execute(
                "DELETE FROM reflection_run_sources WHERE run_id IN "
                "(SELECT id FROM reflection_runs WHERE created_by LIKE %s)", (like,),
            )
            c.execute("DELETE FROM reflection_runs WHERE created_by LIKE %s", (like,))
            texts = c.rowcount
            c.execute("DELETE FROM feedback WHERE submitted_by LIKE %s", (like,))
            ratings = c.rowcount
            # Every report in a demo database was made from demo texts.
            c.execute("DELETE FROM pattern_reports")
            reports = c.rowcount
        conn.commit()
    except Exception:
        conn.rollback()
        logger.exception("remove_demo_data FAILED (rolled back, nothing removed)")
        raise
    finally:
        conn.close()

    logger.info("Demo data removed: %d texts, %d ratings, %d reports", texts, ratings, reports)
    _audit(actor_name, actor_role,
           f"demo data removed: {texts} texts, {ratings} ratings, {reports} reports")
    return {"status": "ok", "texts": texts, "ratings": ratings, "reports": reports}


def _audit(actor_name, actor_role, details):
    try:
        log_action("purged", None, "", "demo data", actor_name, actor_role, details=details)
    except Exception:
        logger.exception("demo data: could not write the audit line")
