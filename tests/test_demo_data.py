"""
Demo data (17 November 2026, see DEMO.md).

Protects the product owner's rule: fictional demo texts must NEVER mix
with the real pilot's data. Checked here:
  - the fictional texts themselves (how many, languages, spread over
    13 months, inside the 15-month limit, enough in the last month);
  - the locks in services/demo_data.py: demo mode must be on, the
    database must be labelled "demo", System Administrator only;
  - how a database gets its "live" / "demo" label;
  - removal touches only demo rows;
  - the screens: banner on every page, section only in demo mode,
    every text in Spanish, Basque and English;
  - no password or password hash in the code.
"""

import importlib.util
import re
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def _read(*parts):
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


def _load_locale(lang):
    spec = importlib.util.spec_from_file_location(f"loc_demo_{lang}", ROOT / "services" / "locales" / f"{lang}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return next(v for v in vars(module).values() if isinstance(v, dict) and "rs_finish_button" in v)


# ---------------------------------------------------------------------
# A small fake database (no real database needed)
# ---------------------------------------------------------------------
class FakeDB:
    def __init__(self, label=None, real_rows=0, demo_rows=0, ratings=0, reports=0):
        self.label = label
        self.real_rows = real_rows
        self.demo_rows = demo_rows
        self.ratings = ratings
        self.reports = reports
        self.inserted_runs = []
        self.inserted_feedback = []
        self.deletes = []
        self.connections = 0
        self.commits = 0

    def connect(self):
        self.connections += 1
        return FakeConn(self)


class FakeConn:
    def __init__(self, db):
        self.db = db

    def cursor(self):
        return FakeCursor(self.db)

    def commit(self):
        self.db.commits += 1

    def rollback(self):
        pass

    def close(self):
        pass


class FakeCursor:
    def __init__(self, db):
        self.db = db
        self._row = None
        self.rowcount = 0

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=()):
        db = self.db
        s = " ".join(sql.split())
        if s.startswith("SELECT value FROM app_settings"):
            self._row = (db.label,) if db.label is not None else None
        elif s.startswith("SELECT EXISTS"):
            self._row = (bool(db.real_rows or db.demo_rows or db.ratings),)
        elif s.startswith("INSERT INTO app_settings"):
            if db.label is None:
                db.label = params[1]
        elif s.startswith("SELECT COUNT(*) FROM reflection_runs"):
            assert params == ("demo:%",), params
            self._row = (db.demo_rows,)
        elif s.startswith("SELECT COUNT(*) FROM feedback"):
            assert params == ("demo:%",), params
            self._row = (db.ratings,)
        elif s.startswith("INSERT INTO reflection_runs"):
            db.inserted_runs.append(params)
        elif s.startswith("INSERT INTO feedback"):
            db.inserted_feedback.append(params)
        elif s.startswith("DELETE"):
            db.deletes.append((s, params))
            if s.startswith("DELETE FROM reflection_runs"):
                self.rowcount = db.demo_rows
            elif s.startswith("DELETE FROM feedback"):
                self.rowcount = db.ratings
            elif s.startswith("DELETE FROM pattern_reports"):
                self.rowcount = db.reports
            else:
                self.rowcount = 0
        else:
            raise AssertionError(f"unexpected SQL: {s}")

    def fetchone(self):
        return self._row


def _use(db, demo_mode):
    """Patch the module to use the fake database and the given mode."""
    from services import demo_data
    demo_data._status_cache.update(at=0.0, value=None)
    return [
        mock.patch.object(demo_data, "_get_conn", side_effect=db.connect),
        mock.patch("config.DEMO_MODE", demo_mode),
        mock.patch.object(demo_data, "log_action"),
    ]


class _Patched:
    def __init__(self, db, demo_mode):
        self.patches = _use(db, demo_mode)

    def __enter__(self):
        for p in self.patches:
            p.start()

    def __exit__(self, *exc):
        for p in reversed(self.patches):
            p.stop()
        return False


ADMIN = "System Administrator"


# ---------------------------------------------------------------------
# The fictional texts
# ---------------------------------------------------------------------
class DemoTextTests(unittest.TestCase):
    def setUp(self):
        from services.demo_texts import DEMO_TEXTS, DEMO_RATINGS
        self.texts = DEMO_TEXTS
        self.ratings = DEMO_RATINGS

    def test_between_60_and_80_texts_mostly_spanish_some_basque(self):
        self.assertTrue(60 <= len(self.texts) <= 80, len(self.texts))
        langs = [t["language"] for t in self.texts]
        self.assertEqual(set(langs), {"Español", "Euskera"})
        self.assertGreater(langs.count("Español"), langs.count("Euskera"))
        self.assertGreaterEqual(langs.count("Euskera"), 10)

    def test_spread_over_13_months_inside_the_15_month_limit(self):
        import config
        days = [t["days_ago"] for t in self.texts]
        self.assertGreaterEqual(max(days), 360)
        self.assertLessEqual(max(days), 13 * 31)
        self.assertLess(max(days), config.ORIGINAL_TEXT_RETENTION_MONTHS * 30)
        self.assertGreaterEqual(min(days), 0)
        # Every month of the 13 has texts.
        for month in range(13):
            in_month = [d for d in days if month * 30 <= d < (month + 1) * 30]
            self.assertTrue(in_month, f"no text in month {month + 1}")
        # Even a 1-month Pattern Review has more than the minimum of 5.
        self.assertGreater(len([d for d in days if d < 28]), config.PATTERN_MIN_TEXTS)

    def test_both_languages_appear_across_the_whole_period(self):
        basque_days = [t["days_ago"] for t in self.texts if t["language"] == "Euskera"]
        self.assertLess(min(basque_days), 60)
        self.assertGreater(max(basque_days), 300)

    def test_texts_are_real_notes_with_deliberate_patterns(self):
        joined = " ".join(t["text"] for t in self.texts).lower()
        for marker in ("se le exige", "desestructurada", "manipuladora", "se decide",
                       "lo de siempre", "eskatu zaio"):
            self.assertIn(marker, joined)
        for t in self.texts:
            self.assertTrue(t["text"].strip())
            self.assertTrue(re.fullmatch(r"ts0[1-8]", t["author"]), t["author"])

    def test_some_texts_mention_sensitive_details_for_the_anonymiser_demo(self):
        joined = " ".join(t["text"] for t in self.texts).lower()
        for word in ("gay", "lesbiana", "bisexual", "trans", "esquizofrenia", "vih",
                     "sertralina", "eskizofrenia"):
            self.assertIn(word, joined)

    def test_twenty_ratings_from_one_to_five(self):
        self.assertEqual(len(self.ratings), 20)
        for days_ago, rating, author in self.ratings:
            self.assertTrue(1 <= rating <= 5)
            self.assertTrue(0 <= days_ago <= 13 * 31)
            self.assertTrue(author.startswith("ts"))

    def test_every_planned_row_is_marked_as_demo(self):
        from services import demo_data
        now = datetime(2026, 11, 17, 12, tzinfo=timezone.utc)
        texts, ratings = demo_data.planned_rows(now)
        self.assertEqual(len(texts), len(self.texts))
        for row in texts:
            self.assertTrue(row["author"].startswith("demo:"))
            self.assertLess(row["created_at"], now)
            self.assertGreater(row["created_at"], now - timedelta(days=13 * 31 + 1))
        for row in ratings:
            self.assertTrue(row["author"].startswith("demo:"))


# ---------------------------------------------------------------------
# Database label
# ---------------------------------------------------------------------
class DatabaseLabelTests(unittest.TestCase):
    def test_real_app_labels_its_database_live(self):
        from services import demo_data
        db = FakeDB(label=None, real_rows=40)
        with _Patched(db, demo_mode=False):
            self.assertEqual(demo_data.label_database(), "live")
        self.assertEqual(db.label, "live")

    def test_demo_app_labels_an_empty_database_demo(self):
        from services import demo_data
        db = FakeDB(label=None)
        with _Patched(db, demo_mode=True):
            self.assertEqual(demo_data.label_database(), "demo")

    def test_demo_app_never_labels_a_database_with_data(self):
        from services import demo_data
        for db in (FakeDB(real_rows=1), FakeDB(ratings=1)):
            with _Patched(db, demo_mode=True):
                self.assertIsNone(demo_data.label_database())
            self.assertIsNone(db.label)

    def test_a_label_is_never_changed(self):
        from services import demo_data
        live = FakeDB(label="live")
        with _Patched(live, demo_mode=True):
            self.assertEqual(demo_data.label_database(), "live")
        demo = FakeDB(label="demo")
        with _Patched(demo, demo_mode=False):
            self.assertEqual(demo_data.label_database(), "demo")

    def test_status_reports_the_wrong_database_both_ways(self):
        from services import demo_data
        cases = [
            (True, "live", "demo_app_on_real_database"),
            (True, None, "demo_app_on_real_database"),
            (False, "demo", "real_app_on_demo_database"),
            (True, "demo", None),
            (False, "live", None),
            (False, None, None),
        ]
        for mode, label, problem in cases:
            with _Patched(FakeDB(label=label), demo_mode=mode):
                status = demo_data.check_status()
            self.assertEqual(status["problem"], problem, (mode, label))
            self.assertEqual(status["demo_mode"], mode)


# ---------------------------------------------------------------------
# Loading and removing
# ---------------------------------------------------------------------
class LoadAndRemoveTests(unittest.TestCase):
    def test_loading_works_only_in_the_demo_app_on_the_demo_database(self):
        from services import demo_data
        from services.demo_texts import DEMO_TEXTS, DEMO_RATINGS
        db = FakeDB(label="demo")
        with _Patched(db, demo_mode=True):
            result = demo_data.load_demo_data("Demo admin", ADMIN)
        self.assertEqual(result, {"status": "ok", "texts": len(DEMO_TEXTS), "ratings": len(DEMO_RATINGS)})
        self.assertEqual(len(db.inserted_runs), len(DEMO_TEXTS))
        self.assertEqual(len(db.inserted_feedback), len(DEMO_RATINGS))
        for params in db.inserted_runs:
            self.assertTrue(params[5].startswith("demo:"))     # created_by
            self.assertEqual(params[2], demo_data.DEMO_PROMPT_VERSION)
        for params in db.inserted_feedback:
            self.assertTrue(params[3].startswith("demo:"))     # submitted_by
        self.assertEqual(len({p[8] for p in db.inserted_runs}), len(DEMO_TEXTS))  # unique codes

    def test_real_app_never_loads_demo_texts(self):
        from services import demo_data
        for label in ("live", "demo", None):
            db = FakeDB(label=label)
            with _Patched(db, demo_mode=False):
                self.assertEqual(demo_data.load_demo_data("Admin", ADMIN), {"status": "refused"})
                self.assertEqual(demo_data.remove_demo_data("Admin", ADMIN), {"status": "refused"})
            self.assertEqual(db.inserted_runs, [])
            self.assertEqual(db.deletes, [])
            self.assertEqual(db.connections, 0)

    def test_demo_app_on_the_real_database_loads_nothing(self):
        from services import demo_data
        for label in ("live", None):
            db = FakeDB(label=label, real_rows=120)
            with _Patched(db, demo_mode=True):
                self.assertEqual(demo_data.load_demo_data("Admin", ADMIN), {"status": "refused"})
                self.assertEqual(demo_data.remove_demo_data("Admin", ADMIN), {"status": "refused"})
            self.assertEqual(db.inserted_runs, [])
            self.assertEqual(db.inserted_feedback, [])
            self.assertEqual(db.deletes, [])

    def test_only_the_system_administrator(self):
        from services import demo_data
        for role in ("Social Worker", "Supervisor", "Programme Manager", "", None):
            db = FakeDB(label="demo")
            with _Patched(db, demo_mode=True):
                self.assertEqual(demo_data.load_demo_data("Someone", role), {"status": "refused"})
                self.assertEqual(demo_data.remove_demo_data("Someone", role), {"status": "refused"})
            self.assertEqual(db.connections, 0)
        with _Patched(FakeDB(label="demo"), demo_mode=True):
            self.assertEqual(demo_data.load_demo_data("", ADMIN), {"status": "refused"})

    def test_loading_twice_does_not_duplicate(self):
        from services import demo_data
        db = FakeDB(label="demo", demo_rows=70)
        with _Patched(db, demo_mode=True):
            self.assertEqual(demo_data.load_demo_data("Admin", ADMIN), {"status": "already_loaded"})
        self.assertEqual(db.inserted_runs, [])

    def test_removal_touches_only_demo_rows(self):
        from services import demo_data
        db = FakeDB(label="demo", demo_rows=70, ratings=20, reports=2)
        with _Patched(db, demo_mode=True):
            result = demo_data.remove_demo_data("Admin", ADMIN)
        self.assertEqual(result, {"status": "ok", "texts": 70, "ratings": 20, "reports": 2})
        for sql, params in db.deletes:
            if "pattern_reports" in sql:
                continue   # a demo database only holds reports made from demo texts
            self.assertIn("LIKE %s", sql)
            self.assertEqual(params, ("demo:%",))


# ---------------------------------------------------------------------
# Screens, translations, secrets
# ---------------------------------------------------------------------
DEMO_KEYS = (
    "demo_banner", "demo_banner_wrong_database", "demo_banner_real_app_on_demo",
    "admin_demo_header", "admin_demo_intro", "admin_demo_wrong_database", "admin_demo_failed",
    "admin_demo_counts", "admin_demo_load_button", "admin_demo_loaded",
    "admin_demo_already_loaded", "admin_demo_remove_note", "admin_demo_remove_button",
    "admin_demo_removed",
)


class ScreenTests(unittest.TestCase):
    def test_banner_on_every_page_and_label_at_startup(self):
        router = _read("navigation", "router.py")
        self.assertIn("render_database_banner(T)", router)
        self.assertLess(router.index("record_page_visit(page_name)\n    render_database_banner(T)"),
                        router.index("role = st.session_state.get(\"user_role\""))
        app = _read("app.py")
        self.assertLess(app.index("ensure_schema()"), app.index("label_database()"))

    def test_section_only_in_demo_mode_and_checks_in_the_service(self):
        section = _read("pages", "admin_sections", "demo_data.py")
        self.assertIn("if not demo_data.demo_mode_on():\n        return", section)
        self.assertIn("demo_data.may_use_demo_data(role)", section)
        admin = _read("pages", "system_administration.py")
        self.assertIn("demo_data.render(T)", admin)
        # (The no-tabs/columns/dataframe rule for every admin section is
        # checked in tests/test_data_reset.py.)

    def test_demo_mode_is_off_by_default(self):
        import os
        import config
        if "DEMO_MODE" not in os.environ:
            self.assertFalse(config.DEMO_MODE)

    def test_every_text_in_three_languages(self):
        for lang in ("es", "eu", "en"):
            texts = _load_locale(lang)
            for key in DEMO_KEYS:
                self.assertTrue(texts.get(key), f"{key} missing in {lang}")
            self.assertIn("{texts}", texts["admin_demo_counts"])
            self.assertIn("{ratings}", texts["admin_demo_counts"])
            self.assertIn("{reports}", texts["admin_demo_removed"])
        section = _read("pages", "admin_sections", "demo_data.py") + _read("navigation", "router.py")
        es = _load_locale("es")
        for key in re.findall(r'T\["([a-z_]+)"\]', section):
            self.assertIn(key, es, key)

    def test_no_password_or_hash_in_the_code(self):
        # The one allowed value is the login screen's deliberate dummy hash
        # (services/identity.py, used so an unknown username takes as long
        # to check as a real one); it belongs to no account.
        from services.identity import _DUMMY_HASH
        for path in ROOT.rglob("*"):
            if not path.is_file() or path.suffix not in (".py", ".md", ".toml", ".txt", ".yml"):
                continue
            if ".git" in path.parts or "tests" in path.parts:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            found = [m for m in re.findall(r"\$2[aby]\$\d\d\$[./A-Za-z0-9]{53}", text) if m != _DUMMY_HASH]
            self.assertEqual(found, [], str(path))

    def test_demo_texts_never_logged(self):
        source = _read("services", "demo_data.py")
        for call in re.findall(r"logger\.\w+\((?:.|\n)*?\)\n", source):
            for forbidden in ("text\"]", "row[", "original_text"):
                self.assertNotIn(forbidden, call)


if __name__ == "__main__":
    unittest.main()
