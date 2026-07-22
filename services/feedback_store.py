import psycopg2
from datetime import datetime
from config import DATABASE_URL


def _get_conn():
    conn = psycopg2.connect(DATABASE_URL)
    with conn.cursor() as c:
        c.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id SERIAL PRIMARY KEY,
            draft_ids TEXT,
            rating INTEGER,
            comment TEXT,
            submitted_by TEXT,
            submitted_by_role TEXT,
            submitted_at TEXT
        )
        """)
    conn.commit()
    return conn


def save_feedback(draft_ids, rating, comment, submitted_by="", submitted_by_role=""):
    conn = _get_conn()
    with conn.cursor() as c:
        c.execute("""
            INSERT INTO feedback (draft_ids, rating, comment, submitted_by, submitted_by_role, submitted_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            ",".join(str(d) for d in draft_ids),
            rating,
            comment,
            submitted_by,
            submitted_by_role,
            datetime.now().isoformat(),
        ))
    conn.commit()
    conn.close()


def get_all_feedback():
    conn = _get_conn()
    with conn.cursor() as c:
        c.execute("""
            SELECT id, draft_ids, rating, comment, submitted_by, submitted_by_role, submitted_at
            FROM feedback ORDER BY submitted_at DESC
        """)
        rows = c.fetchall()
    conn.close()
    return rows


def get_feedback_summary():
    """
    Sprint 10 (Research Metrics): aggregate usefulness-rating stats with
    no professional or case attribution -- just how useful the
    reflection process is rated, org-wide.

    Returns:
        {
            "count": int,                         # ratings submitted
            "average": float | None,               # None if count == 0
            "distribution": {1: n, 2: n, ..., 5: n},
            "comment_count": int,                  # how many left a comment
        }
    """
    conn = _get_conn()
    with conn.cursor() as c:
        c.execute("SELECT rating, comment FROM feedback")
        rows = c.fetchall()
    conn.close()

    distribution = {i: 0 for i in range(1, 6)}
    comment_count = 0
    ratings = []

    for rating, comment in rows:
        if rating in distribution:
            distribution[rating] += 1
        if rating is not None:
            ratings.append(rating)
        if comment and comment.strip():
            comment_count += 1

    average = (sum(ratings) / len(ratings)) if ratings else None

    return {
        "count": len(rows),
        "average": average,
        "distribution": distribution,
        "comment_count": comment_count,
    }