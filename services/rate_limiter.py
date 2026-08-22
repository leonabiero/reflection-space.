from datetime import datetime, timedelta
from services.db_pool import get_conn as _acquire_pooled_conn

DEFAULT_MAX_PER_HOUR = 20
WINDOW_MINUTES = 60
CLEANUP_HOURS = 24


def _get_conn():
    return _acquire_pooled_conn()


def check_and_record(user_name, max_per_hour=DEFAULT_MAX_PER_HOUR):
    """Atomically check and record one reflection for a user.

    The per-user PostgreSQL advisory transaction lock closes the
    check-then-insert race: concurrent requests for the same user are
    serialized before either request reads the current count.

    Returns (allowed, current_count). Fails open if the limiter database
    is unavailable, preserving the application's existing graceful
    degradation policy.
    """
    if not user_name:
        return True, 0

    conn = None
    try:
        conn = _get_conn()
        try:
            with conn.cursor() as c:
                now = datetime.now()
                window_start = (now - timedelta(minutes=WINDOW_MINUTES)).isoformat()
                cleanup_cutoff = (now - timedelta(hours=CLEANUP_HOURS)).isoformat()

                # Transaction-scoped PostgreSQL advisory lock. This is the
                # critical reliability boundary: SELECT COUNT followed by
                # INSERT must behave as one serialized operation for a user.
                # hashtextextended gives a stable bigint advisory-lock key;
                # a rare hash collision only serializes unrelated users and
                # cannot allow the limit to be exceeded.
                c.execute(
                    "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                    (user_name,),
                )

                c.execute(
                    "DELETE FROM reflection_rate_log WHERE occurred_at < %s",
                    (cleanup_cutoff,),
                )

                c.execute(
                    "SELECT COUNT(*) FROM reflection_rate_log WHERE user_name = %s AND occurred_at >= %s",
                    (user_name, window_start),
                )
                (count,) = c.fetchone()

                if count >= max_per_hour:
                    conn.commit()
                    return False, count

                c.execute(
                    "INSERT INTO reflection_rate_log (user_name, occurred_at) VALUES (%s, %s)",
                    (user_name, now.isoformat()),
                )
            conn.commit()
            return True, count + 1
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    except Exception:
        return True, 0
