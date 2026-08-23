from datetime import timedelta

from services.db_pool import get_conn as _acquire_pooled_conn
from services.db_time import now_utc, get_logger
import config

logger = get_logger(__name__)

# Knowledge Assistant Rate Limiter
# ===================================
#
# Reliability-hardening pass (September pilot). Same cost-safety
# reasoning as services/rate_limiter.py (the reflection-generation
# limiter), applied to the Knowledge Assistant (pages/learning.py),
# which was previously the one AI-calling feature in this app with NO
# volume cap at all -- see the accompanying handoff notes for the
# audit that found this gap.
#
# Deliberately a SEPARATE table/module from rate_limiter.py rather
# than a shared/generic one: the two features have very different
# realistic usage patterns (reflections are generated a handful of
# times per practitioner per week; Knowledge Assistant questions are
# free-form and could reasonably be asked more often in a single
# session), so they get independently tunable limits rather than
# sharing one number that would have to compromise between both.
#
# The limit itself lives in config.py (KA_MAX_PER_HOUR), not
# hard-coded here or in the page -- consistent with every other
# deployment-tunable "how many/how long" knob in this app.
#
# Fails OPEN (returns allowed=True) if the database is unreachable,
# same philosophy as rate_limiter.py -- this must never be the reason
# a practitioner or manager can't get an answer.
#
# Phase 3 load-testing fix (concurrency race, September pilot
# hardening): this module used to read the current count and then
# separately insert a new row, with nothing stopping two of a person's
# questions arriving at almost the same moment (e.g. a slow connection
# causing a resend, or two browser tabs) from BOTH reading a count
# below the limit and BOTH inserting -- letting someone exceed
# KA_MAX_PER_HOUR by a call or two. services/rate_limiter.py already
# solved exactly this problem for reflection generation using a
# PostgreSQL "advisory transaction lock" (pg_advisory_xact_lock) keyed
# per user, which makes the read-count-then-insert sequence atomic for
# that one user without needing to lock the whole table for everyone
# else. This module now does the same thing, for the same reason -- see
# tests/test_scalability_ka_rate_limiter_concurrency.py for a
# concurrency test that would have failed against the old code.

WINDOW_MINUTES = 60
CLEANUP_HOURS = 24


def _get_conn():
    return _acquire_pooled_conn()


def check_and_record(user_name, max_per_hour=None):
    """
    Call this ONCE, right before asking the Knowledge Assistant a
    question (i.e. right before services.knowledge_assistant.ask() is
    called).

    Returns (allowed, current_count) -- identical shape and meaning to
    services.rate_limiter.check_and_record(). If allowed is True, the
    new question is also recorded immediately, so the count is
    accurate for the very next call.

    max_per_hour defaults to config.KA_MAX_PER_HOUR if not given.
    """
    if max_per_hour is None:
        max_per_hour = config.KA_MAX_PER_HOUR

    if not user_name:
        return True, 0

    conn = None
    try:
        conn = _get_conn()
        try:
            with conn.cursor() as c:
                now = now_utc()
                window_start = now - timedelta(minutes=WINDOW_MINUTES)
                cleanup_cutoff = now - timedelta(hours=CLEANUP_HOURS)

                # Reliability boundary: serialize the check + insert for
                # this user at the database transaction level, exactly
                # like services/rate_limiter.py -- see the Phase 3 note
                # above for why this is needed.
                c.execute(
                    "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                    (user_name,),
                )

                c.execute("DELETE FROM ka_rate_log WHERE occurred_at < %s", (cleanup_cutoff,))

                c.execute(
                    "SELECT COUNT(*) FROM ka_rate_log WHERE user_name = %s AND occurred_at >= %s",
                    (user_name, window_start),
                )
                (count,) = c.fetchone()

                if count >= max_per_hour:
                    conn.commit()
                    return False, count

                c.execute(
                    "INSERT INTO ka_rate_log (user_name, occurred_at) VALUES (%s, %s)",
                    (user_name, now),
                )
            conn.commit()
            return True, count + 1
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    except Exception:
        logger.warning("ka_rate_limiter.check_and_record FAILED (failing open)", exc_info=True)
        return True, 0
