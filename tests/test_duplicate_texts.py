"""One saved copy per text (24 November 2026, product owner's decision).

A case text identical to one already saved (same words in the same order;
only spaces, line breaks and capital letters are ignored; any user, any
language) is not saved again. The person still gets their reflection and a
small note. Duplicates are found with a coded fingerprint, never with an
extra copy of the text; the fingerprint goes with its text; Pattern Review
counts each text once. See REFLECTIONS.md, "One saved copy per text".

These tests need no database. The real-database checks are in
test_duplicate_texts_postgres.py.
"""
import importlib.util
import re
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]

TEXT = "La usuaria vive sola.\nRefiere que no tiene apoyo familiar."


def _read(*parts):
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


def _load_locale(lang):
    spec = importlib.util.spec_from_file_location(f"dup_loc_{lang}", ROOT / "services" / "locales" / f"{lang}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return next(v for v in vars(module).values() if isinstance(v, dict) and "rs_finish_button" in v)


class FingerprintRulesTests(unittest.TestCase):
    def setUp(self):
        from services.text_fingerprint import text_fingerprint
        self.fp = text_fingerprint

    def test_identical_text_same_fingerprint(self):
        self.assertEqual(self.fp(TEXT), self.fp(TEXT))
        self.assertEqual(len(self.fp(TEXT)), 64)

    def test_spaces_line_breaks_and_capitals_ignored(self):
        variants = [
            "  " + TEXT + "  \n\n",
            TEXT.replace("\n", " "),
            TEXT.replace(" ", "   "),
            TEXT.replace(" ", "\t"),
            TEXT.replace("\n", "\r\n\r\n"),
            TEXT.replace(" ", " "),       # non-breaking space from Word
            TEXT.upper(),
            TEXT.lower(),
        ]
        for variant in variants:
            with self.subTest(variant=variant):
                self.assertEqual(self.fp(variant), self.fp(TEXT))

    def test_accent_encoding_ignored(self):
        composed = "Atención familiar"
        decomposed = "Atención familiar"   # "o" + combining accent
        self.assertNotEqual(composed, decomposed)
        self.assertEqual(self.fp(composed), self.fp(decomposed))

    def test_one_different_word_is_a_new_text(self):
        self.assertNotEqual(self.fp(TEXT), self.fp(TEXT.replace("sola", "acompañada")))
        self.assertNotEqual(self.fp(TEXT), self.fp(TEXT + " Fin."))

    def test_word_order_and_punctuation_count(self):
        self.assertNotEqual(self.fp("vive sola"), self.fp("sola vive"))
        self.assertNotEqual(self.fp(TEXT), self.fp(TEXT.replace(".", ",", 1)))

    def test_empty_text_has_no_fingerprint(self):
        for empty in ("", "   ", "\n\t", None):
            self.assertIsNone(self.fp(empty))

    def test_fingerprint_is_not_the_text(self):
        fingerprint = self.fp(TEXT)
        self.assertNotIn("usuaria", fingerprint)
        self.assertTrue(re.fullmatch(r"[0-9a-f]{64}", fingerprint))

    def test_language_and_user_play_no_part(self):
        # The fingerprint only takes the text: no language, no user.
        import inspect
        from services import text_fingerprint
        self.assertEqual(list(inspect.signature(text_fingerprint.text_fingerprint).parameters), ["text"])


# ---------------------------------------------------------------------
# The save step, with a fake database
# ---------------------------------------------------------------------
class _FakeCursor:
    def __init__(self, db):
        self.db = db
        self._row = None
        self.rowcount = 0

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=()):
        s = " ".join(sql.split())
        self.db.sql.append((s, params))
        if s.startswith("SELECT pg_advisory_xact_lock"):
            self._row = (None,)
        elif s.startswith("SELECT 1 FROM reflection_runs r WHERE r.text_fingerprint"):
            self._row = (1,) if params[0] in self.db.saved else None
        elif s.startswith("INSERT INTO reflection_runs"):
            self.db.inserted.append(params)
            self.db.saved.add(params[-1])
            self._row = (len(self.db.inserted),)
        else:
            self._row = None

    def fetchone(self):
        return self._row

    def fetchall(self):
        return []


class _FakeDb:
    def __init__(self):
        self.sql, self.inserted, self.saved = [], [], set()
        self.commits = self.rollbacks = 0

    def connect(self):
        db = self

        class _Conn:
            def cursor(self):
                return _FakeCursor(db)

            def commit(self):
                db.commits += 1

            def rollback(self):
                db.rollbacks += 1

            def close(self):
                pass

        return _Conn()


class SaveStepTests(unittest.TestCase):
    def setUp(self):
        from services import findings_store
        from services.text_fingerprint import text_fingerprint
        self.fs = findings_store
        self.fp = text_fingerprint
        self.db = _FakeDb()
        patcher = mock.patch.object(findings_store, "_get_conn", side_effect=self.db.connect)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _save(self, text, user="ana", language="Español", code="RS-AAAAAA"):
        return self.fs.save_reflection_run(
            case_ref=code, source_draft_ids=[], language=language, prompt_version="v",
            model="m", module_status={}, findings=[], created_by=user,
            created_by_role="Social Worker", reflection_code=code,
            original_text=text, text_fingerprint=self.fp(text),
        )

    def test_first_copy_saved_with_its_fingerprint(self):
        saved = self._save(TEXT)
        self.assertFalse(saved["duplicate"])
        self.assertEqual(saved["run_id"], 1)
        self.assertEqual(self.db.inserted[0][-1], self.fp(TEXT))
        self.assertEqual(self.db.inserted[0][-2], TEXT)

    def test_identical_text_not_saved_twice(self):
        self._save(TEXT)
        again = self._save(TEXT, code="RS-BBBBBB")
        self.assertEqual(again, {"run_id": None, "finding_ids": {}, "duplicate": True})
        self.assertEqual(len(self.db.inserted), 1)

    def test_spacing_and_capitals_variant_not_saved(self):
        self._save(TEXT)
        self.assertTrue(self._save("  " + TEXT.upper().replace("\n", "\n\n"))["duplicate"])
        self.assertEqual(len(self.db.inserted), 1)

    def test_one_different_word_is_saved(self):
        self._save(TEXT)
        self.assertFalse(self._save(TEXT.replace("sola", "acompañada"))["duplicate"])
        self.assertEqual(len(self.db.inserted), 2)

    def test_different_users_and_languages_still_one_copy(self):
        self._save(TEXT, user="ana", language="Español")
        self.assertTrue(self._save(TEXT, user="mikel", language="Euskara")["duplicate"])
        self.assertTrue(self._save(TEXT, user="jon", language="English")["duplicate"])
        self.assertEqual(len(self.db.inserted), 1)

    def test_check_locks_and_uses_the_usual_rules(self):
        self._save(TEXT)
        statements = [s for s, _ in self.db.sql]
        lock = next(i for i, s in enumerate(statements) if "pg_advisory_xact_lock" in s)
        check = next(i for i, s in enumerate(statements) if "r.text_fingerprint = %s" in s)
        insert = next(i for i, s in enumerate(statements) if s.startswith("INSERT INTO reflection_runs"))
        self.assertLess(lock, check)
        self.assertLess(check, insert)
        check_sql = statements[check]
        self.assertIn("r.deleted_at IS NULL", check_sql)          # 48-hour bin ignored
        self.assertIn("make_interval(months => %s)", check_sql)   # 15-month limit

    def test_no_fingerprint_without_text(self):
        saved = self.fs.save_reflection_run(
            case_ref="RS-CCCCCC", source_draft_ids=[], language="Español", prompt_version="v",
            model="m", module_status={}, findings=[], created_by="ana",
            original_text=None, text_fingerprint=self.fp(TEXT),
        )
        self.assertFalse(saved["duplicate"])
        self.assertIsNone(self.db.inserted[0][-1])
        self.assertFalse(any("pg_advisory_xact_lock" in s for s, _ in self.db.sql))

    def test_older_callers_without_fingerprint_unchanged(self):
        self.fs.save_reflection_run("RS-DDDDDD", [], "Español", "v", "m", {}, [], "ana",
                                    original_text=TEXT)
        self.fs.save_reflection_run("RS-EEEEEE", [], "Español", "v", "m", {}, [], "ana",
                                    original_text=TEXT)
        self.assertEqual(len(self.db.inserted), 2)


# ---------------------------------------------------------------------
# The fingerprint goes with its text; Pattern Review counts once
# ---------------------------------------------------------------------
class DeletionAndPatternReviewTests(unittest.TestCase):
    def test_fifteen_month_cleanup_clears_the_fingerprint(self):
        from services import reflection_records
        db = _FakeDb()
        with mock.patch.object(reflection_records, "_get_conn", side_effect=db.connect):
            reflection_records.purge_expired_original_text()
        sql = " ".join(s for s, _ in db.sql)
        self.assertIn("SET original_text = NULL, text_fingerprint = NULL", sql)

    def test_fingerprint_lives_in_the_reflection_row(self):
        # Deleting the row (48-hour bin purge, admin delete) or emptying the
        # table (Erase all data) therefore removes the fingerprint too.
        schema = _read("services", "db_schema.py")
        self.assertIn("ALTER TABLE reflection_runs ADD COLUMN IF NOT EXISTS text_fingerprint TEXT", schema)
        self.assertNotIn("CREATE TABLE IF NOT EXISTS text_fingerprints", schema)
        from services.data_reset import DATA_TABLES
        self.assertIn("reflection_runs", DATA_TABLES)
        self.assertIn("DELETE FROM reflection_runs WHERE id = ANY(%s)", _read("services", "reflection_records.py"))

    def test_pattern_review_counts_each_text_once(self):
        source = _read("services", "pattern_text_store.py")
        self.assertIn("COALESCE(r.text_fingerprint, 'run:' || r.id::text)", source)
        self.assertIn("SELECT COUNT(DISTINCT {_ONE_PER_TEXT})", source)
        self.assertIn("SELECT DISTINCT ON ({_ONE_PER_TEXT})", source)

    def test_pattern_review_reads_one_copy_with_fake_database(self):
        from services import pattern_text_store
        rows = [("English", "Second text.", 9), ("Español", TEXT, 4)]

        class _Cur(_FakeCursor):
            def fetchall(self_inner):
                return rows

        db = _FakeDb()
        conn = db.connect()
        conn.cursor = lambda: _Cur(db)
        with mock.patch.object(pattern_text_store, "_get_conn", return_value=conn):
            texts = pattern_text_store.texts_for_period("Supervisor", 3)
        # Saving order kept; only language and text are returned.
        self.assertEqual(texts, [{"language": "Español", "text": TEXT},
                                 {"language": "English", "text": "Second text."}])
        self.assertIn("DISTINCT ON", db.sql[0][0])

    def test_backfill_only_touches_rows_missing_a_fingerprint(self):
        from services.text_fingerprint import backfill_fingerprints, text_fingerprint
        batches = [[(1, TEXT), (2, "   ")], []]
        db = _FakeDb()

        class _Cur(_FakeCursor):
            def fetchall(self_inner):
                return batches.pop(0)

        conn = db.connect()
        conn.cursor = lambda: _Cur(db)
        self.assertEqual(backfill_fingerprints(conn), 1)
        select = db.sql[0][0]
        self.assertIn("text_fingerprint IS NULL", select)
        updates = [p for s, p in db.sql if s.startswith("UPDATE reflection_runs")]
        self.assertEqual(updates, [(text_fingerprint(TEXT), 1)])

    def test_texts_and_fingerprints_never_logged(self):
        for path in (("services", "text_fingerprint.py"), ("services", "findings_store.py")):
            source = _read(*path)
            for call in re.findall(r"logger\.\w+\((?:.|\n)*?\)\n", source):
                self.assertNotIn("original", call.split(",", 1)[-1])
                self.assertNotIn("fingerprint)", call)


# ---------------------------------------------------------------------
# The screen and the note
# ---------------------------------------------------------------------
class ScreenAndNoteTests(unittest.TestCase):
    def setUp(self):
        self.page = _read("pages", "reflection_space.py")

    def test_page_passes_the_fingerprint_of_the_original_text(self):
        self.assertIn("text_fingerprint(material) if SAVE_ORIGINAL_TEXT else None", self.page)
        self.assertIn('if saved.get("duplicate"):', self.page)
        self.assertIn("session.duplicate_not_saved = True", self.page)

    def test_note_is_shown_and_finish_caption_is_honest(self):
        self.assertGreaterEqual(self.page.count('T["rs_duplicate_not_saved_note"]'), 1)
        self.assertIn('T["rs_finish_caption_duplicate"]', self.page)

    def test_reflection_and_cost_records_still_happen(self):
        # The AI call and the activity record come before, and do not depend
        # on, the save step; usage records are made by the AI calls themselves.
        run = self.page.index("result = run_reflection(")
        log = self.page.index("log_reflection(reflection_code")
        save = self.page.index("saved = save_reflection_run(")
        self.assertLess(run, save)
        self.assertLess(log, save)

    def test_session_knows_about_duplicates(self):
        source = _read("rdi", "reflection_session.py")
        self.assertIn("self.duplicate_not_saved = False", source)

    def test_note_in_all_three_languages(self):
        texts = {lang: _load_locale(lang) for lang in ("es", "eu", "en")}
        for key in ("rs_duplicate_not_saved_note", "rs_finish_caption_duplicate"):
            values = [texts[lang][key] for lang in ("es", "eu", "en")]
            for value in values:
                self.assertTrue(value.strip())
                # Never reveals who saved it, when, or which reflection.
                self.assertNotIn("{", value)
            self.assertEqual(len(set(values)), 3, key)
        self.assertIn("already saved", texts["en"]["rs_duplicate_not_saved_note"])
        self.assertIn("ya estaba guardado", texts["es"]["rs_duplicate_not_saved_note"])
        self.assertIn("gordeta zegoen", texts["eu"]["rs_duplicate_not_saved_note"])

    def test_help_explains_it_in_all_three_languages(self):
        words = {"es": "huella", "eu": "hatz-marka", "en": "fingerprint"}
        for lang, word in words.items():
            points = _load_locale(lang)["help"]["privacy_points"]
            self.assertTrue(any(word in point for point in points), lang)


if __name__ == "__main__":
    unittest.main()
