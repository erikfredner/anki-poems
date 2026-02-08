import pytest

from poetry_errors import FileProcessingError
from poetry_to_anki import parse_poem, parse_poem_with_metadata, wrap_long_lines


def test_parse_poem_stanzas():
    sample_text = """Line 1
Line 2

Line 3
Line 4

Line 5"""

    stanzas, line_groups = parse_poem(sample_text, wrap_lines=False)
    assert len(stanzas) == 3
    assert stanzas[0] == ["Line 1", "Line 2"]
    assert stanzas[1] == ["Line 3", "Line 4"]
    assert stanzas[2] == ["Line 5"]
    assert line_groups[0] == {0: 0, 1: 1}


def test_yaml_frontmatter_parsing():
    yaml_poem = """---
title: "The Test"
author: "Test Poet"
collection: "Test Collection"
year: 2024
---

Line 1
Line 2
"""

    metadata, content = parse_poem_with_metadata(yaml_poem)
    assert metadata["title"] == "The Test"
    assert metadata["author"] == "Test Poet"
    assert metadata["collection"] == "Test Collection"
    assert metadata["year"] == 2024
    assert content == "Line 1\nLine 2"


def test_unterminated_frontmatter_raises():
    bad_yaml = """---
title: "Broken"
author: "Nobody"

Line 1
Line 2
"""

    with pytest.raises(FileProcessingError, match="closing '---' is missing"):
        parse_poem_with_metadata(bad_yaml)


def test_wrap_long_lines_maps_logical_lines():
    wrapped, line_groups = wrap_long_lines(
        [
            "This is a very long line that should wrap at a small threshold",
            "Short line",
        ],
        max_length=20,
    )

    assert len(wrapped) > 2
    assert set(line_groups.values()) == {0, 1}
