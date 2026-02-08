import re

from poetry_to_anki import build_notes


def test_windowed_cloze_centering():
    poem_text = "\n".join([f"Line {i}" for i in range(1, 16)])
    notes = build_notes(poem_text, shuffle_stanzas=False, wrap_lines=False)

    target_note = next(note for note in notes if note.fields[1] == "Stanza 1, Line 8")
    content = re.sub(r"</?div[^>]*>", "", target_note.fields[0])
    lines = content.split("\n")

    assert len(lines) == 13
    assert lines[0] == "Line 2"
    assert lines[6] == "{{c1::Line 8}}"


def test_windowed_cloze_near_end():
    poem_text = "\n".join([f"Line {i}" for i in range(1, 21)])
    notes = build_notes(poem_text, shuffle_stanzas=False, wrap_lines=False)

    target_note = next(note for note in notes if note.fields[1] == "Stanza 1, Line 20")
    content = re.sub(r"</?div[^>]*>", "", target_note.fields[0])
    lines = content.split("\n")

    assert len(lines) == 13
    assert lines[0] == "Line 8"
    assert lines[-1] == "{{c1::Line 20}}"
