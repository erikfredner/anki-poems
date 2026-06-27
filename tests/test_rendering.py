import re

from anki_poems import build_notes


def _poem_lines(field_text: str) -> list[str]:
    content = re.sub(r"</?div[^>]*>", "", field_text)
    return content.split("\n")


def test_full_poem_rendered_with_word_cloze():
    poem_text = "\n".join([f"Line {i}" for i in range(1, 16)])
    notes = build_notes(poem_text, shuffle_stanzas=False, wrap_lines=False)

    target_note = next(
        note for note in notes if re.match(r"Stanza 1, Line 8, Word 1", note.fields[1])
    )
    lines = _poem_lines(target_note.fields[0])

    # The entire 15-line poem is present, not a clipped window.
    assert len(lines) == 15
    assert lines[0] == "Line 1"
    assert lines[-1] == "Line 15"
    # Exactly one cloze, on line 8 (index 7), wrapping a single word.
    assert sum(bool(re.search(r"\{\{c1::\w+\}\}", ln)) for ln in lines) == 1
    assert re.search(r"\{\{c1::\w+\}\}", lines[7])
    assert lines[7].replace("{{c1::Line}}", "Line") == "Line 8"


def test_full_poem_rendered_for_last_line():
    poem_text = "\n".join([f"Line {i}" for i in range(1, 21)])
    notes = build_notes(poem_text, shuffle_stanzas=False, wrap_lines=False)

    target_note = next(
        note for note in notes if re.match(r"Stanza 1, Line 20, Word 1", note.fields[1])
    )
    lines = _poem_lines(target_note.fields[0])

    assert len(lines) == 20
    assert lines[0] == "Line 1"
    # The cloze sits on the final line.
    assert re.search(r"\{\{c1::\w+\}\}", lines[-1])
    assert sum(bool(re.search(r"\{\{c1::\w+\}\}", ln)) for ln in lines) == 1
