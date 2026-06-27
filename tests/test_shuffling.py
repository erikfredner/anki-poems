import random
import re

from anki_poems import Config, NoteBuilder, build_notes, create_cloze_model


def test_word_level_notes_visit_each_word():
    poem_text = """Line 1
Line 2
Line 3

Line 4
Line 5"""

    notes = build_notes(poem_text, "Test Poem", "Test Author", shuffle_stanzas=True, wrap_lines=False)
    # 5 lines × 2 words each ("Line" and the number) = 10 notes
    assert len(notes) == 10

    # Collect (stanza, line, word) triples and verify all are present
    triples = set()
    for note in notes:
        match = re.match(r"Stanza (\d+), Line (\d+), Word (\d+)", note.fields[1])
        assert match is not None
        triples.add((int(match.group(1)), int(match.group(2)), int(match.group(3))))

    assert triples == {
        (1, 1, 1), (1, 1, 2),
        (1, 2, 1), (1, 2, 2),
        (1, 3, 1), (1, 3, 2),
        (2, 1, 1), (2, 1, 2),
        (2, 2, 1), (2, 2, 2),
    }

    # No pass: tags
    for note in notes:
        assert not any(tag.startswith("pass:") for tag in note.tags)


def test_shuffle_groups_clozes_by_window():
    # 30 single-word-pair lines, one stanza. With SHUFFLE_CHUNK_LINES=13, chunks are
    # lines 1-13, 14-26, 27-30 (global line index == line number - 1 here).
    poem_text = "\n".join(f"Line {i}" for i in range(1, 31))

    random.seed(7)
    notes = build_notes(poem_text, "Window Test", "Author", shuffle_stanzas=True, wrap_lines=False)

    line_order = []
    for note in notes:
        match = re.match(r"Stanza 1, Line (\d+)", note.fields[1])
        assert match is not None
        line_order.append(int(match.group(1)))

    # Each line contributes 2 word clozes -> chunk boundaries at 26 and 52.
    chunk1, chunk2, chunk3 = line_order[:26], line_order[26:52], line_order[52:]

    # Chunks stay in poem order and each holds exactly its window's lines.
    assert set(chunk1) == set(range(1, 14))
    assert set(chunk2) == set(range(14, 27))
    assert set(chunk3) == set(range(27, 31))

    # Within the first window, lines interleave instead of marching in order.
    assert chunk1 != sorted(chunk1)


def test_shuffled_guid_is_stable_across_random_order():
    poem_text = """Line 1
Line 2
Line 3

Line 4
Line 5"""

    random.seed(1)
    notes_seed_1 = build_notes(poem_text, "Stable Test", "Author", shuffle_stanzas=True, wrap_lines=False)
    random.seed(2)
    notes_seed_2 = build_notes(poem_text, "Stable Test", "Author", shuffle_stanzas=True, wrap_lines=False)

    guid_map_1 = {note.fields[1]: note.guid for note in notes_seed_1}
    guid_map_2 = {note.fields[1]: note.guid for note in notes_seed_2}
    assert guid_map_1 == guid_map_2


def test_multi_stanza_shuffle_visits_each_target_once():
    poem_text = """Line 1a
Line 1b

Line 2a
Line 2b"""

    builder = NoteBuilder(create_cloze_model())
    config = Config(shuffle_stanzas=True, wrap_lines=False, multi_stanza_cards=True)
    notes = builder.build_notes(poem_text, "Multi Test", "Author", config)

    multi_notes = [note for note in notes if "multi-stanza" in note.tags]
    assert len(multi_notes) == 4

    targets = set()
    for note in multi_notes:
        match = re.search(r"Line (\d+) \((first|second) stanza\)", note.fields[1])
        assert match is not None
        line_num = int(match.group(1))
        stanza_name = match.group(2)
        targets.add((stanza_name, line_num))

    assert targets == {
        ("first", 1),
        ("first", 2),
        ("second", 1),
        ("second", 2),
    }
