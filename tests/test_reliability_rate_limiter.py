import threading
import unittest
from unittest.mock import patch


class _FakeCursor:
    def __init__(self, db):
        self.db = db
        self._result = None
        self.rowcount = 0
        self._lock_held = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        sql_upper = " ".join(sql.split()).upper()
        params = params or ()
        self.rowcount = 0

        if "PG_ADVISORY_XACT_LOCK" in sql_upper:
            self.db.lock.acquire()
            self._lock_held = True
            return

        if sql_upper.startswith("DELETE FROM REFLECTION_RATE_LOG"):
            return

        if sql_upper.startswith("SELECT COUNT(*) FROM REFLECTION_RATE_LOG"):
            username = params[0]
            with self.db.data_lock:
                self._result = (sum(1 for row in self.db.rows if row == username),)
            return

        if sql_upper.startswith("INSERT INTO REFLECTION_RATE_LOG"):
            username = params[0]
            with self.db.data_lock:
                self.db.rows.append(username)
            self.rowcount = 1
            return

        raise AssertionError(f"Unexpected SQL in fake database: {sql}")

    def fetchone(self):
        return self._result


class _FakeConnection:
    def __init__(self, db):
        self.db = db
        self.cursor_obj = _FakeCursor(db)

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        if self.cursor_obj._lock_held:
            self.cursor_obj._lock_held = False
            self.db.lock.release()

    def rollback(self):
        if self.cursor_obj._lock_held:
            self.cursor_obj._lock_held = False
            self.db.lock.release()

    def close(self):
        return None


class _FakeDatabase:
    def __init__(self):
        self.rows = []
        self.lock = threading.RLock()
        self.data_lock = threading.Lock()

    def connection(self):
        return _FakeConnection(self)


class RateLimiterReliabilityTests(unittest.TestCase):
    def test_user_scoped_database_lock_precedes_count(self):
        from services import rate_limiter

        db = _FakeDatabase()
        with patch.object(rate_limiter, "_get_conn", side_effect=db.connection):
            allowed, count = rate_limiter.check_and_record("alice", max_per_hour=2)

        self.assertTrue(allowed)
        self.assertEqual(count, 1)
        self.assertEqual(db.rows, ["alice"])

    def test_concurrent_requests_cannot_both_pass_final_slot(self):
        from services import rate_limiter

        db = _FakeDatabase()
        results = []
        start = threading.Barrier(2)

        def worker():
            start.wait()
            results.append(rate_limiter.check_and_record("alice", max_per_hour=1))

        with patch.object(rate_limiter, "_get_conn", side_effect=db.connection):
            threads = [threading.Thread(target=worker) for _ in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=5)

        self.assertEqual(len(results), 2)
        self.assertEqual(sum(1 for allowed, _ in results if allowed), 1)
        self.assertEqual(sum(1 for allowed, _ in results if not allowed), 1)
        self.assertEqual(db.rows.count("alice"), 1)

    def test_empty_user_fails_open_without_database_call(self):
        from services import rate_limiter

        with patch.object(rate_limiter, "_get_conn") as get_conn:
            self.assertEqual(rate_limiter.check_and_record("", max_per_hour=1), (True, 0))
            get_conn.assert_not_called()

    def test_database_failure_fails_open(self):
        from services import rate_limiter

        with patch.object(rate_limiter, "_get_conn", side_effect=RuntimeError("db down")):
            self.assertEqual(rate_limiter.check_and_record("alice", max_per_hour=1), (True, 0))


if __name__ == "__main__":
    unittest.main()
