#!/usr/bin/env python
"""Simple test for poetry_to_anki.py functionality"""

from poetry_to_anki import parse_poem, build_notes, cloze_stanza, parse_poem_with_metadata, format_metadata_display

def test_parse_poem():
    """Test poem parsing with stanzas separated by blank lines."""
    sample_text = """Line 1
Line 2

Line 3
Line 4

Line 5"""
    
    stanzas = parse_poem(sample_text)
    assert len(stanzas) == 3, f"Expected 3 stanzas, got {len(stanzas)}"
    assert stanzas[0] == ["Line 1", "Line 2"]
    assert stanzas[1] == ["Line 3", "Line 4"] 
    assert stanzas[2] == ["Line 5"]
    print("✓ Poem parsing test passed")

def test_cloze_stanza():
    """Test cloze deletion creation."""
    lines = ["First line", "Second line", "Third line"]
    cloze = cloze_stanza(lines, 1)
    expected = "First line<br>{{c1::Second line}}<br>Third line"
    assert cloze == expected, f"Expected '{expected}', got '{cloze}'"
    print("✓ Cloze stanza test passed")

def test_build_notes():
    """Test note building from poem text."""
    poem_text = """Line 1
Line 2

Line 3
Line 4"""
    
    notes = build_notes(poem_text, "Test Poem", "Test Author")
    
    # Should have 4 notes total (2 lines per stanza × 2 stanzas)
    assert len(notes) == 4, f"Expected 4 notes, got {len(notes)}"
    
    # Check first note (updated field structure)
    first_note = notes[0]
    assert "{{c1::Line 1}}" in first_note.fields[0]  # Cloze text
    assert first_note.fields[1] == "1.1"              # Line number
    assert first_note.fields[2] == "Test Poem"        # Title
    assert first_note.fields[3] == "Test Author"      # Author
    # Metadata should contain the formatted display
    expected_metadata = '"Test Poem" by Test Author'
    actual_metadata = first_note.fields[4]
    assert actual_metadata == expected_metadata, f"Expected '{expected_metadata}', got '{actual_metadata}'"
    
    # Check tags
    assert "title:test-poem" in first_note.tags
    assert "author:test-author" in first_note.tags
    
    print("✓ Note building test passed")


def test_yaml_parsing():
    """Test YAML frontmatter parsing."""
    yaml_poem = '''---
title: "The Test"
author: "Test Poet"
collection: "Test Collection"
year: 2024
---

Line 1
Line 2

Line 3'''
    
    metadata, content = parse_poem_with_metadata(yaml_poem)
    assert metadata['title'] == "The Test"
    assert metadata['author'] == "Test Poet"
    assert metadata['collection'] == "Test Collection"
    assert metadata['year'] == 2024
    assert "Line 1" in content
    print("✓ YAML parsing test passed")


def test_metadata_formatting():
    """Test metadata display formatting."""
    metadata = {
        'title': 'Test Poem',
        'author': 'Test Author',
        'collection': 'Test Collection',
        'year': 1999
    }
    
    display = format_metadata_display(metadata)
    expected = '"Test Poem" by Test Author from <i>Test Collection</i> (1999)'
    assert display == expected, f"Expected '{expected}', got '{display}'"
    print("✓ Metadata formatting test passed")

if __name__ == "__main__":
    test_parse_poem()
    test_cloze_stanza()
    test_build_notes()
    test_yaml_parsing()
    test_metadata_formatting()
    print("\n🎉 All tests passed!")
