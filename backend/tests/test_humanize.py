"""
Unit tests for the humanization change-quota metric.

Runnable two ways:
    python backend/tests/test_humanize.py      # plain, no pytest needed
    python -m pytest backend/tests/test_humanize.py

The module under test is pure stdlib, so it is loaded directly by file path to
avoid importing the langgraph-heavy ``backend.runtime`` package for a metric test.
"""

import importlib.util
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_MOD = os.path.normpath(os.path.join(_HERE, "..", "runtime", "humanize.py"))
_spec = importlib.util.spec_from_file_location("humanize_under_test", _MOD)
h = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(h)

WORDS_200 = " ".join(f"word{i}" for i in range(200))
# Replace the first 80 of 200 words, keep the rest (length preserved).
EDIT_80 = " ".join(f"new{i}" for i in range(80)) + " " + " ".join(f"word{i}" for i in range(80, 200))
BLUEPRINT = {"sections": [
    {"name": "Introduction", "role": "body"},
    {"name": "Related Work", "role": "macro_lit_review"},
    {"name": "Abstract", "role": "front_matter"},
    {"name": "Conclusion", "role": "back_matter"},
    {"name": "References", "role": "back_matter"},
]}


def test_changed_words_extremes():
    assert h.changed_words(WORDS_200, WORDS_200) == 0
    assert h.changed_words(WORDS_200, "") == 200  # every original word deleted
    assert h.changed_words("", "brand new text") == 3
    assert h.changed_words(WORDS_200, EDIT_80) == 80


def test_required_changes():
    assert h.required_changes(WORDS_200, 0.40) == 80
    assert h.required_changes(" ".join(["w"] * 24), 0.40) == 0  # < 25 words exempt
    assert h.required_changes("", 0.40) == 0


def test_quota_met_and_length_floor():
    ok = h.section_stats("Introduction", WORDS_200, EDIT_80, 0.40, "body")
    assert ok["met"] and ok["length_ok"] and ok["required"] == 80 and ok["changed"] == 80

    # Delete-gaming: cut to 110 words (changed high) but below the 140 floor.
    deleted = " ".join(f"word{i}" for i in range(110))
    gamed = h.section_stats("Introduction", WORDS_200, deleted, 0.40, "body")
    assert gamed["changed"] >= 80 and not gamed["length_ok"] and not gamed["met"]


def test_editability_by_role():
    assert h.is_editable("body")
    assert h.is_editable("macro_lit_review")
    assert h.is_editable("micro_lit_review")
    assert not h.is_editable("front_matter")
    assert not h.is_editable("back_matter")
    assert not h.is_editable(None)
    # Non-editable sections are always "met" regardless of edits.
    assert h.section_stats("Abstract", WORDS_200, WORDS_200, 0.40, "front_matter")["met"]


def test_validate_quota():
    unedited = {"Introduction": WORDS_200, "Abstract": "a b c d e", "References": ""}
    fails = h.validate_quota(unedited, unedited, 0.40, BLUEPRINT)
    assert [f["name"] for f in fails] == ["Introduction"]

    edited = {"Introduction": EDIT_80, "Abstract": "a b c d e", "References": ""}
    assert h.validate_quota(unedited, edited, 0.40, BLUEPRINT) == []


def test_build_humanize_meta_roles():
    meta = h.build_humanize_meta(
        {"Introduction": WORDS_200, "Related Work": WORDS_200, "Abstract": "a b c", "References": ""},
        0.40,
        BLUEPRINT,
    )
    assert meta["fraction"] == 0.40
    assert meta["sections"]["Introduction"]["editable"] and meta["sections"]["Introduction"]["required"] == 80
    assert meta["sections"]["Related Work"]["editable"]
    assert not meta["sections"]["Abstract"]["editable"]
    assert not meta["sections"]["References"]["editable"]


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"ok  {t.__name__}")
    print(f"\n{len(tests)} passed")
