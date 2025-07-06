#!/usr/bin/env python
"""Simple test for poetry_to_anki.py functionality"""

from poetry_to_anki import parse_poem, build_notes, cloze_stanza

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
    
    # Check first note
    first_note = notes[0]
    assert "{{c1::Line 1}}" in first_note.fields[0]  # Cloze text
    assert first_note.fields[1] == "1.1"              # Line number
    assert first_note.fields[2] == "Test Poem"        # Title
    assert first_note.fields[3] == "Test Author"      # Author
    
    # Check tags
    assert "title:test-poem" in first_note.tags
    assert "author:test-author" in first_note.tags
    
    print("✓ Note building test passed")

if __name__ == "__main__":
    test_parse_poem()
    test_cloze_stanza()
    test_build_notes()
    print("\n🎉 All tests passed!")
