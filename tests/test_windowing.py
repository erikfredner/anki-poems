import re

from anki_poems import build_notes


def test_windowed_cloze_centering():
    poem_text = "\n".join([f"Line {i}" for i in range(1, 16)])
    notes = build_notes(poem_text, shuffle_stanzas=False, wrap_lines=False)

    # With word-level cloze and no shuffle, Line 8 word 0 ("Line") is the first card for line 8
    target_note = next(
        note for note in notes if re.match(r"Stanza 1, Line 8, Word 1", note.fields[1])
    )
    content = re.sub(r"</?div[^>]*>", "", target_note.fields[0])
    lines = content.split("\n")

    assert len(lines) == 13
    assert lines[0] == "Line 2"
    # Line 8 should contain exactly one word-level cloze
    assert re.search(r"\{\{c1::\w+\}\}", lines[6])
    assert lines[6].replace("{{c1::Line}}", "Line") == "Line 8"


def test_windowed_cloze_near_end():
    poem_text = "\n".join([f"Line {i}" for i in range(1, 21)])
    notes = build_notes(poem_text, shuffle_stanzas=False, wrap_lines=False)

    target_note = next(
        note for note in notes if re.match(r"Stanza 1, Line 20, Word 1", note.fields[1])
    )
    content = re.sub(r"</?div[^>]*>", "", target_note.fields[0])
    lines = content.split("\n")

    assert len(lines) == 13
    assert lines[0] == "Line 8"
    assert re.search(r"\{\{c1::\w+\}\}", lines[-1])
