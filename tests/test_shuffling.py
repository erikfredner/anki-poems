import random
import re

from poetry_to_anki import Config, NoteBuilder, build_notes, create_cloze_model


def test_shuffled_mode_visits_each_line_once_per_cycle():
    poem_text = """Line 1
Line 2
Line 3

Line 4
Line 5"""

    notes = build_notes(poem_text, "Test Poem", "Test Author", shuffle_stanzas=True, wrap_lines=False)
    assert len(notes) == 5

    stanza_to_lines = {1: [], 2: []}
    for note in notes:
        match = re.search(r"Stanza (\d+), Line (\d+)", note.fields[1])
        assert match is not None
        stanza = int(match.group(1))
        line = int(match.group(2))
        stanza_to_lines[stanza].append(line)

    assert sorted(stanza_to_lines[1]) == [1, 2, 3]
    assert sorted(stanza_to_lines[2]) == [1, 2]

    pass_counts = {}
    for note in notes:
        pass_tag = next(tag for tag in note.tags if tag.startswith("pass:"))
        pass_num = int(pass_tag.split(":", 1)[1])
        pass_counts[pass_num] = pass_counts.get(pass_num, 0) + 1

    assert pass_counts == {1: 2, 2: 2, 3: 1}


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
