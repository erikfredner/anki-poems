#!/usr/bin/env python
"""Simple test for poetry_to_anki.py functionality"""

from poetry_to_anki import parse_poem, build_notes, cloze_stanza, parse_poem_with_metadata, format_metadata_display, build_transition_notes

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
    
    # Test without transitions
    notes = build_notes(poem_text, "Test Poem", "Test Author", include_transitions=False)
    
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


def test_build_notes_with_transitions():
    """Test note building with transition cards."""
    poem_text = """Line 1
Line 2

Line 3
Line 4

Line 5
Line 6"""
    
    # Test with transitions (default)
    notes = build_notes(poem_text, "Test Poem", "Test Author", include_transitions=True)
    
    # Should have 6 line notes + 2 transition notes = 8 total
    assert len(notes) == 8, f"Expected 8 notes (6 line + 2 transition), got {len(notes)}"
    
    # Find transition notes (they should have the transition tag)
    transition_notes = [n for n in notes if "transition" in n.tags]
    assert len(transition_notes) == 2, f"Expected 2 transition notes, got {len(transition_notes)}"
    
    # Check first transition note
    first_transition = transition_notes[0]
    assert "Line 1<br>Line 2" in first_transition.fields[0]  # Previous lines
    assert "{{c1::Line 3}}" in first_transition.fields[1]    # Next line cloze
    assert first_transition.fields[2] == "1 → 2"             # Stanza numbers
    
    print("✓ Note building with transitions test passed")


def test_transition_notes():
    """Test transition note building specifically."""
    stanzas = [
        ["Line 1", "Line 2", "Line 3"],
        ["Line 4", "Line 5"],
        ["Line 6"]
    ]
    
    transition_notes = build_transition_notes(stanzas, "Test", "Author", '"Test" by Author')
    
    # Should have 2 transition notes (3 stanzas = 2 transitions)
    assert len(transition_notes) == 2, f"Expected 2 transition notes, got {len(transition_notes)}"
    
    # Check first transition (stanza 1 → 2)
    first = transition_notes[0]
    assert "Line 2<br>Line 3" in first.fields[0]  # Last 2 lines of first stanza
    assert "{{c1::Line 4}}" in first.fields[1]    # First line of second stanza
    assert first.fields[2] == "1 → 2"             # Stanza numbers
    
    # Check second transition (stanza 2 → 3)
    second = transition_notes[1]
    assert "Line 4<br>Line 5" in second.fields[0]  # All lines of second stanza (≤2 lines)
    assert "{{c1::Line 6}}" in second.fields[1]    # First line of third stanza
    assert second.fields[2] == "2 → 3"             # Stanza numbers
    
    print("✓ Transition notes test passed")


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
    test_build_notes_with_transitions()
    test_transition_notes()
    test_yaml_parsing()
    test_metadata_formatting()
    print("\n🎉 All tests passed!")
