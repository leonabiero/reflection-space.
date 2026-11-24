"""
Text fingerprints -- one saved copy per case text (24 November 2026)
======================================================================

Product owner's decision: during testing the same practice text was
reflected several times and every copy was saved, so Pattern Review
counted it several times. From now on a case text that is IDENTICAL to
one already saved is not saved again (see REFLECTIONS.md, "One saved
copy per text").

"Identical" means the same words in the same order. Only these
differences are ignored:
  - extra spaces, tabs and line breaks (any run of them counts as one
    space; spaces at the start and end are ignored);
  - capital letters;
  - the way an accented letter is encoded (an "é" pasted from Word and an
    "é" typed on the keyboard can be stored differently but look the
    same; they count as the same letter).
Anything else -- one different word, a changed comma -- is a new text.
The language chosen for the reflection plays no part, and neither does
who wrote it: the check is across all users.

Privacy
-------
Duplicates are found by comparing a one-way coded fingerprint (SHA-256)
of the tidied text, never by keeping another copy of the text. The
fingerprint is stored in the same row as the original text
(reflection_runs.text_fingerprint), so it goes whenever the text goes:
the 15-month limit clears both (reflection_records.
purge_expired_original_text), and deleting a reflection or "Erase all
data" removes the whole row. Fingerprints and texts are never logged.
"""

import hashlib
import re
import unicodedata

from services.db_time import get_logger

logger = get_logger(__name__)

_WHITESPACE = re.compile(r"\s+")

# How many old rows are filled in per round by backfill_fingerprints().
_BACKFILL_BATCH = 200


def normalise_text(text):
    """The text as it is compared: accents encoded one way, every run of
    spaces / tabs / line breaks turned into one space, trimmed, lower
    case. "" for an empty or missing text."""
    if not text:
        return ""
    tidied = unicodedata.normalize("NFC", str(text))
    tidied = _WHITESPACE.sub(" ", tidied).strip()
    return tidied.lower()


def text_fingerprint(text):
    """The coded fingerprint of a case text (64 hexadecimal characters),
    or None for an empty text. Two texts get the same fingerprint only if
    they are identical apart from spacing, line breaks and capitals."""
    tidied = normalise_text(text)
    if not tidied:
        return None
    return hashlib.sha256(tidied.encode("utf-8")).hexdigest()


def backfill_fingerprints(conn):
    """Give a fingerprint to saved original texts that do not have one
    yet (texts saved before 24 November 2026). Safe to run again: it only
    touches rows still missing a fingerprint, in small rounds, and commits
    each round. Returns how many rows were filled in. Never logs text."""
    filled = 0
    last_id = 0
    while True:
        with conn.cursor() as c:
            c.execute(
                """
                SELECT id, original_text FROM reflection_runs
                WHERE text_fingerprint IS NULL
                  AND original_text IS NOT NULL
                  AND id > %s
                ORDER BY id
                LIMIT %s
                """,
                (last_id, _BACKFILL_BATCH),
            )
            rows = c.fetchall()
            if not rows:
                break
            for run_id, original in rows:
                last_id = run_id
                fingerprint = text_fingerprint(original)
                if fingerprint:
                    c.execute(
                        "UPDATE reflection_runs SET text_fingerprint = %s "
                        "WHERE id = %s AND text_fingerprint IS NULL",
                        (fingerprint, run_id),
                    )
                    filled += 1
        conn.commit()
    if filled:
        logger.info("Text fingerprints added to %d saved text(s)", filled)
    return filled
