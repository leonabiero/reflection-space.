"""One type per passage, everywhere on the screen (26 November 2026).

The same passage of the text can be quoted by several of the eight lenses
and by the analysis report, and the AI does not always give it the same
type. In a test by the product owner, "aunque la familia no suele
implicarse" was "Estereotipo" (blue) in the analysis report but "Prejuicio"
(red) in the highlighted text, because each view took the type from a
different place.

This module is THE ONE PLACE that decides which type a passage shows. The
cards, the analysis report, the highlighted text and the download all use
its result, so a passage always has the same type and colour.

The rule (product owner, 26 November 2026):
  1. Two quotes are the same passage when they overlap in the anonymised
     text (a quote inside a longer quote counts too).
  2. If the analysis report quotes the passage, the report's type wins.
  3. Otherwise the type given by most lenses wins.
  4. If lenses are tied, the lens that comes first in the fixed card order
     wins (then the first quote in that lens), so the result is always
     the same.

Only the type (and so the label and colour) changes; the quotes and
everything the AI wrote are left as they are. A quote that cannot be found
in the text keeps its own type (it is not highlighted anyway). Nothing is
saved and no AI is called.
"""

import copy
from collections import Counter

from services.evidence import locate_quote, EVIDENCE_TYPES


def agree_types(text, lens_evidence, report):
    """
    `text`: the anonymised text the quotes come from.
    `lens_evidence`: the evidence lists of the lenses, IN CARD ORDER
        (each a list of {"quote", "type", ...}).
    `report`: the analysis report ({"items": [{"quote", "type", ...}]}) or
        None.

    Returns (lens_evidence, report): copies in which every quote of the
    same passage has the same type. The arguments are never changed.
    """
    lenses = [copy.deepcopy(list(ev or [])) for ev in (lens_evidence or [])]
    report = copy.deepcopy(report) if isinstance(report, dict) else report
    report_items = []
    if isinstance(report, dict) and isinstance(report.get("items"), list):
        report_items = report["items"]

    # Every typed quote that can be found in the text:
    # (start, end, type, is_report, lens_index, position, the dict to set)
    entries = []
    for pos, item in enumerate(report_items):
        _add(entries, text, item, True, -1, pos)
    for lens_index, evidence in enumerate(lenses):
        for pos, item in enumerate(evidence):
            _add(entries, text, item, False, lens_index, pos)

    for group in _overlapping_groups(entries):
        winner = _winning_type(group)
        for entry in group:
            entry[6]["type"] = winner

    return lenses, report


def _add(entries, text, item, is_report, lens_index, position):
    if not isinstance(item, dict) or item.get("type") not in EVIDENCE_TYPES:
        return
    found = locate_quote(item.get("quote"), text or "")
    if found:
        entries.append((found[0], found[1], item["type"], is_report, lens_index, position, item))


def _overlapping_groups(entries):
    """Entries joined when their passages overlap (directly or through a
    third quote)."""
    order = sorted(range(len(entries)), key=lambda i: (entries[i][0], entries[i][1]))
    groups, current, current_end = [], [], -1
    for i in order:
        start, end = entries[i][0], entries[i][1]
        if current and start < current_end:
            current.append(entries[i])
            current_end = max(current_end, end)
        else:
            if current:
                groups.append(current)
            current, current_end = [entries[i]], end
    if current:
        groups.append(current)
    return groups


def _winning_type(group):
    from_report = [e for e in group if e[3]]
    candidates = from_report or group
    counts = Counter(e[2] for e in candidates)
    best = max(counts.values())
    # Tie-break: report order for the report; card order, then position
    # in the card, for the lenses.
    for entry in sorted(candidates, key=lambda e: (e[4], e[5])):
        if counts[entry[2]] == best:
            return entry[2]
    return candidates[0][2]
